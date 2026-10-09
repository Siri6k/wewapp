from django.contrib import admin

from .models import DriverProfile


@admin.register(DriverProfile)
class DriverProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "plate",
        "is_online",
        "last_location_at",
        "rating_avg",
        "rides_count",
    )
    list_filter = ("is_online",)
    search_fields = ("user__name", "user__phone", "plate")
