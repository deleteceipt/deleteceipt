"""Reconciliation job for deletion inconsistencies.

Detects and remedies two classes of inconsistency that arise when the
deletion pipeline is interrupted mid-flight:

  Type A — ``deleted`` audit event exists but no receipt document.
            Remedy: regenerate the receipt from audit log data.

  Type B — Filesystem still contains the job directory despite a
            ``deleted`` audit event.
            Remedy: re-run filesystem deletion and update the receipt.

The reconciliation job should run nightly (or on any schedule appropriate
for your SLA).  It is designed to be idempotent: running it twice produces
the same result.

Usage::

    from deleteceipt.reconcile import Reconciler, InMemoryReceiptStore
    from deleteceipt.audit import AuditLog

    log = AuditLog()
    store = InMemoryReceiptStore()
    reconciler = Reconciler(audit_log=log, receipt_store=store)
    report = reconciler.run()
    print(report)
"""
from __future__ import annotations

import json
import os
import pathlib
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable


# ---------------------------------------------------------------------------
# Receipt store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ReceiptStore(Protocol):
    def get(self, job_id: str) -> list[dict]: ...
    def insert(self, receipt: dict) -> None: ...


class InMemoryReceiptStore:
    """Simple in-memory receipt store for testing."""

    def __init__(self) -> None:
        self._receipts: list[dict] = []

    def get(self, job_id: str) -> list[dict]:
        return [r for r in self._receipts if r.get("job_id") == job_id]

    def insert(self, receipt: dict) -> None:
        self._receipts.append(receipt)

    def all(self) -> list[dict]:
        return list(self._receipts)


# ---------------------------------------------------------------------------
# Filesystem helpers
# ---------------------------------------------------------------------------

def _delete_directory_tree(job_dir: str) -> list[dict]:
    """Walk a job directory, delete all files, remove empty dirs.

    Returns list of dicts: {path, size_bytes, role}
    """
    deleted: list[dict] = []
    job_path = pathlib.Path(job_dir)
    if not job_path.exists():
        return deleted

    for file_path in job_path.rglob("*"):
        if file_path.is_file():
            size = file_path.stat().st_size
            role = _infer_role(file_path.name)
            os.remove(file_path)
            deleted.append({"path": str(file_path), "size_bytes": size, "role": role})

    for dir_path in sorted(job_path.rglob("*"), reverse=True):
        if dir_path.is_dir():
            dir_path.rmdir()
    job_path.rmdir()
    return deleted


def _infer_role(filename: str) -> str:
    name = filename.lower()
    if any(name.endswith(ext) for ext in (".pdf", ".docx", ".doc", ".png", ".jpg")):
        return "input"
    if "output" in name or "result" in name:
        return "output"
    return "intermediate"


# ---------------------------------------------------------------------------
# Reconciler
# ---------------------------------------------------------------------------

class Reconciler:
    """Detects and remediates deletion inconsistencies.

    Args:
        audit_log: An AuditLog (or AsyncAuditLog) instance.
        receipt_store: A ReceiptStore implementation.
        storage_root: Optional root directory for job filesystem trees.
                      When provided, Type B inconsistencies (orphan directories)
                      are also detected and remedied.
    """

    def __init__(
        self,
        audit_log,
        receipt_store: ReceiptStore,
        storage_root: str | None = None,
    ) -> None:
        self._log = audit_log
        self._store = receipt_store
        self._root = storage_root

    def run(self) -> dict:
        """Run one reconciliation pass.

        Returns a report dict::

            {
                "type_a_fixed": [...],   # receipts regenerated from audit log
                "type_b_fixed": [...],   # orphan directories deleted
                "errors": [...],
                "total_fixed": int,
                "ran_at": str,
            }
        """
        type_a: list[dict] = []
        type_b: list[dict] = []
        errors: list[str] = []

        entries = self._log._backend.get_all_ordered()

        # Collect job_ids that have a 'deleted' audit event
        deleted_job_ids: set[str] = set()
        upload_events: dict[str, dict] = {}
        delete_events: dict[str, dict] = {}

        for e in entries:
            jid = e.get("job_id", "")
            if e.get("event_type") == "upload":
                upload_events[jid] = e
            if e.get("event_type") == "deleted":
                deleted_job_ids.add(jid)
                delete_events[jid] = e

        # Type A: deleted event exists but no receipt
        for job_id in deleted_job_ids:
            receipts = self._store.get(job_id)
            if not receipts:
                try:
                    receipt = self._regenerate_receipt(
                        job_id, upload_events.get(job_id), delete_events[job_id]
                    )
                    self._store.insert(receipt)
                    type_a.append({"job_id": job_id, "action": "receipt_regenerated"})
                except Exception as exc:
                    errors.append(f"Type A {job_id}: {exc}")

        # Type B: orphan directories for jobs that have a deleted event
        if self._root:
            root = pathlib.Path(self._root)
            if root.exists():
                for job_dir in root.iterdir():
                    if not job_dir.is_dir():
                        continue
                    job_id = job_dir.name
                    if job_id in deleted_job_ids:
                        try:
                            deleted_files = _delete_directory_tree(str(job_dir))
                            receipt = self._build_supplementary_receipt(
                                job_id, deleted_files, delete_events.get(job_id, {})
                            )
                            self._store.insert(receipt)
                            type_b.append({
                                "job_id": job_id,
                                "action": "orphan_directory_deleted",
                                "files_deleted": len(deleted_files),
                            })
                        except Exception as exc:
                            errors.append(f"Type B {job_id}: {exc}")

        return {
            "type_a_fixed": type_a,
            "type_b_fixed": type_b,
            "errors": errors,
            "total_fixed": len(type_a) + len(type_b),
            "ran_at": datetime.now(timezone.utc).isoformat(),
        }

    def _regenerate_receipt(
        self, job_id: str, upload_event: dict | None, delete_event: dict
    ) -> dict:
        return {
            "job_id": job_id,
            "file_hash_sha256": upload_event.get("file_hash_sha256", "") if upload_event else "",
            "uploaded_at": upload_event.get("timestamp", "") if upload_event else "",
            "processing_completed_at": delete_event.get("timestamp", ""),
            "deleted_at": delete_event.get("timestamp", ""),
            "files_deleted": delete_event.get("files_deleted", []),
            "notes": "Receipt generated during reconciliation; original deletion was interrupted.",
            "trigger": delete_event.get("trigger", "ttl_expiry_recovery"),
        }

    def _build_supplementary_receipt(
        self, job_id: str, deleted_files: list[dict], delete_event: dict
    ) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        return {
            "job_id": job_id,
            "deleted_at": now,
            "files_deleted": deleted_files,
            "notes": "Supplementary receipt: orphan directory found and deleted during reconciliation.",
            "supersedes": job_id,
            "supplementary_run": True,
            "trigger": "ttl_expiry_recovery",
        }
