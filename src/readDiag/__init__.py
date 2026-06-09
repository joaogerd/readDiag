from __future__ import annotations

"""
Top-level package exports for readDiag
======================================

This module centralizes the most common entrypoints for users of the
:mod:`readDiag` package. By exposing a curated set of names, it provides
a **clean, stable interface** while keeping the internal package structure
flexible.

Exports
-------
- :func:`open_diagnostic`
    High-level entrypoint to open GSI diagnostic files and return a
    :class:`DiagnosticAPI` instance.
- :class:`DiagnosticAPI`
    Abstract interface for interacting with diagnostic backends.
- :class:`Metadata`
    Container for stable dataset metadata (file name, date, kind, etc.).
- :class:`Kind`
    Enumeration of dataset kinds (``"conv"`` or ``"rad"``).
- :class:`AccessAdapter`
    Adapter that normalizes the low-level backend output into the
    :class:`DiagnosticAPI` interface.
- :class:`ImpactAnalyzer`
    Utility class for computing observation impact diagnostics.

Notes
-----
- End-users are expected to import from this top-level module rather than
  deep submodules. For example::

      from readDiag import open_diagnostic, ImpactAnalyzer

- Some optional components are imported lazily to avoid loading heavy
  dependencies during package import.

Examples
--------
Open a conventional diagnostic file:

>>> from readDiag import open_diagnostic
>>> diag = open_diagnostic("data/diag_conv_01.2024013018")
>>> meta = diag.meta()
>>> print(meta.kind)
conv

Open a radiance diagnostic file:

>>> from readDiag import open_diagnostic
>>> diag = open_diagnostic("data/diag_amsua_n15_03.2024013018")
>>> meta = diag.meta()
>>> print(meta.kind)
rad

Access dataset metadata:

>>> from readDiag import open_diagnostic
>>> diag = open_diagnostic("data/diag_conv_01.2024013018")
>>> m = diag.meta()
>>> print(m.file_name, m.date, m.n_obs)
data/diag_conv_01.2024013018 2024-01-30 18:00:00 15234

Use the impact analysis API:

>>> from readDiag import ImpactAnalyzer
>>> analyzer = ImpactAnalyzer  # doctest: +SKIP

Use the API for plotting (if plotting dependencies are available):

>>> from readDiag import open_diagnostic
>>> from readDiag.plotting.wrappers import plot_kx_count
>>> diag = open_diagnostic("data/diag_conv_01.2024013018")
>>> plot_kx_count(diag)  # doctest: +SKIP
"""

from .open import open_diagnostic
from .surface.api import DiagnosticAPI, Metadata, Kind
from .surface.access_adapter import AccessAdapter

__all__ = [
    "open_diagnostic",
    "DiagnosticAPI",
    "Metadata",
    "Kind",
    "AccessAdapter",
    "ImpactAnalyzer",
]


def __getattr__(name: str):
    """Lazily expose optional or heavier top-level objects."""

    if name == "ImpactAnalyzer":
        from .analysis.impact import ImpactAnalyzer

        return ImpactAnalyzer

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
