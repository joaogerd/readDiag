"""
Deprecated shim: `readDiag.reader`
Use `readDiag.io.reader` instead.
"""
import warnings as _w
_w.warn("readDiag.reader is deprecated; use readDiag.io.reader", DeprecationWarning, stacklevel=2)
from .io.reader import *  # re-export diagAccess, etc.  # noqa: F401,F403
