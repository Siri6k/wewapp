from django.urls import path

from .views import (
    EstimateView,
    OfferAcceptView,
    OfferDeclineView,
    PendingOffersView,
    RideCreateView,
    RideDetailView,
)

app_name = "rides"
urlpatterns = [
    path("estimate/", EstimateView.as_view()),
    path("", RideCreateView.as_view()),
    path("<int:pk>/", RideDetailView.as_view()),
    path("driver/offers/pending/", PendingOffersView.as_view()),
    path("offers/<int:pk>/accept/", OfferAcceptView.as_view()),
    path("offers/<int:pk>/decline/", OfferDeclineView.as_view()),
]
