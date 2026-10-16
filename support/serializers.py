from django.db.models import Q
from rest_framework import serializers

from rides.models import Ride

from .models import Report

MAX_MESSAGE_LENGTH = 1000


class ReportCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=Report.Category.choices)
    message = serializers.CharField(min_length=5, max_length=MAX_MESSAGE_LENGTH)
    ride = serializers.IntegerField(required=False, allow_null=True)
    app_version = serializers.CharField(
        max_length=20, required=False, allow_blank=True, default=""
    )

    def validate_ride(self, ride_id):
        if ride_id is None:
            return None
        user = self.context["request"].user
        ride = (
            Ride.objects.filter(pk=ride_id)
            .filter(Q(passenger=user) | Q(driver=user))
            .first()
        )
        if ride is None:
            # Même message qu'il n'existe pas ou qu'elle ne vous concerne pas.
            raise serializers.ValidationError("Course introuvable.")
        return ride


class ReportSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(
        source="get_category_display", read_only=True
    )
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    ride = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Report
        fields = [
            "id",
            "category",
            "category_label",
            "message",
            "status",
            "status_label",
            "admin_response",
            "ride",
            "created_at",
            "responded_at",
        ]
        read_only_fields = fields
