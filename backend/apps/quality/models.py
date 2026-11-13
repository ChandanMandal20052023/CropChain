"""Quality inspection and certificate models for CropChain."""

from django.db import models
from django.utils import timezone

from apps.accounts.models import User


class Certificate(models.Model):
    """A quality certificate attached to a batch."""

    class CertificateType(models.TextChoices):
        CERTIFICATE_OF_ORIGIN = "certificate_of_origin", "Certificate of Origin"
        CYTOLOGICAL_AND_BOTANICAL = "cytological_and_botanical", (
            "Cytological and Botanical Analysis"
        )
        PHYTosanitary = "phytosanitary", "Phytosanitary Certificate"
        MICROBIAL = "microbial", "Microbial Analysis Report"
        CHEMICAL = "chemical", "Chemical Composition Report"
        NUTRIENT_ANALYSIS = "nutrient_analysis", "Nutrient Analysis"
        OTHER = "other", "Other"

    batch = models.ForeignKey(
        "batches.Batch",
        on_delete=models.PROTECT,
        related_name="certificates",
    )
    certificate_type = models.CharField(
        max_length=60, choices=CertificateType.choices
    )
    issue_date = models.DateField()
    issued_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="issued_certificates",
    )
    organization = models.CharField(max_length=150, blank=True)
    storage_path = models.CharField(
        max_length=512,
        blank=True,
        help_text="Relative storage path for the uploaded certificate file.",
    )
    original_name = models.CharField(max_length=255, blank=True)
    sha256 = models.CharField(
        max_length=64,
        blank=True,
        help_text="Server-computed SHA-256 hash of the uploaded file.",
    )
    status = models.CharField(
        max_length=20,
        choices=[
            ("pending", "Pending"),
            ("verified", "Verified"),
            ("failed", "Hash mismatch"),
            ("rejected", "Rejected"),
        ],
        default="pending",
        db_index=True,
    )
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["batch", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return f"{self.batch.batch_code} ({self.certificate_type})"
