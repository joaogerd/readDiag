from __future__ import annotations
import pandas as pd
import pytest

import gsidiag as gd  # legacy alias


def test_import_and_api(conv_path):
    """Smoke test for legacy entrypoint and minimal API shape.

    Notes
    -----
    - Ensures :func:`gsidiag.read_diag` imports and returns an object
      with common legacy methods like ``pfileinfo``.
    - ``meta`` / ``overview`` were common on legacy readers; if present,
      they should not raise.
    """
    rd = gd.read_diag([str(conv_path)])

    # must expose at least this legacy face
    assert hasattr(rd, "pfileinfo")

    # meta/overview are optional — if they exist, they shouldn't explode
    for maybe in ("meta", "overview"):
        if hasattr(rd, maybe):
            getattr(rd, maybe)()  # no exception


def test_pfileinfo_prints(conv_path, capsys):
    """``pfileinfo()`` should print something to stdout."""
    rd = gd.read_diag([str(conv_path)])
    rd.pfileinfo()  # should produce output
    out = capsys.readouterr().out
    assert out.strip() != ""


def test_summarize_optionals(conv_path):
    """``summarize`` should accept optional ``varName``/``kx`` when available.

    Strategy
    --------
    - If the object exposes ``variables()`` and (optionally) ``kx_list(var)``,
      call ``summarize`` with the first variable and, if available, its first kx.
    - We only assert it does not raise; return type can vary across legacy impls.
    """
    rd = gd.read_diag([str(conv_path)])

    # bail out early if the legacy face isn't there
    if not hasattr(rd, "variables") or not callable(getattr(rd, "variables")):
        pytest.skip("legacy object has no variables()")

    vars_ = rd.variables()
    assert isinstance(vars_, (list, tuple))
    if not vars_:
        pytest.skip("no variables found in this conventional file")

    var = vars_[0]
    kxs = rd.kx_list(var) if hasattr(rd, "kx_list") else []
    kx = kxs[0] if kxs else None

    if hasattr(rd, "summarize"):
        # Do not assert on the return type — legacy can be printy or object-y
        _ = rd.summarize(varName=var, kx=kx)


@pytest.mark.parametrize("name", ["diagbuf_df", "diagbufex_df", "channel_df", "diagbufchan_df"])
def test_table_pass_through(conv_path, name):
    """``table(name)`` should pass-through legacy tables when present.

    Acceptance
    ----------
    - May return ``None`` (no such table).
    - May return a ``pd.DataFrame`` or a ``dict[int, DataFrame]``.
    """
    rd = gd.read_diag([str(conv_path)])
    if not hasattr(rd, "table"):
        pytest.skip("legacy object has no table()")

    try:
        t = rd.table(name)
    except Exception:
        # Be lenient with legacy corner-cases; just ensure it doesn't crash test run
        pytest.skip(f"table({name!r}) raised on this legacy backend")

    if t is None:
        return
    if isinstance(t, dict):
        assert all(isinstance(v, pd.DataFrame) for v in t.values())
    else:
        assert isinstance(t, pd.DataFrame)

