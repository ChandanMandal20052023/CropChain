"""Crop batch model for CropChain."""

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Batch(models.Model):
    """A traceable quantity of a crop harvested from a farm.

    A batch is the unit that quality inspections, custody events, blockchain
    anchors, and consumer passports attach to.
    """

    class Unit(models.TextChoices):
        KG = "kg", "Kilogram"
        TONNE = "tonne", "Tonne"
        BAG = "bag", "Bag"
        CRATE = "crate", "Crate"
        LITRE = "litre", "Litre"
        PIECE = "piece", "Piece"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        HARVESTED = "harvested", "Harvested"
        IN_TRANSIT = "in_transit", "In Transit"
        PROCESSING = "processing", "Processing"
        PACKED = "packed", "Packed"
        DELIVERED = "delivered", "Delivered"
        SOLD = "sold", "Sold"
        RECALLED = "recalled", "Recalled"

    STATUS_TRANSITIONS = {
        Status.DRAFT: frozenset({Status.HARVESTED, Status.RECALLED}),
        Status.HARVESTED: frozenset(
            {Status.IN_TRANSIT, Status.PROCESSING, Status.RECALLED}
        ),
        Status.IN_TRANSIT: frozenset(
            {Status.PROCESSING, Status.PACKED, Status.RECALLED}
        ),
        Status.PROCESSING: frozenset({Status.PACKED, Status.RECALLED}),
        Status.PACKED: frozenset(
            {Status.IN_TRANSIT, Status.DELIVERED, Status.RECALLED}
        ),
        Status.DELIVERED: frozenset({Status.SOLD, Status.RECALLED}),
        Status.SOLD: frozenset({Status.RECALLED}),
        Status.RECALLED: frozenset(),
    }

    batch_code = models.CharField(max_length=32, unique=True, editable=False)
    farm = models.ForeignKey(
        "farms.Farm",
        on_delete=models.PROTECT,
        related_name="batches",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_batches",
    )
    crop_name = models.CharField(max_length=120, db_index=True)
    variety = models.CharField(max_length=120, blank=True)
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    unit = models.CharField(
        max_length=12, choices=Unit.choices, default=Unit.KG
    )
    planting_date = models.DateField(null=True, blank=True)
    harvest_date = models.DateField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    description = models.TextField(blank=True)
    is_public = models.BooleanField(
        default=True,
        help_text=(
            "Designates whether this batch may be shown in the public "
            "traceability passport."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "batch"
        verbose_name_plural = "batches"
        indexes = [
            models.Index(fields=["farm", "status"]),
            models.Index(fields=["created_by", "status"]),
            models.Index(fields=["crop_name"]),
        ]

    def save(self, *args, **kwargs):
        if not self.batch_code:
            self.batch_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_unique_code(cls):
        year = timezone.now().year
        for _ in range(10):
            code = f"BATCH-{year}-{secrets.token_hex(3).upper()}"
            if not cls.objects.filter(batch_code=code).exists():
                return code
        raise RuntimeError("Unable to generate a unique batch code.")

    @property
    def allowed_next_statuses(self):
        return sorted(self.STATUS_TRANSITIONS.get(self.status, frozenset()))

    def can_transition_to(self, status):
        return status in self.STATUS_TRANSITIONS.get(
            self.status, frozenset()
        )

    def __str__(self):
        return f"{self.batch_code} - {self.crop_name}"
