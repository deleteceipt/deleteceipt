"""deleteceipt — cryptographic proof-of-deletion receipts.

Core API (no external dependencies):
    compute_file_hash(data)         -> str  (SHA-256 hex digest, call at upload time)
    issue_receipt(...)              -> dict (HMAC-SHA256 signed deletion receipt)
    verify_receipt(receipt, key)    -> bool (verify HMAC signature)

ECDSA API (requires ``pip install deleteceipt[ecdsa]``):
    generate_keypair()              -> (private_key_pem, public_key_pem)
    issue_receipt_ecdsa(...)        -> dict (ECDSA-signed deletion receipt)
    verify_receipt_ecdsa(receipt)   -> bool (self-contained ECDSA verification)

Audit log API:
    AuditLog                        — synchronous, hash-chained audit log
    AsyncAuditLog                   — asyncio-compatible counterpart

Enterprise receipt API:
    issue_enterprise_receipt(...)   -> dict (GDPR Article 30 extended receipt)
    verify_enterprise_receipt(...)  -> bool

Reconciliation:
    Reconciler                      — detects and remediates deletion inconsistencies
    InMemoryReceiptStore            — in-memory receipt store (testing)

Secure temporary files:
    secure_temp_file(...)           — context manager for RAM-backed temp files
    secure_temp_dir(...)            — context manager for RAM-backed temp dirs
    is_tmpfs(path)                  -> bool

TTL scheduler:
    DeletionScheduler               — runs registered TTL policies
    StorePolicy                     — configures one storage layer's TTL policy

Legal hold gate:
    LegalHoldGate                   — intercepts deletion requests, enforces holds
    InMemoryHoldStore               — in-memory hold store (testing)

Cryptographic erasure:
    CryptoShredder                  — AES-256-GCM encrypt + key deletion
    InMemoryKeyStore                — in-memory key store (testing)

Receipt renderer:
    render_receipt(receipt, fmt)    -> str  (text / html / json)

Data inventory:
    DataInventory                   — registry of storage layers and deletion controls
    StorageLayerEntry               — one storage layer's deletion metadata
    DeletionMechanism               — enum of deletion mechanism types
"""
from .receipt import compute_file_hash, issue_receipt, verify_receipt
from .audit import AuditLog, AsyncAuditLog
from .ecdsa_receipt import generate_keypair, issue_receipt_ecdsa, verify_receipt_ecdsa
from .enterprise import issue_enterprise_receipt, verify_enterprise_receipt
from .reconcile import Reconciler, InMemoryReceiptStore
from .tmpfs import secure_temp_file, secure_temp_dir, is_tmpfs
from .scheduler import DeletionScheduler, StorePolicy
from .legal_hold import LegalHoldGate, InMemoryHoldStore
from .renderer import render_receipt
from .inventory import DataInventory, StorageLayerEntry, DeletionMechanism

__all__ = [
    # HMAC core
    "compute_file_hash",
    "issue_receipt",
    "verify_receipt",
    # ECDSA
    "generate_keypair",
    "issue_receipt_ecdsa",
    "verify_receipt_ecdsa",
    # Audit log
    "AuditLog",
    "AsyncAuditLog",
    # Enterprise
    "issue_enterprise_receipt",
    "verify_enterprise_receipt",
    # Reconciliation
    "Reconciler",
    "InMemoryReceiptStore",
    # Secure temp files
    "secure_temp_file",
    "secure_temp_dir",
    "is_tmpfs",
    # TTL scheduler
    "DeletionScheduler",
    "StorePolicy",
    # Legal hold
    "LegalHoldGate",
    "InMemoryHoldStore",
    # Crypto shredder (imported on demand — requires cryptography package)
    # Renderer
    "render_receipt",
    # Inventory
    "DataInventory",
    "StorageLayerEntry",
    "DeletionMechanism",
]
