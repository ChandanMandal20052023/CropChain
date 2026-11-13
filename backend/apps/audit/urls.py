from django.urls import path

from . import views

urlpatterns = [
    # Audit log entries for administrators and audit tooling.
    path("audit/", views.AuditLogListView.as_view(), name="audit-log-list"),
    path(
        "audit/<str:request_id>/",
        views.AuditLogByRequestIDView.as_view(),
        name="audit-log-request",
    ),
]
