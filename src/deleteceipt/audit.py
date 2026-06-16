"""Tamper-evident, hash-chained audit log.

Each entry is linked to the previous via SHA-256, so any retroactive
modification breaks the chain. Only file metadata is stored — never
file content.

Events (conventional, not enforced):
    upload              file received
    processing_start    pipeline began
    processing_complete pipeline finished
    deleted             job directory removed
    download            output artifact downloaded

Storage backends
----------------
The AuditLog class accepts any object that implements the StorageBackend
protocol. Two backends are provided:

    InMemoryBackend         — for testing and embedding (sync)
    MongoBackend            — for production (requires pymongo, sync)

For async workloads (e.g. FastAPI / asyncio):

    AsyncMongoBackend       — Motor-based async backend (requires motor)
    AsyncAuditLog           — mirrors AuditLog with async/await API
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StorageBackend(Protocol):
    def get_last(self) -> dict | None: ...
    def insert(self, entry: dict) -> None: ...
    def get_all_ordered(self) -> list[dict]: ...


class InMemoryBackend:
    """Simple in-memory backend. Not thread-safe. Use for tests only."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    def get_last(self) -> dict | None:
        return self._entries[-1] if self._entries else None

    def insert(self, entry: dict) -> None:
        self._entries.append(entry)

    def get_all_ordered(self) -> list[dict]:
        return list(self._entries)


class MongoBackend:
    """Production backend using a synchronous pymongo collection.

    The collection must be configured to allow inserts only (no updates
    or deletes) to maintain append-only semantics.

    Args:
        collection: A pymongo Collection instance.
    """

    def __init__(self, collection) -> None:
        self._col = collection

    def get_last(self) -> dict | None:
        return self._col.find_one(sort=[("seq", -1)])

    def insert(self, entry: dict) -> None:
        self._col.insert_one(entry)

    def get_all_ordered(self) -> list[dict]:
        return list(self._col.find({}, {"_id": 0}).sort("seq", 1))


def _build_entry(seq: int, prev_hash: str, event_type: str, job_id: str, metadata: dict) -> dict:
    entry: dict = {
        "seq": seq,
        "event_type": event_type,
        "job_id": job_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "prev_hash": prev_hash,
        **metadata,
    }
    canonical = json.dumps(entry, sort_keys=True, default=str)
    entry["entry_hash"] = hashlib.sha256(canonical.encode()).hexdigest()
    return entry


