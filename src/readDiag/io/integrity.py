# --- filecheck.py -------------------------------------------------------------
from __future__ import annotations

"""
Tiny, dependency-free helpers for *file integrity* and *binary read safety*.

This module provides:
- :class:`FileCheck`: an immutable record with absolute path, file size, and
  SHA256 checksum (hex).
- :func:`sha256sum`: a streaming SHA256 hasher suitable for large files.
- :func:`stat_file`: convenience wrapper that returns a populated ``FileCheck``.
- :func:`assert_min_size`: guard against obviously truncated inputs.
- :func:`sanity_nchanl`: quick plausibility check for a "number of channels".
- :func:`sanity_remaining_bytes`: assert there are enough bytes left in a
  file-like object before attempting a structured read.

Design notes
------------
- All functions avoid loading whole files into memory. Hashing is *streamed*.
- APIs are minimal and typed; surfaces are stable for reuse in readers/parsers.
- Errors are explicit (:class:`ValueError`) with actionable messages.

Examples
--------
Hash a small text file and validate size:

>>> from pathlib import Path
>>> p = Path("example.txt")
>>> _ = p.write_text("hello world")                 # 11 bytes
>>> sha256sum(p)
'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
>>> fc = stat_file(p)
>>> (fc.path.is_absolute(), fc.size) == (True, 11)
(True, 11)
>>> assert_min_size(p, 1)                           # ok

Guard a binary read with remaining-bytes logic:

>>> import io, numpy as np
>>> buf = io.BytesIO(b"abcdefghij")                 # 10 bytes total
>>> buf.seek(4)                                     # 6 bytes remain
4
>>> itemsize, nitems = 2, 3                         # need 6 bytes → ok
>>> sanity_remaining_bytes(buf, itemsize, nitems)   # no exception

"""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, runtime_checkable
import hashlib
import os

import numpy as np  # kept for projects that co-locate this module with NumPy readers

__all__ = [
    "FileCheck",
    "sha256sum",
    "stat_file",
    "assert_min_size",
    "sanity_nchanl",
    "sanity_remaining_bytes",
]

# --------------------------------------------------------------------------- #
# Protocols & dataclasses
# --------------------------------------------------------------------------- #

@runtime_checkable
class SeekTell(Protocol):
    """Minimal protocol for a seekable, tellable binary stream.

    This is intentionally tiny to support ``io.BytesIO``, real files,
    and memory-mapped wrappers.

    Notes
    -----
    Only the methods used by :func:`sanity_remaining_bytes` are required.
    """
    def tell(self) -> int: ...
    def seek(self, offset: int, whence: int = os.SEEK_SET) -> int: ...


@dataclass(frozen=True)
class FileCheck:
    """Immutable container for file metadata.

    Attributes
    ----------
    path : pathlib.Path
        Absolute path to the file.
    size : int
        File size in bytes.
    sha256 : str
        SHA256 checksum of the file contents (hex, lowercase).

    Examples
    --------
    >>> from pathlib import Path
    >>> _ = Path("ex.txt").write_text("data")
    >>> fc = stat_file(Path("ex.txt"))
    >>> isinstance(fc, FileCheck), fc.size >= 4, len(fc.sha256) == 64
    (True, True, True)
    """
    path: Path
    size: int
    sha256: str


# --------------------------------------------------------------------------- #
# Hashing & stat helpers
# --------------------------------------------------------------------------- #

def sha256sum(path: Path, chunk: int = 1 << 20) -> str:
    """Return the SHA256 checksum of a file (streaming, memory-safe).

    The file is read in fixed-size blocks to keep memory bounded. Useful for
    very large inputs (multi-GB).

    Parameters
    ----------
    path : pathlib.Path
        Path to the file to hash.
    chunk : int, optional
        Chunk size in bytes to read at once. Default is 1 MiB.

    Returns
    -------
    str
        The SHA256 hex digest of the file.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    PermissionError
        If the file cannot be opened.

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("hash_me.txt")
    >>> _ = textfile.write_text("hello world")
    >>> sha256sum(textfile)
    'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """
    h = hashlib.sha256()
    # Open in binary mode; rely on OS kernel readahead to keep things efficient.
    with Path(path).open("rb") as f:
        # Using sentinel-iter avoids an explicit while True / break loop.
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def stat_file(path: Path) -> FileCheck:
    """Collect file statistics and SHA256 checksum.

    Resolves the path to an absolute path, performs an ``os.stat`` to retrieve
    size, and computes a streaming SHA256 digest.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file.

    Returns
    -------
    FileCheck
        Immutable dataclass containing file metadata.

    Raises
    ------
    FileNotFoundError
        If ``path`` does not exist.
    PermissionError
        If the file cannot be read.

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("example.txt")
    >>> _ = textfile.write_text("hello world")
    >>> fc = stat_file(textfile)
    >>> (fc.size, fc.path == textfile.resolve(), len(fc.sha256))
    (11, True, 64)
    """
    p = Path(path).resolve()
    st = p.stat()
    return FileCheck(path=p, size=st.st_size, sha256=sha256sum(p))


