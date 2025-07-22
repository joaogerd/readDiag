import os
import sys
import importlib.util
from pathlib import Path
import pytest

# Ensure project root in sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import refactored and legacy classes
from readDiag import diagAccess as NewDiagAccess
spec = importlib.util.spec_from_file_location(
    "diagAccess_legacy",
    str(ROOT / "diagAccess_legacy.py")
)
legacy_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(legacy_mod)
LegacyDiagAccess = legacy_mod.diagAccess

# Test data files
DATA_DIR = ROOT / "data"
CONV_FILE = str(DATA_DIR / "diag_conv_01.2020010100")
RAD_FILE = str(DATA_DIR / "diag_amsua_n15_01.2020010100")

# --- Conventional reads ---
@pytest.mark.benchmark(group="conv_read_legacy")
def test_conv_read_legacy(benchmark):
    """Legacy conventional read benchmark."""
    def read_legacy():
        return LegacyDiagAccess(CONV_FILE)
    inst = benchmark(read_legacy)
    assert hasattr(inst, 'get_data_frame')

@pytest.mark.benchmark(group="conv_read_new")
def test_conv_read_new(benchmark):
    """New conventional read benchmark."""
    def read_new():
        return NewDiagAccess(CONV_FILE, use_memmap=False)
    inst = benchmark(read_new)
    assert hasattr(inst, 'get_data_frame')

# --- Radiance reads ---
@pytest.mark.benchmark(group="rad_read_legacy")
def test_rad_read_legacy(benchmark):
    """Legacy radiance read benchmark."""
    def read_legacy():
        return LegacyDiagAccess(RAD_FILE)
    inst = benchmark(read_legacy)
    assert isinstance(inst.get_data_frame(), dict)

@pytest.mark.benchmark(group="rad_read_new")
def test_rad_read_new(benchmark):
    """New radiance read benchmark (no memmap)."""
    def read_new():
        return NewDiagAccess(RAD_FILE, use_memmap=False)
    inst = benchmark(read_new)
    assert isinstance(inst.get_data_frame(), dict)

@pytest.mark.benchmark(group="rad_read_new_memmap")
def test_rad_read_new_memmap(benchmark):
    """New radiance read benchmark (with memmap)."""
    def read_new_mmap():
        return NewDiagAccess(RAD_FILE, use_memmap=True)
    inst = benchmark(read_new_mmap)
    assert isinstance(inst.get_data_frame(), dict)

