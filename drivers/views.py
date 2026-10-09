from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DriverProfile
from .permissions import IsDriver
from .serializers import DriverProfileSerializer, LocationSerializer


def get_profile(user):
    profile, _ = DriverProfile.objects.get_or_create(user=user)
    return profile


def save_location(profile, data):
    profile.latitude = data["latitude"]
    profile.longitude = data["longitude"]
    profile.last_location_at = timezone.now()


class ProfileView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        return Response(DriverProfileSerializer(get_profile(request.user)).data)

    def patch(self, request):
        serializer = DriverProfileSerializer(
            get_profile(request.user), data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OnlineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        profile = get_profile(request.user)
        if not profile.plate:
            return Response(
                {"detail": "Renseignez votre plaque avant de passer en ligne."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        location = LocationSerializer(data=request.data)
        location.is_valid(raise_exception=True)
        save_location(profile, location.validated_data)
        profile.is_online = True
        profile.save()
        return Response(DriverProfileSerializer(profile).data)


class OfflineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        profile = get_profile(request.user)
        profile.is_online = False
        profile.save()
        return Response(DriverProfileSerializer(profile).data)


class LocationView(APIView):
    permission_classes = [IsDriver]

    def post(self, request):
        profile = get_profile(request.user)
        if not profile.is_online:
            return Response(
                {"detail": "Vous êtes hors ligne."}, status=status.HTTP_409_CONFLICT
            )
        location = LocationSerializer(data=request.data)
        location.is_valid(raise_exception=True)
        save_location(profile, location.validated_data)
        profile.save()
        return Response(DriverProfileSerializer(profile).data)
