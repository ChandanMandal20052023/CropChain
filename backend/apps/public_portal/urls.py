from django.urls import path

from . import views

urlpatterns = [
    # Public batch passport / QR tracking endpoint.
    path(
        "public/track/<str:batch_code>/",
        views.BatchPublicTrackView.as_view(),
        name="public-track",
    ),
]
