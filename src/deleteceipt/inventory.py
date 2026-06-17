"""Data inventory and deletion-readiness scanner.

Provides a structured audit of every storage layer in a system, producing
a deletion-readiness report that answers the question from Chapter 15.1:
"Does your system truly delete?"

The ``DataInventory`` class holds a registry of ``StorageLayerEntry`` records,
each describing one storage system and its deletion controls.  The
``generate_report()`` method scores each layer and produces a structured
report suitable for the transparency page.

Usage::

    from deleteceipt.inventory import DataInventory, StorageLayerEntry, DeletionMechanism

    inv = DataInventory()
    inv.register(StorageLayerEntry(
        name="postgres:users",
        data_held="User profiles, email addresses",
        retention_policy="Deleted on account closure",
        mechanism=DeletionMechanism.HARD_DELETE,
        ttl_seconds=None,
        deletion_hook_wired=True,
        tested=True,
        notes="Hard delete via DELETE WHERE id=:user_id",
    ))

    report = inv.generate_report()
    print(report["summary"])
    print(report["gaps"])
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class DeletionMechanism(str, Enum):
    HARD_DELETE = "hard_delete"
    SOFT_DELETE_WITH_PIPELINE = "soft_delete_with_pipeline"
    TTL_EXPIRY = "ttl_expiry"
    CRYPTO_SHREDDING = "crypto_shredding"
    KEY_DELETION = "key_deletion"
    LOG_ROTATION = "log_rotation"
    MANUAL = "manual"
    NONE = "none"
    UNKNOWN = "unknown"


@dataclass
class StorageLayerEntry:
    """Describes one storage layer and its deletion controls.

    Attributes:
        name: Identifier (e.g. ``"postgres:users"``, ``"redis:session_cache"``).
        data_held: Human-readable description of personal data stored.
        retention_policy: Documented retention policy text.
        mechanism: How deletion is implemented.
        ttl_seconds: For TTL-based stores, the configured TTL.  ``None`` if N/A.
        deletion_hook_wired: Whether the deletion pipeline explicitly calls
                             this layer's delete API.
        tested: Whether automated tests verify deletion on this layer.
        monitored: Whether continuous monitoring/alerting is in place.
        notes: Additional implementation notes.
    """
    name: str
    data_held: str
    retention_policy: str
    mechanism: DeletionMechanism = DeletionMechanism.UNKNOWN
    ttl_seconds: Optional[int] = None
    deletion_hook_wired: bool = False
    tested: bool = False
    monitored: bool = False
    notes: str = ""

    def maturity_score(self) -> int:
        """Return a 0–4 maturity score for this layer.

        0 — No deletion mechanism
        1 — Mechanism documented but not implemented
        2 — Implemented (hook wired)
        3 — Implemented and tested
        4 — Implemented, tested, and monitored
        """
        if self.mechanism == DeletionMechanism.NONE:
            return 0
        if self.mechanism == DeletionMechanism.UNKNOWN:
            return 0
        if not self.deletion_hook_wired:
            return 1
        if not self.tested:
            return 2
        if not self.monitored:
            return 3
        return 4

    def maturity_label(self) -> str:
        return ["None", "Documented", "Implemented", "Tested", "Monitored"][self.maturity_score()]

    def gaps(self) -> list[str]:
        issues: list[str] = []
        if self.mechanism in (DeletionMechanism.NONE, DeletionMechanism.UNKNOWN):
            issues.append("No deletion mechanism defined")
        if self.mechanism == DeletionMechanism.SOFT_DELETE_WITH_PIPELINE and not self.deletion_hook_wired:
            issues.append("Soft delete detected — hard-delete pipeline not confirmed wired")
        if not self.deletion_hook_wired:
            issues.append("Deletion hook not confirmed wired to this layer")
        if not self.tested:
            issues.append("No automated tests verify deletion on this layer")
        if not self.monitored:
            issues.append("No continuous monitoring or alerting configured")
        if not self.retention_policy:
            issues.append("No documented retention policy")
        return issues


class DataInventory:
    """Registry of storage layers and their deletion controls."""

    CHECKLIST_CATEGORIES = [
        "primary_database",
        "search_index",
        "cache",
        "message_queue",
        "backup_archive",
        "logs_observability",
        "third_party_processor",
        "ml_model",
        "audit_log",
    ]

    def __init__(self) -> None:
        self._layers: list[StorageLayerEntry] = []

    def register(self, entry: StorageLayerEntry) -> None:
        """Register a storage layer."""
        self._layers.append(entry)

    def generate_report(self) -> dict:
        """Produce a deletion-readiness report.

        Returns::

            {
                "generated_at": str,
                "total_layers": int,
                "average_maturity": float,
                "overall_label": str,
                "layers": [...],     # per-layer scores and gaps
                "gaps": [...],       # all unresolved gaps
                "summary": str,
            }
        """
        now = datetime.now(timezone.utc).isoformat()
        layer_reports = []
        all_gaps: list[dict] = []

        scores = []
        for entry in self._layers:
            score = entry.maturity_score()
            scores.append(score)
            gaps = entry.gaps()
            layer_reports.append({
                "name": entry.name,
                "data_held": entry.data_held,
                "retention_policy": entry.retention_policy,
                "mechanism": entry.mechanism.value,
                "ttl_seconds": entry.ttl_seconds,
                "maturity_score": score,
                "maturity_label": entry.maturity_label(),
                "gaps": gaps,
                "notes": entry.notes,
            })
            for gap in gaps:
                all_gaps.append({"layer": entry.name, "gap": gap, "maturity_score": score})

        avg = sum(scores) / len(scores) if scores else 0.0
        overall = _overall_label(avg)

        summary_lines = [
            f"Data Inventory Report — {now}",
            f"Layers assessed: {len(self._layers)}",
            f"Average maturity: {avg:.1f}/4 ({overall})",
            f"Unresolved gaps:  {len(all_gaps)}",
        ]
        if all_gaps:
            summary_lines.append("\nTop gaps requiring attention:")
            for g in sorted(all_gaps, key=lambda x: x["maturity_score"])[:5]:
                summary_lines.append(f"  [{g['layer']}] {g['gap']}")

        return {
            "generated_at": now,
            "total_layers": len(self._layers),
            "average_maturity": round(avg, 2),
            "overall_label": overall,
            "layers": layer_reports,
            "gaps": all_gaps,
            "summary": "\n".join(summary_lines),
        }

    def transparency_table(self) -> list[dict]:
        """Return rows suitable for a public transparency page."""
        return [
            {
                "layer": e.name,
                "data_held": e.data_held,
                "retention_policy": e.retention_policy,
                "mechanism": e.mechanism.value,
                "ttl_seconds": e.ttl_seconds,
                "status": e.maturity_label(),
            }
            for e in self._layers
        ]


def _overall_label(avg: float) -> str:
    if avg >= 3.5:
        return "Exemplary"
    if avg >= 2.5:
        return "Advanced"
    if avg >= 1.5:
        return "Developing"
    return "Foundational"
