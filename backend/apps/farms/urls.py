"""URL routes for farms."""

from django.urls import path

from . import views

urlpatterns = [
    path("farms/", views.FarmListCreateView.as_view(), name="farm-list"),
    path(
        "farms/<int:pk>/",
        views.FarmDetailView.as_view(),
        name="farm-detail",
    ),
]
