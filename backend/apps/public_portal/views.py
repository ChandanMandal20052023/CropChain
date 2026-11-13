"""Public analytics and batch passport endpoints for CropChain."""

from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.batches.models import Batch

from .models import BatchToken


class BatchPublicTrackView(APIView):
    """Serve a public batch passport with sanitized fields."""

    permission_classes = [AllowAny]

    def get(self, request, batch_code):
        try:
            batch = (
                Batch.objects.select_related("farm", "farm__owner", "created_by")
                .get(batch_code=batch_code, is_public=True)
            )
        except Batch.DoesNotExist:
            return Response(
                {
                    "detail": "No batch found with this code.",
                    "verified": False,
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Public data must never include private fields. We deliberately
        # exclude: exact coordinates, created_by identity, private notes,
        # the batch code is fine to show but we reuse a token-issued
        # reference where appropriate.
        public_events = []
        for event in batch.events.select_related("actor").order_by("occurred_at", "id")[:100]:
            public_events.append(
                {
                    "event_type": event.event_type,
                    "event_type_label": event.get_event_type_display(),
                    "occurred_at": event.occurred_at.isoformat(),
                    "quantity": event.quantity,
                    "unit": event.unit,
                    "actor_org": event.actor.organization if event.actor else "Supply-chain participant",
                    "blockchain_status": event.blockchain_status,
                    "blockchain_tx_id": event.blockchain_tx_id,
                }
            )

        # Token the public URL so we can attribute lookups to an anonymous
        # visitor without exposing the raw batch code in markup.
        token, _ = BatchToken.objects.get_or_create(
            batch=batch,
            defaults={"token": timezone.now().strftime("%Y%m%d%H%M%S")},
        )

        return Response(
            {
                "batch_code": batch.batch_code,
                "crop_name": batch.crop_name,
                "variety": batch.variety,
                "quantity": batch.quantity,
                "unit": batch.unit,
                "status": batch.status,
                "status_label": batch.get_status_display(),
                "farm": {
                    "farm_code": batch.farm.farm_code,
                    "name": batch.farm.name,
                    "region": batch.farm.region,
                    "district": batch.farm.district,
                    "is_verified": batch.farm.is_verified,
                },
                "public_events": public_events,
                "verified": batch.status in {
                    "harvested",
                    "in_transit",
                    "processing",
                    "packed",
                    "delivered",
                    "sold",
                },
                "public_url_token": token.token,
            },
            status=status.HTTP_200_OK,
        )
