"""
Deprecated shim: `readDiag.adapters`

Re-exports the modern AccessAdapter from `readDiag.surface.access_adapter`.
"""
import warnings as _w
_w.warn("readDiag.adapters is deprecated; use readDiag.surface.access_adapter.AccessAdapter", DeprecationWarning, stacklevel=2)
from ..surface.access_adapter import AccessAdapter  # type: ignore
__all__ = ["AccessAdapter"]
