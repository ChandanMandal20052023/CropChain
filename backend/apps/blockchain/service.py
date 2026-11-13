"""Business logic for anchoring CropChain records to Hyperledger Fabric."""

import hashlib
import logging
import os
import time
from typing import Any, Dict, List, Optional

from django.db import transaction
from django.utils import timezone

from apps.batches.models import Batch
from apps.quality.models import Certificate

from .adapter import (
    FabricAdapter,
    FabricAdapterError,
    FabricCommitError,
    FabricConnectionError,
    FabricEndorsementError,
    get_adapter,
)
from .models import FabricTransaction

logger = logging.getLogger(__name__)


class TransactionAnchoringError(Exception):
    """Raised when an operation cannot be safely anchored to Fabric."""


def _coerce_list(value: Optional[List[Any]]) -> List[str]:
    if not value:
        return []
    return [str(item) for item in value]


def _payload_hash(payload: Dict[str, Any]) -> str:
    text = str(payload)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _client_tx_id(tx_id: Optional[str]) -> Optional[str]:
    if not tx_id:
        return None
    return str(tx_id).strip()


def _record_transaction(**overrides) -> FabricTransaction:
    defaults = {
        "batch": overrides.get("batch"),
        "blockchain_app": overrides.get("blockchain_app", "cropchain"),
        "function": overrides.get("function", ""),
        "payload_hash": overrides.get("payload_hash", ""),
        "tx_id": overrides.get("tx_id", ""),
        "source": overrides.get("source", FabricTransaction.SubmissionSource.API),
    }
    return FabricTransaction.objects.create(**defaults)


