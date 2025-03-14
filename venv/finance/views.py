from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum, Q
from django.utils.timezone import now
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO
import base64
from .models import *
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .serializers import *
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from datetime import datetime
from rest_framework_simplejwt.tokens import RefreshToken


# ================================
# User Authentication Views
# ================================
@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    print("Received Data:", request.data)  # Debugging

    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully"})

    print("Errors:", serializer.errors)  # Debugging
    return Response(serializer.errors, status=400)


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)

    if user:
        tokens = RefreshToken.for_user(user)
        login(request, user)
        return JsonResponse(
            {
                "message": "Login successful",
                "access": str(tokens.access_token),
                "refresh": str(tokens),
            }
        )
    return Response({"error": "Invalid credentials"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_logout(request):
    try:
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response({"error": "Refresh token required"}, status=400)

        token = RefreshToken(refresh_token)
        token.blacklist()  # Blacklist the refresh token

        return Response({"message": "Logout successful"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)


# ================================
# CRUD Operations for Transactions
# ================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_transaction(request):
    serializer = TransactionSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    transaction.is_deleted = True
    transaction.save()
    return Response({"message": "Transaction deleted successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_transactions(request):
    transactions = Transaction.objects.filter(user=request.user, is_deleted=False).only(
        "id", "type", "category", "amount", "date", "payment_mode"
    )
    serializer = TransactionSerializer(transactions, many=True)
    return Response(serializer.data)


# ================================
# Analytics & Insights
# ================================

from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import base64
from io import BytesIO
from django.http import JsonResponse
from .models import Transaction


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_summary(request):
    total_expense = (
        Transaction.objects.filter(
            user=request.user, type="expense", is_deleted=False
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    total_income = (
        Transaction.objects.filter(
            user=request.user, type="income", is_deleted=False
        ).aggregate(Sum("amount"))["amount__sum"]
        or 0
    )
    balance = total_income - total_expense

    return Response(
        {
            "total_expense": total_expense,
            "total_income": total_income,
            "balance": balance,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_categories(request):
    categories = [
        {"key": key, "value": value} for key, value in Transaction.CATEGORY_CHOICES
    ]
    return JsonResponse({"categories": categories})


# ================================
# Data Visualization & ML Insights
# ================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_expense_trends(request):
    transactions = Transaction.objects.filter(
        user=request.user, type="expense", is_deleted=False
    ).only("amount", "date")

    if not transactions.exists():
        return Response({"error": "No expense data available"}, status=404)

    df = pd.DataFrame(list(transactions.values("amount", "date")))
    df["date"] = pd.to_datetime(df["date"])
    df.set_index("date", inplace=True)
    df = df.resample("M").sum()

    plt.figure(figsize=(10, 5))
    sns.lineplot(data=df, x=df.index, y="amount", marker="o", label="Monthly Expense")
    plt.title("Expense Trends Over Time")
    plt.xlabel("Month")
    plt.ylabel("Amount")
    plt.grid()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    encoded_image = base64.b64encode(buffer.getvalue()).decode()
    return Response({"chart": encoded_image})


# ================================
# Import & Export Transactions
# ================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_transactions_xlsx(request):
    transactions = Transaction.objects.filter(
        user=request.user, is_deleted=False
    ).values("type", "category", "description", "amount", "date")

    df = pd.DataFrame(list(transactions))

    response = HttpResponse(
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    response["Content-Disposition"] = "attachment; filename=transactions.xlsx"
    df.to_excel(response, index=False)
    return response


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_transactions_pdf(request):
    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=transactions.pdf"

    p = canvas.Canvas(response, pagesize=letter)
    p.drawString(100, 750, "Transactions Report")

    transactions = Transaction.objects.filter(user=request.user, is_deleted=False)
    y = 720

    for transaction in transactions:
        p.drawString(
            100, y, f"{transaction.category}: {transaction.amount} ({transaction.type})"
        )
        y -= 20

    p.showPage()
    p.save()
    return response


def detect_bank_format(df):
    """Detects the bank format based on column names."""
    bank_formats = {
        "ICICI": [
            "Date",
            "Narration",
            "Withdrawal Amount",
            "Deposit Amount",
            "Balance",
        ],
        "SBI": ["Txn Date", "Description", "Debit", "Credit", "Balance"],
        "HDFC": ["Date", "Particulars", "Withdrawals", "Deposits", "Balance"],
        "Axis": [
            "Transaction Date",
            "Transaction Details",
            "Debit Amount",
            "Credit Amount",
            "Balance",
        ],
    }

    for bank, columns in bank_formats.items():
        if all(col in df.columns for col in columns):
            return bank
    return None


def process_transactions(df, bank, user):
    """Processes the transactions and saves them in the Transaction model."""
    transactions = []

    for _, row in df.iterrows():
        date_col = next(
            (
                col
                for col in ["Date", "Txn Date", "Transaction Date"]
                if col in df.columns
            ),
            None,
        )
        desc_col = next(
            (
                col
                for col in ["Narration", "Description", "Transaction Details"]
                if col in df.columns
            ),
            None,
        )
        debit_col = next(
            (
                col
                for col in ["Withdrawal Amount", "Debit", "Withdrawals", "Debit Amount"]
                if col in df.columns
            ),
            None,
        )
        credit_col = next(
            (
                col
                for col in ["Deposit Amount", "Credit", "Deposits", "Credit Amount"]
                if col in df.columns
            ),
            None,
        )

        date = datetime.strptime(str(row[date_col]), "%d/%m/%Y") if date_col else None
        description = row[desc_col] if desc_col else "Unknown Transaction"
        amount = row[debit_col] if pd.notna(row[debit_col]) else row[credit_col]
        transaction_type = "expense" if pd.notna(row[debit_col]) else "income"

        transactions.append(
            Transaction(
                user=user,
                type=transaction_type,
                category="Bank Transaction",
                description=description,
                amount=amount,
                date=date,
            )
        )

    Transaction.objects.bulk_create(transactions)
    return len(transactions)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_transactions(request):
    """Handles file upload and imports transactions."""
    if "file" not in request.FILES:
        return JsonResponse({"error": "No file uploaded."}, status=400)

    file = request.FILES["file"]

    try:
        if file.name.endswith(".csv"):
            df = pd.read_csv(file)
        elif file.name.endswith(".xlsx"):
            df = pd.read_excel(file)
        else:
            return JsonResponse(
                {"error": "Invalid file format. Upload CSV or XLSX."}, status=400
            )

        bank = detect_bank_format(df)
        if not bank:
            return JsonResponse(
                {"error": "Unsupported bank statement format."}, status=400
            )

        total_imported = process_transactions(df, bank, request.user)
        return JsonResponse(
            {
                "message": f"Successfully imported {total_imported} transactions from {bank}."
            }
        )

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)


# ================================
# Budget Alert System
# ================================


def check_budget_limit(user):
    try:
        budget_limit = user.profile.budget_limit
    except AttributeError:
        return None

    if budget_limit:
        total_expense = (
            Transaction.objects.filter(
                user=user,
                type="expense",
                is_deleted=False,
                month=now().month,
                year=now().year,
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        if total_expense >= budget_limit:
            return (
                f"Alert: You have reached your monthly budget limit of {budget_limit}!"
            )

    return None


@login_required
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_budget_alert(request):
    alert_message = check_budget_limit(request.user)
    return JsonResponse({"alert": alert_message if alert_message else "Within budget"})
