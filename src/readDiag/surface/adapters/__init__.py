"""
readDiag.surface.adapters
=========================

Modern adapters package that provides bridges between internal backends
(``diagAccess``) and the stable :class:`DiagnosticAPI` surface.

This package centralizes two key adapters:

- :class:`AccessAdapter`:
    Main bridge to the modern backend ``diagAccess`` (from
    :mod:`readDiag.io.reader`). It exposes a stable, typed API that matches
    :class:`DiagnosticAPI`, ensuring forward compatibility.
- :class:`LegacyCompatAdapter`:
    Compatibility layer for legacy-like objects used in tests. It attempts
    to normalize old APIs into the stable interface, useful during
    migration.

Notes
-----
- This module is meant to be imported by external code that needs to use
  stable adapters without caring about internal paths.
- Prefer :class:`AccessAdapter` for production workflows.
- Use :class:`LegacyCompatAdapter` only when dealing with old test doubles
  or transitional backends.

Examples
--------
Importing and using the modern adapter:

>>> from readDiag.surface.adapters import AccessAdapter
>>> from readDiag.io.reader import diagAccess
>>> backend = diagAccess("data/diag_conv_01.2020010100")
>>> api = AccessAdapter(backend)   # api : DiagnosticAPI
>>> m = api.meta()
>>> m.kind
'conv'

Working with a legacy-like object:

>>> from readDiag.surface.adapters import LegacyCompatAdapter
>>> class FakeLegacy:
...     file_name = "diag_conv_01.2020010100"
...     def get_variables(self): return ["t", "q"]
...     def get_kx_list(self, var): return [120, 130]
...     def get_dataframe(self, var, kx):
...         import pandas as pd
...         return pd.DataFrame({"var": [var], "kx": [kx]})
...
>>> legacy_api = LegacyCompatAdapter(FakeLegacy())
>>> legacy_api.variables()
['t', 'q']
>>> legacy_api.kx_list("t")
[120, 130]
"""

# Import the modern AccessAdapter (bridge to diagAccess backend)
from ..access_adapter import AccessAdapter

# Import the legacy compatibility adapter
from .legacy import LegacyCompatAdapter

# Public symbols exported by this package
__all__ = ["AccessAdapter", "LegacyCompatAdapter"]

