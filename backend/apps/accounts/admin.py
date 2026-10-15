from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (("Profile", {"fields": ("organisation", "phone")}),)
    list_display = ("username", "email", "first_name", "last_name", "is_active", "is_superuser")
