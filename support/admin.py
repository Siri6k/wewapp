from django.contrib import admin
from django.utils import timezone

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "category",
        "status",
        "user_name",
        "user_phone",
        "ride",
        "response_delay",
    )
    list_filter = ("status", "category")
    search_fields = ("user__phone", "user__name", "message")
    list_select_related = ("user", "ride")
    readonly_fields = (
        "user",
        "ride",
        "category",
        "message",
        "app_version",
        "created_at",
        "responded_at",
    )
    fields = (
        "user",
        "ride",
        "category",
        "message",
        "app_version",
        "created_at",
        "status",
        "admin_response",
        "responded_at",
    )

    @admin.display(description="Utilisateur")
    def user_name(self, report):
        return report.user.name

    @admin.display(description="Téléphone")
    def user_phone(self, report):
        return report.user.phone

    @admin.display(description="Délai de réponse")
    def response_delay(self, report):
        if not report.responded_at:
            return "—"
        minutes = int((report.responded_at - report.created_at).total_seconds() // 60)
        return f"{minutes} min"

    def save_model(self, request, obj, form, change):
        # On note l'heure de la première réponse, pour mesurer le délai réel.
        if obj.admin_response.strip() and obj.responded_at is None:
            obj.responded_at = timezone.now()
        super().save_model(request, obj, form, change)
