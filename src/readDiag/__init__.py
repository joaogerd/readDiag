# ---------------------------------------------------------------------------
# readDiag - GSI Diagnostic Reader & Visualization Toolkit
# ---------------------------------------------------------------------------
"""
readDiag
========

A Python toolkit for reading, processing, and visualizing GSI diagnostic files.

This package provides a modern API for conventional and radiance diagnostics,
impact analysis (FSOI / TI / FI / FBI), and publication-ready plots — while
maintaining backward compatibility with the legacy ``read_diag`` interface.

Main Features
-------------
- **Reading diagnostics**
  - :func:`read_conv` – Conventional diagnostics (3 modes: split, compact, raw)
  - :func:`read_rad`  – Radiance diagnostics with optional memmap
  - :func:`read_any`  – Auto-detects file type and dispatches accordingly
  - :class:`diagAccess` – Unified class-based access for diagnostics

- **Impact analysis**
  - :class:`ImpactAnalyzer` – Computes TI, FI, FBI from diag pairs
  - :class:`ExperimentComparator` – Cross-experiment diagnostics comparison
  - :class:`ComparisonPlotter` – Visualization helpers for comparisons

- **Plotting**
  - :class:`diagPlotter` – High-level plotting interface for diagnostics
  - :class:`PlotConfig` – Centralized styling for figures and tables

- **Legacy compatibility**
  - :func:`read_diag` – Deprecated entrypoint mimicking older API
    (wraps :class:`diagAccess` and :class:`ImpactAnalyzer`)

Examples
--------
Basic conventional usage
~~~~~~~~~~~~~~~~~~~~~~~~
>>> from readDiag import read_conv
>>> conv = read_conv("diag_conv_01.2020010100")
>>> df_t_kx187 = conv["t"][187]
>>> df_t_kx187.head()  # doctest: +SKIP

Radiance example
~~~~~~~~~~~~~~~~
>>> from readDiag import read_rad
>>> rad = read_rad("diag_amsua_n19_01.2020010100")
>>> rad["dataframes"]["channel_df"].head()  # doctest: +SKIP

Impact analysis with two files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
>>> from readDiag import ImpactAnalyzer
>>> ia = ImpactAnalyzer.from_pair("diag_omf", "diag_oma", var="t")
>>> ia.compute_all_metrics().head()  # doctest: +SKIP

Legacy interface (deprecated)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
>>> from readDiag import read_diag
>>> r = read_diag(["diag_omf", "diag_oma"])
>>> r.impact(var="t").compute_all_metrics().head()  # doctest: +SKIP

Notes
-----
- The legacy interface (``read_diag``) is provided for backward compatibility
  and will be removed in a future major release.
- For new projects, prefer the functional API (``read_conv``, ``read_rad``,
  ``read_any``) or ``ImpactAnalyzer.from_pair`` for impact studies.
"""
from __future__ import annotations

import argparse
from importlib.metadata import (
    PackageNotFoundError,
    metadata as _pkg_metadata,
    version as _pkg_version,
)
from typing import Tuple

# Public, light-weight imports (avoid pulling heavy plotting/impact deps at import time)
from .reader import diagAccess
from .api import read_conv, read_rad, read_any  # legacy-like functional API
from .legacy import read_diag  # deprecated wrapper for backward compatibility
from .open import open_diagnostic                  # NEW: stable factory (adapter-based)
from .surface import DiagnosticAPI, Metadata       # NEW: stable contract (Protocol + DTO)


# --- Package metadata (PEP 621 via importlib.metadata) -----------------------
try:
    __version__ = _pkg_version("readDiag")
    _md = _pkg_metadata("readDiag")
    __title__ = _md.get("Name", "readDiag")
    __summary__ = _md.get("Summary", "")
    __url__ = _md.get("Home-page", "")
    __license__ = _md.get("License", "LGPL-3.0")
    __author__ = _md.get("Author", "") or _md.get("Author-email", "")
except PackageNotFoundError:
    # Useful when running directly from source without installing (editable mode)
    __version__ = "0+unknown"
    __title__ = "readDiag"
    __summary__ = "Read, analyze and visualize GSI diagnostics (conv & radiance)."
    __url__ = ""
    __license__ = "LGPL-3.0"
    __author__ = "João Gerd Zell de Mattos"


def __version_tuple__() -> Tuple[int, int, int, str]:
    """Return version as an orderable tuple.

    Returns
    -------
    tuple of (int, int, int, str)
        ``(major, minor, micro, suffix)`` where ``suffix`` may be empty
        (e.g., ``''``) or contain prerelease/local tags such as ``'rc1'``,
        ``'dev5'`` or a local build identifier.

    Notes
    -----
    - Uses :mod:`packaging.version` when available for robust parsing.
    - Falls back to a conservative regex if parsing fails.

    Examples
    --------
    >>> mt, mn, mc, suf = __version_tuple__()
    >>> isinstance(mt, int) and isinstance(mn, int) and isinstance(mc, int)
    True
    """
    try:
        from packaging.version import parse as _parse

        v = _parse(__version__)
        # Build a readable suffix preserving pre/dev/local when present
        if v.pre:
            # e.g., ('rc', 1) → 'rc1'
            suffix = f"{v.pre[0]}{v.pre[1]}"
        elif v.dev is not None:
            suffix = f"dev{v.dev}"
        elif v.local:
            suffix = str(v.local)
        else:
            suffix = ""
        return (int(v.major), int(v.minor), int(v.micro), suffix)
    except Exception:
        # Fallback: '2.0.0rc1' -> (2, 0, 0, 'rc1')
        import re

        m = re.match(r"^(\d+)\.(\d+)\.(\d+)(.*)$", __version__)
        if not m:
            return (0, 0, 0, "unknown")
        major, minor, micro, tail = m.groups()
        tail = tail.lstrip(".-+")
        return (int(major), int(minor), int(micro), tail)


