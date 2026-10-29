"""API views for farms."""

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.db.models.deletion import ProtectedError
from rest_framework import generics, status
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsVerified, role_required

from .models import Farm
from .permissions import IsFarmOwnerOrAdmin
from .serializers import (
    FarmCreateSerializer,
    FarmSerializer,
    FarmUpdateSerializer,
)

User = get_user_model()


def _parse_boolean(value):
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FarmListCreateView(generics.ListCreateAPIView):
    """List farms, or register a new farm as a verified farmer."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsAuthenticated(),
                IsVerified(),
                role_required(User.Role.FARMER)(),
            ]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return FarmCreateSerializer
        return FarmSerializer

    def get_queryset(self):
        queryset = (
            Farm.objects.select_related("owner")
            .annotate(batches_count=Count("batches"))
        )
        params = self.request.query_params

        if _parse_boolean(params.get("mine")):
            queryset = queryset.filter(owner=self.request.user)

        owner = params.get("owner")
        if owner and owner.isdigit():
            queryset = queryset.filter(owner_id=int(owner))

        is_verified = _parse_boolean(params.get("is_verified"))
        if is_verified is not None:
            queryset = queryset.filter(is_verified=is_verified)

        is_active = _parse_boolean(params.get("is_active"))
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(farm_code__icontains=search)
                | Q(region__icontains=search)
                | Q(district__icontains=search)
                | Q(village__icontains=search)
                | Q(owner__email__icontains=search)
                | Q(owner__first_name__icontains=search)
                | Q(owner__last_name__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        return Response(
            FarmSerializer(farm).data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data),
        )


class FarmDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a single farm."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [
            IsAuthenticated(),
            IsVerified(),
            IsFarmOwnerOrAdmin(),
        ]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return FarmUpdateSerializer
        return FarmSerializer

    def get_queryset(self):
        return (
            Farm.objects.select_related("owner")
            .annotate(batches_count=Count("batches"))
        )

    def update(self, request, *args, **kwargs):
        farm = self.get_object()
        serializer = self.get_serializer(
            farm, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        farm = serializer.save()
        return Response(FarmSerializer(farm).data)

    def destroy(self, request, *args, **kwargs):
        farm = self.get_object()
        try:
            farm.delete()
        except ProtectedError:
            return Response(
                {
                    "detail": (
                        "This farm has batches and cannot be deleted. "
                        "Deactivate it instead."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)
