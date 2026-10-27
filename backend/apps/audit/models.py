from django.db import models

# Create your models here.
from django.conf import settings

class AuditLog(models.Model):
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                              on_delete=models.SET_NULL, related_name="audit_logs")
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}:{self.entity_id}"