"""Permissions for the audit log and admin-only endpoints."""

from rest_framework.permissions import BasePermission


class IsAuditAdmin(BasePermission):
    """Restrict audit reads to administrators and superusers."""

    message = "Only administrators may view audit logs."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_admin_role or user.is_staff)
        )
