"""URL routes for batches."""

from django.urls import path

from . import views

urlpatterns = [
    path("batches/", views.BatchListCreateView.as_view(), name="batch-list"),
    path(
        "batches/<int:pk>/",
        views.BatchDetailView.as_view(),
        name="batch-detail",
    ),
]
