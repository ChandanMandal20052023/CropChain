from django.urls import path

from . import views

urlpatterns = [
    # Traceability events for a specific batch.
    path(
        "batches/<str:batch_code>/events/",
        views.BatchEventListCreate.as_view(),
        name="batch-events",
    ),
]
