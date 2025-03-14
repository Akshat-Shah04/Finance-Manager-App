from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError


def current_month():
    return now().month


def current_year():
    return now().year


# Custom manager for filtering out soft-deleted records
class ActiveExpenseManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class ActiveIncomeManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class FinUserManager(BaseUserManager):
    def create_user(self, username, email=None, password=None, **extra_fields):
        if not username:
            raise ValueError("The Username field must be set")
        email = self.normalize_email(email) if email else None
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(username, email, password, **extra_fields)


class FinUser(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True, blank=False)
    name = models.CharField(max_length=150, blank=True)
    email = models.EmailField(unique=True, blank=True, null=True)
    date_joined = models.DateTimeField(auto_now_add=True, editable=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    objects = FinUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"@{self.username}"

    def has_perm(self, perm, obj=None):
        return self.is_staff or self.is_superuser

    def has_module_perms(self, app_label):
        return self.is_staff or self.is_superuser


class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ("Income", "Income"),
        ("Expense", "Expense"),
    ]

    CATEGORY_CHOICES = [
        ("Food", "Food"),
        ("Shopping", "Shopping"),
        ("Bills", "Bills"),
        ("Entertainment", "Entertainment"),
        ("Insurance", "Insurance"),
        ("Rent", "Rent"),
        ("Travel", "Travel"),
        ("Education", "Education"),
        ("Gifts", "Gifts"),
        ("Fuel", "Fuel"),
        ("Loans", "Loans"),
        ("Investment", "Investment"),
        ("Health", "Health"),
        ("Salary", "Salary"),
        ("Bonus", "Bonus"),
        ("Refund", "Refund"),
        ("Interest", "Interest"),
        ("Dividend", "Dividend"),
        ("Cash Deposit", "Cash Deposit"),
        ("Other", "Other"),
    ]

    PAYMENT_MODES = [
        ("UPI", "UPI"),
        ("IMPS", "IMPS"),
        ("NEFT", "NEFT"),
        ("Net Banking", "Net Banking"),
        ("Debit Card", "Debit Card"),
        ("Credit Card", "Credit Card"),
        ("ATM Withdrawal", "ATM Withdrawal"),
        ("Cash", "Cash"),
        ("Cheque", "Cheque"),
        ("Other", "Other"),
    ]

    user = models.ForeignKey(
        FinUser, on_delete=models.CASCADE, related_name="transactions"
    )
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES, db_index=True)
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, db_index=True, default="Other"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
        db_index=True,
    )
    date = models.DateField(default=now, db_index=True)
    payment_mode = models.CharField(
        max_length=50, choices=PAYMENT_MODES, db_index=True, default="Other"
    )
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False)

    objects = models.Manager()  # Default manager

    def save(self, *args, **kwargs):
        """Ensure expenses are stored as negative amounts and income as positive."""
        if self.type == "Expense" and self.amount > 0:
            self.amount = -self.amount
        elif self.type == "Income" and self.amount < 0:
            self.amount = abs(self.amount)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """Soft delete a transaction instead of actually deleting it."""
        self.is_deleted = True
        self.save()

    def __str__(self):
        return f"{self.user.username} - {self.type} - {self.amount} on {self.date}"
