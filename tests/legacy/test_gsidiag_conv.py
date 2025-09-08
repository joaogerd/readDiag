# tests/legacy/test_gsidiag_conv.py
from __future__ import annotations

"""
Lightweight, backward-compatible tests for the legacy `gsidiag` (conventional) API.

These tests exercise a **minimum viable surface** expected from the legacy layer,
without over-constraining internal shapes. The goal is to keep legacy user code
working while the new surface/API evolves.

Notes
-----
- The `conv_path` fixture is expected to yield a `pathlib.Path` pointing to a
  valid *conventional* GSI diagnostic file (e.g., ``diag_conv_01.*``).
- We tolerate optional methods that may or may not exist in older shims
  (e.g., ``get_variable``). When present, they must not crash.
- We avoid asserting exact column sets, but check for common geographic columns
  (``lat``, ``lon``) when a DataFrame is returned.

Examples
--------
Typical legacy usage that these tests aim to protect:

>>> import gsidiag as gd
>>> rd = gd.read_diag(["/path/to/diag_conv_01.2024013018"])
>>> rd.pfileinfo()  # prints a human-readable summary
>>> for var in rd.variables():
...     for kx in rd.kx_list(var):
...         df = rd.frame_conv(var, kx)  # pandas.DataFrame
...         # downstream plotting or aggregation...
"""

import io
from typing import Iterable

import pandas as pd
import pytest
import gsidiag as gd


def _is_iterable(obj) -> bool:
    """Return True if *obj* is a (non-string) iterable.

    This small helper prevents accidental truthiness checks on strings.

    Parameters
    ----------
    obj : Any
        Object under test.

    Returns
    -------
    bool
        True when ``obj`` is an iterable (list/tuple/etc.) and not a string.
    """
    if isinstance(obj, (str, bytes)):
        return False
    return isinstance(obj, Iterable)


@pytest.mark.usefixtures("conv_path")
def test_conv_open_and_iter(conv_path):
    """Open a conventional file and iterate over a minimal legacy flow.

    The test is intentionally permissive: it only checks that typical entry
    points exist and behave, and that opening a single (var, kx) frame returns
    a DataFrame with expected *geographic* columns.

    Steps
    -----
    1. Open via ``read_diag([path])``.
    2. If ``variables`` exists, fetch the first variable.
    3. If ``kx_list`` exists, fetch the first kx for that variable.
    4. If ``frame_conv`` exists, load the frame and sanity-check the shape.
    """
    rd = gd.read_diag([str(conv_path)])

    # variables() is common in legacy conv readers
    if hasattr(rd, "variables") and callable(getattr(rd, "variables")):
        vars_ = rd.variables()
        assert _is_iterable(vars_), "variables() should return an iterable"
        if vars_:
            var = vars_[0]

            # kx_list(var) is also common and should be iterable
            if hasattr(rd, "kx_list") and callable(getattr(rd, "kx_list")):
                kxs = rd.kx_list(var)
                assert _is_iterable(kxs), "kx_list(var) should return an iterable"
                if kxs:
                    kx = kxs[0]

                    # frame_conv(var, kx) should yield a pandas DataFrame
                    if hasattr(rd, "frame_conv") and callable(getattr(rd, "frame_conv")):
                        df = rd.frame_conv(var, kx)
                        assert isinstance(df, pd.DataFrame), "frame_conv must return a DataFrame"

                        # Not all legacy builds guarantee full column sets,
                        # but lat/lon are widely present and useful for plotting.
                        assert {"lat", "lon"} <= set(df.columns), (
                            "Expected geographic columns {'lat','lon'} to be present"
                        )


@pytest.mark.usefixtures("conv_path")
def test_conv_get_variable_fallback(conv_path):
    """Exercise the optional legacy ``get_variable(var, kx)`` shim when available.

    Some historical code paths call ``get_variable`` instead of ``frame_conv``.
    If the method exists, it must accept a variable name and an optional ``kx``
    and return *something* meaningful (shape may vary by legacy version).
    This test only ensures it *does not crash* under typical usage.
    """
    rd = gd.read_diag([str(conv_path)])

    if hasattr(rd, "get_variable") and callable(getattr(rd, "get_variable")):
        # We try to find at least one (var, kx) pair, but tolerate absence.
        var = None
        kx = None
        if hasattr(rd, "variables") and callable(getattr(rd, "variables")):
            vars_ = rd.variables() or []
            if vars_:
                var = vars_[0]
                if hasattr(rd, "kx_list") and callable(getattr(rd, "kx_list")):
                    kxs = rd.kx_list(var) or []
                    if kxs:
                        kx = kxs[0]

        # The call itself must not raise
        _ = rd.get_variable(var, kx)  # return type varies across legacy impls


@pytest.mark.usefixtures("conv_path")
def test_conv_pfileinfo_prints(conv_path, capsys):
    """Ensure ``pfileinfo()`` prints a non-empty summary.

    Printing is a long-standing user-facing behavior. We only require that some
    output is produced, without constraining its exact format.
    """
    rd = gd.read_diag([str(conv_path)])
    if hasattr(rd, "pfileinfo") and callable(getattr(rd, "pfileinfo")):
        rd.pfileinfo()
        out = capsys.readouterr().out
        assert out.strip() != ""


@pytest.mark.usefixtures("conv_path")
def test_conv_summarize_is_stable(conv_path):
    """Call ``summarize`` with typical kwargs if method exists.

    Historically, some implementations provide ``summarize(varName=..., kx=...)``.
    We only call it when the method is available and we can infer a (var, kx)
    pair. The return type is *not* enforced (string/DataFrame accepted).
    """
    rd = gd.read_diag([str(conv_path)])

    if not hasattr(rd, "summarize") or not callable(getattr(rd, "summarize")):
        pytest.skip("summarize() not available in this legacy build")

    var = None
    kx = None
    if hasattr(rd, "variables") and callable(getattr(rd, "variables")):
        vars_ = rd.variables() or []
        if vars_:
            var = vars_[0]
            if hasattr(rd, "kx_list") and callable(getattr(rd, "kx_list")):
                kxs = rd.kx_list(var) or []
                if kxs:
                    kx = kxs[0]

    # Do not assert the exact type; accept str/df/other printable summaries.
    res = rd.summarize(varName=var, kx=kx)
    # minimal "sanity" — object exists and is representable
    assert res is not None
    _ = str(res)  # must be convertible to text for logs/prints


@pytest.mark.usefixtures("conv_path")
def test_conv_overview_safe(conv_path):
    """If ``overview()`` exists, it must not raise.

    Some legacy objects expose a convenience ``overview()`` printer. We don't
    enforce its presence or format; only that it is safe to call when present.
    """
    rd = gd.read_diag([str(conv_path)])
    if hasattr(rd, "overview") and callable(getattr(rd, "overview")):
        # Should not raise
        rd.overview()

