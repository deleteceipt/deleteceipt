"""Cryptographic erasure (crypto-shredding).

For data categories where physical deletion is not feasible — Kafka topics,
backup archives, log aggregators — cryptographic erasure provides an
alternative: encrypt data under a per-user key, then delete the key.  The
ciphertext persists but is computationally unrecoverable without the key.

Privacy authorities including the EDPB increasingly accept crypto-shredding
as a valid form of deletion for these residual data categories, provided the
key management is rigorous and the encryption algorithm is sound.

This module provides:

  ``CryptoShredder``  — encrypts data and manages keys via a pluggable KeyStore.
  ``InMemoryKeyStore`` — testing backend.
  ``FilesystemKeyStore`` — development/demo backend (stores keys as files).

For production, back the KeyStore with AWS KMS, HashiCorp Vault, or GCP
Secret Manager.  The key never leaves the secure boundary; only the
ciphertext is held in application storage.

Usage::

    from deleteceipt.crypto_shred import CryptoShredder, InMemoryKeyStore

    store = InMemoryKeyStore()
    shredder = CryptoShredder(key_store=store)

    # Encrypt user data
    ciphertext, key_id = shredder.encrypt(user_id="usr-123", plaintext=b"sensitive data")

    # Later — delete the key (cryptographic erasure)
    receipt = shredder.shred(user_id="usr-123")
    assert receipt["erased"] is True

    # Decryption now fails
    result = shredder.decrypt(user_id="usr-123", key_id=key_id, ciphertext=ciphertext)
    assert result is None
"""
from __future__ import annotations

import os
import base64
import hashlib
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAS_CRYPTOGRAPHY = True
except ImportError:
    _HAS_CRYPTOGRAPHY = False


# ---------------------------------------------------------------------------
# Key store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class KeyStore(Protocol):
    def get(self, user_id: str, key_id: str) -> bytes | None: ...
    def put(self, user_id: str, key_id: str, key_bytes: bytes) -> None: ...
    def delete(self, user_id: str) -> list[str]: ...
    def list_key_ids(self, user_id: str) -> list[str]: ...


class InMemoryKeyStore:
    """In-memory key store for testing. Never use in production."""

    def __init__(self) -> None:
        self._keys: dict[str, dict[str, bytes]] = {}

    def get(self, user_id: str, key_id: str) -> bytes | None:
        return self._keys.get(user_id, {}).get(key_id)

    def put(self, user_id: str, key_id: str, key_bytes: bytes) -> None:
        self._keys.setdefault(user_id, {})[key_id] = key_bytes

    def delete(self, user_id: str) -> list[str]:
        deleted = list(self._keys.pop(user_id, {}).keys())
        return deleted

    def list_key_ids(self, user_id: str) -> list[str]:
        return list(self._keys.get(user_id, {}).keys())


# ---------------------------------------------------------------------------
# Shredder
# ---------------------------------------------------------------------------

class CryptoShredder:
    """Encrypts data per-user and supports cryptographic erasure via key deletion.

    Requires ``pip install deleteceipt[ecdsa]`` (brings in the ``cryptography``
    package which provides AES-GCM).

    Args:
        key_store: A KeyStore implementation.
    """

    def __init__(self, key_store: KeyStore) -> None:
        if not _HAS_CRYPTOGRAPHY:
            raise ImportError(
                "crypto_shred requires the 'cryptography' package. "
                "Install it with: pip install deleteceipt[ecdsa]"
            )
        self._store = key_store

    def _new_key_id(self, user_id: str) -> str:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        return f"{user_id}/{ts}"

    def encrypt(self, user_id: str, plaintext: bytes) -> tuple[bytes, str]:
        """Encrypt *plaintext* under a new per-user AES-256-GCM key.

        Args:
            user_id: Identifies whose key to use.
            plaintext: Raw bytes to encrypt.

        Returns:
            ``(ciphertext, key_id)`` — store the ciphertext; record the
            key_id alongside it so you can decrypt or shred later.
        """
        key_bytes = os.urandom(32)  # 256-bit AES key
        key_id = self._new_key_id(user_id)
        self._store.put(user_id, key_id, key_bytes)

        aesgcm = AESGCM(key_bytes)
        nonce = os.urandom(12)  # 96-bit nonce for GCM
        ct = aesgcm.encrypt(nonce, plaintext, None)
        # Prepend nonce so the ciphertext blob is self-contained
        return nonce + ct, key_id

    def decrypt(self, user_id: str, key_id: str, ciphertext: bytes) -> bytes | None:
        """Decrypt *ciphertext* using the stored key.

        Returns ``None`` if the key has been shredded (erasure confirmed).

        Args:
            user_id: Identifies whose key to retrieve.
            key_id: Key version identifier returned by ``encrypt()``.
            ciphertext: The nonce-prefixed ciphertext returned by ``encrypt()``.
        """
        key_bytes = self._store.get(user_id, key_id)
        if key_bytes is None:
            return None  # key was shredded — data is computationally unrecoverable

        nonce, ct = ciphertext[:12], ciphertext[12:]
        aesgcm = AESGCM(key_bytes)
        try:
            return aesgcm.decrypt(nonce, ct, None)
        except Exception:
            return None

    def shred(self, user_id: str) -> dict:
        """Delete all keys for *user_id* — cryptographic erasure.

        After this call, any ciphertext encrypted under the user's keys
        is computationally unrecoverable.

        Returns a deletion receipt-style dict documenting the erasure::

            {
                "user_id": str,
                "erased": True,
                "key_ids_deleted": [...],
                "erased_at": str,
                "method": "AES-256-GCM key deletion",
            }
        """
        deleted_key_ids = self._store.delete(user_id)
        return {
            "user_id": user_id,
            "erased": True,
            "key_ids_deleted": deleted_key_ids,
            "erased_at": datetime.now(timezone.utc).isoformat(),
            "method": "AES-256-GCM key deletion (crypto-shredding)",
            "note": (
                "Ciphertext may persist in logs, backups, and derived stores. "
                "Without the deleted key it is computationally unrecoverable."
            ),
        }
