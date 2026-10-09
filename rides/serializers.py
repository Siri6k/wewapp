from django.utils import timezone
from rest_framework import serializers

from .geo import haversine_km
from .models import Ride, RideOffer

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
    driver = serializers.SerializerMethodField()

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
            "driver",
        ]
        read_only_fields = fields

    def get_driver(self, ride):
        if ride.driver_id is None:
            return None
        profile = getattr(ride.driver, "driver_profile", None)
        return {
            "name": ride.driver.name,
            "phone": ride.driver.phone,
            "plate": profile.plate if profile else "",
        }


class OfferSerializer(serializers.ModelSerializer):
    ride = serializers.SerializerMethodField()
    passenger_name = serializers.SerializerMethodField()
    pickup_distance_km = serializers.SerializerMethodField()
    seconds_left = serializers.SerializerMethodField()

    class Meta:
        model = RideOffer
        fields = [
            "id",
            "expires_at",
            "seconds_left",
            "passenger_name",
            "pickup_distance_km",
            "ride",
        ]
        read_only_fields = fields

    def get_ride(self, offer):
        ride = offer.ride
        return {
            "id": ride.id,
            "origin_lat": ride.origin_lat,
            "origin_lng": ride.origin_lng,
            "dest_lat": ride.dest_lat,
            "dest_lng": ride.dest_lng,
            "dest_label": ride.dest_label,
            "distance_km": ride.distance_km,
            "price": ride.price,
            "currency": ride.currency,
        }

    def get_passenger_name(self, offer):
        return offer.ride.passenger.name

    def get_pickup_distance_km(self, offer):
        lat, lng = self.context["driver_location"]
        return round(
            haversine_km(lat, lng, offer.ride.origin_lat, offer.ride.origin_lng), 2
        )

    def get_seconds_left(self, offer):
        return max(0, int((offer.expires_at - timezone.now()).total_seconds()))
