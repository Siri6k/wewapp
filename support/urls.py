from django.urls import path

from .views import ReportListCreateView

app_name = "support"
urlpatterns = [
    path("", ReportListCreateView.as_view()),
]
