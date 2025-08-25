# ---------------------------------------------------------------------------
# readDiag - GSI Diagnostic Reader & Visualization Toolkit
# ---------------------------------------------------------------------------
"""
readDiag
========

A Python toolkit for reading, processing, and visualizing GSI diagnostic files.

This package provides a modern API for conventional and radiance diagnostics,
impact analysis (FSOI / TI / FI / FBI), and publication-ready plots — while
maintaining backward compatibility with the legacy `read_diag` interface.

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
  - :class:`read_diag` – Deprecated entrypoint mimicking older API
    (wraps :class:`diagAccess` and :class:`ImpactAnalyzer`)

Examples
--------
Basic conventional usage:

    >>> from readDiag import read_conv
    >>> conv = read_conv("diag_conv_01.2020010100")
    >>> df_t_kx187 = conv["t"][187]
    >>> df_t_kx187.head()

Radiance example:

    >>> from readDiag import read_rad
    >>> rad = read_rad("diag_amsua_n19_01.2020010100")
    >>> rad["dataframes"]["channel_df"].head()

Impact analysis with two files:

    >>> from readDiag import ImpactAnalyzer
    >>> ia = ImpactAnalyzer.from_pair("diag_omf", "diag_oma", var="t")
    >>> ia.compute_all_metrics().head()

Legacy interface (deprecated):

    >>> from readDiag import read_diag
    >>> r = read_diag(["diag_omf", "diag_oma"])
    >>> r.impact(var="t").compute_all_metrics().head()

Notes
-----
- The legacy interface (`read_diag`) is provided for backward compatibility
  and will be removed in a future major release.
- For new projects, prefer the functional API (`read_conv`, `read_rad`,
  `read_any`) or `ImpactAnalyzer.from_pair` for impact studies.
"""

from .reader import diagAccess
from .plotting import diagPlotter
from .style import PlotConfig
from .impact import ImpactAnalyzer, ExperimentComparator, ComparisonPlotter
from .api import read_conv, read_rad, read_any
from .legacy import read_diag  # deprecated wrapper for backward compatibility

__all__ = [
    "diagAccess",
    "diagPlotter",
    "PlotConfig",
    "ImpactAnalyzer",
    "ExperimentComparator",
    "ComparisonPlotter",
    "read_conv",
    "read_rad",
    "read_any",
    "read_diag",  # deprecated
]

