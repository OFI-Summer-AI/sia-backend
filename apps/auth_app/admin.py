"""
Django admin configuration for the auth_app.
"""

from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = [
        "email", "full_name", "role", "tenant", "is_active",
        "email_confirmed", "last_login", "created_at",
    ]
    list_filter = ["role", "is_active", "email_confirmed"]
    search_fields = ["email", "full_name"]
    readonly_fields = ["id", "created_at", "updated_at", "last_login"]

    fieldsets = (
        ("Identity", {"fields": ("id", "email", "full_name", "phone", "avatar_url")}),
        ("Role & Tenant", {"fields": ("role", "tenant")}),
        ("Status", {"fields": ("is_active", "email_confirmed")}),
        ("Timestamps", {"fields": ("last_login", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
