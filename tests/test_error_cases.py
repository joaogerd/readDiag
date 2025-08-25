"""
Error cases: missing/empty/small files.
"""
from __future__ import annotations
from pathlib import Path
import pytest
from readDiag import diagAccess

def test_missing_file(tmp_path: Path):
    missing = tmp_path / "nope.bin"
    with pytest.raises(FileNotFoundError):
        diagAccess(str(missing))

def test_empty_file(tmp_path: Path):
    empty = tmp_path / "empty.bin"
    empty.write_bytes(b"")
    with pytest.raises(ValueError):
        diagAccess(str(empty))

def test_small_rad_file(tmp_path: Path):
    small = tmp_path / "small.bin"
    # write 4 bytes != 4 (conventional block header), so reader tries radiance and fails
    small.write_bytes((5).to_bytes(4, "big"))
    with pytest.raises(ValueError):
        diagAccess(str(small))

