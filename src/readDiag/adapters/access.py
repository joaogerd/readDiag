"""
Deprecated shim: `readDiag.adapters.access`.

This module provides a backward-compatibility shim to allow old imports of
``AccessAdapter`` from ``readDiag.adapters.access`` to continue working.

Notes
-----
- New code should import directly from:
  ``readDiag.surface.access_adapter``.
- A deprecation warning will be issued upon import.
- This shim will be removed in a future release.

Examples
--------
Legacy (deprecated):

>>> from readDiag.adapters.access import AccessAdapter  # doctest: +SKIP
>>> api = AccessAdapter("diag_conv_01.2024013018")      # doctest: +SKIP

Preferred:

>>> from readDiag.surface.access_adapter import AccessAdapter
>>> api = AccessAdapter("diag_conv_01.2024013018")      # doctest: +SKIP
"""

import warnings as _w

# Emit a deprecation warning when this shim is imported
_w.warn(
    "readDiag.adapters.access is deprecated; "
    "use readDiag.surface.access_adapter.AccessAdapter",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export the modern AccessAdapter for backward compatibility
from ..surface.access_adapter import AccessAdapter  # noqa: F401

# Limit public API to the re-exported symbol
__all__ = ["AccessAdapter"]

