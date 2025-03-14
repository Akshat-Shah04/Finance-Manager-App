from .models import Transaction
from rest_framework import serializers
from django.contrib.auth import get_user_model
from decimal import Decimal

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "password"]
        read_only_fields = ["id"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)  # Hash password
        return user


# ✅ Common Transaction Serializer (For Income & Expense)
class TransactionSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # Read-only user field
    date = serializers.DateField(
        format="%d-%m-%Y", input_formats=["%d-%m-%Y", "iso-8601"]
    )
    amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    type = serializers.ChoiceField(choices=Transaction.TRANSACTION_TYPES)
    category = serializers.ChoiceField(choices=Transaction.CATEGORY_CHOICES)
    payment_mode = serializers.ChoiceField(choices=Transaction.PAYMENT_MODES)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "user",
            "type",
            "category",
            "date",
            "amount",
            "payment_mode",
            "description",
        ]

    def validate_amount(self, value):
        """Ensure amount follows correct sign based on transaction type."""
        transaction_type = self.initial_data.get("type", "").capitalize()

        if transaction_type == "Expense" and value > 0:
            return -value  # Convert to negative for expenses
        elif transaction_type == "Income" and value < 0:
            return abs(value)  # Convert to positive for income

        return value


# ✅ Aggregated Data Serializers


# 1️⃣ Transaction Summary (Total Per Category)
class TransactionSummarySerializer(serializers.Serializer):
    category = serializers.CharField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# 2️⃣ Monthly Transaction Summary
class MonthlyTransactionSerializer(serializers.Serializer):
    month = serializers.CharField()  # "January", "February", etc.
    year = serializers.IntegerField()
    total_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# ✅ Matplotlib Graph Serializer (For Chart APIs)
class ChartSerializer(serializers.Serializer):
    chart = serializers.CharField()  # Base64 Encoded Image String
