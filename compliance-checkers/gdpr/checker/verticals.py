"""
Vertical definitions: per-section weights and cross-framework control mappings.

Maturity levels (0-4):
  0 = None / Ad-hoc
  1 = Documented
  2 = Implemented
  3 = Tested
  4 = Continuous / Automated
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Valid vertical identifiers
# ---------------------------------------------------------------------------

VERTICALS: set[str] = {
    "general_saas",
    "healthcare",
    "financial_services",
    "legal_services",
    "public_sector_eu",
}

# ---------------------------------------------------------------------------
# Per-section weights per vertical
# (sections not listed default to 1.0 in the engine)
# ---------------------------------------------------------------------------

# Section IDs match YAML filenames (without .yaml) / "section:" field.
_SECTION_IDS = [
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

VERTICAL_WEIGHTS: dict[str, dict[str, float]] = {
    "general_saas": {
        "primary_storage": 1.0,
        "search_indexes": 0.9,
        "cache_invalidation": 0.8,
        "message_queues": 0.8,
        "backup_archive": 0.9,
        "logs_observability": 0.8,
        "third_party_processors": 1.0,
        "ml_models": 0.7,
        "deletion_receipt_issuance": 1.0,
        "audit_log_integrity": 1.0,
        "legal_hold_procedures": 0.7,
        "federated_systems": 0.8,
        "cryptographic_erasure": 0.9,
        "deletion_testing": 1.0,
    },
    "healthcare": {
        "primary_storage": 1.0,
        "search_indexes": 0.9,
        "cache_invalidation": 0.8,
        "message_queues": 0.8,
        "backup_archive": 1.0,
        "logs_observability": 0.9,
        "third_party_processors": 1.0,
        "ml_models": 0.9,
        "deletion_receipt_issuance": 1.4,  # HIPAA heightened
        "audit_log_integrity": 1.4,        # HIPAA heightened
        "legal_hold_procedures": 1.3,      # HIPAA heightened
        "federated_systems": 0.9,
        "cryptographic_erasure": 1.2,
        "deletion_testing": 1.0,
    },
    "financial_services": {
        "primary_storage": 1.0,
        "search_indexes": 0.9,
        "cache_invalidation": 0.8,
        "message_queues": 0.9,
        "backup_archive": 1.3,             # PCI/SOX heightened
        "logs_observability": 0.9,
        "third_party_processors": 1.0,
        "ml_models": 0.8,
        "deletion_receipt_issuance": 1.2,
        "audit_log_integrity": 1.2,
        "legal_hold_procedures": 1.4,      # Litigation hold heightened
        "federated_systems": 1.3,          # Cross-entity sharing heightened
        "cryptographic_erasure": 1.0,
        "deletion_testing": 1.0,
    },
    "legal_services": {
        "primary_storage": 1.0,
        "search_indexes": 1.0,
        "cache_invalidation": 0.7,
        "message_queues": 0.7,
        "backup_archive": 1.1,
        "logs_observability": 0.9,
        "third_party_processors": 1.0,
        "ml_models": 0.8,
        "deletion_receipt_issuance": 1.2,
        "audit_log_integrity": 1.3,
        "legal_hold_procedures": 1.5,      # Core to legal sector
        "federated_systems": 0.8,
        "cryptographic_erasure": 1.0,
        "deletion_testing": 1.0,
    },
    "public_sector_eu": {
        "primary_storage": 1.0,
        "search_indexes": 0.9,
        "cache_invalidation": 0.8,
        "message_queues": 0.8,
        "backup_archive": 1.0,
        "logs_observability": 1.0,
        "third_party_processors": 1.1,
        "ml_models": 1.0,
        "deletion_receipt_issuance": 1.3,  # Accountability to citizens
        "audit_log_integrity": 1.3,
        "legal_hold_procedures": 1.0,
        "federated_systems": 1.2,
        "cryptographic_erasure": 1.1,
        "deletion_testing": 1.1,
    },
}

# ---------------------------------------------------------------------------
# Cross-framework mappings
# ---------------------------------------------------------------------------

CROSS_FRAMEWORK: dict[str, dict[str, list[str]]] = {
    "general_saas": {
        "primary_storage": ["SOC 2 CC6.5", "SOC 2 CC6.7", "ISO 27001 A.8.3"],
        "search_indexes": ["SOC 2 CC6.5", "ISO 27001 A.8.3"],
        "cache_invalidation": ["SOC 2 CC6.5"],
        "message_queues": ["SOC 2 CC6.5", "SOC 2 CC6.7"],
        "backup_archive": ["SOC 2 CC6.5", "SOC 2 A1.2", "ISO 27001 A.12.3"],
        "logs_observability": ["SOC 2 CC7.2", "ISO 27001 A.12.4"],
        "third_party_processors": ["SOC 2 CC9.2", "ISO 27001 A.15.1"],
        "ml_models": ["SOC 2 CC6.5"],
        "deletion_receipt_issuance": ["SOC 2 CC6.5", "SOC 2 CC7.5"],
        "audit_log_integrity": ["SOC 2 CC7.2", "ISO 27001 A.12.4"],
        "legal_hold_procedures": ["SOC 2 CC6.5"],
        "federated_systems": ["SOC 2 CC6.5", "SOC 2 CC6.7"],
        "cryptographic_erasure": ["SOC 2 CC6.7", "ISO 27001 A.10.1"],
        "deletion_testing": ["SOC 2 CC4.1", "SOC 2 CC4.2"],
    },
    "healthcare": {
        "primary_storage": [
            "HIPAA §164.530(j)", "HIPAA §164.310(d)(2)(i)", "HITRUST CSF 07.a",
        ],
        "search_indexes": ["HIPAA §164.530(j)", "HITRUST CSF 07.a"],
        "cache_invalidation": ["HIPAA §164.530(j)"],
        "message_queues": ["HIPAA §164.530(j)", "HITRUST CSF 09.ab"],
        "backup_archive": [
            "HIPAA §164.530(j)", "HIPAA §164.310(d)(2)(iv)", "HITRUST CSF 09.l",
        ],
        "logs_observability": ["HIPAA §164.312(b)", "HITRUST CSF 09.ab"],
        "third_party_processors": ["HIPAA §164.308(b)(1)", "HITRUST CSF 05.b"],
        "ml_models": ["HIPAA §164.530(j)"],
        "deletion_receipt_issuance": [
            "HIPAA §164.530(j)", "HIPAA §164.528", "HITRUST CSF 09.aa",
        ],
        "audit_log_integrity": [
            "HIPAA §164.312(b)", "HIPAA §164.308(a)(1)(ii)(D)", "HITRUST CSF 09.ab",
        ],
        "legal_hold_procedures": ["HIPAA §164.530(j)", "HIPAA §164.316(b)(2)(i)"],
        "federated_systems": ["HIPAA §164.530(j)", "HITRUST CSF 09.ab"],
        "cryptographic_erasure": ["HIPAA §164.312(a)(2)(iv)", "HIPAA §164.530(j)"],
        "deletion_testing": ["HIPAA §164.308(a)(8)", "HITRUST CSF 06.d"],
    },
    "financial_services": {
        "primary_storage": ["PCI DSS 3.2.1", "SOX §802", "GLBA §6801"],
        "search_indexes": ["PCI DSS 3.2.1"],
        "cache_invalidation": ["PCI DSS 3.3"],
        "message_queues": ["PCI DSS 3.2.1", "SOX §802"],
        "backup_archive": ["PCI DSS 9.5", "SOX §802", "GLBA §6801"],
        "logs_observability": ["PCI DSS 10.2", "SOX §302", "GLBA §6801"],
        "third_party_processors": ["PCI DSS 12.8", "GLBA §6801", "DORA Art. 28"],
        "ml_models": ["FCRA §611", "ECOA"],
        "deletion_receipt_issuance": ["PCI DSS 3.2.1", "SOX §802"],
        "audit_log_integrity": ["PCI DSS 10.3", "SOX §302", "SOX §906"],
        "legal_hold_procedures": ["SOX §802", "FRCP Rule 37(e)", "DORA Art. 17"],
        "federated_systems": ["PCI DSS 1.3", "DORA Art. 28"],
        "cryptographic_erasure": ["PCI DSS 3.4", "PCI DSS 9.8"],
        "deletion_testing": ["PCI DSS 11.3", "SOX §302"],
    },
    "legal_services": {
        "primary_storage": ["ABA Model Rule 1.6", "ISO 27001 A.8.3"],
        "search_indexes": ["ABA Model Rule 1.6"],
        "cache_invalidation": ["ABA Model Rule 1.6"],
        "message_queues": ["ABA Model Rule 1.6"],
        "backup_archive": ["ABA Model Rule 1.6", "ISO 27001 A.12.3"],
        "logs_observability": ["ABA Model Rule 1.6", "ISO 27001 A.12.4"],
        "third_party_processors": ["ABA Model Rule 1.6", "ISO 27001 A.15.1"],
        "ml_models": ["ABA Model Rule 1.6"],
        "deletion_receipt_issuance": ["ABA Model Rule 1.6", "ISO 27001 A.12.4"],
        "audit_log_integrity": ["ABA Model Rule 1.6", "FRCP Rule 37(e)"],
        "legal_hold_procedures": ["FRCP Rule 37(e)", "ABA Model Rule 3.4", "EDRM"],
        "federated_systems": ["ABA Model Rule 1.6"],
        "cryptographic_erasure": ["ABA Model Rule 1.6", "ISO 27001 A.10.1"],
        "deletion_testing": ["ISO 27001 A.12.1"],
    },
    "public_sector_eu": {
        "primary_storage": ["GDPR Art. 17", "NIS2 Art. 21", "eIDAS"],
        "search_indexes": ["GDPR Art. 17"],
        "cache_invalidation": ["GDPR Art. 17"],
        "message_queues": ["GDPR Art. 17", "NIS2 Art. 21"],
        "backup_archive": ["GDPR Art. 17", "NIS2 Art. 21"],
        "logs_observability": ["GDPR Art. 5(1)(e)", "NIS2 Art. 21"],
        "third_party_processors": ["GDPR Art. 28", "NIS2 Art. 21"],
        "ml_models": ["GDPR Art. 17", "EU AI Act Art. 10"],
        "deletion_receipt_issuance": ["GDPR Art. 17", "GDPR Art. 5(2)"],
        "audit_log_integrity": ["GDPR Art. 5(2)", "NIS2 Art. 21"],
        "legal_hold_procedures": ["GDPR Art. 17(3)", "EU Evidence Regulation"],
        "federated_systems": ["GDPR Art. 17", "GDPR Art. 44-49"],
        "cryptographic_erasure": ["GDPR Art. 17", "ENISA Guidelines"],
        "deletion_testing": ["GDPR Art. 5(2)", "NIS2 Art. 21"],
    },
}
