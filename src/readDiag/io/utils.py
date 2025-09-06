"""
Shim module: `readDiag.io.utils`
================================

This module acts as a **compatibility shim** after the refactor of
the `readDiag` package. It re-exports all public helpers from the
package-level :mod:`readDiag._utils` so that relative imports
(e.g. ``from .utils import ...`` inside :mod:`readDiag.io.reader`)
continue to work without requiring code changes.

Notes
-----
- This shim should not be used directly in new code.
- Prefer importing from :mod:`readDiag._utils` instead.
- It exists solely to avoid breaking existing internal imports.

Examples
--------
Legacy relative import inside :mod:`readDiag.io.reader`:

>>> # Before refactor
>>> from .utils import fix_endian
>>> fix_endian(b"\x01\x00")

>>> # After refactor (still works via shim)
>>> from readDiag.io.utils import fix_endian
>>> fix_endian(b"\x01\x00")

Recommended modern usage:

>>> from readDiag._utils import fix_endian
>>> fix_endian(b"\x01\x00")
"""

# Re-export all public names from the private _utils module
# This keeps internal imports functional during the transition.
# Linting is suppressed because we intentionally use `import *`.
from .._utils import *  # noqa: F401,F403

