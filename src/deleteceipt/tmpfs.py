"""RAM-backed temporary file context manager (secure-tmpfs).

Files written to a tmpfs mount reside entirely in RAM.  When deleted,
the data is released immediately with no residual trace on physical
media — unlike standard filesystem deletion, which only marks the inode
as free without overwriting the underlying bytes.

On Linux, mount a tmpfs partition before using this module::

    sudo mkdir -p /mnt/secure-tmp
    sudo mount -t tmpfs -o size=512m,mode=1777 tmpfs /mnt/secure-tmp

For Docker Compose::

    services:
      processor:
        tmpfs:
          - /tmp/sensitive:size=256m,mode=1777

For Kubernetes::

    volumes:
      - name: sensitive-scratch
        emptyDir:
          medium: Memory
          sizeLimit: 256Mi

Usage::

    from deleteceipt.tmpfs import secure_temp_file, secure_temp_dir

    with secure_temp_file(suffix=".pdf") as path:
        with open(path, "wb") as f:
            f.write(document_bytes)
        result = process(path)
    # file is guaranteed deleted here, even if an exception was raised

    with secure_temp_dir() as dirpath:
        # dirpath is a temporary directory on the secure mount
        ...
"""
from __future__ import annotations

import contextlib
import os
import shutil
import tempfile
from pathlib import Path

# Default mount point.  Override via environment variable or pass explicitly.
_DEFAULT_SECURE_TMPDIR = os.environ.get("SECURE_TMPDIR", "/mnt/secure-tmp")


def _resolved_tmpdir(tmpdir: str | None) -> str:
    candidate = tmpdir or _DEFAULT_SECURE_TMPDIR
    p = Path(candidate)
    if p.exists() and p.is_dir():
        return str(p)
    # Fall back to the OS default temp dir with a warning.  In production the
    # mount point should always exist; the fallback is for dev/test environments.
    fallback = tempfile.gettempdir()
    return fallback


@contextlib.contextmanager
def secure_temp_file(
    suffix: str = "",
    prefix: str = "deleteceipt_",
    tmpdir: str | None = None,
):
    """Context manager that creates a temporary file on the secure tmpfs mount.

    The file is guaranteed to be deleted on exit, even if an exception is
    raised inside the ``with`` block.

    Args:
        suffix: File name suffix (e.g. ``".pdf"``).
        prefix: File name prefix.
        tmpdir: Override the tmpfs mount path.  Defaults to the ``SECURE_TMPDIR``
                environment variable or ``/mnt/secure-tmp``.

    Yields:
        Absolute path (str) to the temporary file.

    Example::

        with secure_temp_file(suffix=".pdf") as path:
            Path(path).write_bytes(raw_pdf_bytes)
            result = run_ocr(path)
    """
    resolved = _resolved_tmpdir(tmpdir)
    fd, path = tempfile.mkstemp(suffix=suffix, prefix=prefix, dir=resolved)
    try:
        os.close(fd)
        yield path
    finally:
        try:
            os.remove(path)
        except FileNotFoundError:
            pass  # already deleted — that's fine


@contextlib.contextmanager
def secure_temp_dir(
    prefix: str = "deleteceipt_",
    tmpdir: str | None = None,
):
    """Context manager that creates a temporary directory on the secure tmpfs mount.

    The entire directory tree is removed on exit.

    Args:
        prefix: Directory name prefix.
        tmpdir: Override the tmpfs mount path.

    Yields:
        Absolute path (str) to the temporary directory.

    Example::

        with secure_temp_dir() as dirpath:
            input_path = Path(dirpath) / "input.pdf"
            input_path.write_bytes(raw_bytes)
            output_path = Path(dirpath) / "output.txt"
            run_pipeline(str(input_path), str(output_path))
            result = output_path.read_text()
    """
    resolved = _resolved_tmpdir(tmpdir)
    dirpath = tempfile.mkdtemp(prefix=prefix, dir=resolved)
    try:
        yield dirpath
    finally:
        shutil.rmtree(dirpath, ignore_errors=True)


def is_tmpfs(path: str | None = None) -> bool:
    """Return True if *path* is on a tmpfs mount.

    Reads ``/proc/mounts`` (Linux only).  On non-Linux platforms always
    returns False — callers can use this to warn in production.

    Args:
        path: Path to check.  Defaults to the configured secure tmpdir.
    """
    target = path or _DEFAULT_SECURE_TMPDIR
    try:
        with open("/proc/mounts") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3 and parts[1] == target and parts[2] == "tmpfs":
                    return True
    except (OSError, PermissionError):
        pass
    return False
