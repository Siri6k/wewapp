from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class PricingConfig(models.Model):
    currency = models.CharField(max_length=3, default="CDF")
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=1000)
    price_per_km = models.DecimalField(max_digits=10, decimal_places=2, default=500)
    min_fare = models.DecimalField(max_digits=10, decimal_places=2, default=1500)
    rounding_step = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=100,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def get_active(cls):
        return cls.objects.order_by("-id").first() or cls.objects.create()

    def __str__(self):
        return f"{self.base_fare} + {self.price_per_km}/km ({self.currency})"


class Ride(models.Model):
    class Status(models.TextChoices):
        SEARCHING = "searching", "Recherche d'un motard"
        ACCEPTED = "accepted", "Acceptée"
        IN_PROGRESS = "in_progress", "En cours"
        COMPLETED = "completed", "Terminée"
        CANCELLED = "cancelled", "Annulée"
        NO_DRIVER = "no_driver", "Aucun motard disponible"

    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="rides_as_passenger",
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="rides_as_driver",
    )
    origin_lat = models.FloatField()
    origin_lng = models.FloatField()
    dest_lat = models.FloatField()
    dest_lng = models.FloatField()
    dest_label = models.CharField(max_length=120, blank=True)
    distance_km = models.DecimalField(max_digits=6, decimal_places=2)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.SEARCHING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Course {self.pk} ({self.status})"


ACTIVE_STATUSES = [Ride.Status.SEARCHING, Ride.Status.ACCEPTED, Ride.Status.IN_PROGRESS]
