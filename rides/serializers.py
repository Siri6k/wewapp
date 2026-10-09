from rest_framework import serializers

from .geo import haversine_km
from .models import Ride

MIN_DISTANCE_KM = 0.1


class PointsSerializer(serializers.Serializer):
    origin_lat = serializers.FloatField(min_value=-90, max_value=90)
    origin_lng = serializers.FloatField(min_value=-180, max_value=180)
    dest_lat = serializers.FloatField(min_value=-90, max_value=90)
    dest_lng = serializers.FloatField(min_value=-180, max_value=180)

    def validate(self, attrs):
        distance = haversine_km(
            attrs["origin_lat"],
            attrs["origin_lng"],
            attrs["dest_lat"],
            attrs["dest_lng"],
        )
        if distance < MIN_DISTANCE_KM:
            raise serializers.ValidationError(
                "La destination est trop proche du départ."
            )
        return attrs


class RideCreateSerializer(PointsSerializer):
    dest_label = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )


class RideSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ride
        fields = [
            "id",
            "status",
            "origin_lat",
            "origin_lng",
            "dest_lat",
            "dest_lng",
            "dest_label",
            "distance_km",
            "price",
            "currency",
            "created_at",
        ]
        read_only_fields = fields
