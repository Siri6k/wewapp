from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ACTIVE_STATUSES, Ride
from .permissions import IsPassenger
from .pricing import quote
from .serializers import PointsSerializer, RideCreateSerializer, RideSerializer


def quote_from(data):
    return quote(
        data["origin_lat"], data["origin_lng"], data["dest_lat"], data["dest_lng"]
    )


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
            return Response(
                {"detail": "Vous avez déjà une course en cours.", "ride_id": active.id},
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
        return Response(RideSerializer(ride).data, status=status.HTTP_201_CREATED)


class RideDetailView(generics.RetrieveAPIView):
    serializer_class = RideSerializer
    permission_classes = [IsPassenger]

    def get_queryset(self):
        return Ride.objects.filter(passenger=self.request.user)