class AuditLog:
    """Append-only, hash-chained audit log.

    Usage::

        log = AuditLog()  # uses InMemoryBackend by default
        log.append_event("upload", job_id="abc", metadata={"filename": "doc.pdf", "size_bytes": 4096})
        log.append_event("deleted", job_id="abc", metadata={"files_count": 3})
        result = log.verify_chain()
        assert result["valid"]

    For production with MongoDB::

        from pymongo import MongoClient
        from deleteceipt.audit import AuditLog, MongoBackend

        col = MongoClient(url)["mydb"]["audit_log"]
        log = AuditLog(backend=MongoBackend(col))
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, backend: StorageBackend | None = None) -> None:
        self._backend = backend or InMemoryBackend()

    def append_event(self, event_type: str, job_id: str, metadata: dict) -> dict:
        """Append a hash-chained event. metadata must contain only scalar values.

        Returns the stored entry dict (including entry_hash).
        """
        last = self._backend.get_last()
        prev_hash = last.get("entry_hash", self.GENESIS_HASH) if last else self.GENESIS_HASH
        seq = (last["seq"] + 1) if last else 1

        entry = _build_entry(seq, prev_hash, event_type, job_id, metadata)
        self._backend.insert(entry)
        return entry

    def verify_chain(self) -> dict:
        """Walk the full chain and verify every entry_hash is consistent.

        Returns:
            {"valid": True, "broken_at_seq": None, "total_entries": N}
            or
            {"valid": False, "broken_at_seq": int, "total_entries": N}
        """
        entries = self._backend.get_all_ordered()
        for entry in entries:
            entry = dict(entry)
            stored_hash = entry.pop("entry_hash", None)
            canonical = json.dumps(entry, sort_keys=True, default=str)
            expected = hashlib.sha256(canonical.encode()).hexdigest()
            if stored_hash != expected:
                return {"valid": False, "broken_at_seq": entry["seq"], "total_entries": len(entries)}
            entry["entry_hash"] = stored_hash
        return {"valid": True, "broken_at_seq": None, "total_entries": len(entries)}


# ---------------------------------------------------------------------------
# Async API
# ---------------------------------------------------------------------------

@runtime_checkable
class AsyncStorageBackend(Protocol):
    """Protocol that async storage backends must implement."""

    async def get_last(self) -> dict | None: ...
    async def insert(self, entry: dict) -> None: ...
    async def get_all_ordered(self) -> list[dict]: ...


class AsyncMongoBackend:
    """Production async backend using a Motor (async pymongo) collection.

    The collection must be configured to allow inserts only (no updates
    or deletes) to maintain append-only semantics.

    Args:
        collection: A Motor AsyncIOMotorCollection instance.

    Example::

        import motor.motor_asyncio
        client = motor.motor_asyncio.AsyncIOMotorClient(url)
        col = client["mydb"]["audit_log"]
        backend = AsyncMongoBackend(col)
        log = AsyncAuditLog(backend=backend)
    """

    def __init__(self, collection: Any) -> None:
        self._col = collection

    async def get_last(self) -> dict | None:
        return await self._col.find_one(sort=[("seq", -1)])

    async def insert(self, entry: dict) -> None:
        await self._col.insert_one(entry)

    async def get_all_ordered(self) -> list[dict]:
        cursor = self._col.find({}, {"_id": 0}).sort("seq", 1)
        return await cursor.to_list(length=None)


class AsyncInMemoryBackend:
    """Async in-memory backend for testing AsyncAuditLog without Motor."""

    def __init__(self) -> None:
        self._entries: list[dict] = []

    async def get_last(self) -> dict | None:
        return self._entries[-1] if self._entries else None

    async def insert(self, entry: dict) -> None:
        self._entries.append(entry)

    async def get_all_ordered(self) -> list[dict]:
        return list(self._entries)


class AsyncAuditLog:
    """Async append-only, hash-chained audit log.

    Mirrors :class:`AuditLog` but with ``async``/``await`` semantics so it
    can be used inside FastAPI route handlers and other asyncio contexts
    without blocking the event loop.

    Usage::

        log = AsyncAuditLog()  # uses AsyncInMemoryBackend by default
        await log.append_event("upload", job_id="abc", metadata={"filename": "doc.pdf"})
        await log.append_event("deleted", job_id="abc", metadata={"files_count": 3})
        result = await log.verify_chain()
        assert result["valid"]

    For production with Motor::

        import motor.motor_asyncio
        from deleteceipt.audit import AsyncAuditLog, AsyncMongoBackend

        col = motor.motor_asyncio.AsyncIOMotorClient(url)["db"]["audit_log"]
        log = AsyncAuditLog(backend=AsyncMongoBackend(col))
    """

    GENESIS_HASH = "0" * 64

    def __init__(self, backend: AsyncStorageBackend | None = None) -> None:
        self._backend: AsyncStorageBackend = backend or AsyncInMemoryBackend()

    async def append_event(self, event_type: str, job_id: str, metadata: dict) -> dict:
        """Append a hash-chained event asynchronously.

        Returns the stored entry dict (including entry_hash).
        """
        last = await self._backend.get_last()
        prev_hash = last.get("entry_hash", self.GENESIS_HASH) if last else self.GENESIS_HASH
        seq = (last["seq"] + 1) if last else 1

        entry = _build_entry(seq, prev_hash, event_type, job_id, metadata)
        await self._backend.insert(entry)
        return entry

    async def verify_chain(self) -> dict:
        """Walk the full chain and verify every entry_hash is consistent.

        Returns:
            {"valid": True, "broken_at_seq": None, "total_entries": N}
            or
            {"valid": False, "broken_at_seq": int, "total_entries": N}
        """
        entries = await self._backend.get_all_ordered()
        for entry in entries:
            entry = dict(entry)
            stored_hash = entry.pop("entry_hash", None)
            canonical = json.dumps(entry, sort_keys=True, default=str)
            expected = hashlib.sha256(canonical.encode()).hexdigest()
            if stored_hash != expected:
                return {
                    "valid": False,
                    "broken_at_seq": entry["seq"],
                    "total_entries": len(entries),
                }
            entry["entry_hash"] = stored_hash
        return {"valid": True, "broken_at_seq": None, "total_entries": len(entries)}
