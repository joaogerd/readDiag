"""
Deprecated: `readDiag.legacy`
=============================

This module exists only for **backward compatibility**.  
It re-exports legacy helper functions and classes from
:mod:`gsidiag.legacy_api` to avoid breaking older scripts.

Notes
-----
- New code should **not** use this module.
- Use :mod:`gsidiag.legacy_api` directly instead.
- A :class:`DeprecationWarning` is raised on import to
  inform users of the deprecation.

Examples
--------
Legacy import (deprecated):

>>> import readDiag.legacy  # doctest: +SKIP
... # DeprecationWarning: readDiag.legacy is deprecated; use gsidiag.legacy_api

Modern usage (recommended):

>>> from gsidiag import legacy_api
>>> # access helpers directly, e.g. legacy_api.LegacyHandle
"""

import warnings as _w

# ---------------------------------------------------------------------
# Emit deprecation warning at import time
# ---------------------------------------------------------------------
_w.warn(
    "readDiag.legacy is deprecated; use gsidiag.legacy_api",
    DeprecationWarning,
    stacklevel=2,
)

# ---------------------------------------------------------------------
# Re-export all symbols from gsidiag.legacy_api for compatibility
# ---------------------------------------------------------------------
from gsidiag.legacy_api import *  # type: ignore  # noqa: F401,F403

