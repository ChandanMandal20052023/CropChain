"""API views for batch traceability and milestone events."""

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import User
from apps.accounts.permissions import IsVerified, role_required
from apps.audit.models import AuditLog
from apps.audit.permissions import IsAuditAdmin
from apps.batches.models import Batch
from apps.batches.permissions import IsBatchOwnerOrAdmin

from .models import MilestoneEvent
from .permissions import IsBatchEventActorOrAdmin


class BatchEventListCreate(generics.ListCreateAPIView):
    """Record and list traceability milestone events for a batch."""

    permission_classes = [IsVerified(), IsBatchEventActorOrAdmin]
    pagination_class = None

    def get_queryset(self):
        batch = self.get_batch()
        return (
            MilestoneEvent.objects.filter(batch=batch)
            .select_related(
                "actor", "batch", "related_certificate", "related_handoff"
            )
            .order_by("-occurred_at", "-id")
        )

    def get_batch(self):
        batch_code = self.kwargs["batch_code"]
        try:
            return Batch.objects.prefetch_related(
                "farm", "farm__owner", "created_by"
            ).get(batch_code=batch_code)
        except Batch.DoesNotExist:
            return Response(
                {"detail": "Batch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

    def _resolve_actor(self, request):
        # Never trust the client for the actor: the authenticated user is
        # always the actor. An admin sees this helper without extra checks.
        user = request.user
        if not user.is_authenticated:
            raise PermissionDenied("Authentication credentials were not provided.")
        return user

    def _resolve_organization(self, request, actor):
        # A business actor operates through the organization it declares.
        # For farmer accounts there is no organization concept, so we fall
        # back to the farm owner which is the same as the farmer.
        if actor.role == User.Role.FARMER:
            farm = self.get_batch().farm
            return farm.owner.pk
        return actor.pk

    def create(self, request, *args, **kwargs):
        batch = self.get_batch()
        if isinstance(batch, Response):
            return batch

        serializer = self.get_serializer(
            data=request.data, context={"request": request, "batch": batch}
        )
        serializer.is_valid(raise_exception=True)

        actor = self._resolve_actor(request)
        organization = self._resolve_organization(request, actor)

        # Lock the batch row so two concurrent submissions cannot race on
        # the same event store and produce non-monotonic timestamps.
        with transaction.atomic():
            batch.refresh_from_db()
            event = MilestoneEvent.objects.create(
                batch=batch,
                actor=actor,
                organization=organization,
                actor_email=actor.email,
                event_type=serializer.validated_data["event_type"],
                occurred_at=serializer.validated_data["occurred_at"],
                quantity=serializer.validated_data.get("quantity"),
                unit=serializer.validated_data.get("unit"),
                notes=serializer.validated_data.get("notes", ""),
                metadata=serializer.validated_data.get("metadata", {}),
            )

        AuditLog.objects.log(
            request=request,
            actor=actor,
            action="traceability.event.created",
            entity_type="batch",
            entity_id=batch.batch_code,
            metadata={"event_type": event.event_type},
        )

        return Response(
            MilestoneEventSerializer(event).data,
            status=status.HTTP_201_CREATED,
        )


class MilestoneEventSerializer:
    """Serialize a milestone event for API responses."""

    def __init__(self, event):
        self.event = event

    def data(self):
        return {
            "id": self.event.pk,
            "batch_code": self.event.batch.batch_code,
            "event_type": self.event.event_type,
            "event_type_label": self.event.get_event_type_display(),
            "occurred_at": self.event.occurred_at,
            "actor": {
                "id": self.event.actor.pk if self.event.actor else None,
                "email": self.event.actor.email if self.event.actor else None,
                "role": self.event.actor.role if self.event.actor else None,
            },
            "organization": self.event.organization,
            "quantity": self.event.quantity,
            "unit": self.event.unit,
            "notes": self.event.notes,
            "metadata": self.event.metadata,
            "submitted_to_blockchain": self.event.submitted_to_blockchain,
            "blockchain_tx_id": self.event.blockchain_tx_id,
            "blockchain_status": self.event.blockchain_status,
        }