def show_versions() -> None:
    """Print a compact environment report (useful in issues).

    The report prints versions of core dependencies when available.

    Notes
    -----
    - Only imports :mod:`importlib.metadata` and standard library.
    - Avoids importing heavy optional dependencies during package import.

    Examples
    --------
    >>> # Prints to stdout
    >>> show_versions()  # doctest: +SKIP
    readDiag    : 2.1.0
    Python      : 3.12.2
    OS          : Linux 6.8.0-...  # etc.
    """
    import platform
    import sys
    from importlib.metadata import PackageNotFoundError, version

    def _ver(pkg: str) -> str:
        try:
            return version(pkg)
        except PackageNotFoundError:
            return "not installed"

    info = {
        "readDiag": __version__,
        "Python": sys.version.split()[0],
        "OS": f"{platform.system()} {platform.release()}",
        "NumPy": _ver("numpy"),
        "Pandas": _ver("pandas"),
        "Matplotlib": _ver("matplotlib"),
        "Cartopy": _ver("cartopy"),
    }
    widest = max(len(k) for k in info)
    for k, v in info.items():
        print(f"{k:<{widest}} : {v}")


def __getattr__(name: str):
    """Module-level lazy import hook.

    This enables accessing optional/heavy submodules on demand without
    importing them eagerly at package import time.

    Supported names
    ---------------
    - ``diagPlotter``, ``PlotConfig`` from :mod:`.plotting`
    - ``ImpactAnalyzer``, ``ExperimentComparator``, ``ComparisonPlotter`` from :mod:`.impact`
    - ``AccessAdapter``, ``LegacyCompatAdapter`` from :mod:`.adapters`

    Raises
    ------
    AttributeError
        If *name* is not one of the supported lazy attributes.
    """
    if name in ("diagPlotter", "PlotConfig"):
        from .plotting import PlotConfig, diagPlotter

        return {"diagPlotter": diagPlotter, "PlotConfig": PlotConfig}[name]
    if name in ("ImpactAnalyzer", "ExperimentComparator", "ComparisonPlotter"):
        from .impact import ComparisonPlotter, ExperimentComparator, ImpactAnalyzer

        return {
            "ImpactAnalyzer": ImpactAnalyzer,
            "ExperimentComparator": ExperimentComparator,
            "ComparisonPlotter": ComparisonPlotter,
        }[name]
    if name in ("AccessAdapter", "LegacyCompatAdapter"):
        from .adapters import AccessAdapter, LegacyCompatAdapter

        return {
            "AccessAdapter": AccessAdapter,
            "LegacyCompatAdapter": LegacyCompatAdapter,
        }[name]
    raise AttributeError(name)


def main(argv: list[str] | None = None) -> None:
    """Command-line entry point for ``python -m readDiag`` and ``readDiag``.

    Parameters
    ----------
    argv : list of str, optional
        Argument vector. If *None*, uses :data:`sys.argv[1:]`.

    Notes
    -----
    Exposes two quick commands:

    - ``--version``: print package version and exit.
    - ``--show-versions``: print a compact environment report.

    Examples
    --------
    From a shell:

    .. code-block:: bash

        $ python -m readDiag --version
        2.1.0

        $ python -m readDiag --show-versions
        readDiag    : 2.1.0
        Python      : 3.12.2
        ...

    Programmatic use:

    >>> main(['--version'])  # doctest: +SKIP
    """
    parser = argparse.ArgumentParser(prog="readDiag", add_help=True)
    parser.add_argument("--version", action="store_true", help="show package version and exit")
    parser.add_argument("--show-versions", action="store_true", help="print environment versions")
    args = parser.parse_args(argv)

    if args.version:
        print(__version__)
        return
    if args.show_versions:
        show_versions()
        return

    parser.print_help()


if __name__ == "__main__":
    # Allow `python readDiag/__init__.py --show-versions` during local dev,
    # but the canonical path is `python -m readDiag`.
    main()

__all__ = [
    # Core accessors
    "diagAccess",
    # Plotting (lazily provided via __getattr__)
    "diagPlotter",
    "PlotConfig",
    # Impact (lazily provided via __getattr__)
    "ImpactAnalyzer",
    "ExperimentComparator",
    "ComparisonPlotter",
    # Functional API
    "read_conv",
    "read_rad",
    "read_any",
    # Legacy
    "read_diag",
    # New stable, adapter-based surface
    "open_diagnostic",
    "DiagnosticAPI",
    "Metadata",
    # Adapters (lazily provided via __getattr__)
    "AccessAdapter",
    "LegacyCompatAdapter",
    # Utils
    "__version_tuple__",
    "show_versions",
    "main",
]

