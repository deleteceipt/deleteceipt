from __future__ import annotations

import pytest

pytest.importorskip("cryptography", reason="cryptography package not installed")

from deleteceipt.crypto_shred import CryptoShredder, InMemoryKeyStore


def _shredder() -> CryptoShredder:
    return CryptoShredder(key_store=InMemoryKeyStore())


class TestEncryptDecrypt:
    def test_decrypt_returns_original_plaintext(self):
        s = _shredder()
        ct, key_id = s.encrypt("usr-1", b"sensitive data")
        result = s.decrypt("usr-1", key_id, ct)
        assert result == b"sensitive data"

    def test_different_encryptions_produce_different_ciphertext(self):
        s = _shredder()
        ct1, _ = s.encrypt("usr-1", b"same plaintext")
        ct2, _ = s.encrypt("usr-1", b"same plaintext")
        assert ct1 != ct2  # different nonces

    def test_wrong_user_id_returns_none(self):
        s = _shredder()
        ct, key_id = s.encrypt("usr-1", b"data")
        result = s.decrypt("usr-2", key_id, ct)
        assert result is None

    def test_empty_plaintext(self):
        s = _shredder()
        ct, key_id = s.encrypt("usr-1", b"")
        result = s.decrypt("usr-1", key_id, ct)
        assert result == b""

    def test_large_plaintext(self):
        s = _shredder()
        data = b"x" * 10_000
        ct, key_id = s.encrypt("usr-1", data)
        assert s.decrypt("usr-1", key_id, ct) == data


class TestShred:
    def test_shred_makes_decrypt_return_none(self):
        s = _shredder()
        ct, key_id = s.encrypt("usr-1", b"data")
        s.shred("usr-1")
        assert s.decrypt("usr-1", key_id, ct) is None

    def test_shred_returns_receipt(self):
        s = _shredder()
        s.encrypt("usr-1", b"data")
        receipt = s.shred("usr-1")
        assert receipt["erased"] is True
        assert receipt["user_id"] == "usr-1"
        assert "erased_at" in receipt
        assert "key_ids_deleted" in receipt

    def test_shred_reports_deleted_key_ids(self):
        s = _shredder()
        _, k1 = s.encrypt("usr-1", b"a")
        _, k2 = s.encrypt("usr-1", b"b")
        receipt = s.shred("usr-1")
        assert set(receipt["key_ids_deleted"]) == {k1, k2}

    def test_shred_nonexistent_user_is_safe(self):
        s = _shredder()
        receipt = s.shred("usr-nobody")
        assert receipt["erased"] is True
        assert receipt["key_ids_deleted"] == []

    def test_other_users_unaffected(self):
        s = _shredder()
        ct1, k1 = s.encrypt("usr-1", b"data1")
        ct2, k2 = s.encrypt("usr-2", b"data2")
        s.shred("usr-1")
        assert s.decrypt("usr-1", k1, ct1) is None
        assert s.decrypt("usr-2", k2, ct2) == b"data2"
