"""
Legacy compatibility package for old gsidiag-style imports.

This package provides shims and adapters to help migrate to the modern
`readDiag` API. New code should import from `readDiag` directly.
"""
import warnings as _w
_w.warn(
    "You are importing from `gsidiag` (legacy). Please migrate to `readDiag`. "
    "See MIGRATION_LEGACY.md for details.",
    DeprecationWarning, stacklevel=2
)

# Re-export conveniences if needed by old scripts (add minimally):
try:
    from readDiag import read_diag, open_diagnostic  # type: ignore
except Exception:
    pass
