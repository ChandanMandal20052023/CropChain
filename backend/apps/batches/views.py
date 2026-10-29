"""API views for batches."""

from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import SAFE_METHODS, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.permissions import IsVerified, role_required

from .models import Batch
from .permissions import IsBatchOwnerOrAdmin
from .serializers import (
    BatchCreateSerializer,
    BatchSerializer,
    BatchUpdateSerializer,
)

User = get_user_model()


def _parse_boolean(value):
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BatchListCreateView(generics.ListCreateAPIView):
    """List batches, or create one for a farmer's own farm."""

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
            return BatchCreateSerializer
        return BatchSerializer

    def get_queryset(self):
        queryset = Batch.objects.select_related(
            "farm", "farm__owner", "created_by"
        )
        params = self.request.query_params

        farm = params.get("farm")
        if farm and farm.isdigit():
            queryset = queryset.filter(farm_id=int(farm))

        status_filter = params.get("status")
        if status_filter:
            queryset = queryset.filter(status=status_filter)

        crop = params.get("crop")
        if crop:
            queryset = queryset.filter(crop_name__icontains=crop)

        is_public = _parse_boolean(params.get("is_public"))
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public)

        if _parse_boolean(params.get("mine")):
            queryset = queryset.filter(
                Q(created_by=self.request.user)
                | Q(farm__owner=self.request.user)
            )

        search = params.get("search", "").strip()
        if search:
            queryset = queryset.filter(
                Q(batch_code__icontains=search)
                | Q(crop_name__icontains=search)
                | Q(variety__icontains=search)
                | Q(farm__name__icontains=search)
                | Q(farm__farm_code__icontains=search)
            )
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        return Response(
            BatchSerializer(batch).data,
            status=status.HTTP_201_CREATED,
            headers=self.get_success_headers(serializer.data),
        )


class BatchDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete a single batch."""

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            return [IsAuthenticated()]
        return [
            IsAuthenticated(),
            IsVerified(),
            IsBatchOwnerOrAdmin(),
        ]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return BatchUpdateSerializer
        return BatchSerializer

    def get_queryset(self):
        return Batch.objects.select_related(
            "farm", "farm__owner", "created_by"
        )

    def update(self, request, *args, **kwargs):
        batch = self.get_object()
        serializer = self.get_serializer(
            batch, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        batch = serializer.save()
        return Response(BatchSerializer(batch).data)

    def destroy(self, request, *args, **kwargs):
        batch = self.get_object()
        if batch.status != Batch.Status.DRAFT:
            return Response(
                {
                    "detail": (
                        "Only draft batches can be deleted. Recall the "
                        "batch instead of deleting it."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        batch.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
