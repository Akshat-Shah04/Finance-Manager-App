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
from .models import FinUser, Expense, Income
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from .serializers import ExpenseSerializer, IncomeSerializer, UserSerializer
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import JsonResponse
from datetime import datetime



# ================================
# User Authentication Views
# ================================


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    serializer = UserSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response({"message": "User registered successfully"})
    return Response(serializer.errors, status=400)


@csrf_protect
@api_view(["POST"])
@permission_classes([AllowAny])
def user_login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(username=username, password=password)

    if user:
        login(request, user)
        return Response({"message": "Login successful"})
    return Response({"error": "Invalid credentials"}, status=400)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def user_logout(request):
    logout(request)
    return Response({"message": "Logged out successfully"})


# ================================
# CRUD Operations for Expense
# ================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_expense(request):
    serializer = ExpenseSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_expense(request, expense_id):
    expense = get_object_or_404(Expense, id=expense_id, user=request.user)
    expense.is_deleted = True
    expense.save()
    return Response({"message": "Expense deleted successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_expenses(request):
    expenses = Expense.objects.filter(user=request.user, is_deleted=False).only(
        "id", "category", "amount", "date"
    )
    serializer = ExpenseSerializer(expenses, many=True)
    return Response(serializer.data)


# ================================
# CRUD Operations for Income
# ================================


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_income(request):
    serializer = IncomeSerializer(data=request.data, context={"request": request})
    if serializer.is_valid():
        serializer.save(user=request.user)
        return Response(serializer.data, status=201)
    return Response(serializer.errors, status=400)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_income(request, income_id):
    income = get_object_or_404(Income, id=income_id, user=request.user)
    income.is_deleted = True
    income.save()
    return Response({"message": "Income deleted successfully"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_income(request):
    incomes = Income.objects.filter(user=request.user, is_deleted=False).only(
        "id", "source", "amount", "date"
    )
    serializer = IncomeSerializer(incomes, many=True)
    return Response(serializer.data)


# ================================
# Analytics & Insights
# ================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_summary(request):
    total_expense = (
        Expense.objects.filter(user=request.user, is_deleted=False).aggregate(
            Sum("amount")
        )["amount__sum"]
        or 0
    )
    total_income = (
        Income.objects.filter(user=request.user, is_deleted=False).aggregate(
            Sum("amount")
        )["amount__sum"]
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


# ================================
# Data Visualization & ML Insights
# ================================


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_expense_trends(request):
    expenses = Expense.objects.filter(user=request.user, is_deleted=False).only(
        "amount", "date"
    )
    if not expenses.exists():
        return Response({"error": "No expense data available"}, status=404)

    df = pd.DataFrame(list(expenses.values("amount", "date")))
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
    transactions = list(
        Expense.objects.filter(user=request.user, is_deleted=False).values(
            "category", "amount", "date"
        )
    ) + list(
        Income.objects.filter(user=request.user, is_deleted=False).values(
            "source", "amount", "date"
        )
    )
    df = pd.DataFrame(transactions)
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
    transactions = Expense.objects.filter(
        user=request.user, is_deleted=False
    ) | Income.objects.filter(user=request.user, is_deleted=False)
    y = 720
    for transaction in transactions:
        p.drawString(
            100,
            y,
            f"{transaction.category if hasattr(transaction, 'category') else transaction.source}: {transaction.amount}",
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
    """Processes the transactions and saves them as Expense or Income."""
    transactions = []

    for _, row in df.iterrows():
        if bank in ["ICICI", "SBI", "HDFC", "Axis"]:
            date_col = (
                "Date"
                if "Date" in row
                else "Txn Date" if "Txn Date" in row else "Transaction Date"
            )
            desc_col = (
                "Narration"
                if "Narration" in row
                else "Description" if "Description" in row else "Transaction Details"
            )
            debit_col = (
                "Withdrawal Amount"
                if "Withdrawal Amount" in row
                else (
                    "Debit"
                    if "Debit" in row
                    else "Withdrawals" if "Withdrawals" in row else "Debit Amount"
                )
            )
            credit_col = (
                "Deposit Amount"
                if "Deposit Amount" in row
                else (
                    "Credit"
                    if "Credit" in row
                    else "Deposits" if "Deposits" in row else "Credit Amount"
                )
            )

            date = datetime.strptime(str(row[date_col]), "%d/%m/%Y")
            description = row[desc_col]
            amount = row[debit_col] if pd.notna(row[debit_col]) else row[credit_col]

            if pd.notna(row[debit_col]):  # Expense
                transactions.append(
                    Expense(
                        user=user,
                        category="Bank Transaction",
                        description=description,
                        amount=amount,
                        date=date,
                    )
                )
            elif pd.notna(row[credit_col]):  # Income
                transactions.append(
                    Income(
                        user=user,
                        source="Bank Deposit",
                        description=description,
                        amount=amount,
                        date=date,
                    )
                )

    Expense.objects.bulk_create([t for t in transactions if isinstance(t, Expense)])
    Income.objects.bulk_create([t for t in transactions if isinstance(t, Income)])
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
        total_expense = Expense.objects.filter(
            user=user, is_deleted=False, month=now().month, year=now().year
        ).aggregate(total=Sum("amount"))["total"]
        if total_expense and total_expense >= budget_limit:
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
