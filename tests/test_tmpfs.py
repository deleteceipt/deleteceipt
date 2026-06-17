from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from deleteceipt.tmpfs import secure_temp_file, secure_temp_dir, is_tmpfs


class TestSecureTempFile:
    def test_file_exists_inside_context(self, tmp_path):
        with secure_temp_file(tmpdir=str(tmp_path)) as path:
            assert Path(path).exists()

    def test_file_deleted_after_context(self, tmp_path):
        with secure_temp_file(tmpdir=str(tmp_path)) as path:
            recorded = path
        assert not Path(recorded).exists()

    def test_file_deleted_on_exception(self, tmp_path):
        recorded = None
        with pytest.raises(ValueError):
            with secure_temp_file(tmpdir=str(tmp_path)) as path:
                recorded = path
                raise ValueError("boom")
        assert recorded is not None
        assert not Path(recorded).exists()

    def test_suffix_applied(self, tmp_path):
        with secure_temp_file(suffix=".pdf", tmpdir=str(tmp_path)) as path:
            assert path.endswith(".pdf")

    def test_prefix_applied(self, tmp_path):
        with secure_temp_file(prefix="myprefix_", tmpdir=str(tmp_path)) as path:
            assert Path(path).name.startswith("myprefix_")

    def test_can_write_and_read_inside_context(self, tmp_path):
        with secure_temp_file(tmpdir=str(tmp_path)) as path:
            Path(path).write_bytes(b"sensitive data")
            assert Path(path).read_bytes() == b"sensitive data"


class TestSecureTempDir:
    def test_dir_exists_inside_context(self, tmp_path):
        with secure_temp_dir(tmpdir=str(tmp_path)) as dirpath:
            assert Path(dirpath).is_dir()

    def test_dir_deleted_after_context(self, tmp_path):
        with secure_temp_dir(tmpdir=str(tmp_path)) as dirpath:
            recorded = dirpath
        assert not Path(recorded).exists()

    def test_dir_deleted_on_exception(self, tmp_path):
        recorded = None
        with pytest.raises(RuntimeError):
            with secure_temp_dir(tmpdir=str(tmp_path)) as dirpath:
                recorded = dirpath
                (Path(dirpath) / "file.txt").write_text("data")
                raise RuntimeError("crash")
        assert not Path(recorded).exists()

    def test_can_create_files_inside(self, tmp_path):
        with secure_temp_dir(tmpdir=str(tmp_path)) as dirpath:
            f = Path(dirpath) / "doc.pdf"
            f.write_bytes(b"pdf content")
            assert f.read_bytes() == b"pdf content"


class TestIsTmpfs:
    def test_returns_bool(self):
        result = is_tmpfs("/mnt/secure-tmp")
        assert isinstance(result, bool)

    def test_nonexistent_path_returns_false(self):
        assert is_tmpfs("/nonexistent/path/12345") is False
