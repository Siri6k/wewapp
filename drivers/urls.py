from django.urls import path


from .views import LocationView, OfflineView, OnlineView, ProfileView

app_name = "drivers"
urlpatterns = [
    path("profile/", ProfileView.as_view()),
    path("online/", OnlineView.as_view()),
    path("offline/", OfflineView.as_view()),
    path("location/", LocationView.as_view()),
]
