from django.contrib import admin

from .models import PricingConfig, Ride


@admin.register(PricingConfig)
class PricingConfigAdmin(admin.ModelAdmin):
    list_display = (
        "currency",
        "base_fare",
        "price_per_km",
        "min_fare",
        "rounding_step",
        "updated_at",
    )

    def has_add_permission(self, request):
        return not PricingConfig.objects.exists()


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "passenger",
        "driver",
        "status",
        "price",
        "currency",
        "created_at",
    )
    list_filter = ("status",)
