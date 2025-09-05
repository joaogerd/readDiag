"""
Deprecated: `readDiag.legacy`
Redirects to `gsidiag.legacy_api` for old helpers.
"""
import warnings as _w
_w.warn("readDiag.legacy is deprecated; use gsidiag.legacy_api", DeprecationWarning, stacklevel=2)
from gsidiag.legacy_api import *  # type: ignore  # noqa: F401,F403
