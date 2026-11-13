"""Adapter boundary between Django and the Hyperledger Fabric SDK.

The Fabric Gateway client is intentionally isolated behind this adapter.
The rest of the Django application never imports a Fabric-specific class;
it only depends on the ``FabricAdapter`` protocol defined here.

Configuration comes from the environment (see the ``.env.example`` values):

    FABRIC_MODE=disabled|enabled
    FABRIC_GATEWAY_URL=http://127.0.0.1:8081
    FABRIC_GATEWAY_TOKEN=<optional JWT / enrollment token>
    FABRIC_TIMEOUT_SECONDS=15
    FABRIC_MAX_ATTEMPTS=5
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

DEFAULT_GATEWAY_URL = os.environ.get(
    "FABRIC_GATEWAY_URL", "http://127.0.0.1:8081"
)
DEFAULT_GATEWAY_TOKEN = os.environ.get("FABRIC_GATEWAY_TOKEN", "")
DEFAULT_TIMEOUT_SECONDS = int(os.environ.get("FABRIC_TIMEOUT_SECONDS", "15"))
DEFAULT_MAX_ATTEMPTS = int(os.environ.get("FABRIC_MAX_ATTEMPTS", "5"))


class FabricAdapterError(Exception):
    """Base class for adapter failures."""


class FabricModeDisabledError(FabricAdapterError):
    """Raised when the adapter is asked to run but Fabric is disabled."""


class FabricConnectionError(FabricAdapterError):
    """Raised when the Fabric network is unreachable."""


class FabricEndorsementError(FabricAdapterError):
    """Raised when an endorsement/transaction fails validation."""


class FabricCommitError(FabricAdapterError):
    """Raised when a transaction does not commit on the ledger."""


class FabricAdapter:
    """Protocol for communicating with a Fabric network.

    Production code should subclass this and implement the four
    protocol methods using the Fabric Gateway SDK that matches the
    actual network. The Django application only calls this interface.
    """

    def submit(self, chaincode: str, fcn: str, args: List[str]) -> Dict[str, Any]:
        """Submit a transaction to the Fabric network.

        Returns a dict that must contain at least a ``tx_id`` key.
        Raises ``FabricAdapterError`` subclasses on failure.
        """
        raise NotImplementedError

    def query(self, chaincode: str, fcn: str, args: List[str]) -> Dict[str, Any]:
        """Query state from the Fabric ledger."""
        raise NotImplementedError

    def query_transaction(self, tx_id: str) -> Dict[str, Any]:
        """Query the status/evidence of a transaction on the network."""
        raise NotImplementedError

    def close(self) -> None:
        """Release any pooled connections or gateways."""
        raise NotImplementedError


class DisabledFabricAdapter(FabricAdapter):
    """A no-op adapter used when Fabric is not configured/operational."""

    enabled = False

    def __init__(self) -> None:
        if self.enabled:
            raise FabricModeDisabledError(
                "Fabric is not configured. Set FABRIC_MODE=disabled or run "
                "the network; this adapter refuses to fabricate a result."
            )

    def submit(self, chaincode: str, fcn: str, args: List[str]) -> Dict[str, Any]:
        raise FabricModeDisabledError(
            "Fabric is not enabled. Contact the blockchain team before "
            "submission will be allowed."
        )

    def query(self, chaincode: str, fcn: str, args: List[str]) -> Dict[str, Any]:
        raise FabricModeDisabledError(
            "Fabric is not enabled, so no ledger query is possible."
        )

    def query_transaction(self, tx_id: str) -> Dict[str, Any]:
        raise FabricModeDisabledError(
            "Fabric is not enabled, so no transaction status is available."
        )

    def close(self) -> None:
        return None


def get_adapter() -> FabricAdapter:
    """Return the configured adapter implementation.

    The production deployment should replace this function (or the branch
    within it) with a real Fabric Gateway SDK client once the network is
    available. Until then the adapter runs in a strictly local, logged mode.
    """
    mode = (os.environ.get("FABRIC_MODE", "disabled") or "disabled").strip().lower()

    if mode == "disabled":
        return DisabledFabricAdapter()

    # Production path. A real implementation must be installed here once the
    # network, gateway URL, and credentials exist. No credentials are loaded
    # from source code; every secret comes from the environment.
    raise FabricModeDisabledError(
        "No Fabric adapter implementation is installed. Configure FABRIC_MODE=enabled "
        "and provide a real FabricGateway implementation before anchoring data."
    )