# --------------------------------------------------------------------------- #
# Sanity checks for callers/readers
# --------------------------------------------------------------------------- #

def assert_min_size(path: Path, min_bytes: int) -> None:
    """Assert that a file has at least a minimum size.

    This is a quick guard to fail early on truncated downloads or incomplete
    staging before a heavy parse begins.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file.
    min_bytes : int
        Minimum required file size in bytes.

    Raises
    ------
    ValueError
        If the file is smaller than ``min_bytes``.
    FileNotFoundError
        If ``path`` does not exist.

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("small.txt")
    >>> _ = textfile.write_text("hi")   # 2 bytes
    >>> assert_min_size(textfile, 1)    # OK
    >>> assert_min_size(textfile, 10)
    Traceback (most recent call last):
        ...
    ValueError: File too small (2 B < 10 B): small.txt
    """
    size = os.path.getsize(path)
    if size < min_bytes:
        raise ValueError(f"File too small ({size} B < {min_bytes} B): {path}")


def sanity_nchanl(nchanl: int, *, max_channels: int = 8192) -> None:
    """Validate a channel count for plausibility.

    Useful when parsing headers that declare ``nchanl`` before allocating
    arrays or loops.

    Parameters
    ----------
    nchanl : int
        Number of channels to validate.
    max_channels : int, optional
        Maximum allowed number of channels. Default is ``8192``.

    Raises
    ------
    ValueError
        If ``nchanl`` is not within ``[1, max_channels]``.

    Examples
    --------
    >>> sanity_nchanl(10)  # OK
    >>> sanity_nchanl(0)
    Traceback (most recent call last):
        ...
    ValueError: Invalid nchanl=0 (expected 1..8192)
    """
    # Force int to reject numpy scalars with NaN, etc., via ValueError/TypeError.
    n = int(nchanl)
    if not (1 <= n <= max_channels):
        raise ValueError(f"Invalid nchanl={nchanl} (expected 1..{max_channels})")


def sanity_remaining_bytes(f: SeekTell, itemsize: int, nitems: int) -> None:
    """Check if enough bytes remain in a file-like stream for reading.

    Particularly useful before reading binary data into a NumPy structured array
    with ``np.fromfile``/``np.frombuffer`` or when slicing memory-mapped files.

    Parameters
    ----------
    f : file-like
        Open file object (must support ``tell`` and ``seek``). See :class:`SeekTell`.
    itemsize : int
        Size in bytes of one item to be read.
    nitems : int
        Number of items expected.

    Raises
    ------
    ValueError
        If the stream does not have enough remaining bytes.

    Examples
    --------
    >>> import io
    >>> buf = io.BytesIO(b"1234567890")  # 10 bytes
    >>> buf.seek(0)
    0
    >>> sanity_remaining_bytes(buf, 1, 5)  # OK (need 5, have 10)
    >>> buf.seek(8)
    8
    >>> sanity_remaining_bytes(buf, 1, 5)
    Traceback (most recent call last):
        ...
    ValueError: Need 5 bytes, only 2 remain in stream.
    """
    if not isinstance(f, SeekTell):
        # Fail fast with a clear error message if an incompatible stream is passed.
        raise TypeError("Stream must support tell() and seek(); see SeekTell protocol.")

    # Current position
    pos = f.tell()

    # Jump to end to compute remaining bytes without reading data.
    f.seek(0, os.SEEK_END)
    remaining = f.tell() - pos

    # Restore position (do not surprise the caller).
    f.seek(pos, os.SEEK_SET)

    needed = int(itemsize) * int(nitems)
    if needed > remaining:
        raise ValueError(f"Need {needed} bytes, only {remaining} remain in stream.")


# --------------------------------------------------------------------------- #
# Developer tips & gotchas (kept as comments for quick reference)
# --------------------------------------------------------------------------- #
# - For hashing huge files faster on spinning disks, larger chunks (e.g., 8–32 MiB)
#   may help; for SSDs, 1–4 MiB is typically fine. Tweak `chunk` if profiling suggests it.
# - Avoid memory mapping for integrity checks—the OS will still page data and you
#   gain little versus a simple streamed read with hashlib.
# - If you must compare many files, pre-filter by size first (cheap), then hash.
# - When guarding structured reads, always validate counts (e.g., nrows*ncols*dtype.itemsize)
#   against :func:`sanity_remaining_bytes` to produce early, clear exceptions.

