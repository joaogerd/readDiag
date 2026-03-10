"""
readDiag
========

Top-level public API for the :mod:`readDiag` package.

This module provides a **stable, minimal surface API** for users while
keeping the internal package structure flexible. Most users should import
objects directly from this module instead of internal submodules.

The main entrypoint for working with diagnostics is :func:`open_diagnostic`,
which returns an object implementing :class:`DiagnosticAPI`.

Heavy components such as impact analysis tools are **lazily imported**
to avoid unnecessary import overhead.

Primary API
-----------

Opening diagnostics
~~~~~~~~~~~~~~~~~~~

>>> from readDiag import open_diagnostic
>>> diag = open_diagnostic("data/diag_conv_01.2024013018")
>>> meta = diag.meta()
>>> print(meta.kind)

Impact analysis
~~~~~~~~~~~~~~~

>>> from readDiag import ImpactAnalyzer
>>> ia = ImpactAnalyzer.from_pair("diag_omf", "diag_oma", var="t")
>>> df = ia.compute_all_metrics()  # doctest: +SKIP

Notes
-----
- Users should prefer importing from :mod:`readDiag` rather than internal
  modules (e.g. ``readDiag.analysis`` or ``readDiag.surface``).
- This guarantees compatibility with future refactors of the internal
  architecture.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

# ---------------------------------------------------------------------
# Core public API (lightweight imports)
# ---------------------------------------------------------------------

from .open import open_diagnostic
from .surface.api import DiagnosticAPI, Metadata, Kind
from .surface.access_adapter import AccessAdapter


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

__all__ = [
    # Core access
    "open_diagnostic",

    # Stable API contracts
    "DiagnosticAPI",
    "Metadata",
    "Kind",

    # Backend adapters
    "AccessAdapter",

    # Impact analysis (lazy-loaded)
    "ImpactAnalyzer",
    "ExperimentComparator",
    "ComparisonPlotter",
]


# ---------------------------------------------------------------------
# Type-checking support
# ---------------------------------------------------------------------
# These imports are only evaluated by type checkers and IDEs
# (mypy, pylance, pyright, etc.), not at runtime.

if TYPE_CHECKING:
    from .analysis.impact import (
        ImpactAnalyzer,
        ExperimentComparator,
        ComparisonPlotter,
    )


# ---------------------------------------------------------------------
# Lazy import system
# ---------------------------------------------------------------------

_LAZY_IMPORTS = {
    "ImpactAnalyzer": "analysis.impact",
    "ExperimentComparator": "analysis.impact",
    "ComparisonPlotter": "analysis.impact",
}


def __getattr__(name: str):
    """
    Lazily import optional submodules.

    This mechanism prevents heavy dependencies (e.g. NumPy, Matplotlib,
    or analysis utilities) from being imported during a simple
    ``import readDiag``.

    The requested attribute is imported only when accessed.

    Examples
    --------
    >>> from readDiag import ImpactAnalyzer
    >>> ia = ImpactAnalyzer(...)  # module imported here
    """

    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(f".{_LAZY_IMPORTS[name]}", __name__)
        return getattr(module, name)

    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
