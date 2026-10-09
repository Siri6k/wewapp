from rest_framework import serializers

from .models import DriverProfile


class DriverProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverProfile
        fields = [
            "plate",
            "is_online",
            "latitude",
            "longitude",
            "last_location_at",
            "rating_avg",
            "rides_count",
        ]
        read_only_fields = [
            "is_online",
            "latitude",
            "longitude",
            "last_location_at",
            "rating_avg",
            "rides_count",
        ]

    def validate_plate(self, value):
        return value.strip().upper()


class LocationSerializer(serializers.Serializer):
    latitude = serializers.FloatField(min_value=-90, max_value=90)
    longitude = serializers.FloatField(min_value=-180, max_value=180)
