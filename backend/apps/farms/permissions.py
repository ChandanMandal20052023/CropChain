"""Permissions for farm endpoints."""

from rest_framework.permissions import BasePermission


class IsFarmOwnerOrAdmin(BasePermission):
    """Allow the farm owner or any administrator to modify the farm."""

    message = "Only the farm owner or an administrator can do that."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_admin_role or obj.owner_id == user.id)
        )
