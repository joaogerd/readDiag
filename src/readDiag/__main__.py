# readDiag/__main__.py
"""Executable entry point for the ``readDiag`` package.

This module enables users to run the package as a script using::

    python -m readDiag

It simply delegates execution to the :func:`readDiag.main` function,
defined in ``__init__.py``. This design ensures that the package can be
used both as a library (via imports) and as a command-line tool.

Notes
-----
- This file is required if you want to support execution of the package
  with the ``-m`` flag (PEP 338).
- Without this file, ``python -m readDiag`` would raise an error because
  Python expects a ``__main__.py`` inside the package.

Examples
--------
Run the CLI directly from the source tree:

>>> # From a shell, inside the repository root
>>> python -m readDiag --show-versions
readDiag version: 2.0.0
Python version: 3.11.9
...

Equivalent to calling:

>>> from readDiag import main
>>> main(["--show-versions"])
"""

# Import the CLI entry point defined in __init__.py
from . import main

# -------------------------------------------------------------------------
# Script execution
# -------------------------------------------------------------------------
if __name__ == "__main__":
    # Delegate execution to the main() function
    # This allows handling of command-line arguments consistently
    main()

