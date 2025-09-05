"""
Public surface contract re-export.
Prefer: `from readDiag.surface.api import DiagnosticAPI`
"""
from .surface.api import *  # noqa: F401,F403


# Back-compat helper expected by some tests
from . import read_diag as read_any  # type: ignore
