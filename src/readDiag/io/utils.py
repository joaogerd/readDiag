"""
Shim module: `readDiag.io.utils`

This re-exports helpers from the package-level `_utils` so that
`from .utils import ...` inside `readDiag.io.reader` keeps working
after the refactor.
"""
from .._utils import *  # noqa: F401,F403
