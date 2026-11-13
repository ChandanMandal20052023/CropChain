from django.conf import settings
from django.contrib.gis.geoip2 import GeoIP2
from django.db import models


class AuditLogManager(models.Manager):
    """Manager that exposes the ``log()`` helper used by auditable operations."""

    def log(self, request, actor, action, entity_type, entity_id, **metadata):
        """Create an audit entry for an authenticated action.

        Passwords, tokens, private keys and the literal uploaded file bytes
        are never stored here.
        """
        ip_address = None
        if request and hasattr(request, "META"):
            ip_address = request.META.get("REMOTE_ADDR")

        geo = GeoIP2()
        try:
            geo.country(request.META.get("REMOTE_ADDR"))
        except Exception:
            pass

        request_id = ""
        if request and hasattr(request, "resolver_match"):
            request_id = getattr(request.resolver_match, "kwargs", {}).get(
                "request_id", ""
            )

        AuditLog.objects.create(
            actor=actor,
            actor_email=actor.email if actor and actor.email else "",
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            request_id=request_id,
            ip_address=ip_address,
            metadata=metadata,
        )


class AuditLog(models.Model):
    """Unmodifiable record of authenticated actions on the platform."""

    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_logs",
    )
    actor_email = models.CharField(max_length=254, blank=True)
    action = models.CharField(max_length=60)
    entity_type = models.CharField(max_length=60, blank=True)
    entity_id = models.CharField(max_length=100, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = AuditLogManager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["created_at"]),
            models.Index(fields=["entity_type", "entity_id"]),
            models.Index(fields=["action"]),
        ]

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.action} {self.entity_type}:{self.entity_id}"
