"""
Backward-compat opener alias.
Prefer: `from readDiag import read_diag` or `open_diagnostic`.
"""
from . import open_diagnostic as open_diagnostic  # noqa: F401
read_diag = open_diagnostic
__all__ = ["open_diagnostic", "read_diag"]
