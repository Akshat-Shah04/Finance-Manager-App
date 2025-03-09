from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from django.db.models import Q
from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
import logging
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from .models import Expense, Income
from .serializers import ExpenseSerializer, IncomeSerializer, UserSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


# Custom Pagination
class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


# --- Helper functions for filtering, sorting, and pagination ---
def apply_filters(queryset, params, field_name, lookup="iexact"):
    value = params.get(field_name)
    if value:
        lookup_expr = f"{field_name}__{lookup}"
        return queryset.filter(**{lookup_expr: value})
    return queryset


def apply_date_filters(queryset, params):
    start_date = params.get("start_date")
    end_date = params.get("end_date")
    if start_date:
        queryset = queryset.filter(date__gte=parse_date(start_date))
    if end_date:
        queryset = queryset.filter(date__lte=parse_date(end_date))
    return queryset


def apply_search_filter(queryset, params, fields):
    search_query = params.get("search")
    if search_query:
        query = Q()
        for field in fields:
            query |= Q(**{f"{field}__icontains": search_query})
        queryset = queryset.filter(query)
    return queryset


def apply_sorting(queryset, params, valid_fields):
    sort_by = params.get("sort_by", "date")
    order = params.get("order", "desc")
    if sort_by not in valid_fields:
        return None, Response(
            {"error": "Invalid sort field"}, status=status.HTTP_400_BAD_REQUEST
        )
    sort_by = f"-{sort_by}" if order == "desc" else sort_by
    return queryset.order_by(sort_by), None


def paginate_queryset(queryset, request):
    paginator = CustomPagination()
    paginated = paginator.paginate_queryset(queryset, request)
    return paginated, paginator


# --- User API Views ---
class UserListCreateView(generics.ListCreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]


