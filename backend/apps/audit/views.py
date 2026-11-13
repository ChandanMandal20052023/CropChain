"""API views for the audit log."""

from django.utils import timezone
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AuditLog
from .permissions import IsAuditAdmin


class AuditLogListView(generics.ListAPIView):
    """Return audit log entries, ordered newest first."""

    permission_classes = [IsAuditAdmin]
    queryset = AuditLog.objects.all()
    page_size = 100

    def get_queryset(self):
        queryset = super().get_queryset()
        search = self.request.query_params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                models.Q(action__icontains=search)
                | models.Q(entity_type__icontains=search)
                | models.Q(entity_id__icontains=search)
                | models.Q(actor_email__icontains=search)
            )
        return queryset.order_by("-created_at")


class AuditLogByRequestIDView(generics.RetrieveAPIView):
    """Return audit entries for a single correlation/request ID."""

    permission_classes = [IsAuditAdmin]
    queryset = AuditLog.objects.all()
    lookup_field = "request_id"
