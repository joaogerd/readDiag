"""
Test fixtures and utilities for *readDiag*.

This module centralizes common test setup and helpers used across the
project's pytest suite.

Key responsibilities
--------------------
- Force a non-interactive Matplotlib backend (``Agg``) for headless CI.
- Discover data roots via environment variables with sensible defaults.
- Provide reusable fixtures for conventional and radiance diagnostic files.
- Offer robust pickers for available (variable, kx) pairs in conventional data.
- Provide small *fake backends* to exercise adapters in isolation.

Notes
-----
- Environment variables recognized:
  - ``READDIAG_DATA``: base path for real sample data.
  - ``READDIAG_DATA_TEST``: base path for test-specific data (preferred).
- If a required sample file is missing, the corresponding test(s) are
  skipped via :func:`pytest.skip` instead of failing hard.

Examples
--------
Use a fixture in a test to open a conventional file::

    def test_smoke_conv(conv01_path):
        from readDiag import diagAccess
        d = diagAccess(str(conv01_path))
        assert d.get_variables(), "Expected at least one variable"

Pick a robust ``(var, kx)`` pair for subsequent tests::

    def test_pick_var_kx(conv_var_kx, conv01_path):
        var, kx = conv_var_kx
        from readDiag import diagAccess
        d = diagAccess(str(conv01_path))
        df = d.get_dataframe(var, kx)
        assert not df.empty
"""
from __future__ import annotations

# Standard library
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Third-party
import matplotlib
import pandas as pd
import pytest

# -----------------------------------------------------------------------------
# Matplotlib: force non-interactive backend for all tests
# -----------------------------------------------------------------------------
# This prevents tests from hanging in headless environments (e.g., CI, ssh).
matplotlib.use("Agg")

# -----------------------------------------------------------------------------
# Paths & environment discovery
# -----------------------------------------------------------------------------

def _discover_base() -> Path:
    """Return the project root (directory containing test assets).

    The heuristic assumes this file lives under ``tests/``; therefore
    the parent directory of this file is treated as the project root.

    Returns
    -------
    pathlib.Path
        Absolute path to the project root.
    """
    here = Path(__file__).resolve().parent
    root = here.parent
    return root


# Absolute project root (used to derive default data locations)
PROJECT_ROOT: Path = _discover_base()

# Environment overrides (allow local + CI customizations)
READDIAG_DATA: Path = Path(
    os.getenv("READDIAG_DATA", PROJECT_ROOT / "data")
).resolve()
READDIAG_DATA_TEST: Path = Path(
    os.getenv("READDIAG_DATA_TEST", PROJECT_ROOT / "dataTest" / "exp20")
).resolve()


def _require_file(p: Path) -> Path:
    """Ensure a given file exists or skip the test suite branch.

    Parameters
    ----------
    p : pathlib.Path
        Candidate path to a diagnostic file.

    Returns
    -------
    pathlib.Path
        The same path, if it exists.

    Notes
    -----
    If ``p`` does not exist, the current test is skipped with a clear message.
    This is preferred in CI where sample datasets may be optional.
    """
    if not p.exists():
        pytest.skip(f"Missing test file: {p}")
    return p


# -----------------------------------------------------------------------------
# Fixtures: conventional and radiance example files
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def conv01_path() -> Path:
    """Path to a conventional sample for *cycle 01*.

    Preference order
    ----------------
    1. ``READDIAG_DATA_TEST/diag_conv_01.2024013018``
    2. ``READDIAG_DATA/diag_conv_01.2024013018``

    Returns
    -------
    pathlib.Path
        Absolute path to the file, or the test is skipped if not present.
    """
    p_test = READDIAG_DATA_TEST / "diag_conv_01.2024013018"
    p_data = READDIAG_DATA / "diag_conv_01.2024013018"
    return _require_file(p_test) if p_test.exists() else _require_file(p_data)


@pytest.fixture(scope="session")
def conv03_path() -> Path:
    """Path to a conventional sample for *cycle 03* (pair for impact tests).

    Preference order
    ----------------
    1. ``READDIAG_DATA_TEST/diag_conv_03.2024013018``
    2. ``READDIAG_DATA/diag_conv_03.2024013018``

    Returns
    -------
    pathlib.Path
        Absolute path to the file, or the test is skipped if not present.
    """
    p_test = READDIAG_DATA_TEST / "diag_conv_03.2024013018"
    p_data = READDIAG_DATA / "diag_conv_03.2024013018"
    return _require_file(p_test) if p_test.exists() else _require_file(p_data)


@pytest.fixture(scope="session")
def rad01_path() -> Path:
    """Path to a radiance sample for *cycle 01* (AMSUA preferred).

    Candidates are tried in order until one exists.

    Returns
    -------
    pathlib.Path
        Absolute path to the file, or the test is skipped if not present.
    """
    candidates = [
        READDIAG_DATA_TEST / "diag_amsua_n19_01.2024013018",
        READDIAG_DATA / "diag_amsua_n19_01.2024013018",
        READDIAG_DATA / "diag_amsua_n15_01.2024013018",
    ]
    for p in candidates:
        if p.exists():
            return p
    pytest.skip("No radiance test file found in expected locations.")


