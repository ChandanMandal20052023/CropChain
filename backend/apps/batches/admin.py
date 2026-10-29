"""Django admin configuration for batches."""

from django.contrib import admin

from .models import Batch


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = (
        "batch_code",
        "crop_name",
        "farm",
        "quantity",
        "unit",
        "status",
        "is_public",
        "created_at",
    )
    list_filter = ("status", "unit", "is_public", "farm__is_verified")
    search_fields = (
        "batch_code",
        "crop_name",
        "variety",
        "farm__name",
        "farm__farm_code",
        "created_by__email",
    )
    list_select_related = ("farm", "created_by")
    readonly_fields = ("batch_code", "created_at", "updated_at")
    autocomplete_fields = ("farm", "created_by")
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "batch_code",
                    "farm",
                    "created_by",
                    "crop_name",
                    "variety",
                )
            },
        ),
        (
            "Harvest",
            {
                "fields": (
                    "quantity",
                    "unit",
                    "planting_date",
                    "harvest_date",
                    "description",
                )
            },
        ),
        (
            "Traceability",
            {"fields": ("status", "is_public")},
        ),
        (
            "Important dates",
            {"fields": ("created_at", "updated_at")},
        ),
    )
