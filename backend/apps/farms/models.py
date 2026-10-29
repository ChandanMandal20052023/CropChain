"""Farm model for CropChain."""

import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Farm(models.Model):
    """A farm that produces crop batches.

    Farms are owned by a single farmer account. Administrators verify farms
    before they are exposed through the consumer-facing portal.
    """

    farm_code = models.CharField(max_length=20, unique=True, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="farms",
    )
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    country = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    village = models.CharField(max_length=100, blank=True)
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("-90")),
            MaxValueValidator(Decimal("90")),
        ],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        validators=[
            MinValueValidator(Decimal("-180")),
            MaxValueValidator(Decimal("180")),
        ],
    )
    size_hectares = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=(
            "Designates whether an administrator has verified this farm and "
            "its location details."
        ),
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "farm"
        verbose_name_plural = "farms"
        indexes = [
            models.Index(fields=["is_verified", "is_active"]),
            models.Index(fields=["region", "district"]),
        ]

    def save(self, *args, **kwargs):
        if not self.farm_code:
            self.farm_code = self._generate_unique_code()
        super().save(*args, **kwargs)

    @classmethod
    def _generate_unique_code(cls):
        for _ in range(10):
            code = f"FARM-{secrets.token_hex(4).upper()}"
            if not cls.objects.filter(farm_code=code).exists():
                return code
        raise RuntimeError("Unable to generate a unique farm code.")

    def __str__(self):
        return f"{self.name} ({self.farm_code})"
