"""
Backward-compatibility opener alias for diagnostic file readers.

This module provides a simple alias to ensure older code using
``read_diag`` continues to function. Internally, it redirects
to the preferred function :func:`open_diagnostic`.

Notes
-----
- Modern code should import directly:

  >>> from readDiag import open_diagnostic

- For backwards compatibility, you can still do:

  >>> from readDiag import read_diag

Attributes
----------
open_diagnostic : Callable
    Primary entry point for opening diagnostic files.
read_diag : Callable
    Alias for :func:`open_diagnostic`.

Examples
--------
Preferred usage:

>>> from readDiag import open_diagnostic
>>> d = open_diagnostic("diag_conv_01.2024013018")
>>> m = d.meta()
>>> print(m.kind)
conv

"""

from __future__ import annotations
from .io.reader import diagAccess
from .surface.access_adapter import AccessAdapter
from .surface.api import DiagnosticAPI

def open_diagnostic(path: str) -> DiagnosticAPI:
    """High-level entrypoint: open a GSI diagnostic and return a DiagnosticAPI."""
    raw = diagAccess(path)               # motor baixo-nível (NÃO é legacy)
    return AccessAdapter(raw)            # superfície estável


