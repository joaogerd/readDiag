"""
Deprecated shim: `readDiag.adapters`

This module exists **only for backward compatibility**.
It re-exports the modern adapters located in `readDiag.surface.*`.

Notes
-----
- Prefer explicit imports from the new locations:
  - ``readDiag.surface.access_adapter.AccessAdapter``
  - ``readDiag.surface.adapters.legacy.LegacyCompatAdapter``

- This shim will be removed in a future release.
  Update your imports accordingly.

Examples
--------
Legacy-style imports (deprecated):

>>> from readDiag.adapters import AccessAdapter, LegacyCompatAdapter

Modern imports (preferred):

>>> from readDiag.surface.access_adapter import AccessAdapter
>>> from readDiag.surface.adapters.legacy import LegacyCompatAdapter
"""
import warnings as _w

# ---------------------------------------------------------------------
# Deprecation warning
# ---------------------------------------------------------------------
_w.warn(
    "readDiag.adapters is deprecated; use "
    "readDiag.surface.access_adapter.AccessAdapter or "
    "readDiag.surface.adapters.legacy.LegacyCompatAdapter",
    DeprecationWarning,
    stacklevel=2,
)

# ---------------------------------------------------------------------
# Re-exports
# ---------------------------------------------------------------------
# AccessAdapter is always expected to be available
from ..surface.access_adapter import AccessAdapter  # type: ignore

# LegacyCompatAdapter may not always be present
try:
    from ..surface.adapters.legacy import LegacyCompatAdapter  # type: ignore
except Exception:
    # Fallback dummy class to avoid ImportError in environments
    # where the legacy adapter is intentionally omitted.
    class LegacyCompatAdapter:  # type: ignore
        """Fallback no-op adapter when legacy support is unavailable."""

        pass


__all__ = ["AccessAdapter", "LegacyCompatAdapter"]


