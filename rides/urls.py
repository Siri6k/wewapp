from django.urls import path

from .views import (
    EstimateView,
    OfferAcceptView,
    OfferDeclineView,
    PendingOffersView,
    RideCreateView,
    RideDetailView,
    ActiveDriverRideView,
    ActiveRideView,
    CancelRideView,
    CompleteRideView,
    RateRideView,
    StartRideView,
)

app_name = "rides"
urlpatterns = [
    path("estimate/", EstimateView.as_view()),
    path("", RideCreateView.as_view()),
    path("<int:pk>/", RideDetailView.as_view()),
    path("driver/offers/pending/", PendingOffersView.as_view()),
    path("offers/<int:pk>/accept/", OfferAcceptView.as_view()),
    path("offers/<int:pk>/decline/", OfferDeclineView.as_view()),
    path("active/", ActiveRideView.as_view()),
    path("driver/active/", ActiveDriverRideView.as_view()),
    path("<int:pk>/start/", StartRideView.as_view()),
    path("<int:pk>/complete/", CompleteRideView.as_view()),
    path("<int:pk>/cancel/", CancelRideView.as_view()),
    path("<int:pk>/rating/", RateRideView.as_view()),
]
