# --- readDiag/api.py ---------------------------------------------------------
from __future__ import annotations

"""
Public function-based API that wraps the existing `diagAccess` class.

This module keeps your current implementation intact (it calls `diagAccess`
under the hood) while exposing simple functions that are convenient for
pipelines and new users:

- read_conv(path, ...)  → conventional diagnostics
- read_rad(path, ...)   → radiance diagnostics
- read_any(path, ...)   → auto-detect and read either kind

The return values are exactly the structures produced today by `diagAccess`,
so no duplication of logic and full compatibility.
"""

from pathlib import Path
from typing import Any, Dict, Literal

from .reader import diagAccess  # reuse your existing unified reader

Mode = Literal["raw", "compact", "split"]


def read_conv(
    path: str | Path,
    *,
    mode: Mode = "split",
    base20_only: bool = True,
    read_sids: bool = False,
    compat_legacy: bool = True,
    fast: bool = True,
) -> Dict[str, Any]:
    """
    Read a GSI conventional diagnostic file (via `diagAccess`).

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the `diag_conv_*` binary file.
    mode : {'raw', 'compact', 'split'}, default 'split'
        Output layout mode:
          - 'raw'     → raw NumPy arrays per variable,
          - 'compact' → one DataFrame per variable (key '__ALL__'),
          - 'split'   → nested dict: ``out[var][kx] -> DataFrame``.
    base20_only : bool, default True
        When ``nreal > 20``, read only the first 20 slots (faster, less RAM).
    read_sids : bool, default False
        Decode and include 8-character station IDs (when present).
    compat_legacy : bool, default True
        Include legacy alias columns to keep older downstream scripts working.
    fast : bool, default True
        Enable fast-path parsing (base-20 layout).

    Returns
    -------
    dict
        The same structure returned today by ``diagAccess(...).get_data_frame()``,
        but restricted to conventional files.

    Raises
    ------
    ValueError
        If the detected file is radiance instead of conventional.
    """
    raw_numpy = mode == "raw"
    compact = mode == "compact"

    diag = diagAccess(
        str(path),
        var=None,
        use_memmap=False,          # memmap is only relevant for radiance
        fast=fast,
        base20_only=base20_only,
        read_sids=read_sids,
        compat_legacy=compat_legacy,
        raw_numpy=raw_numpy,
        compact=compact,
    )
    if diag.get_data_type() != 1:
        raise ValueError("`read_conv` received a radiance file. Use `read_rad` or `read_any`.")
    return diag.get_data_frame()


def read_rad(
    path: str | Path,
    *,
    use_memmap: bool = True,
) -> Dict[str, Any]:
    """
    Read a GSI radiance diagnostic file (via `diagAccess`).

    Parameters
    ----------
    path : str or pathlib.Path
        Path to the radiance `diag_*` binary file (not NetCDF).
    use_memmap : bool, default True
        Use ``numpy.memmap`` for the payload when possible (lower RAM, more I/O).

    Returns
    -------
    dict
        The same structure returned today by ``diagAccess(...).get_data_frame()``,
        with keys like ``sensor``, ``kx`` and the nested ``dataframes`` dict.

    Raises
    ------
    ValueError
        If the detected file is conventional instead of radiance.
    """
    diag = diagAccess(
        str(path),
        var=None,
        use_memmap=use_memmap,
        fast=True,                 # unused for radiance, kept for symmetry
        base20_only=True,          # unused for radiance
        read_sids=False,           # unused for radiance
        compat_legacy=True,        # unused for radiance
        raw_numpy=False,           # unused for radiance
        compact=False,             # unused for radiance
    )
    if diag.get_data_type() != 2:
        raise ValueError("`read_rad` received a conventional file. Use `read_conv` or `read_any`.")
    return diag.get_data_frame()


def read_any(
    path: str | Path,
    *,
    conv_mode: Mode = "split",
    conv_base20_only: bool = True,
    conv_read_sids: bool = False,
    conv_compat_legacy: bool = True,
    conv_fast: bool = True,
    rad_use_memmap: bool = True,
) -> Dict[str, Any]:
    """
    Auto-detect the diagnostic type (conventional vs radiance) and read accordingly.

    Parameters
    ----------
    path : str or pathlib.Path
        Path to a binary diagnostic file (not NetCDF).
    conv_mode : {'raw','compact','split'}, default 'split'
        Output mode used if the file is detected as conventional.
    conv_base20_only : bool, default True
        Passed to :func:`read_conv` when conventional.
    conv_read_sids : bool, default False
        Passed to :func:`read_conv` when conventional.
    conv_compat_legacy : bool, default True
        Passed to :func:`read_conv` when conventional.
    conv_fast : bool, default True
        Passed to :func:`read_conv` when conventional.
    rad_use_memmap : bool, default True
        Passed to :func:`read_rad` when radiance.

    Returns
    -------
    dict
        Exactly the structure produced by ``diagAccess(...).get_data_frame()``.
    """
    # we let diagAccess sniff the file and do the heavy lifting
    raw_numpy = conv_mode == "raw"
    compact = conv_mode == "compact"

    diag = diagAccess(
        str(path),
        var=None,
        use_memmap=rad_use_memmap,
        fast=conv_fast,
        base20_only=conv_base20_only,
        read_sids=conv_read_sids,
        compat_legacy=conv_compat_legacy,
        raw_numpy=raw_numpy,
        compact=compact,
    )
    return diag.get_data_frame()

