from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from drivers.permissions import IsDriver

from .dispatch import (
    BUSY_STATUSES,
    OfferError,
    accept_offer,
    advance_ride,
    decline_offer,
)
from .lifecyle import RideError, cancel_ride, complete_ride, rate_ride, start_ride
from .models import ACTIVE_STATUSES, Ride, RideOffer
from .permissions import IsPassenger
from .pricing import quote
from .serializers import (
    OfferSerializer,
    PointsSerializer,
    RatingSerializer,
    RideCreateSerializer,
    RideSerializer,
)


def quote_from(data):
    return quote(
        data["origin_lat"], data["origin_lng"], data["dest_lat"], data["dest_lng"]
    )


def ride_data(ride, request):
    return RideSerializer(ride, context={"request": request}).data


def conflict(error):
    return Response({"detail": str(error)}, status=status.HTTP_409_CONFLICT)


class EstimateView(APIView):
    permission_classes = [IsPassenger]

    def post(self, request):
        serializer = PointsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(quote_from(serializer.validated_data))


class RideCreateView(APIView):
    permission_classes = [IsPassenger]

    def post(self, request):
        active = Ride.objects.filter(
            passenger=request.user, status__in=ACTIVE_STATUSES
        ).first()
        if active:
            active = advance_ride(active.pk)  # peut la passer en « aucun motard »
            if active.status in ACTIVE_STATUSES:
                return Response(
                    {
                        "detail": "Vous avez déjà une course en cours.",
                        "ride_id": active.id,
                    },
                    status=status.HTTP_409_CONFLICT,
                )

        serializer = RideCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        q = quote_from(data)
        ride = Ride.objects.create(
            passenger=request.user,
            origin_lat=data["origin_lat"],
            origin_lng=data["origin_lng"],
            dest_lat=data["dest_lat"],
            dest_lng=data["dest_lng"],
            dest_label=data["dest_label"],
            distance_km=q["distance_km"],
            price=q["price"],
            currency=q["currency"],
        )
        ride = advance_ride(ride.pk)  # envoie la première offre tout de suite
        return Response(ride_data(ride, request), status=status.HTTP_201_CREATED)


class RideDetailView(generics.RetrieveAPIView):
    serializer_class = RideSerializer
    permission_classes = [IsPassenger]

    def get_queryset(self):
        return Ride.objects.filter(passenger=self.request.user)

    def get_object(self):
        ride = super().get_object()
        return advance_ride(ride.pk)


class ActiveRideView(APIView):
    """Course active du passager : permet de la reprendre après un redémarrage."""

    permission_classes = [IsPassenger]

    def get(self, request):
        ride = Ride.objects.filter(
            passenger=request.user, status__in=ACTIVE_STATUSES
        ).first()
        if ride is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ride_data(advance_ride(ride.pk), request))


class ActiveDriverRideView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        ride = (
            Ride.objects.filter(driver=request.user, status__in=BUSY_STATUSES)
            .select_related("passenger")
            .first()
        )
        if ride is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(ride_data(ride, request))


class StartRideView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, pk):
        ride = get_object_or_404(Ride, pk=pk, driver=request.user)
        try:
            ride = start_ride(ride.pk, request.user)
        except RideError as error:
            return conflict(error)
        return Response(ride_data(ride, request))


class CompleteRideView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, pk):
        ride = get_object_or_404(Ride, pk=pk, driver=request.user)
        try:
            ride = complete_ride(ride.pk, request.user)
        except RideError as error:
            return conflict(error)
        return Response(ride_data(ride, request))


class CancelRideView(APIView):
    def post(self, request, pk):
        ride = get_object_or_404(
            Ride, Q(passenger=request.user) | Q(driver=request.user), pk=pk
        )
        try:
            ride = cancel_ride(ride.pk, request.user)
        except RideError as error:
            return conflict(error)
        return Response(ride_data(ride, request))


class RateRideView(APIView):
    permission_classes = [IsPassenger]

    def post(self, request, pk):
        ride = get_object_or_404(Ride, pk=pk, passenger=request.user)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            rating = rate_ride(
                ride.pk, request.user, serializer.validated_data["stars"]
            )
        except RideError as error:
            return conflict(error)
        return Response({"stars": rating.stars}, status=status.HTTP_201_CREATED)


class PendingOffersView(APIView):
    permission_classes = [IsDriver]

    def get(self, request):
        profile = getattr(request.user, "driver_profile", None)
        if profile is None or profile.latitude is None:
            return Response([])
        offers = RideOffer.objects.filter(
            driver=request.user,
            status=RideOffer.Status.PENDING,
            expires_at__gt=timezone.now(),
            ride__status=Ride.Status.SEARCHING,
        ).select_related("ride__passenger")
        serializer = OfferSerializer(
            offers,
            many=True,
            context={"driver_location": (profile.latitude, profile.longitude)},
        )
        return Response(serializer.data)


class OfferAcceptView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, pk):
        offer = get_object_or_404(RideOffer, pk=pk, driver=request.user)
        try:
            ride = accept_offer(offer, request.user)
        except OfferError as error:
            return conflict(error)
        return Response(ride_data(ride, request))


class OfferDeclineView(APIView):
    permission_classes = [IsDriver]

    def post(self, request, pk):
        offer = get_object_or_404(RideOffer, pk=pk, driver=request.user)
        try:
            decline_offer(offer)
        except OfferError as error:
            return conflict(error)
        return Response({"status": "declined"})
