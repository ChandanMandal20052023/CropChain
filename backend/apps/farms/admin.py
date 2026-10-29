"""Django admin configuration for farms."""

from django.contrib import admin

from .models import Farm


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    list_display = (
        "farm_code",
        "name",
        "owner",
        "region",
        "district",
        "is_verified",
        "is_active",
        "created_at",
    )
    list_filter = ("is_verified", "is_active", "country", "region")
    search_fields = (
        "farm_code",
        "name",
        "owner__email",
        "owner__first_name",
        "owner__last_name",
        "region",
        "district",
        "village",
    )
    list_select_related = ("owner",)
    readonly_fields = ("farm_code", "created_at", "updated_at")
    autocomplete_fields = ("owner",)
    fieldsets = (
        (None, {"fields": ("farm_code", "owner", "name", "description")}),
        (
            "Location",
            {
                "fields": (
                    "country",
                    "region",
                    "district",
                    "village",
                    "latitude",
                    "longitude",
                    "size_hectares",
                )
            },
        ),
        (
            "Status",
            {"fields": ("is_verified", "is_active")},
        ),
        (
            "Important dates",
            {"fields": ("created_at", "updated_at")},
        ),
    )
