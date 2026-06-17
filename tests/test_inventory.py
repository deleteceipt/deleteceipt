from __future__ import annotations

import pytest

from deleteceipt.inventory import DataInventory, StorageLayerEntry, DeletionMechanism


def _full_entry(name: str = "postgres:users") -> StorageLayerEntry:
    return StorageLayerEntry(
        name=name,
        data_held="User profiles",
        retention_policy="Deleted on account closure",
        mechanism=DeletionMechanism.HARD_DELETE,
        deletion_hook_wired=True,
        tested=True,
        monitored=True,
    )


def _bare_entry(name: str = "kafka:events") -> StorageLayerEntry:
    return StorageLayerEntry(
        name=name,
        data_held="Event stream",
        retention_policy="",
        mechanism=DeletionMechanism.NONE,
        deletion_hook_wired=False,
        tested=False,
        monitored=False,
    )


class TestStorageLayerEntry:
    def test_full_entry_score_is_4(self):
        assert _full_entry().maturity_score() == 4

    def test_full_entry_label(self):
        assert _full_entry().maturity_label() == "Monitored"

    def test_no_mechanism_score_is_0(self):
        assert _bare_entry().maturity_score() == 0

    def test_wired_but_untested_score_is_2(self):
        e = StorageLayerEntry(
            name="x", data_held="d", retention_policy="p",
            mechanism=DeletionMechanism.HARD_DELETE,
            deletion_hook_wired=True, tested=False, monitored=False,
        )
        assert e.maturity_score() == 2

    def test_wired_and_tested_score_is_3(self):
        e = StorageLayerEntry(
            name="x", data_held="d", retention_policy="p",
            mechanism=DeletionMechanism.HARD_DELETE,
            deletion_hook_wired=True, tested=True, monitored=False,
        )
        assert e.maturity_score() == 3

    def test_bare_entry_has_gaps(self):
        gaps = _bare_entry().gaps()
        assert len(gaps) > 0

    def test_full_entry_has_no_gaps(self):
        gaps = _full_entry().gaps()
        assert gaps == []


class TestDataInventory:
    def test_empty_inventory_report(self):
        inv = DataInventory()
        report = inv.generate_report()
        assert report["total_layers"] == 0
        assert report["average_maturity"] == 0.0

    def test_single_layer_report(self):
        inv = DataInventory()
        inv.register(_full_entry())
        report = inv.generate_report()
        assert report["total_layers"] == 1
        assert report["average_maturity"] == 4.0
        assert report["overall_label"] == "Exemplary"

    def test_mixed_layers_average(self):
        inv = DataInventory()
        inv.register(_full_entry("a"))   # score 4
        inv.register(_bare_entry("b"))   # score 0
        report = inv.generate_report()
        assert report["average_maturity"] == 2.0

    def test_gaps_collected(self):
        inv = DataInventory()
        inv.register(_bare_entry())
        report = inv.generate_report()
        assert len(report["gaps"]) > 0

    def test_no_gaps_when_all_full(self):
        inv = DataInventory()
        inv.register(_full_entry("a"))
        inv.register(_full_entry("b"))
        report = inv.generate_report()
        assert report["gaps"] == []

    def test_generated_at_present(self):
        inv = DataInventory()
        report = inv.generate_report()
        assert "generated_at" in report

    def test_summary_contains_layer_count(self):
        inv = DataInventory()
        inv.register(_full_entry())
        report = inv.generate_report()
        assert "1" in report["summary"]

    def test_transparency_table(self):
        inv = DataInventory()
        inv.register(_full_entry("postgres:users"))
        table = inv.transparency_table()
        assert len(table) == 1
        assert table[0]["layer"] == "postgres:users"
        assert table[0]["status"] == "Monitored"

    def test_overall_labels(self):
        from deleteceipt.inventory import _overall_label
        assert _overall_label(4.0) == "Exemplary"
        assert _overall_label(3.0) == "Advanced"
        assert _overall_label(2.0) == "Developing"
        assert _overall_label(0.5) == "Foundational"
