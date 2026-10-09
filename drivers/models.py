from django.conf import settings
from django.db import models


class DriverProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="driver_profile",
    )
    plate = models.CharField(max_length=20, blank=True)
    is_online = models.BooleanField(default=False)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    last_location_at = models.DateTimeField(null=True, blank=True)
    rating_avg = models.FloatField(default=0)
    rides_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.user.name} ({self.plate or 'sans plaque'})"