@pytest.fixture(scope="session")
def rad03_path() -> Path:
    """Path to a radiance sample for *cycle 03* (AMSUA preferred).

    Candidates are tried in order until one exists.

    Returns
    -------
    pathlib.Path
        Absolute path to the file, or the test is skipped if not present.
    """
    candidates = [
        READDIAG_DATA_TEST / "diag_amsua_n19_03.2024013018",
        READDIAG_DATA / "diag_amsua_n19_03.2024013018",
        READDIAG_DATA / "diag_amsua_n15_03.2024013018",
    ]
    for p in candidates:
        if p.exists():
            return p
    pytest.skip("No radiance test file (03) found in expected locations.")


# -----------------------------------------------------------------------------
# Variable/KX picker (conventional)
# -----------------------------------------------------------------------------

@pytest.fixture(scope="session")
def conv_var_kx(conv01_path: Path) -> Tuple[str, int]:
    """Pick a robust ``(var, kx)`` pair available in ``conv01``.

    This tries to prefer temperature (``"t"``) for cross-test consistency,
    but will fall back to the first variable if temperature is not present.

    Parameters
    ----------
    conv01_path : pathlib.Path
        Path to the conventional diagnostic file used for probing.

    Returns
    -------
    tuple of (str, int)
        A valid variable name and one of its available KX values.

    Raises
    ------
    AssertionError
        If no variables or no KX values are found in the file.
    """
    from readDiag import open_diagnostic

    d = open_diagnostic(str(conv01_path))
    vars_ = d.get_variables()
    assert vars_, "No variables found in conventional file."

    # Prefer temperature when available to stabilize downstream tests.
    var = "t" if "t" in vars_ else vars_[0]

    kxs = d.get_kx_list(var)
    assert kxs, f"No kx for variable '{var}'."

    return var, int(kxs[0])


# =============================================================================
# Fake backends for adapter tests
# =============================================================================

# The classes below emulate the *modern* diagAccess surface so that adapters
# (e.g., AccessAdapter, LegacyCompatAdapter) can be unit-tested without touching
# real files. Keep them intentionally small and deterministic.

class FakeAccessConvBackend:
    """Minimal modern-like backend for **conventional** data.

    This object mimics the key methods of :mod:`readDiag.diagAccess` used by
    the adapters, returning tiny in-memory data frames for predictability.

    Parameters
    ----------
    path : str
        File path (stored for metadata realism; not opened).
    **_ : Any
        Ignored keyword arguments for surface compatibility.

    Examples
    --------
    >>> b = FakeAccessConvBackend("/tmp/diag_conv_01.2025010100")
    >>> info = b.get_file_info(); info["data_type"], info["n_obs"]
    ('conv', 3)
    >>> b.get_variables()
    ['t', 'q']
    >>> b.get_kx_list('t')
    [120, 130]
    >>> b.get_dataframe('t', 120).iloc[0].to_dict()["var"], 120 in b.get_kx_list('t')
    ('t', True)
    """

    def __init__(self, path: str, **_: Any) -> None:
        self._path = path
        self._meta: Dict[str, Any] = {
            "file_name": path,
            "data_type": "conv",
            "date": datetime(2025, 1, 1, 0),
            "sensor": None,
            "platform": None,
            "n_channels": None,
            "n_obs": 3,
        }
        self._vars: List[str] = ["t", "q"]
        self._kx: Dict[str, List[int]] = {"t": [120, 130], "q": [120]}
        self._frames: Dict[Tuple[str, int], pd.DataFrame] = {
            ("t", 120): pd.DataFrame({"var": ["t"], "kx": [120], "v": [1.0]}),
            ("t", 130): pd.DataFrame({"var": ["t"], "kx": [130], "v": [2.0]}),
            ("q", 120): pd.DataFrame({"var": ["q"], "kx": [120], "v": [3.0]}),
        }

    # --- Expected surface for AccessAdapter ---------------------------------
    def get_file_info(self) -> Dict[str, Any]:
        """Return file metadata such as kind, date and counts.

        Returns
        -------
        dict
            Keys include ``file_name``, ``data_type``, ``date``, ``n_obs``.
        """
        return self._meta

    def get_variables(self) -> List[str]:
        """List variables available in the conventional dataset."""
        return list(self._vars)

    def get_kx_list(self, var: str) -> List[int]:
        """Return available KX values for a variable.

        Parameters
        ----------
        var : str
            Variable name (e.g., ``"t"`` or ``"q"``).
        """
        return list(self._kx.get(var, []))

    def get_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        """Return a tiny DataFrame for ``(var, kx)``.

        Raises
        ------
        KeyError
            If the pair does not exist in this fake store.
        """
        return self._frames[(var, kx)]


