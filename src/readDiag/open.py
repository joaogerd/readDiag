# readDiag/open.py
from __future__ import annotations

"""Convenience factory for opening diagnostic files.

This module provides :func:`open_diagnostic`, the preferred entry point for
users and higher-level tools. It abstracts away the choice of backend and
returns a stable :class:`~readDiag.surface.DiagnosticAPI` object.

Design
------
- Currently wraps :class:`readDiag.reader.diagAccess` via
  :class:`readDiag.adapters.AccessAdapter`.
- Allows forwarding backend-specific kwargs to the underlying reader.
- Ensures that callers always interact with the stable API surface defined
  in :mod:`readDiag.surface`.

Examples
--------
Basic usage (works for both conventional and radiance files):

>>> from readDiag.open import open_diagnostic
>>> api = open_diagnostic("data/diag_amsua_n15_03.2024013018")
>>> meta = api.meta()
>>> print(meta.kind, meta.sensor, meta.n_channels)
rad amsua 15

For conventional files:

>>> api = open_diagnostic("data/diag_conv_01.2020010100")
>>> if api.kind() == "conv":
...     for var in api.variables():
...         for kx in api.kx_list(var):
...             df = api.frame_conv(var, kx)
...             print(var, kx, len(df))

For radiance files:

>>> api = open_diagnostic("data/diag_amsua_n15_03.2024013018")
>>> if api.kind() == "rad":
...     for ch in api.channels():
...         df = api.frame_channel(ch)
...         print("channel", ch, "rows", len(df))
"""

from .surface import DiagnosticAPI
from .adapters import AccessAdapter
from .reader import diagAccess


def open_diagnostic(path: str, **kwargs) -> DiagnosticAPI:
    """Open a diagnostic binary file and return a stable API.

    Parameters
    ----------
    path : str
        Path to a diagnostic binary file (conventional or radiance).
    **kwargs
        Extra keyword arguments forwarded to
        :class:`readDiag.reader.diagAccess`. This allows callers to
        configure backend behavior (e.g., use of memory mapping,
        base20 filtering, read_sids, etc.).

    Returns
    -------
    DiagnosticAPI
        An adapter-wrapped backend instance that implements the stable
        :class:`~readDiag.surface.DiagnosticAPI`.

    Notes
    -----
    - The returned object is guaranteed to follow the stable surface,
      independent of backend internals.
    - The backend is *not* cached globally; callers should reuse the
      returned instance rather than reopening the same file repeatedly.

    See Also
    --------
    readDiag.surface.DiagnosticAPI
    readDiag.adapters.AccessAdapter
    """
    # Instantiate the backend reader with all forwarded kwargs
    backend = diagAccess(path, **kwargs)

    # Wrap in an AccessAdapter to expose the stable DiagnosticAPI surface
    return AccessAdapter(backend)

