from django.urls import path

from . import views

urlpatterns = [
    # Submit a batch-creation/anchor transaction to the Fabric network.
    path(
        "transactions/",
        views.TransactionSubmitView.as_view(),
        name="transaction-submit",
    ),
    # Query the persisted state of a Fabric transaction.
    path(
        "transactions/<str:tx_id>/",
        views.TransactionDetailView.as_view(),
        name="transaction-detail",
    ),
    # Retrieve batch history from the Fabric ledger.
    path(
        "batches/<str:batch_code>/history/",
        views.BatchHistoryView.as_view(),
        name="batch-history",
    ),
]
