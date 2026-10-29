"""Reusable permission classes for role-based access control."""

from rest_framework.permissions import SAFE_METHODS, BasePermission

from .models import User


def role_required(*roles):
    """Build a permission class that allows superusers and the given roles.

    Usage::

        permission_classes = [role_required(User.Role.FARMER)]
    """
    role_values = frozenset(
        getattr(role, "value", role) for role in roles
    )

    class _RoleRequired(BasePermission):
        message = "You do not have permission to perform this action."

        def has_permission(self, request, view):
            user = request.user
            return bool(
                user
                and user.is_authenticated
                and (user.is_superuser or user.role in role_values)
            )

    _RoleRequired.__name__ = "Is" + "Or".join(
        str(role).title().replace("_", "") for role in sorted(role_values)
    )
    return _RoleRequired


IsAdmin = role_required(User.Role.ADMIN)


class IsAdminOrReadOnly(BasePermission):
    """Allow anyone to read, but only administrators to write."""

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin_role)


class IsAdminOrSelf(BasePermission):
    """Allow administrators to act on any account, users only on themselves."""

    message = "You may only access your own account."

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj):
        return obj.pk == request.user.pk or request.user.is_admin_role


class IsVerified(BasePermission):
    """Require an administrator-verified account for operational endpoints."""

    message = "Your account must be verified by an administrator first."

    def has_permission(self, request, view):
        user = request.user
        return bool(
            user
            and user.is_authenticated
            and (user.is_verified or user.is_admin_role)
        )
