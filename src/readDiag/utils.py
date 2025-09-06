"""
Deprecated public utils shim.
Use `from readDiag._utils import ...` instead.

This module acts as a **compatibility layer** for older scripts that still
import from ``readDiag.utils``. In new code, prefer importing utilities
directly from :mod:`readDiag._utils`.

Notes
-----
- A deprecation warning is raised upon import, to guide users toward the new
  namespace.
- All objects are re-exported from :mod:`readDiag._utils`, ensuring that
  existing scripts relying on ``readDiag.utils`` continue to function.

Examples
--------
Legacy-style import (deprecated, but still works):

>>> from readDiag import utils  # doctest: +SKIP
>>> arr = utils.safe_asarray([1, 2, 3])  # doctest: +SKIP

Preferred import (direct):

>>> from readDiag._utils import safe_asarray
>>> arr = safe_asarray([1, 2, 3])
>>> arr
array([1, 2, 3])
"""
import warnings as _w

# -------------------------------------------------------------------------
# Emit deprecation warning once per session
# -------------------------------------------------------------------------
_w.warn(
    "readDiag.utils is deprecated; import from readDiag._utils",
    DeprecationWarning,
    stacklevel=2,
)

# -------------------------------------------------------------------------
# Re-export everything from the new internal utils module
# This preserves backward compatibility with old code.
# -------------------------------------------------------------------------
from ._utils import *  # noqa: F401,F403

