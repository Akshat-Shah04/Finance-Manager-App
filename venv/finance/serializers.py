from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Expense, Income
from decimal import Decimal

User = get_user_model()


# ✅ User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email"]
        read_only_fields = ["id"]


# ✅ Common Transaction Serializer (For Expense & Income)
class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # Read-only user field
    date = serializers.DateField(
        format="%d-%m-%Y", input_formats=["%d-%m-%Y", "iso-8601"]
    )
    amount = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )

    class Meta:
        fields = ["id", "user", "date", "amount", "description"]


# ✅ Expense Serializer
class ExpenseSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        model = Expense
        fields = TransactionSerializer.Meta.fields + ["category"]


# ✅ Income Serializer
class IncomeSerializer(TransactionSerializer):
    class Meta(TransactionSerializer.Meta):
        model = Income
        fields = TransactionSerializer.Meta.fields + ["source"]


# ✅ Aggregated Data Serializers


# 1️⃣ Expense Summary (Total Per Category)
class ExpenseSummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# 2️⃣ Income Summary (Total Per Source)
class IncomeSummarySerializer(serializers.Serializer):
    source = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# 3️⃣ Monthly Expense Summary
class MonthlyExpenseSerializer(serializers.Serializer):
    month = serializers.CharField()  # "January", "February", etc.
    year = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# 4️⃣ Monthly Income Summary
class MonthlyIncomeSerializer(serializers.Serializer):
    month = serializers.CharField()
    year = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# ✅ Matplotlib Graph Serializer (If Needed for Chart APIs)
class ChartSerializer(serializers.Serializer):
    chart = serializers.CharField()  # Base64 Encoded Image String
