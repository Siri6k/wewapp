from django.urls import path

from .views import EstimateView, RideCreateView, RideDetailView

app_name = "rides"
urlpatterns = [
    path("estimate/", EstimateView.as_view()),
    path("", RideCreateView.as_view()),
    path("<int:pk>/", RideDetailView.as_view()),
]
