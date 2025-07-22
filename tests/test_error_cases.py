import os
import sys
import pytest
from pathlib import Path

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from readDiag import diagAccess


def test_missing_file():
    """
    Missing file should raise FileNotFoundError.
    """
    missing = ROOT / 'data' / 'nonexistent_file.bin'
    with pytest.raises(FileNotFoundError):
        diagAccess(str(missing))


def test_empty_file(tmp_path):
    """
    Empty file (0 bytes) should raise an exception during header detection.
    """
    empty = tmp_path / 'empty.bin'
    empty.write_bytes(b'')
    with pytest.raises(ValueError):
        diagAccess(str(empty))


def test_small_rad_file(tmp_path):
    """
    File with 4 bytes not equal to valid conv header should attempt rad read and then fail.
    """
    small = tmp_path / 'small.bin'
    # header 5 => treated as rad, but no content => cannot parse header
    small.write_bytes((5).to_bytes(4, byteorder='big'))
    with pytest.raises(ValueError):
        diagAccess(str(small))

