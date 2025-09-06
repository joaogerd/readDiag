"""
Deprecated shim: `readDiag.reader`
----------------------------------

This module exists **only for backward compatibility**.

It re-exports objects from :mod:`readDiag.io.reader` so that older
imports like ``import readDiag.reader`` continue to work.

Notes
-----
- Prefer **new imports** from :mod:`readDiag.io.reader`.
- This shim may be removed in future releases.
- A `DeprecationWarning` is issued upon import to encourage migration.

Examples
--------
Legacy usage (deprecated):

>>> import readDiag.reader as rdr  # doctest: +SKIP
>>> d = rdr.diagAccess("diag_conv_01.2024013018")  # doctest: +SKIP

Modern usage (preferred):

>>> from readDiag.io import reader
>>> d = reader.diagAccess("diag_conv_01.2024013018")  # doctest: +SKIP
"""

import warnings as _w

# -------------------------------------------------------------------------
# Emit a deprecation warning as soon as this module is imported.
# The `stacklevel=2` ensures the warning points to the user code line.
# -------------------------------------------------------------------------
_w.warn(
    "readDiag.reader is deprecated; use readDiag.io.reader",
    DeprecationWarning,
    stacklevel=2,
)

# -------------------------------------------------------------------------
# Re-export all public symbols from the modern module.
# This allows older code to continue working unchanged,
# while gently pushing users toward the new API.
# -------------------------------------------------------------------------
from .io.reader import *  # noqa: F401,F403

