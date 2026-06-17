"""Legal hold gate for deletion pipelines.

When an organization is subject to litigation or regulatory investigation,
it must preserve data that would otherwise be deleted.  Deleting data
under a legal hold can constitute spoliation — a serious legal violation.

This module provides a ``LegalHoldGate`` that intercepts deletion requests,
checks a hold store, and either:

  - Blocks deletion and returns a ``HoldNotification`` (not a receipt).
  - Passes through to the deletion pipeline when no hold applies.

When a hold is lifted, ``release_hold()`` clears the hold and the normal
deletion pipeline can proceed.

Usage::

    from deleteceipt.legal_hold import LegalHoldGate, InMemoryHoldStore

    store = InMemoryHoldStore()
    gate = LegalHoldGate(hold_store=store)

    # Place a hold
    gate.place_hold("job-123", reason="Active litigation: Case 2025-CV-001")

    # Attempt deletion — will be blocked
    result = gate.check("job-123")
    assert result["held"] is True
    assert result["notification"]["type"] == "hold_notification"

    # Release hold
    gate.release_hold("job-123")

    result = gate.check("job-123")
    assert result["held"] is False
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Hold store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class HoldStore(Protocol):
    def get(self, job_id: str) -> dict | None: ...
    def put(self, job_id: str, hold: dict) -> None: ...
    def delete(self, job_id: str) -> None: ...
    def all_held(self) -> list[str]: ...


class InMemoryHoldStore:
    """Simple in-memory hold store for testing."""

    def __init__(self) -> None:
        self._holds: dict[str, dict] = {}

    def get(self, job_id: str) -> dict | None:
        return self._holds.get(job_id)

    def put(self, job_id: str, hold: dict) -> None:
        self._holds[job_id] = hold

    def delete(self, job_id: str) -> None:
        self._holds.pop(job_id, None)

    def all_held(self) -> list[str]:
        return list(self._holds.keys())


# ---------------------------------------------------------------------------
# Gate
# ---------------------------------------------------------------------------

class LegalHoldGate:
    """Intercepts deletion requests and enforces legal holds.

    Args:
        hold_store: A HoldStore implementation.
    """

    def __init__(self, hold_store: HoldStore) -> None:
        self._store = hold_store

    def place_hold(
        self,
        job_id: str,
        reason: str,
        reference: str = "",
    ) -> dict:
        """Place a legal hold on a job.

        Args:
            job_id: The job identifier to hold.
            reason: Human-readable reason (e.g. case name/number).
            reference: Optional external reference (ticket ID, court order number).

        Returns:
            The hold record that was stored.
        """
        hold = {
            "job_id": job_id,
            "reason": reason,
            "reference": reference,
            "placed_at": datetime.now(timezone.utc).isoformat(),
            "active": True,
        }
        self._store.put(job_id, hold)
        return hold

    def release_hold(self, job_id: str) -> dict:
        """Lift a legal hold.

        Args:
            job_id: The job identifier to release.

        Returns:
            A release record with timestamps.

        Raises:
            KeyError: If no active hold exists for this job_id.
        """
        hold = self._store.get(job_id)
        if hold is None:
            raise KeyError(f"No hold found for job_id={job_id!r}")
        self._store.delete(job_id)
        return {
            "job_id": job_id,
            "released_at": datetime.now(timezone.utc).isoformat(),
            "original_reason": hold.get("reason", ""),
            "original_reference": hold.get("reference", ""),
        }

    def check(self, job_id: str) -> dict:
        """Check whether a job is under a legal hold.

        Returns::

            {"held": False}
            or
            {
                "held": True,
                "notification": {
                    "type": "hold_notification",
                    "job_id": str,
                    "reason": str,
                    "placed_at": str,
                    "message": str,
                }
            }

        Callers should inspect ``result["held"]`` before proceeding with
        deletion.  When ``held`` is True, store the ``notification`` in
        place of a deletion receipt — it documents that deletion was
        requested but could not proceed due to the hold.
        """
        hold = self._store.get(job_id)
        if hold is None:
            return {"held": False}

        return {
            "held": True,
            "notification": {
                "type": "hold_notification",
                "job_id": job_id,
                "reason": hold.get("reason", ""),
                "reference": hold.get("reference", ""),
                "placed_at": hold.get("placed_at", ""),
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "message": (
                    "Deletion request received but cannot proceed. "
                    "This job is subject to a legal hold. "
                    "Deletion will be re-queued when the hold is lifted."
                ),
            },
        }

    def all_held(self) -> list[str]:
        """Return all currently held job IDs."""
        return self._store.all_held()
