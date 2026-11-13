"""Permissions for batch traceability events."""

from django.contrib.auth import get_user_model
from rest_framework.permissions import BasePermission

from apps.batches.models import Batch

User = get_user_model()


class IsBatchEventActorOrAdmin(BasePermission):
    """Only the authenticated actor, or an administrator, may submit events."""

    message = (
        "Only the authenticated user who created this batch, "
        "or an administrator, may record an event."
    )

    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.user.is_admin_role:
            return True
        batch_code = view.kwargs.get("batch_code")
        if not batch_code:
            return False
        try:
            batch = Batch.objects.get(batch_code=batch_code)
        except Batch.DoesNotExist:
            return False
        return (
            request.user.is_verified
            and (batch.created_by_id == request.user.id or batch.farm.owner_id == request.user.id)
        )

    def has_object_permission(self, request, view, obj):
        # Event records are immutable from the API; only the original
        # actor or an admin may act on the batch behind the event.
        if request.user.is_admin_role:
            return True
        try:
            batch = Batch.objects.get(batch_code=view.kwargs.get("batch_code", ""))
        except Batch.DoesNotExist:
            return False
        return batch.created_by_id == request.user.id or batch.farm.owner_id == request.user.id
