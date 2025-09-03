from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib
import os
import numpy as np

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
        SHA256 checksum of the file contents.

    Examples
    --------
    >>> from pathlib import Path
    >>> fc = stat_file(Path("example.txt"))
    >>> isinstance(fc, FileCheck)
    True
    >>> fc.size > 0
    True
    """
    path: Path
    size: int
    sha256: str


def sha256sum(path: Path, chunk: int = 1 << 20) -> str:
    """Return the SHA256 checksum of a file.

    The file is read in streaming mode to avoid excessive memory usage.

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

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("example.txt")
    >>> textfile.write_text("hello world")
    11
    >>> sha256sum(textfile)  
    'b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9'
    """
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def stat_file(path: Path) -> FileCheck:
    """Collect file statistics and SHA256 checksum.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file.

    Returns
    -------
    FileCheck
        Immutable dataclass containing file metadata.

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("example.txt")
    >>> textfile.write_text("hello world")
    11
    >>> fc = stat_file(textfile)
    >>> fc.size
    11
    >>> fc.path == textfile.resolve()
    True
    """
    p = Path(path).resolve()
    st = p.stat()
    return FileCheck(path=p, size=st.st_size, sha256=sha256sum(p))


def assert_min_size(path: Path, min_bytes: int) -> None:
    """Assert that a file has at least a minimum size.

    Parameters
    ----------
    path : pathlib.Path
        Path to the file.
    min_bytes : int
        Minimum required file size in bytes.

    Raises
    ------
    ValueError
        If the file is smaller than `min_bytes`.

    Examples
    --------
    >>> from pathlib import Path
    >>> textfile = Path("small.txt")
    >>> textfile.write_text("hi")
    2
    >>> assert_min_size(textfile, 1)  # OK
    >>> assert_min_size(textfile, 10)  
    Traceback (most recent call last):
        ...
    ValueError: File too small (2 B < 10 B): small.txt
    """
    size = os.path.getsize(path)
    if size < min_bytes:
        raise ValueError(
            f"File too small ({size} B < {min_bytes} B): {path}"
        )


def sanity_nchanl(nchanl: int, *, max_channels: int = 8192) -> None:
    """Validate a channel count for plausibility.

    Parameters
    ----------
    nchanl : int
        Number of channels to validate.
    max_channels : int, optional
        Maximum allowed number of channels. Default is 8192.

    Raises
    ------
    ValueError
        If `nchanl` is not within [1, max_channels].

    Examples
    --------
    >>> sanity_nchanl(10)  # OK
    >>> sanity_nchanl(0)  
    Traceback (most recent call last):
        ...
    ValueError: Invalid nchanl=0 (expected 1..8192)
    """
    if not (1 <= int(nchanl) <= max_channels):
        raise ValueError(f"Invalid nchanl={nchanl} (expected 1..{max_channels})")


def sanity_remaining_bytes(f, itemsize: int, nitems: int) -> None:
    """Check if enough bytes remain in a file-like stream for reading.

    This is particularly useful before reading binary data into a NumPy
    structured array or similar.

    Parameters
    ----------
    f : file-like
        Open file object (must support ``tell`` and ``seek``).
    itemsize : int
        Size in bytes of one item to be read.
    nitems : int
        Number of items expected.

    Raises
    ------
    ValueError
        If the file does not have enough remaining bytes.

    Examples
    --------
    >>> import io
    >>> buf = io.BytesIO(b"1234567890")
    >>> buf.seek(0)
    0
    >>> sanity_remaining_bytes(buf, 1, 5)  # OK
    >>> buf.seek(8)
    8
    >>> sanity_remaining_bytes(buf, 1, 5)
    Traceback (most recent call last):
        ...
    ValueError: Need 5 bytes, only 2 remain in stream.
    """
    pos = f.tell()
    f.seek(0, os.SEEK_END)
    remaining = f.tell() - pos
    f.seek(pos)
    needed = itemsize * int(nitems)
    if needed > remaining:
        raise ValueError(
            f"Need {needed} bytes, only {remaining} remain in stream."
        )

