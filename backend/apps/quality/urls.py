from django.urls import path

from . import views

urlpatterns = [
    # Certificates for a specific batch.
    path(
        "batches/<str:batch_code>/certificates/",
        views.BatchCertificateListCreate.as_view(),
        name="batch-certificates",
    ),
    # Verify an uploaded certificate by its stored hash.
    path(
        "certificates/<int:pk>/verify/",
        views.CertificateVerifyView.as_view(),
        name="certificate-verify",
    ),
]
