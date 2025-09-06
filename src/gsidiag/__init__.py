"""
Legacy compatibility package for old gsidiag-style imports.

This package provides shims and adapters to help migrate to the modern
`readDiag` API. New code should import from `readDiag` directly.
"""
from __future__ import annotations
import warnings as _w

_w.warn(
    "You are importing the legacy package 'gsidiag'. "
    "This interface is deprecated and will be removed in a future major release. "
    "Please migrate to 'readDiag.open.open_diagnostic' and the DiagnosticAPI.",
    DeprecationWarning,
    stacklevel=2,
)

# Reexporta a classe antiga para não quebrar scripts
from .legacy_api import read_diag  # noqa: F401

__all__ = ["read_diag"]

