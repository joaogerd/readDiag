# tests/legacy/test_gsidiag_cli.py
from __future__ import annotations
import sys
import pytest

"""
CLI tests for the legacy `gsidiag` entrypoint.

These tests call `gsidiag.__main__.cli()` directly while temporarily
patching `sys.argv`. We exercise both conventional and radiance files,
as well as the optional summarize path controlled by `--var/--kx`.

Notes
-----
- The legacy CLI (see `src/gsidiag/__main__.py`) expects:
  * one or more diagnostic file paths (nargs="+")
  * optional `--var` (only for conventional files)
  * optional `--kx` (int; only for conventional files)
- The CLI prints via `pfileinfo()` and, if `--var` is provided,
  also prints `summarize(...)`.
- We do *not* assert exact strings beyond general hints,
  to keep the tests tolerant to minor wording changes.

Examples
--------
Typical manual usage (shell):

>>> # Show info for a single conv file
... gsidiag data/diag_conv_01.2024013018

>>> # Show info for multiple files (conv/rad mix is tolerated if supported)
... gsidiag data/diag_conv_01.2024013018 data/diag_amsua_n19_03.2024013018

>>> # Summarize a specific (var, kx) for conventional diagnostics
... gsidiag data/diag_conv_01.2024013018 --var t --kx 120
"""


def _with_argv(argv: list[str]):
    """Context-like helper to temporarily set sys.argv.

    Parameters
    ----------
    argv : list of str
        Full `sys.argv` to simulate, e.g., ["gsidiag", "<file>", "--var", "t"].

    Yields
    ------
    None
        Restores the previous `sys.argv` after the `yield`.
    """
    old = list(sys.argv)
    try:
        sys.argv = argv
        yield
    finally:
        sys.argv = old


def test_gsidiag_cli_conv(conv_path, capsys):
    """Exercise the basic CLI path for a conventional file.

    We assert:
    - return code is 0
    - output contains something indicative of file info or variable/kx listing
    """
    from gsidiag.__main__ import cli

    with _with_argv(["gsidiag", str(conv_path)]):
        ret = cli()
        assert ret == 0
        out = capsys.readouterr().out
        # We don't expect the program name literally in the output
        assert "legacy" not in out.lower()
        # Heuristics: either the joined path, or a variables/kx listing hint
        assert str(conv_path)[:10] in out or "var=" in out or "kx=" in out


def test_gsidiag_cli_rad(rad_path, capsys):
    """Exercise the basic CLI path for a radiance file.

    We assert:
    - return code is 0
    - output hints about channels being printed
    """
    from gsidiag.__main__ import cli

    with _with_argv(["gsidiag", str(rad_path)]):
        ret = cli()
        assert ret == 0
        out = capsys.readouterr().out
        assert "channels" in out.lower() or "channel" in out.lower()


def test_gsidiag_cli_with_summarize(conv_path, capsys):
    """If `--var/--kx` are accepted, the summarize path should run.

    We don't validate the exact text content, just that there is *some* output.
    """
    from gsidiag.__main__ import cli

    with _with_argv(["gsidiag", str(conv_path), "--var", "t", "--kx", "120"]):
        ret = cli()
        assert ret == 0
        out = capsys.readouterr().out
        assert out.strip() != ""


# ---------------------------
# Extra cases (useful checks)
# ---------------------------

def test_gsidiag_cli_multiple_files(conv_path, rad_path, capsys):
    """CLI should tolerate multiple input files (nargs='+').

    We assert:
    - return code is 0
    - output contains hints from both conventional and radiance summaries
    """
    from gsidiag.__main__ import cli

    with _with_argv(["gsidiag", str(conv_path), str(rad_path)]):
        ret = cli()
        assert ret == 0
        out = capsys.readouterr().out
        # Expect at least a channel hint (from rad) OR variables/kx hint (from conv)
        assert ("channels" in out.lower() or "channel" in out.lower()
                or "var=" in out.lower() or "kx=" in out.lower()
                or str(conv_path)[:10] in out)


def test_gsidiag_cli_var_without_kx(conv_path, capsys):
    """`--var` alone should still produce a summarize-like output (lenient path).

    Depending on implementation, summarize(varName=..., kx=None) may be allowed.
    We only assert that the command runs and prints something.
    """
    from gsidiag.__main__ import cli

    with _with_argv(["gsidiag", str(conv_path), "--var", "t"]):
        ret = cli()
        assert ret == 0
        out = capsys.readouterr().out
        assert out.strip() != ""


def test_gsidiag_cli_help_shows_usage(capsys):
    """`-h/--help` should display the usage and exit with SystemExit.

    We catch SystemExit to intercept the help path.
    """
    from gsidiag.__main__ import cli

    # argparse -h triggers SystemExit, so we guard it:
    with pytest.raises(SystemExit):
        with _with_argv(["gsidiag", "--help"]):
            cli()
    out = capsys.readouterr().out + capsys.readouterr().err
    # A generic but stable hint that usage/help was printed:
    assert "usage:" in out.lower()

