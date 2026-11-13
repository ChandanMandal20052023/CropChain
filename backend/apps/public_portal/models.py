"""Public portal models for CropChain."""

from django.db import models

from apps.batches.models import Batch


class BatchToken(models.Model):
    """Opaque, revocable tokens that expose a batch to the public portal."""

    batch = models.OneToOneField(
        Batch,
        on_delete=models.CASCADE,
        related_name="public_token",
    )
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    used_at = models.DateTimeField(null=True, blank=True)
