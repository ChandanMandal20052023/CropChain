"""Serializers for the batches API."""

from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.serializers import UserSummarySerializer
from apps.farms.models import Farm
from apps.farms.serializers import FarmSummarySerializer

from .models import Batch


class BatchSerializer(serializers.ModelSerializer):
    """Read-only representation of a batch."""

    farm = FarmSummarySerializer(read_only=True)
    created_by = UserSummarySerializer(read_only=True)
    unit_label = serializers.CharField(source="get_unit_display", read_only=True)
    status_label = serializers.CharField(
        source="get_status_display", read_only=True
    )
    allowed_next_statuses = serializers.ListField(
        child=serializers.CharField(), read_only=True
    )

    class Meta:
        model = Batch
        fields = (
            "id",
            "batch_code",
            "farm",
            "created_by",
            "crop_name",
            "variety",
            "quantity",
            "unit",
            "unit_label",
            "planting_date",
            "harvest_date",
            "status",
            "status_label",
            "allowed_next_statuses",
            "description",
            "is_public",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class BatchCreateSerializer(serializers.ModelSerializer):
    """Create a batch for a farm owned by the requesting farmer."""

    farm = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.select_related("owner")
    )

    class Meta:
        model = Batch
        fields = (
            "farm",
            "crop_name",
            "variety",
            "quantity",
            "unit",
            "planting_date",
            "harvest_date",
            "description",
            "is_public",
        )

    def validate_farm(self, value):
        request = self.context["request"]
        if not request.user.is_admin_role and value.owner_id != request.user.id:
            raise PermissionDenied(
                "You can only create batches for your own farms."
            )
        if not value.is_active:
            raise serializers.ValidationError(
                "Batches cannot be created for an inactive farm."
            )
        return value

    def validate(self, attrs):
        planting_date = attrs.get("planting_date")
        harvest_date = attrs.get("harvest_date")
        if (
            planting_date
            and harvest_date
            and harvest_date < planting_date
        ):
            raise serializers.ValidationError(
                {
                    "harvest_date": (
                        "The harvest date cannot be before the planting date."
                    )
                }
            )
        return attrs

    def create(self, validated_data):
        return Batch.objects.create(
            created_by=self.context["request"].user, **validated_data
        )


class BatchUpdateSerializer(serializers.ModelSerializer):
    """Update batch details or advance its supply-chain status."""

    class Meta:
        model = Batch
        fields = (
            "crop_name",
            "variety",
            "quantity",
            "unit",
            "planting_date",
            "harvest_date",
            "description",
            "is_public",
            "status",
        )

    def validate(self, attrs):
        instance = self.instance
        planting_date = attrs.get(
            "planting_date",
            instance.planting_date if instance else None,
        )
        harvest_date = attrs.get(
            "harvest_date",
            instance.harvest_date if instance else None,
        )
        if (
            planting_date
            and harvest_date
            and harvest_date < planting_date
        ):
            raise serializers.ValidationError(
                {
                    "harvest_date": (
                        "The harvest date cannot be before the planting date."
                    )
                }
            )

        new_status = attrs.get("status")
        if (
            instance is not None
            and new_status
            and new_status != instance.status
            and not instance.can_transition_to(new_status)
        ):
            raise serializers.ValidationError(
                {
                    "status": (
                        f"A batch cannot move from "
                        f"{instance.get_status_display()} to "
                        f"{Batch.Status(new_status).label}."
                    )
                }
            )
        return attrs
