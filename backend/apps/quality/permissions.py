"""Permissions for quality inspection and certificate records."""

from rest_framework.permissions import BasePermission

from apps.batches.models import Batch


class IsCertificateOwnerOrAdmin(BasePermission):
    """Only the certificate issuer, an administrator, or a superuser may act."""

    message = (
        "Only the certificate issuer or an administrator may verify this "
        "certificate."
    )

    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return user.is_admin_role or user.is_staff

    def has_object_permission(self, request, view, obj):
        user = request.user
        if user.is_admin_role or user.is_staff:
            return True
        return obj.issued_by_id == user.id
