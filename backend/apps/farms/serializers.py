"""Serializers for the farms API."""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied

from apps.accounts.serializers import UserSummarySerializer

from .models import Farm

User = get_user_model()


class FarmSerializer(serializers.ModelSerializer):
    """Read-only representation of a farm."""

    owner = UserSummarySerializer(read_only=True)
    batches_count = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = (
            "id",
            "farm_code",
            "owner",
            "name",
            "description",
            "country",
            "region",
            "district",
            "village",
            "latitude",
            "longitude",
            "size_hectares",
            "is_verified",
            "is_active",
            "batches_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_batches_count(self, obj):
        annotated = getattr(obj, "batches_count", None)
        if annotated is not None:
            return annotated
        return obj.batches.count()


class FarmSummarySerializer(serializers.ModelSerializer):
    """Compact farm representation used by batch responses."""

    class Meta:
        model = Farm
        fields = (
            "id",
            "farm_code",
            "name",
            "region",
            "district",
            "is_verified",
        )


class FarmCreateSerializer(serializers.ModelSerializer):
    """Create a farm.

    Farmers always own the farms they create. Administrators may pass an
    ``owner`` to register a farm on behalf of a farmer.
    """

    owner = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(role=User.Role.FARMER),
        required=False,
        help_text="Farmer who owns the farm. Administrators only.",
    )

    class Meta:
        model = Farm
        fields = (
            "owner",
            "name",
            "description",
            "country",
            "region",
            "district",
            "village",
            "latitude",
            "longitude",
            "size_hectares",
        )

    def validate_owner(self, value):
        request = self.context["request"]
        if not request.user.is_admin_role:
            raise PermissionDenied(
                "Only administrators can assign a farm to another user."
            )
        return value

    def validate(self, attrs):
        request = self.context["request"]
        owner = attrs.get("owner")

        if owner is None:
            if request.user.role != User.Role.FARMER:
                raise serializers.ValidationError(
                    {
                        "owner": (
                            "Select the farmer who owns this farm."
                        )
                    }
                )
            owner = request.user
        elif owner.role != User.Role.FARMER:
            raise serializers.ValidationError(
                {"owner": "The owner must be a farmer."}
            )

        attrs["owner"] = owner
        return attrs

    def create(self, validated_data):
        return Farm.objects.create(**validated_data)


class FarmUpdateSerializer(serializers.ModelSerializer):
    """Update a farm. Only administrators may change verification."""

    class Meta:
        model = Farm
        fields = (
            "name",
            "description",
            "country",
            "region",
            "district",
            "village",
            "latitude",
            "longitude",
            "size_hectares",
            "is_active",
            "is_verified",
        )

    def validate_is_verified(self, value):
        request = self.context["request"]
        if not request.user.is_admin_role:
            raise PermissionDenied(
                "Only administrators can verify farms."
            )
        return value
