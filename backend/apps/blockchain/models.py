"""Persisted Fabric transaction and batch history models.

These models give the Django side a durable, queryable record of what was
anchored to the Hyperledger Fabric ledger, so the REST API and public
portal can report genuine COMMITTED/PENDING/FAILED state instead of
fabricating a confirmation.
"""

from django.db import models
from django.utils import timezone

from apps.accounts.models import User


class FabricTransaction(models.Model):
    """A single submission to, and result of, the Fabric network."""

    class TransactionStatus(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        FAILED = "FAILED", "Failed"

    class Outcome(models.TextChoices):
        SUBMITTED = "SUBMITTED", "Submitted"
        COMMITTED = "COMMITTED", "Committed"
        VALIDATED = "VALIDATED", "Validated"
        EXECUTED = "EXECUTED", "Executed"

    class SubmissionSource(models.TextChoices):
        API = "api", "API submission"
        MIGRATION = "migration", "Migration/seed"
        REPLAY = "replay", "Idempotent replay"

    batch = models.ForeignKey(
        "batches.Batch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blockchain_transactions",
    )
    blockchain_app = models.CharField(max_length=100, blank=True)
    function = models.CharField(max_length=100, blank=True)
    payload_hash = models.CharField(max_length=64, blank=True)
    tx_id = models.CharField(max_length=128, unique=True, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
        db_index=True,
    )
    outcome = models.CharField(
        max_length=20, choices=Outcome.choices, blank=True
    )
    event_query = models.TextField(blank=True)
    event_query_result = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    last_error_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(
        max_length=20,
        choices=SubmissionSource.choices,
        default=SubmissionSource.API,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-confirmed_at", "-id"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["batch", "-confirmed_at"]),
            models.Index(fields=["tx_id"]),
        ]

    def __str__(self):
        return f"{self.tx_id} ({self.get_status_display()})"

    def mark_pending(self):
        self.status = self.TransactionStatus.PENDING
        self.retry_count += 1
        self.save(update_fields=["status", "retry_count"])

    def mark_confirmed(self, tx_id=None):
        self.status = self.TransactionStatus.CONFIRMED
        self.tx_id = tx_id or self.tx_id
        self.confirmed_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "tx_id",
                "confirmed_at",
                "retry_count",
                "updated_at",
            ]
        )

    def mark_failed(self, message):
        self.status = self.TransactionStatus.FAILED
        self.error_message = message
        self.last_error_at = timezone.now()
        self.save(
            update_fields=[
                "status",
                "error_message",
                "last_error_at",
                "retry_count",
                "updated_at",
            ]
        )