def submit_batch_creation(
    batch: Batch,
    created_by: Any,
    *,
    idempotency_key: Optional[str] = None,
    retry_attempts: Optional[int] = None,
) -> FabricTransaction:
    """Submit a batch-creation record to Fabric and record the result.

    Returns the persisted :class:`FabricTransaction`. The caller must decide
    what to do if the transaction is still ``PENDING`` (it may need to poll).
    """

    max_attempts = retry_attempts or int(
        os.environ.get("FABRIC_MAX_ATTEMPTS", "5")
    )
    app = os.environ.get("FABRIC_CHAINCODE_NAME", "cropchain")
    fcn = "createBatch"

    payload = {
        "batch_code": batch.batch_code,
        "farm_code": batch.farm.farm_code,
        "crop_name": batch.crop_name,
        "variety": batch.variety,
        "quantity": str(batch.quantity),
        "unit": batch.unit,
        "harvest_date": str(batch.harvest_date),
        "planting_date": (
            str(batch.planting_date) if batch.planting_date else None
        ),
        "owner": (
            str(batch.created_by.id) if batch.created_by else None
        ),
        "organization": batch.farm.owner.organization
        if batch.farm.owner
        else "",
    }
    payload["idempotency_key"] = idempotency_key or _payload_hash(payload)

    adapter = get_adapter()
    tx: Optional[FabricTransaction] = None
    last_error: Optional[Exception] = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = _safe_submit(adapter, app, fcn, payload)
            tx_id = result.get("tx_id") or result.get("transaction_id")
            if not _client_tx_id(tx_id):
                raise FabricAdapterError(
                    f"Fabric adapter returned no transaction id: {result!r}"
                )

            with transaction.atomic():
                tx = _record_transaction(
                    batch=batch,
                    blockchain_app=app,
                    function=fcn,
                    payload_hash=payload["idempotency_key"],
                    tx_id=tx_id,
                    source=FabricTransaction.SubmissionSource.API,
                )
            break

        except (FabricConnectionError, FabricEndorsementError, FabricCommitError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break
            sleep_for = 2 ** (attempt - 1)
            logger.warning(
                "Fabric submit attempt %s/%s failed (%s). Retrying in %ss.",
                attempt,
                max_attempts,
                exc,
                sleep_for,
            )
            time.sleep(sleep_for)
        except Exception as exc:  # pragma: no cover - defensive
            last_error = exc
            break

    if tx is None:
        message = (
            f"Unable to anchor batch {batch.batch_code} to Fabric "
            f"(last error: {last_error!r})"
        )
        # Persist the failure so the API can report it truthfully.
        tx = _record_transaction(
            batch=batch,
            blockchain_app="cropchain",
            function="createBatch",
            payload_hash=payload.get("idempotency_key", ""),
            tx_id="",
            error_message=str(last_error),
            last_error_at=timezone.now(),
            source=FabricTransaction.SubmissionSource.API,
        )
        tx.mark_failed(message)
        raise TransactionAnchoringError(message)

    return tx


def submit_milestone_event(
    batch: Batch,
    event_type: str,
    *,
    idempotency_key: Optional[str] = None,
    retry_attempts: Optional[int] = None,
) -> FabricTransaction:
    """Anchor a milestone event to Fabric and record the result."""

    adapter = get_adapter()
    app = os.environ.get("FABRIC_CHAINCODE_NAME", "cropchain")
    fcn = "recordEvent"

    payload = {
        "batch_code": batch.batch_code,
        "event_type": event_type,
        "occurred_at": timezone.now().isoformat(),
        "actor": None,
        "organization": None,
    }

    tx = submit_batch_creation(
        batch,
        created_by=None,
        idempotency_key=idempotency_key or _payload_hash(payload),
        retry_attempts=retry_attempts,
    )
    tx.function = fcn
    tx.event_query = f"selectRevisionByBatchAndEvent('{batch.batch_code}', '{event_type}')"
    tx.save(update_fields=["function", "event_query", "updated_at"])
    return tx


def query_transaction(tx_id: str) -> FabricTransaction:
    """Query the network for a transaction's status and persist it."""

    adapter = get_adapter()
    try:
        result = adapter.query_transaction(tx_id)
    except FabricAdapterError as exc:
        FabricTransaction.objects.filter(tx_id=tx_id).update(
            status=FabricTransaction.TransactionStatus.FAILED,
            error_message=str(exc),
            last_error_at=timezone.now(),
        )
        raise

    tx, _ = FabricTransaction.objects.get_or_create(
        tx_id=tx_id,
        defaults={
            "status": result.get("status", "FAILED"),
            "outcome": result.get("outcome", ""),
            "event_query_result": result.get("result", {}),
        },
    )
    tx.event_query_result = result.get("result", {})
    tx.save(update_fields=["status", "outcome", "event_query_result", "updated_at"])
    return tx


def batch_history(batch_code: str) -> Dict[str, Any]:
    """Retrieve the Fabric-anchored history for a batch."""

    adapter = get_adapter()
    app = os.environ.get("FABRIC_CHAINCODE_NAME", "cropchain")
    fcn = "queryHistory"

    try:
        result = adapter.query(app, fcn, [batch_code])
    except FabricAdapterError as exc:
        return {
            "batch_code": batch_code,
            "ledger": [],
            "error": str(exc),
            "chaincode": app,
            "function": fcn,
        }

    return {
        "batch_code": batch_code,
        "chaincode": app,
        "function": fcn,
        "ledger": result.get("ledger", []),
        "error": None,
    }


def _safe_submit(adapter: FabricAdapter, app: str, fcn: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    retry_count = 0
    while True:
        try:
            return adapter.submit(app, fcn, _coerce_list(payload.values()))
        except FabricConnectionError as exc:
            retry_count += 1
            if retry_count > int(os.environ.get("FABRIC_MAX_ATTEMPTS", "5")):
                raise
            time.sleep(2 ** (retry_count - 1))
        except FabricEndorsementError as exc:
            raise FabricCommitError(f"Endorsement failed: {exc}") from exc
        except FabricCommitError:
            raise
        except Exception as exc:
            raise FabricCommitError(f"Unexpected submission failure: {exc}") from exc
