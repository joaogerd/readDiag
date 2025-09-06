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

Backward-compatible usage:

>>> from readDiag import read_diag
>>> d = read_diag("diag_amsua_n15_01.2024013018")
>>> m = d.meta()
>>> print(m.kind)
rad
"""

# Import the preferred opener from the main package
from . import open_diagnostic as open_diagnostic  # noqa: F401

# Provide legacy alias
read_diag = open_diagnostic

# Explicit export list
__all__ = ["open_diagnostic", "read_diag"]

