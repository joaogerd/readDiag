"""
Deprecated public utils shim.
Use `from readDiag._utils import ...` instead.
"""
import warnings as _w
_w.warn("readDiag.utils is deprecated; import from readDiag._utils", DeprecationWarning, stacklevel=2)
from ._utils import *  # noqa: F401,F403
