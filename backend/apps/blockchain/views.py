"""API views for Fabric transaction submission and status tracking."""

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog

import os
from apps.audit.permissions import IsAuditAdmin
from apps.batches.models import Batch

from .adapter import FabricAdapterError, FabricModeDisabledError
from .service import batch_history, query_transaction, submit_batch_creation, submit_milestone_event
from .models import FabricTransaction
from .service import submit_batch_creation, query_transaction


class TransactionSubmitView(APIView):
    """Submit a batch-creation transaction to Fabric and record it."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        batch_code = request.data.get("batch_code")
        idempotency_key = request.data.get("idempotency_key")
        app = os.environ.get("FABRIC_CHAINCODE_NAME", "cropchain")

        try:
            batch = Batch.objects.get(batch_code=batch_code)
        except Batch.DoesNotExist:
            return Response(
                {"detail": "Batch not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            if not idempotency_key:
                idempotency_key = f"{batch.batch_code}-{batch.id}"
            tx = submit_batch_creation(
                batch,
                batch.created_by,
                idempotency_key=idempotency_key,
            )
        except Exception as exc:
            AuditLog.objects.log(
                request=request,
                actor=request.user,
                action="blockchain.transaction.submit.failed",
                entity_type="batch",
                entity_id=batch.batch_code,
                metadata={"error": str(exc)},
            )
            tx = FabricTransaction.objects.create(
                batch=batch,
                blockchain_app=app,
                function="createBatch",
                status=FabricTransaction.TransactionStatus.FAILED,
                error_message=str(exc),
                last_error_at=timezone.now(),
                source=FabricTransaction.SubmissionSource.API,
            )
            return Response(
                {
                    "detail": "Transaction could not be anchored to Fabric.",
                    "error": str(exc),
                    "status": "FAILED",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "tx_id": tx.tx_id,
                "status": tx.status,
                "function": tx.function,
                "blockchain_app": tx.blockchain_app,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class TransactionDetailView(APIView):
    """Return the persisted status of a Fabric transaction."""

    permission_classes = [IsAuthenticated]

    def get(self, request, tx_id):
        try:
            tx = FabricTransaction.objects.get(tx_id=tx_id)
        except FabricTransaction.DoesNotExist:
            return Response(
                {"detail": "Transaction not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            {
                "tx_id": tx.tx_id,
                "status": tx.status,
                "outcome": tx.outcome,
                "error": tx.error_message or None,
                "retry_count": tx.retry_count,
                "submitted_at": tx.submitted_at.isoformat(),
                "confirmed_at": tx.confirmed_at.isoformat()
                if tx.confirmed_at
                else None,
                "failed_at": tx.failed_at.isoformat() if tx.failed_at else None,
            },
            status=status.HTTP_200_OK,
        )


class BatchHistoryView(APIView):
    """Return the Fabric-anchored history for a batch."""

    permission_classes = [IsAuthenticated]

    def get(self, request, batch_code):
        try:
            result = batch_history(batch_code)
        except FabricAdapterError as exc:
            return Response(
                {
                    "batch_code": batch_code,
                    "ledger": [],
                    "error": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "batch_code": batch_code,
                "chaincode": result.get("chaincode"),
                "function": result.get("function"),
                "ledger": result.get("ledger", []),
                "error": result.get("error"),
            },
            status=status.HTTP_200_OK,
        )
