from django.db import models
from django.utils.timezone import now
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.core.validators import RegexValidator
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
    def create_user(
        self, username, mobile_number, email=None, password=None, **extra_fields
    ):
        if not username:
            raise ValueError("The Username field must be set")
        if not mobile_number:
            raise ValueError("The Mobile Number field must be set")
        email = self.normalize_email(email) if email else None
        user = self.model(
            username=username, mobile_number=mobile_number, email=email, **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, username, mobile_number, email=None, password=None, **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(
            username, mobile_number, email, password, **extra_fields
        )


class FinUser(AbstractBaseUser):
    username = models.CharField(max_length=150, unique=True)
    name = models.CharField(max_length=150, blank=True)
    # mobile_number = models.CharField(
    #     max_length=15,
    #     unique=True,
    #     validators=[RegexValidator(r"^\+?\d{10,15}$", "Enter a valid mobile number.")],
    # )
    email = models.EmailField(unique=True, blank=True, null=True, default=None)
    date_joined = models.DateTimeField(auto_now_add=True, editable=False)
    is_active = models.BooleanField(default=True)
    # is_staff = models.BooleanField(default=False)
    # is_superuser = models.BooleanField(default=False)

    objects = FinUserManager()

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"@{self.username}"

    # def has_perm(self, perm, obj=None):
    #     return self.is_staff or self.is_superuser

    # def has_module_perms(self, app_label):
    #     return self.is_staff or self.is_superuser


class Expense(models.Model):
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
        ("Other", "Other"),
    ]

    user = models.ForeignKey(FinUser, on_delete=models.CASCADE, related_name="expenses")
    category = models.CharField(max_length=255, choices=CATEGORY_CHOICES, db_index=True)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    date = models.DateField(default=now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False)
    month = models.PositiveIntegerField(default=current_month, db_index=True)
    year = models.PositiveIntegerField(default=current_year, db_index=True)

    objects = models.Manager()  # Default manager
    active_objects = ActiveExpenseManager()  # Only returns non-deleted records

    def __str__(self):
        return f"{self.user.username} - {self.category} - {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        if self.amount < 0:
            raise ValidationError("Expense amount cannot be negative.")
        if self.category not in dict(self.CATEGORY_CHOICES):
            raise ValidationError("Invalid expense category.")
        super().save(*args, **kwargs)


class Income(models.Model):
    INCOME_SOURCES = [
        ("Salary", "Salary"),
        ("Bonus", "Bonus"),
        ("Award", "Award"),
        ("Refund", "Refund"),
        ("Interest", "Interest"),
        ("Dividends", "Dividends"),
        ("Freelance", "Freelance"),
        ("Business", "Business"),
        ("Other", "Other"),
    ]

    user = models.ForeignKey(FinUser, on_delete=models.CASCADE, related_name="incomes")
    source = models.CharField(max_length=255, choices=INCOME_SOURCES, db_index=True)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, db_index=True)
    date = models.DateField(default=now, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)
    is_deleted = models.BooleanField(default=False)
    month = models.PositiveIntegerField(default=current_month, db_index=True)
    year = models.PositiveIntegerField(default=current_year, db_index=True)

    objects = models.Manager()  # Default manager
    active_objects = ActiveIncomeManager()  # Only returns non-deleted records

    def __str__(self):
        return f"{self.user.username} - {self.source} - {self.amount} on {self.date}"

    def save(self, *args, **kwargs):
        if self.amount < 0:
            raise ValidationError("Income amount cannot be negative.")
        if self.source not in dict(self.INCOME_SOURCES):
            raise ValidationError("Invalid income source.")
        super().save(*args, **kwargs)
