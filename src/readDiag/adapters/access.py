"""
Deprecated shim: `readDiag.adapters.access`
Re-exports AccessAdapter from `readDiag.surface.access_adapter`.
"""
import warnings as _w
_w.warn(
    "readDiag.adapters.access is deprecated; use readDiag.surface.access_adapter.AccessAdapter",
    DeprecationWarning, stacklevel=2
)
from ..surface.access_adapter import AccessAdapter  # noqa: F401
__all__ = ["AccessAdapter"]
