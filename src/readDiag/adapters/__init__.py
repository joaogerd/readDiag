# readDiag/adapters/__init__.py
from __future__ import annotations

"""Adapter layer for diagnostic backends.

This subpackage contains adapters that wrap different generations of
diagnostic backends and expose a unified, stable
:class:`~readDiag.surface.DiagnosticAPI`.

Available adapters
------------------
- :class:`AccessAdapter`
    Wraps the modern :class:`readDiag.reader.diagAccess` backend.
    Preferred choice for all new code.
- :class:`LegacyCompatAdapter`
    Wraps legacy-style objects (including minimal fakes used in tests)
    and adapts them to the new :class:`~readDiag.surface.DiagnosticAPI`
    surface. Intended only for transition.

Examples
--------
Use the recommended adapter (via the factory in :mod:`readDiag.open`):

>>> from readDiag.open import open_diagnostic
>>> api = open_diagnostic("data/diag_amsua_n15_03.2024013018")
>>> meta = api.meta()
>>> print(meta.kind, meta.sensor)

Direct import (not recommended, but possible):

>>> from readDiag.adapters import AccessAdapter
>>> from readDiag.reader import diagAccess
>>> api = AccessAdapter(diagAccess("diag_conv_01.2020010100"))
"""

from .access import AccessAdapter
from .legacy import LegacyCompatAdapter

# Explicitly control public API of this subpackage
__all__ = ["AccessAdapter", "LegacyCompatAdapter"]

