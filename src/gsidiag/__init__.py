from __future__ import annotations
import warnings as _w

# ---------------------------------------------------------------------------
# Emit a deprecation warning when the legacy package is imported
# ---------------------------------------------------------------------------
_w.warn(
    "You are importing the legacy package 'gsidiag'. "
    "This interface is deprecated and will be removed in a future major release. "
    "Please migrate to 'readDiag.open.open_diagnostic' and the DiagnosticAPI.",
    DeprecationWarning,
    stacklevel=2,
)

from .legacy_api import read_diag  # noqa: F401

__all__ = ["read_diag"]


"""
Legacy shim: gsidiag
====================

This module exists **only for backward compatibility**.  
It re-exports the function :func:`read_diag` from the legacy API,
while emitting a deprecation warning at import time.

Users are strongly encouraged to migrate to the new API:

- Use :func:`readDiag.open.open_diagnostic` as the main entry point.
- Work with the stable :class:`DiagnosticAPI` surface.
- Legacy-specific behaviors (like ``read_diag``) will be removed in a
  future release.

Notes
-----
- This module will continue to work for now, but **may be removed in v3.0.0**.
- Warnings are issued at import time to encourage migration.

Examples
--------
Legacy import (deprecated):

>>> import gsidiag
>>> diag = gsidiag.read_diag("data/diag_conv_01.2024013018")
>>> diag.pfileinfo()  # print file metadata
# ... legacy output ...

Modern import (recommended):

>>> from readDiag.open import open_diagnostic
>>> api = open_diagnostic("data/diag_conv_01.2024013018")
>>> meta = api.meta()
>>> print(meta.kind)
'conv'

See Also
--------
readDiag.open.open_diagnostic : Modern entry point for diagnostics.
readDiag.surface.DiagnosticAPI : Stable high-level surface for analysis.
"""

