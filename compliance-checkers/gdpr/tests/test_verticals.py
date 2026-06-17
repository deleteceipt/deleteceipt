"""Tests for checker.verticals — vertical definitions and cross-framework mappings."""

from __future__ import annotations

import pytest

from checker.verticals import VERTICALS, VERTICAL_WEIGHTS, CROSS_FRAMEWORK

EXPECTED_VERTICALS = {
    "general_saas",
    "healthcare",
    "financial_services",
    "legal_services",
    "public_sector_eu",
}

EXPECTED_SECTIONS = [
    "primary_storage",
    "search_indexes",
    "cache_invalidation",
    "message_queues",
    "backup_archive",
    "logs_observability",
    "third_party_processors",
    "ml_models",
    "deletion_receipt_issuance",
    "audit_log_integrity",
    "legal_hold_procedures",
    "federated_systems",
    "cryptographic_erasure",
    "deletion_testing",
]


class TestVerticals:
    def test_all_five_verticals_present(self):
        assert VERTICALS == EXPECTED_VERTICALS

    def test_vertical_weights_has_all_verticals(self):
        for v in EXPECTED_VERTICALS:
            assert v in VERTICAL_WEIGHTS, f"Missing vertical in VERTICAL_WEIGHTS: {v!r}"

    def test_each_vertical_has_all_sections(self):
        for vertical, weights in VERTICAL_WEIGHTS.items():
            for sid in EXPECTED_SECTIONS:
                assert sid in weights, (
                    f"Section {sid!r} missing from vertical {vertical!r} weights"
                )

    def test_all_weights_positive(self):
        for vertical, weights in VERTICAL_WEIGHTS.items():
            for sid, w in weights.items():
                assert w > 0, f"Weight for {sid!r} in {vertical!r} is not positive"

    def test_all_weights_reasonable_range(self):
        """Weights should be between 0.5 and 2.0 (no typos)."""
        for vertical, weights in VERTICAL_WEIGHTS.items():
            for sid, w in weights.items():
                assert 0.5 <= w <= 2.0, (
                    f"Weight {w} for {sid!r} in {vertical!r} out of [0.5, 2.0]"
                )

    def test_general_saas_weights_sensible(self):
        """general_saas has equal or near-equal weights — no huge outliers."""
        weights = VERTICAL_WEIGHTS["general_saas"]
        values = list(weights.values())
        assert max(values) <= 1.5, "general_saas has unexpectedly high weight"

    def test_healthcare_receipt_weight_elevated(self):
        """Healthcare weights deletion_receipt_issuance higher than general_saas."""
        assert (
            VERTICAL_WEIGHTS["healthcare"]["deletion_receipt_issuance"]
            > VERTICAL_WEIGHTS["general_saas"]["deletion_receipt_issuance"]
        )

    def test_healthcare_audit_log_weight_elevated(self):
        assert (
            VERTICAL_WEIGHTS["healthcare"]["audit_log_integrity"]
            > VERTICAL_WEIGHTS["general_saas"]["audit_log_integrity"]
        )

    def test_healthcare_legal_hold_weight_elevated(self):
        assert (
            VERTICAL_WEIGHTS["healthcare"]["legal_hold_procedures"]
            > VERTICAL_WEIGHTS["general_saas"]["legal_hold_procedures"]
        )

    def test_financial_backup_weight_elevated(self):
        assert (
            VERTICAL_WEIGHTS["financial_services"]["backup_archive"]
            > VERTICAL_WEIGHTS["general_saas"]["backup_archive"]
        )

    def test_financial_legal_hold_weight_elevated(self):
        assert (
            VERTICAL_WEIGHTS["financial_services"]["legal_hold_procedures"]
            > VERTICAL_WEIGHTS["general_saas"]["legal_hold_procedures"]
        )

    def test_financial_federated_weight_elevated(self):
        assert (
            VERTICAL_WEIGHTS["financial_services"]["federated_systems"]
            > VERTICAL_WEIGHTS["general_saas"]["federated_systems"]
        )

    def test_legal_services_legal_hold_highest_weight(self):
        """Legal services should have the highest legal_hold weight of all verticals."""
        legal_weights = {
            v: VERTICAL_WEIGHTS[v]["legal_hold_procedures"]
            for v in EXPECTED_VERTICALS
        }
        assert legal_weights["legal_services"] == max(legal_weights.values())


class TestCrossFramework:
    def test_all_verticals_in_cross_framework(self):
        for v in EXPECTED_VERTICALS:
            assert v in CROSS_FRAMEWORK, f"Missing vertical in CROSS_FRAMEWORK: {v!r}"

    def test_each_vertical_has_all_sections(self):
        for vertical, mappings in CROSS_FRAMEWORK.items():
            for sid in EXPECTED_SECTIONS:
                assert sid in mappings, (
                    f"Section {sid!r} missing from CROSS_FRAMEWORK[{vertical!r}]"
                )

    def test_each_section_has_at_least_one_mapping(self):
        for vertical, mappings in CROSS_FRAMEWORK.items():
            for sid, frameworks in mappings.items():
                assert isinstance(frameworks, list), (
                    f"CROSS_FRAMEWORK[{vertical!r}][{sid!r}] is not a list"
                )
                assert len(frameworks) >= 1, (
                    f"CROSS_FRAMEWORK[{vertical!r}][{sid!r}] has no entries"
                )

    def test_healthcare_primary_storage_has_hipaa(self):
        mappings = CROSS_FRAMEWORK["healthcare"]["primary_storage"]
        assert any("HIPAA" in m for m in mappings), "Expected HIPAA reference in healthcare/primary_storage"

    def test_financial_services_backup_has_pci_or_sox(self):
        mappings = CROSS_FRAMEWORK["financial_services"]["backup_archive"]
        assert any("PCI" in m or "SOX" in m for m in mappings)

    def test_general_saas_primary_storage_has_soc2(self):
        mappings = CROSS_FRAMEWORK["general_saas"]["primary_storage"]
        assert any("SOC 2" in m for m in mappings)

    def test_public_sector_eu_has_gdpr_references(self):
        for sid, mappings in CROSS_FRAMEWORK["public_sector_eu"].items():
            assert any("GDPR" in m or "NIS2" in m for m in mappings), (
                f"Expected GDPR/NIS2 in public_sector_eu/{sid}"
            )

    def test_legal_services_legal_hold_has_frcp(self):
        mappings = CROSS_FRAMEWORK["legal_services"]["legal_hold_procedures"]
        assert any("FRCP" in m or "ABA" in m for m in mappings)
