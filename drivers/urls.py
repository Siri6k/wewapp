from django.urls import path

from .views import LocationView, OfflineView, OnlineView, ProfileView

urlpatterns = [
    path("driver/profile/", ProfileView.as_view()),
    path("driver/online/", OnlineView.as_view()),
    path("driver/offline/", OfflineView.as_view()),
    path("driver/location/", LocationView.as_view()),
]