class UserDetailView(generics.RetrieveUpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


# --- Expense-Income Analysis ---
@login_required
def expense_income_analysis(request):
    user = request.user
    # Filter expenses and incomes for the user and date range
    expenses = Expense.objects.filter(user=user)
    incomes = Income.objects.filter(user=user)
    expenses = apply_date_filters(expenses, request.GET)
    incomes = apply_date_filters(incomes, request.GET)

    # Use only necessary fields for analysis
    expenses_vals = expenses.values("amount", "category", "date")
    incomes_vals = incomes.values("amount", "source", "date")

    if not expenses_vals and not incomes_vals:
        return JsonResponse({"error": "No financial data found"}, status=404)

    df_expense = pd.DataFrame(expenses_vals)
    df_income = pd.DataFrame(incomes_vals)

    if not df_expense.empty:
        df_expense["date"] = pd.to_datetime(df_expense["date"])
        df_expense["month"] = df_expense["date"].dt.strftime("%Y-%m")
    if not df_income.empty:
        df_income["date"] = pd.to_datetime(df_income["date"])
        df_income["month"] = df_income["date"].dt.strftime("%Y-%m")

    total_expenses = df_expense["amount"].sum() if not df_expense.empty else 0
    total_income = df_income["amount"].sum() if not df_income.empty else 0
    monthly_expenses = (
        df_expense.groupby("month")["amount"].sum().to_dict()
        if not df_expense.empty
        else {}
    )
    monthly_income = (
        df_income.groupby("month")["amount"].sum().to_dict()
        if not df_income.empty
        else {}
    )
    category_expenses = (
        df_expense.groupby("category")["amount"].sum().to_dict()
        if not df_expense.empty
        else {}
    )

    # Generate Bar Chart for Monthly Income vs. Expenses
    img = io.BytesIO()
    plt.figure(figsize=(8, 5))
    sns.set(style="whitegrid")
    df_plot = pd.DataFrame(
        {"Income": monthly_income, "Expense": monthly_expenses}
    ).fillna(0)
    df_plot.plot(kind="bar", figsize=(8, 5))
    plt.title("Monthly Income vs. Expenses")
    plt.xlabel("Month")
    plt.ylabel("Amount")
    plt.legend()
    plt.savefig(img, format="png")
    img.seek(0)
    monthly_chart_url = (
        f"data:image/png;base64,{base64.b64encode(img.getvalue()).decode()}"
    )

    # Generate Pie Chart for Expense Categories
    img = io.BytesIO()
    plt.figure(figsize=(6, 6))
    if category_expenses:
        plt.pie(
            list(category_expenses.values()),
            labels=list(category_expenses.keys()),
            autopct="%1.1f%%",
            colors=sns.color_palette("pastel"),
        )
        plt.title("Expense Breakdown by Category")
        plt.savefig(img, format="png")
        img.seek(0)
        category_chart_url = (
            f"data:image/png;base64,{base64.b64encode(img.getvalue()).decode()}"
        )
    else:
        category_chart_url = None

    return JsonResponse(
        {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "monthly_income": monthly_income,
            "monthly_expenses": monthly_expenses,
            "category_expenses": category_expenses,
            "monthly_chart": monthly_chart_url,
            "category_chart": category_chart_url,
        }
    )


# --- Expense List & Create API ---
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def expense_list(request):
    try:
        expenses = Expense.objects.filter(user=request.user)
        expenses = apply_date_filters(expenses, request.GET)
        expenses = apply_filters(expenses, request.GET, "category", "iexact")
        expenses = apply_search_filter(
            expenses, request.GET, ["description", "category"]
        )

        sorted_qs, error_response = apply_sorting(
            expenses, request.GET, ["date", "amount"]
        )
        if error_response:
            return error_response

        paginated_expenses, paginator = paginate_queryset(sorted_qs, request)
        serializer = ExpenseSerializer(paginated_expenses, many=True)
        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        logger.error(f"Error in expense_list: {str(e)}")
        return Response(
            {"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Expense Detail API (Retrieve, Update, Delete) ---
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def expense_detail(request, pk):
    try:
        expense = get_object_or_404(Expense, pk=pk, user=request.user)

        if request.method == "GET":
            serializer = ExpenseSerializer(expense)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = ExpenseSerializer(expense, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == "DELETE":
            # Soft delete: mark the expense as deleted instead of removing it
            expense.is_deleted = True
            expense.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error in expense_detail: {str(e)}")
        return Response(
            {"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Income List & Create API ---
@api_view(["GET", "POST"])
@permission_classes([permissions.IsAuthenticated])
def income_list(request):
    try:
        incomes = Income.objects.filter(user=request.user)
        incomes = apply_date_filters(incomes, request.GET)
        incomes = apply_filters(incomes, request.GET, "source", "iexact")
        incomes = apply_search_filter(incomes, request.GET, ["description", "source"])

        sorted_qs, error_response = apply_sorting(
            incomes, request.GET, ["date", "amount"]
        )
        if error_response:
            return error_response

        paginated_incomes, paginator = paginate_queryset(sorted_qs, request)
        serializer = IncomeSerializer(paginated_incomes, many=True)
        return paginator.get_paginated_response(serializer.data)

    except Exception as e:
        logger.error(f"Error in income_list: {str(e)}")
        return Response(
            {"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


# --- Income Detail API (Retrieve, Update, Delete) ---
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([permissions.IsAuthenticated])
def income_detail(request, pk):
    try:
        income = get_object_or_404(Income, pk=pk, user=request.user)

        if request.method == "GET":
            serializer = IncomeSerializer(income)
            return Response(serializer.data)
        elif request.method == "PUT":
            serializer = IncomeSerializer(income, data=request.data)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        elif request.method == "DELETE":
            # Soft delete: mark the income as deleted instead of removing it
            income.is_deleted = True
            income.save()
            return Response(status=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        logger.error(f"Error in income_detail: {str(e)}")
        return Response(
            {"error": "An error occurred"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

