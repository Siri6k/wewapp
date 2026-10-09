from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import BaseUserCreationForm

from .models import User


class UserCreationForm(BaseUserCreationForm):
    class Meta:
        model = User
        fields = ("phone", "name", "role")


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = UserCreationForm
    ordering = ("phone",)
    list_display = ("phone", "name", "role", "cancellation_count", "is_active")
    list_filter = ("role", "is_active")
    search_fields = ("phone", "name")
    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Profil", {"fields": ("name", "role", "cancellation_count")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone", "name", "role", "password1", "password2"),
            },
        ),
    )
