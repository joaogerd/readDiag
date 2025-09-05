"""
Backward-compat opener alias.
Prefer: `from readDiag import read_diag` or `open_diagnostic`.
"""
from .io.reader import open_diagnostic as open_diagnostic  # type: ignore
read_diag = open_diagnostic
__all__ = ["open_diagnostic", "read_diag"]
