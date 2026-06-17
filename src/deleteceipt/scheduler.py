"""TTL-based deletion scheduler.

Every data store should have a documented retention policy.  This module
provides a lightweight, dependency-free TTL engine that:

  1. Accepts registered stores with their TTL configuration.
  2. On each ``run()`` call, identifies jobs/records that have exceeded
     their TTL and invokes a caller-supplied deletion function.
  3. Records the deletion outcome and returns a run report.

It is designed to plug into any scheduler (Celery Beat, APScheduler,
a cron job, or a simple ``while True`` loop).

Usage::

    from deleteceipt.scheduler import DeletionScheduler, StorePolicy

    scheduler = DeletionScheduler(audit_log=log)
    scheduler.register(StorePolicy(
        name="processing-files",
        ttl_seconds=3600,
        find_expired=my_find_expired_fn,
        delete_job=my_delete_fn,
    ))

    report = scheduler.run()
    print(report["deleted_count"])
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable


@dataclass
class StorePolicy:
    """Configuration for one storage layer's TTL policy.

    Attributes:
        name: Human-readable identifier (e.g. ``"processing-files"``).
        ttl_seconds: How long a job's data may remain after upload.
        find_expired: Callable() -> list[str] — returns job_ids that have
                      exceeded TTL and not yet been deleted.
        delete_job: Callable(job_id: str) -> dict — performs the actual
                    deletion and returns a result dict (may include
                    ``files_deleted``, ``trigger``, etc.).
        description: Optional documentation string for the transparency page.
    """
    name: str
    ttl_seconds: int
    find_expired: Callable[[], list[str]]
    delete_job: Callable[[str], dict]
    description: str = ""


class DeletionScheduler:
    """Runs registered TTL policies and reports outcomes.

    Args:
        audit_log: Optional AuditLog instance.  When provided, a
                   ``ttl_cleanup`` event is appended after each run.
    """

    def __init__(self, audit_log=None) -> None:
        self._policies: list[StorePolicy] = []
        self._audit_log = audit_log

    def register(self, policy: StorePolicy) -> None:
        """Register a store policy."""
        self._policies.append(policy)

    def run(self) -> dict:
        """Execute one cleanup pass across all registered policies.

        Returns::

            {
                "ran_at": str,
                "policies_run": int,
                "deleted_count": int,
                "errors": [...],
                "results": {policy_name: {deleted: [...], errors: [...]}},
            }
        """
        ran_at = datetime.now(timezone.utc).isoformat()
        total_deleted = 0
        all_errors: list[str] = []
        results: dict[str, dict] = {}

        for policy in self._policies:
            deleted: list[str] = []
            errors: list[str] = []

            try:
                expired = policy.find_expired()
            except Exception as exc:
                all_errors.append(f"{policy.name}: find_expired failed: {exc}")
                results[policy.name] = {"deleted": [], "errors": [str(exc)]}
                continue

            for job_id in expired:
                try:
                    policy.delete_job(job_id)
                    deleted.append(job_id)
                    total_deleted += 1

                    if self._audit_log is not None:
                        self._audit_log.append_event(
                            "ttl_cleanup",
                            job_id=job_id,
                            metadata={"store": policy.name, "ttl_seconds": policy.ttl_seconds},
                        )
                except Exception as exc:
                    errors.append(f"{job_id}: {exc}")
                    all_errors.append(f"{policy.name}/{job_id}: {exc}")

            results[policy.name] = {"deleted": deleted, "errors": errors}

        return {
            "ran_at": ran_at,
            "policies_run": len(self._policies),
            "deleted_count": total_deleted,
            "errors": all_errors,
            "results": results,
        }

    def inventory(self) -> list[dict]:
        """Return a list of registered policies for the transparency page."""
        return [
            {
                "name": p.name,
                "ttl_seconds": p.ttl_seconds,
                "description": p.description,
            }
            for p in self._policies
        ]
