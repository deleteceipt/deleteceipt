from __future__ import annotations

import pytest

from deleteceipt.audit import AuditLog
from deleteceipt.reconcile import Reconciler, InMemoryReceiptStore


def _log_with_delete(job_id: str = "job-1") -> AuditLog:
    log = AuditLog()
    log.append_event("upload", job_id=job_id, metadata={"filename": "doc.pdf"})
    log.append_event("processing_complete", job_id=job_id, metadata={})
    log.append_event("deleted", job_id=job_id, metadata={"files_deleted": []})
    return log


class TestReconcilerTypeA:
    def test_no_inconsistency_when_receipt_exists(self):
        log = _log_with_delete()
        store = InMemoryReceiptStore()
        store.insert({"job_id": "job-1", "deleted_at": "2025-01-01T00:00:00"})
        r = Reconciler(audit_log=log, receipt_store=store)
        report = r.run()
        assert report["total_fixed"] == 0

    def test_regenerates_missing_receipt(self):
        log = _log_with_delete()
        store = InMemoryReceiptStore()
        r = Reconciler(audit_log=log, receipt_store=store)
        report = r.run()
        assert report["total_fixed"] == 1
        assert len(report["type_a_fixed"]) == 1
        assert report["type_a_fixed"][0]["job_id"] == "job-1"

    def test_regenerated_receipt_stored(self):
        log = _log_with_delete()
        store = InMemoryReceiptStore()
        Reconciler(audit_log=log, receipt_store=store).run()
        receipts = store.get("job-1")
        assert len(receipts) == 1
        assert receipts[0]["notes"].startswith("Receipt generated during reconciliation")

    def test_idempotent_second_run(self):
        log = _log_with_delete()
        store = InMemoryReceiptStore()
        r = Reconciler(audit_log=log, receipt_store=store)
        r.run()
        report2 = r.run()
        assert report2["total_fixed"] == 0

    def test_no_delete_event_no_action(self):
        log = AuditLog()
        log.append_event("upload", job_id="job-1", metadata={})
        store = InMemoryReceiptStore()
        report = Reconciler(audit_log=log, receipt_store=store).run()
        assert report["total_fixed"] == 0

    def test_ran_at_present(self):
        log = AuditLog()
        store = InMemoryReceiptStore()
        report = Reconciler(audit_log=log, receipt_store=store).run()
        assert "ran_at" in report

    def test_multiple_jobs(self):
        log = AuditLog()
        for jid in ("job-a", "job-b", "job-c"):
            log.append_event("upload", job_id=jid, metadata={})
            log.append_event("deleted", job_id=jid, metadata={"files_deleted": []})
        store = InMemoryReceiptStore()
        report = Reconciler(audit_log=log, receipt_store=store).run()
        assert report["total_fixed"] == 3
