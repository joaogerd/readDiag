"""
Test fixtures and utilities for readDiag.

This module centralizes:
- Matplotlib non-interactive backend setup (Agg),
- Data path discovery via environment variables,
- Reusable fixtures for conventional and radiance files,
- Helpers to pick available variables/kx robustly.
"""
from __future__ import annotations

import os
from pathlib import Path
import warnings
import pytest
import matplotlib

# Use non-interactive backend for all tests
matplotlib.use("Agg")

# ---------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------
def _discover_base() -> Path:
    """Return project root (directory containing 'data')."""
    here = Path(__file__).resolve().parent
    root = here.parent
    return root

PROJECT_ROOT = _discover_base()

# Environment overrides
READDIAG_DATA = Path(os.getenv("READDIAG_DATA", PROJECT_ROOT / "data")).resolve()
READDIAG_DATA_TEST = Path(os.getenv("READDIAG_DATA_TEST",
                                    PROJECT_ROOT / "dataTest" / "exp20")).resolve()

def _require_file(p: Path) -> Path:
    if not p.exists():
        pytest.skip(f"Missing test file: {p}")
    return p

# ---------------------------------------------------------------------
# Fixtures: conventional and radiance example files
# ---------------------------------------------------------------------
@pytest.fixture(scope="session")
def conv01_path() -> Path:
    """Conventional sample: cycle 01."""
    return _require_file(READDIAG_DATA_TEST / "diag_conv_01.2024013018") \
        if (READDIAG_DATA_TEST / "diag_conv_01.2024013018").exists() \
        else _require_file(READDIAG_DATA / "diag_conv_01.2020010100")

@pytest.fixture(scope="session")
def conv03_path() -> Path:
    """Conventional sample: cycle 03 (pair for impact)."""
    return _require_file(READDIAG_DATA_TEST / "diag_conv_03.2024013018") \
        if (READDIAG_DATA_TEST / "diag_conv_03.2024013018").exists() \
        else _require_file(READDIAG_DATA / "diag_conv_03.2020010100")

@pytest.fixture(scope="session")
def rad01_path() -> Path:
    """Radiance sample (N19, cycle 01 preferred)."""
    candidates = [
        READDIAG_DATA_TEST / "diag_amsua_n19_01.2024013018",
        READDIAG_DATA / "diag_amsua_n19_01.2020010100",
        READDIAG_DATA / "diag_amsua_n15_01.2020010100",
    ]
    for p in candidates:
        if p.exists():
            return p
    pytest.skip("No radiance test file found in expected locations.")

@pytest.fixture(scope="session")
def rad03_path() -> Path:
    """Radiance sample (N19, cycle 03 preferred)."""
    candidates = [
        READDIAG_DATA_TEST / "diag_amsua_n19_03.2024013018",
        READDIAG_DATA / "diag_amsua_n19_03.2020010100",
        READDIAG_DATA / "diag_amsua_n15_03.2020010100",
    ]
    for p in candidates:
        if p.exists():
            return p
    pytest.skip("No radiance test file (03) found in expected locations.")

# ---------------------------------------------------------------------
# Variable/KX pickers (conventional)
# ---------------------------------------------------------------------
@pytest.fixture(scope="session")
def conv_var_kx(conv01_path):
    """
    Pick a (var, kx) pair available in conv01.

    Returns
    -------
    tuple of (str, int)
        A valid variable name and one of its available kx values.
    """
    from readDiag import diagAccess
    d = diagAccess(str(conv01_path))
    vars_ = d.get_variables()
    assert vars_, "No variables found in conventional file."
    var = "t" if "t" in vars_ else vars_[0]
    kxs = d.get_kx_list(var)
    assert kxs, f"No kx for variable '{var}'."
    return var, int(kxs[0])

