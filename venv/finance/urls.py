from django.urls import path
from .views import (
    register,
    user_login,
    user_logout,
    add_expense,
    delete_expense,
    get_expenses,
    add_income,
    delete_income,
    get_income,
    get_summary,
    generate_expense_trends,
    export_transactions_xlsx,
    export_transactions_pdf,
    get_budget_alert,
    import_transactions,
)

urlpatterns = [
    # User Authentication
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    # Expense URLs
    path("expenses/add/", add_expense, name="add_expense"),
    path("expenses/delete/<int:expense_id>/", delete_expense, name="delete_expense"),
    path("expenses/", get_expenses, name="get_expenses"),
    # Income URLs
    path("income/add/", add_income, name="add_income"),
    path("income/delete/<int:income_id>/", delete_income, name="delete_income"),
    path("income/", get_income, name="get_income"),
    # Summary & Insights
    path("summary/", get_summary, name="get_summary"),
    path("expense-trends/", generate_expense_trends, name="generate_expense_trends"),
    # Export Features
    path("export/xlsx/", export_transactions_xlsx, name="export_transactions_xlsx"),
    path("export/pdf/", export_transactions_pdf, name="export_transactions_pdf"),
    # Import Transactions (Bank Statements)
    path("import-transactions/", import_transactions, name="import_transactions"),
    # Budget Alerts
    path("budget-alert/", get_budget_alert, name="get_budget_alert"),
]
