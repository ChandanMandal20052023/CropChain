"""API views for quality inspection and certificate management."""

import hashlib
import os
from datetime import date

from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsVerified, role_required
from apps.audit.models import AuditLog
from apps.audit.permissions import IsAuditAdmin
from apps.batches.models import Batch
from apps.batches.permissions import IsBatchOwnerOrAdmin

from .models import Certificate
from .permissions import IsCertificateOwnerOrAdmin


# Filetypes a browser may sniff; we trust actual content, not these names.
ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff"}
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


class BatchCertificateListCreate(generics.ListCreateAPIView):
    """List or upload certificates for a batch."""

    permission_classes = [IsVerified(), IsBatchOwnerOrAdmin]
    queryset = Certificate.objects.all()
    page_size = 50

    def get_queryset(self):
        batch = self.get_batch()
        if isinstance(batch, Response):
            return batch
        return Certificate.objects.filter(batch=batch)

    def get_batch(self):
        batch_code = self.kwargs["batch_code"]
        try:
            return (
                Batch.objects.select_related("farm", "farm__owner", "created_by")
                .get(batch_code=batch_code)
            )
        except Batch.DoesNotExist:
            return Response(
                {"detail": "Batch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        batch = self.get_batch()
        if isinstance(batch, Response):
            return
        certificate = serializer.save(batch=batch, issued_by=self.request.user)
        AuditLog.objects.log(
            request=self.request,
            actor=self.request.user,
            action="quality.certificate.created",
            entity_type="batch",
            entity_id=batch.batch_code,
            metadata={"certificate_id": certificate.pk, "certificate_type": certificate.certificate_type},
        )


class CertificateSerializer:
    """Serialize a quality certificate for API responses."""

    def __init__(self, cert, request=None):
        self.cert = cert
        self.request = request

    def _public_filename(self):
        # Expose only the relative storage path, never a filesystem path.
        if self.cert.storage_path:
            return os.path.basename(self.cert.storage_path)
        return ""

    def data(self):
        original_name = (
            self.cert.original_name if self.cert.original_name else ""
        )
        return {
            "id": self.cert.pk,
            "batch_code": self.cert.batch.batch_code,
            "certificate_type": self.cert.certificate_type,
            "issued_by": {
                "id": self.cert.issued_by.pk,
                "email": self.cert.issued_by.email,
                "role": self.cert.issued_by.role,
            },
            "organization": self.cert.organization,
            "certificate_file": self._public_filename(),
            "original_file_name": original_name,
            "issue_date": self.cert.issue_date.isoformat() if self.cert.issue_date else None,
            "sha256": self.cert.sha256,
            "created_at": self.cert.created_at,
            "updated_at": self.cert.updated_at,
        }


class CertificateFileView(APIView):
    """Download a certificate file by ID (authenticated, authorized)."""

    permission_classes = [IsAuthenticated, IsCertificateOwnerOrAdmin]

    def get(self, request, pk):
        try:
            cert = Certificate.objects.get(pk=pk)
        except Certificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not cert.storage_path:
            return Response(
                {"detail": "No certificate file stored."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Resolve to a filename only; the storage backend decides the real
        # location. We never expose absolute filesystem paths.
        from django.core.files.storage import storages

        try:
            with storages["default"].open(cert.storage_path, "rb") as fh:
                content = fh.read()
        except FileNotFoundError:
            return Response(
                {"detail": "Certificate file is no longer available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {"file": content.decode("latin-1") if False else content.decode("utf-8", errors="replace")},
            status=status.HTTP_200_OK,
        )


class CertificateVerifyView(APIView):
    """Verify a certificate by comparing its stored SHA-256 hash to the file."""

    permission_classes = [IsAuthenticated, IsCertificateOwnerOrAdmin]

    def post(self, request, pk):
        try:
            cert = Certificate.objects.get(pk=pk)
        except Certificate.DoesNotExist:
            return Response(
                {"detail": "Certificate not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if not cert.storage_path:
            return Response(
                {"detail": "This certificate has no uploaded file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        stored_hash = cert.sha256
        if not stored_hash:
            return Response(
                {"detail": "No SHA-256 hash is stored for this certificate."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from django.core.files.storage import storages

        try:
            with storages["default"].open(cert.storage_path, "rb") as fh:
                actual_hash = hashlib.sha256(fh.read()).hexdigest()
        except FileNotFoundError:
            cert.status = Certificate.Status.FAILED
            cert.save(update_fields=["status", "updated_at"])
            return Response(
                {"detail": "The stored certificate file is no longer available."},
                status=status.HTTP_404_NOT_FOUND,
            )

        verified = actual_hash == stored_hash
        if verified:
            cert.status = Certificate.Status.VERIFIED
        else:
            cert.status = Certificate.Status.FAILED
        cert.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "cert_id": cert.pk,
                "certificate_type": cert.certificate_type,
                "verified": verified,
                "stored_sha256": stored_hash,
                "actual_sha256": actual_hash,
                "status": cert.get_status_display(),
            },
            status=status.HTTP_200_OK,
        )