class FakeAccessRadBackend:
    """Minimal modern-like backend for **radiance** data.

    The object supplies channels and a structured store analogous to the
    output of real radiance readers (``channel_df``, ``diagbuf_df``,
    ``diagbufex_df`` and a list ``diagbufchan_df``).

    Parameters
    ----------
    path : str
        File path (stored for metadata realism; not opened).
    **_ : Any
        Ignored keyword arguments for surface compatibility.

    Examples
    --------
    >>> b = FakeAccessRadBackend("/tmp/diag_amsua_n15_03.2025010106")
    >>> b.get_file_info()["data_type"], b.get_channels()
    ('rad', [1, 2, 3])
    >>> store = b.get_data_frame(); list(store["dataframes"])[:2]
    ['channel_df', 'diagbuf_df']
    """

    def __init__(self, path: str, **_: Any) -> None:
        self._path = path
        self._meta: Dict[str, Any] = {
            "file_name": path,
            "data_type": "rad",
            "date": datetime(2025, 1, 1, 6),
            "sensor": "amsua",
            "platform": "n15",
            "n_channels": 3,
            "n_obs": 3,
        }
        self._channels: List[int] = [1, 2, 3]
        self._store: Dict[str, Any] = {
            "dataframes": {
                "channel_df": pd.DataFrame({"ch": [1, 2, 3]}),
                "diagbuf_df": pd.DataFrame({"x": [10, 20, 30]}),
                "diagbufex_df": pd.DataFrame({"y": [40, 50, 60]}),
                "diagbufchan_df": [
                    pd.DataFrame({"c": [1], "v": [0.1]}),
                    pd.DataFrame({"c": [2], "v": [0.2]}),
                    pd.DataFrame({"c": [3], "v": [0.3]}),
                ],
            }
        }

    # --- Expected surface for AccessAdapter ---------------------------------
    def get_file_info(self) -> Dict[str, Any]:
        """Return file metadata such as kind, date and counts."""
        return self._meta

    def get_channels(self) -> List[int]:
        """List available channel numbers (1-indexed)."""
        return list(self._channels)

    def get_data_frame(self) -> Dict[str, Any]:
        """Return the in-memory radiance store (``dataframes`` dict)."""
        return self._store


# --- Pytest fixtures exposing the fake backends ------------------------------

@pytest.fixture()
def fake_access_conv_backend() -> FakeAccessConvBackend:
    """Session-scoped fake backend for conventional tests."""
    return FakeAccessConvBackend("data/diag_conv_01.2025010100")


@pytest.fixture()
def fake_access_rad_backend() -> FakeAccessRadBackend:
    """Session-scoped fake backend for radiance tests."""
    return FakeAccessRadBackend("data/diag_amsua_n15_03.2025010106")


# =============================================================================
# Legacy-like fakes for LegacyCompatAdapter
# =============================================================================

class LegacyConvFake:
    """Legacy-shaped conventional reader used by LegacyCompatAdapter tests.

    Provides a minimal surface (``file_name``, ``get_variables()``,
    ``get_kx_list()``, ``get_dataframe()``) to emulate older backends.

    Examples
    --------
    >>> legacy = LegacyConvFake()
    >>> 't' in legacy.get_variables()
    True
    >>> legacy.get_kx_list('t')
    [120, 130]
    >>> legacy.get_dataframe('q', 120).iloc[0]['var']
    'q'
    """

    file_name = "data/diag_conv_01.2025010100"

    def get_variables(self) -> List[str]:
        return ["t", "q"]

    def get_kx_list(self, var: str) -> List[int]:
        return [120, 130] if var == "t" else [120]

    def get_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        return pd.DataFrame({"var": [var], "kx": [kx], "v": [1.23]})


class LegacyRadFake:
    """Legacy-shaped radiance reader used by LegacyCompatAdapter tests.

    Surface includes attributes ``file_name``, ``sensor``, ``platform``,
    and methods ``get_channels()``, ``get_date()``, ``get_data_frame()``.
    """

    file_name = "data/diag_amsua_n15_03.2025010106"
    sensor = "amsua"
    platform = "n15"

    def get_channels(self) -> List[int]:
        return [1, 2, 3]

    def get_date(self) -> datetime:
        return datetime(2025, 1, 1, 6)

    def get_data_frame(self) -> Dict[str, Any]:
        return {
            "dataframes": {
                "channel_df": pd.DataFrame({"ch": [1, 2, 3]}),
                "diagbuf_df": pd.DataFrame({"x": [10, 20, 30]}),
                "diagbufex_df": pd.DataFrame({"y": [40, 50, 60]}),
                "diagbufchan_df": [
                    pd.DataFrame({"c": [1], "v": [0.1]}),
                    pd.DataFrame({"c": [2], "v": [0.2]}),
                    pd.DataFrame({"c": [3], "v": [0.3]}),
                ],
            }
        }


# --- Pytest fixtures exposing the legacy-like fakes --------------------------

@pytest.fixture()
def legacy_conv_fake() -> LegacyConvFake:
    """Provide a fresh instance of :class:`LegacyConvFake`."""
    return LegacyConvFake()


@pytest.fixture()
def legacy_rad_fake() -> LegacyRadFake:
    """Provide a fresh instance of :class:`LegacyRadFake`."""
    return LegacyRadFake()

