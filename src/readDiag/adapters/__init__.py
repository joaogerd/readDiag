"""
Deprecated shim: `readDiag.adapters`

Re-exports the modern adapters from `readDiag.surface.*`.
"""
import warnings as _w
_w.warn(
    "readDiag.adapters is deprecated; use readDiag.surface.access_adapter.AccessAdapter "
    "or readDiag.surface.adapters.legacy.LegacyCompatAdapter",
    DeprecationWarning, stacklevel=2
)

from ..surface.access_adapter import AccessAdapter  # type: ignore

try:
    from ..surface.adapters.legacy import LegacyCompatAdapter  # type: ignore
except Exception:
    # Fallback no-op to keep importable even if legacy adapter is missing
    class LegacyCompatAdapter:  # type: ignore
        pass

__all__ = ["AccessAdapter", "LegacyCompatAdapter"]

