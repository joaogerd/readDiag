"""
Surface exports for DiagnosticAPI
=================================

This module centralizes the most common imports used by downstream
code when working with :mod:`readDiag.surface`.

It re-exports:

- :class:`DiagnosticAPI` : stable high-level interface.
- :class:`Metadata`      : container for dataset metadata.
- :class:`Kind`          : enumeration of dataset kinds (``conv``/``rad``).
- :class:`AccessAdapter` : adapter that wraps ``diagAccess`` to match the API.

Notes
-----
- By collecting these names under a single namespace, user code can
  simply do ``from readDiag.surface import DiagnosticAPI, AccessAdapter``.
- Internals are imported from submodules; this file is purely an alias
  layer for convenience.

Examples
--------
>>> from readDiag.surface import DiagnosticAPI, AccessAdapter
>>> from readDiag.reader import diagAccess
>>> raw = diagAccess("data/diag_amsua_n15_03.2024013018")
>>> api = AccessAdapter(raw)  # api: DiagnosticAPI
>>> m = api.meta()
>>> print(m.kind, m.date)
rad 2024-01-30 18:00:00
"""

# Re-export key API classes and helpers
from .api import DiagnosticAPI, Metadata, Kind  # type: ignore
from .access_adapter import AccessAdapter  # type: ignore

# Public names of this surface
__all__ = ["DiagnosticAPI", "Metadata", "Kind", "AccessAdapter"]

