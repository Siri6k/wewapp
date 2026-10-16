from django.conf import settings
from django.db import models


class Report(models.Model):
    class Category(models.TextChoices):
        PRICE = "price", "Prix différent du prix affiché"
        BEHAVIOR = "behavior", "Comportement de l'autre personne"
        NO_SHOW = "no_show", "Motard ou passager absent"
        SAFETY = "safety", "Problème de sécurité"
        BUG = "bug", "Bug de l'application"
        SUGGESTION = "suggestion", "Suggestion"
        OTHER = "other", "Autre"

    class Status(models.TextChoices):
        OPEN = "open", "Ouvert"
        IN_PROGRESS = "in_progress", "En cours de traitement"
        RESOLVED = "resolved", "Résolu"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reports"
    )
    ride = models.ForeignKey(
        "rides.Ride",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reports",
    )
    category = models.CharField(max_length=12, choices=Category.choices)
    message = models.TextField()
    app_version = models.CharField(max_length=20, blank=True)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.OPEN
    )
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Signalement {self.pk} ({self.get_category_display()})"
