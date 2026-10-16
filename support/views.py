from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle

from .models import Report
from .serializers import ReportCreateSerializer, ReportSerializer


class ReportListCreateView(generics.ListCreateAPIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "reports"

    def get_throttles(self):
        # La limite ne s'applique qu'à l'envoi, pas à la consultation.
        if self.request.method == "POST":
            return super().get_throttles()
        return []

    def get_queryset(self):
        return Report.objects.filter(user=self.request.user).select_related("ride")[:50]

    def get_serializer_class(self):
        return (
            ReportCreateSerializer
            if self.request.method == "POST"
            else ReportSerializer
        )

    def create(self, request, *args, **kwargs):
        serializer = ReportCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        report = Report.objects.create(
            user=request.user,
            ride=data.get("ride"),
            category=data["category"],
            message=data["message"],
            app_version=data["app_version"],
        )
        return Response(ReportSerializer(report).data, status=status.HTTP_201_CREATED)
