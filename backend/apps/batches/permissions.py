"""Permissions for batch endpoints."""

from rest_framework.permissions import BasePermission


class IsBatchOwnerOrAdmin(BasePermission):
    """Allow the batch creator, the farm owner, or an administrator."""

    message = "Only the batch owner or an administrator can do that."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        return bool(
            user.is_admin_role
            or obj.created_by_id == user.id
            or obj.farm.owner_id == user.id
        )
