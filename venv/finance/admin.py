from django.contrib import admin
from .models import Expense,Income,FinUser

# Register your models here.
admin.site.register(Expense)
admin.site.register(Income)
admin.site.register(FinUser)

