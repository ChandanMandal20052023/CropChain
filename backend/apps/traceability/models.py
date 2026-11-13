"""Milestone and traceability event tracking for CropChain batches."""

from django.db import models
from django.utils import timezone

from apps.accounts.models import User

from apps.batches.models import Batch


class MilestoneEvent(models.Model):
    """A single point in a batch's supply-chain journey."""

    class EventType(models.TextChoices):
        HARNVESTED = "harvested", "Harvested"
        COLLECTION_CENTER_RECEIVED = "collection_center_received", (
            "Collection Center Received"
        )
        INSPECTION_COMPLETED = "inspection_completed", "Inspection Completed"
        WAREHOUSE_RECEIVED = "warehouse_received", "Warehouse Received"
        STORAGE_CHECKPOINT = "storage_checkpoint", "Storage Checkpoint"
        PROCESSING_STARTED = "processing_started", "Processing Started"
        PROCESSING_COMPLETED = "processing_completed", "Processing Completed"
        DISPATCHED = "dispatched", "Dispatched"
        DELIVERED = "delivered", "Delivered"
        RETAIL_AVAILABILITY = "retail_availability", "Retail Availability"

    batch = models.ForeignKey(
        "batches.Batch",
        on_delete=models.PROTECT,
        related_name="events",
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="traceability_events",
    )
    actor_email = models.EmailField(blank=True)
    organization = models.PositiveIntegerField(
        help_text="Stored as a positive integer. The actor's ID for " "non-farmer roles; the farm owner's ID for farmers."
    )
    event_type = models.CharField(max_length=60, choices=EventType.choices)
    occurred_at = models.DateTimeField(default=timezone.now)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    unit = models.CharField(
        max_length=12,
        choices=Batch.Unit.choices,
        null=True,
        blank=True,
    )
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    submitted_to_blockchain = models.BooleanField(default=False)
    blockchain_tx_id = models.CharField(max_length=128, blank=True)
    blockchain_status = models.CharField(
        max_length=20,
        choices=[("PENDING", "Pending"), ("CONFIRMED", "Confirmed"), ("FAILED", "Failed")],
        default="PENDING",
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["batch", "-occurred_at"]),
            models.Index(fields=["batch", "event_type"]),
            models.Index(fields=["batch", "occurred_at"]),
            models.Index(fields=["blockchain_status"]),
        ]

    def __str__(self):
        return f"{self.batch.batch_code} ({self.get_event_type_display()})"
