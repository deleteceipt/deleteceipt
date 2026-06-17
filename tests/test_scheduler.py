from __future__ import annotations

import pytest

from deleteceipt.audit import AuditLog
from deleteceipt.scheduler import DeletionScheduler, StorePolicy


def _make_policy(name: str, expired_ids: list[str], deleted: list[str]) -> StorePolicy:
    return StorePolicy(
        name=name,
        ttl_seconds=3600,
        find_expired=lambda: list(expired_ids),
        delete_job=lambda job_id: deleted.append(job_id) or {"job_id": job_id},
        description=f"Test policy: {name}",
    )


class TestDeletionScheduler:
    def test_empty_scheduler_runs_clean(self):
        s = DeletionScheduler()
        report = s.run()
        assert report["deleted_count"] == 0
        assert report["policies_run"] == 0
        assert report["errors"] == []

    def test_deletes_expired_jobs(self):
        deleted = []
        s = DeletionScheduler()
        s.register(_make_policy("files", ["job-1", "job-2"], deleted))
        report = s.run()
        assert report["deleted_count"] == 2
        assert set(deleted) == {"job-1", "job-2"}

    def test_no_expired_jobs_nothing_deleted(self):
        deleted = []
        s = DeletionScheduler()
        s.register(_make_policy("files", [], deleted))
        report = s.run()
        assert report["deleted_count"] == 0
        assert deleted == []

    def test_multiple_policies_run(self):
        deleted_a, deleted_b = [], []
        s = DeletionScheduler()
        s.register(_make_policy("store-a", ["j1"], deleted_a))
        s.register(_make_policy("store-b", ["j2", "j3"], deleted_b))
        report = s.run()
        assert report["deleted_count"] == 3
        assert report["policies_run"] == 2

    def test_error_in_find_expired_recorded(self):
        def bad_find():
            raise RuntimeError("db down")

        s = DeletionScheduler()
        s.register(StorePolicy(
            name="broken",
            ttl_seconds=3600,
            find_expired=bad_find,
            delete_job=lambda j: {},
        ))
        report = s.run()
        assert len(report["errors"]) == 1
        assert "broken" in report["errors"][0]

    def test_error_in_delete_job_recorded(self):
        def bad_delete(job_id):
            raise RuntimeError("disk full")

        s = DeletionScheduler()
        s.register(StorePolicy(
            name="files",
            ttl_seconds=3600,
            find_expired=lambda: ["job-1"],
            delete_job=bad_delete,
        ))
        report = s.run()
        assert report["deleted_count"] == 0
        assert len(report["errors"]) == 1

    def test_appends_audit_event_when_log_provided(self):
        log = AuditLog()
        deleted = []
        s = DeletionScheduler(audit_log=log)
        s.register(_make_policy("files", ["job-1"], deleted))
        s.run()
        entries = log._backend.get_all_ordered()
        assert any(e["event_type"] == "ttl_cleanup" for e in entries)

    def test_ran_at_in_report(self):
        s = DeletionScheduler()
        report = s.run()
        assert "ran_at" in report

    def test_inventory_returns_registered_policies(self):
        s = DeletionScheduler()
        s.register(_make_policy("p1", [], []))
        s.register(_make_policy("p2", [], []))
        inv = s.inventory()
        assert len(inv) == 2
        assert inv[0]["name"] == "p1"
        assert inv[1]["ttl_seconds"] == 3600
