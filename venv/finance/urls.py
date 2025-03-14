from django.urls import path
from .views import (
    register,
    user_login,
    user_logout,
    get_transactions,
    delete_transaction,
    add_transaction,
    get_summary,
    generate_expense_trends,
    export_transactions_xlsx,
    export_transactions_pdf,
    get_budget_alert,
    get_categories,
    import_transactions,
)

urlpatterns = [
    # User Authentication
    path("register/", register, name="register"),
    path("login/", user_login, name="login"),
    path("logout/", user_logout, name="logout"),
    # Transactions
    path("transactions/add/", add_transaction, name="add_transaction"),
    path(
        "transactions/delete/<int:transaction_id>/",
        delete_transaction,
        name="delete_transaction",
    ),
    path("transactions/", get_transactions, name="get_transactions"),
    path("categories/", get_categories, name="get_categories"),
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
