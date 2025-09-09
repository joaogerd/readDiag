# --- readDiag/reader.py ------------------------------------------------------
from __future__ import annotations

"""
readDiag.reader (facade)
========================

High-level *facade* that preserves the historical public API
(:class:`diagAccess` / :class:`DiagAccess`) while delegating all format-
specific heavy lifting to dedicated submodules:

- ``readDiag.conv_reader`` — conventional diagnostics (GSI ``diag_conv_*``)
- ``readDiag.rad_reader``  — radiance  diagnostics (GSI ``diag_<sensor>_*``)
- ``readDiag.utils``       — shared helpers (endianness, logging, timing, NaN fixes)

The goal is to centralize *entry-point ergonomics* (auto-detection, common
flags, unified metadata) without mixing concerns with low-level I/O.

Examples
--------
>>> from readDiag.reader import diagAccess
>>> rd = diagAccess('data/diag_amsua_metop-a_01.2020010100')
>>> rd.get_data_type()
2
>>> meta = rd.get_file_info()
>>> sorted(meta.keys())[:3]
['data_type', 'date', 'file_name']
"""

from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import os
import struct
import pandas as pd
import numpy as np

from .utils import (
    logger,
    log_time,
    fix_endian,
    needs_swap_dtype,
    replace_sentinels,
)
from .conv_reader import read_conv_file, BASE20_COLS
from .rad_reader import (
    init_rad_dtypes,
    read_radiance,
)

__all__ = ["diagAccess", "DiagAccess"]


class diagAccess:
    """
    Unified reader for GSI diagnostics (conventional and radiance).

    The constructor *sniffs* the file type and routes to the appropriate
    implementation. Public methods mirror the legacy surface while adding
    a few quality-of-life utilities (e.g., CSV export, summary strings).

    Parameters
    ----------
    file_name : str
        Path to a **binary** GSI diagnostic file. NetCDF diagnostics are
        not supported here.
    var : str, optional
        Target variable for conventional files (e.g., ``'t'``, ``'q'``, ``'uv'``).
        Ignored for radiance files.
    use_memmap : bool, default False
        Use ``numpy.memmap`` for radiance payloads to reduce peak RAM usage (may
        increase I/O on spinning disks).
    fast : bool, default True
        Fast path for conventional data; enables optimized grouping and fewer copies.
    base20_only : bool, default True
        For conventional files with ``nreal > 20``, load only the first 20 slots
        (faster and memory friendly).
    read_sids : bool, default False
        Decode and include station IDs for conventional files (slower).
    compat_legacy : bool, default True
        Populate legacy alias columns for downstream compatibility.
    raw_numpy : bool, default False
        For conventional data, return raw NumPy arrays instead of DataFrames.
    compact : bool, default False
        For conventional data, return a single DataFrame per variable (no ``kx`` split).

    Notes
    -----
    - Data type codes follow the common convention: ``1 = conv``, ``2 = rad``.
    - Sentinel values present in diagnostics are converted to ``NaN`` on read.

    Examples
    --------
    Conventional (variable/kx drill-down):

    >>> rd = diagAccess('data/diag_conv_01.2024013018', var='t')
    >>> rd.get_data_type()
    1
    >>> rd.get_variables()[:3]
    ['t', 'q', 'ps']
    >>> kx = rd.get_kx_list('t')[:5]
    >>> isinstance(rd.get_dataframe('t', kx[0]), pd.DataFrame)
    True

    Radiance (1-based channel list):

    >>> rd = diagAccess('data/diag_amsua_n15_03.2024013018')
    >>> rd.get_data_type()
    2
    >>> rd.get_channels()[:3]
    [1, 2, 3]
    >>> info = rd.get_file_info()
    >>> info['n_channels'] > 0 and info['n_obs'] >= 0
    True
    """

    # cache to initialize radiance dtype tables only once
    _rad_inited: bool = False

    # --------------------------------------------------------------------- #
    # Constructor: detect format and route to the proper reader
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        file_name: str,
        var: Optional[str] = None,
        use_memmap: bool = False,
        fast: bool = True,
        base20_only: bool = True,
        read_sids: bool = False,
        compat_legacy: bool = True,
        raw_numpy: bool = False,
        compact: bool = False,
    ) -> None:
        # quick structural sanity
        size = os.path.getsize(file_name)
        if size < 4:
            raise ValueError(f"File too small to detect format: {file_name}")

        # NetCDF guard (classic CDF magic)
        with open(file_name, "rb") as f:
            sig = f.read(3)
        if sig == b"CDF":
            raise ValueError(
                "NetCDF detected. Provide *binary* diagnostics (netcdf_diag=.false.) "
                "or use a NetCDF-aware reader."
            )

        # store user knobs
        self.file_name = file_name
        self.var = var
        self.use_memmap = use_memmap
        self.fast = fast
        self.base20_only = base20_only
        self.read_sids = read_sids
        self.compat_legacy = compat_legacy
        self.raw_numpy = raw_numpy
        self.compact = compact

        fmt = self._detect_format_file(file_name)
        if fmt == "conv":
            # -------------------- Conventional path --------------------- #
            self._data_type = 1
            raw_data = read_conv_file(
                file_name,
                var=var,
                fast=fast,
                base20_only=base20_only,
                read_sids=read_sids,
                compat_legacy=compat_legacy,
                raw_numpy=raw_numpy,
                compact=compact,
                set_date_cb=lambda d: setattr(self, "_idate", d),
            )

            # Normalize sentinels to NaN for DataFrame outputs
            if not raw_numpy:
                for v in raw_data:
                    for kx in raw_data[v]:
                        raw_data[v][kx] = replace_sentinels(raw_data[v][kx])

            self._data_frame = raw_data

        else:
            # ---------------------- Radiance path ----------------------- #
            if not type(self)._rad_inited:
                init_rad_dtypes()
                type(self)._rad_inited = True

            self._data_type = 2

            idate, data_frame = read_radiance(
                    path = file_name,
                    use_memmap = use_memmap,
                    )
            # Header date is an integer like 2024013018
            self._idate = idate

            # Public structure for radiances: keep it explicit and predictable
            self._data_frame = data_frame
     
    # ============================== Public API =============================== #

    def get_date(self) -> datetime:
        """
        Return the analysis time embedded in the file.

        Returns
        -------
        datetime
            Datetime parsed from the diagnostic header.

        Raises
        ------
        AttributeError
            If the file did not provide a date.
        """
        if hasattr(self, "_idate"):
            return self._idate  # type: ignore[attr-defined]
        raise AttributeError("Date not set in this diagnostic.")

    def get_data_type(self) -> int:
        """
        Return the data type code.

        Returns
        -------
        int
            ``1`` for conventional; ``2`` for radiance.
        """
        return self._data_type  # type: ignore[attr-defined]

    def get_data_frame(self) -> Any:
        """
        Return the decoded data structure.

        Returns
        -------
        Any
            - **Radiance**: dict with keys ``sensor``, ``kx`` and ``dataframes``.
            - **Conventional**: nested dict of DataFrames (or raw arrays if
              ``raw_numpy=True``) with shape ``{var -> {kx -> DataFrame}}``.
        """
        return self._data_frame  # type: ignore[attr-defined]

    def get_variables(self) -> List[str]:
        """
        List conventional variables available in the file.

        Returns
        -------
        list of str

        Raises
        ------
        ValueError
            If the file is a radiance file.
        """
        if self._data_type != 1:
            raise ValueError("get_variables is only available for conventional data.")
        return list(self._data_frame.keys())

    def get_kx_list(self, var: str) -> List[int]:
        """
        List available ``kx`` codes for a given conventional variable.

        Parameters
        ----------
        var : str
            Variable key present in the dataset.

        Returns
        -------
        list of int
            Sorted observation types.

        Raises
        ------
        ValueError
            If not a conventional file or variable missing.
        """
        if self._data_type != 1:
            raise ValueError("get_kx_list is only available for conventional data.")
        if var not in self._data_frame:
            raise ValueError(f"Variable '{var}' not found.")
        return sorted(self._data_frame[var].keys())

    def get_channels(self) -> List[int]:
        """
        Return **1-based** channel indices for a radiance file.

        Returns
        -------
        list of int
            Channel indices starting at 1 (``[1, 2, ..., N]``).

        Raises
        ------
        ValueError
            If the file is conventional.

        Notes
        -----
        Historically some code used 0-based indices. This facade normalizes
        to **1-based** for user-facing methods. When selecting a channel to
        export (see :meth:`export_to_csv`), pass the same 1-based index.
        """
        if self._data_type != 2:
            raise ValueError("get_channels is only available for radiance data.")
        df_list = self._data_frame["dataframes"]["diagbufchan_df"]
        return list(range(1, len(df_list) + 1))

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return basic metadata for the file (type, date, sensor/platform).

        Returns
        -------
        dict
            Minimal, human-friendly metadata dictionary.
        """
        meta: Dict[str, Any] = {
            "file_name": self.file_name,
            "data_type": "conv" if self._data_type == 1 else "rad",
            "date": self.get_date(),
        }
        if self._data_type == 2:
            meta["sensor"] = self._data_frame.get("sensor")
            meta["kx"] = self._data_frame.get("kx")
        return meta

    def get_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        """
        Return a conventional DataFrame for a given variable and ``kx``.

        Parameters
        ----------
        var : str
            Variable present in the dataset (e.g., ``'t'``).
        kx : int
            Observation type code.

        Returns
        -------
        pandas.DataFrame

        Raises
        ------
        ValueError
            If not a conventional file.
        """
        if self._data_type != 1:
            raise ValueError("get_dataframe only valid for conventional diagnostics.")
        return self._data_frame[var][kx]

    def get_overview(self) -> str:
        """
        Return a human-readable summary of the file contents.

        Returns
        -------
        str
            Multi-line string with basic info and counts.
        """
        lines = [
            f"File: {self.file_name}",
            f"Type: {'Radiance' if self._data_type == 2 else 'Conventional'}",
            f"Date: {self.get_date()}",
        ]
        if self._data_type == 1:
            vars_ = self.get_variables()
            lines.append(f"Variables: {', '.join(vars_)}")
            for v in vars_:
                kx_list = self.get_kx_list(v)
                lines.append(f"  {v}: {len(kx_list)} kx types")
        else:
            lines.append(f"Sensor: {self._data_frame.get('sensor')}")
            lines.append(f"Platform: {self._data_frame.get('kx')}")
            ch = self._data_frame["dataframes"]["channel_df"]
            lines.append(f"Channels: {ch.shape[0]}")
        return "\n".join(lines)

    def get_file_info(self) -> Dict[str, Any]:
        """
        Return machine-friendly metadata for programmatic use.

        Returns
        -------
        dict
            Keys always include:
                - ``file_name``
                - ``data_type`` (``'conv'`` or ``'rad'``)
                - ``date`` (:class:`datetime`)
            For **radiance** also include:
                - ``sensor`` (e.g., ``'amsua'``)
                - ``platform`` (value stored in header ``dplat``)
                - ``n_channels`` (int)
                - ``n_obs`` (row count of main payload)
        """
        info: Dict[str, Any] = {
            "file_name": self.file_name,
            "data_type": "rad" if self._data_type == 2 else "conv",
            "date": self.get_date(),
        }
        if self._data_type == 2:
            info.update(
                {
                    "sensor": self._data_frame.get("sensor"),
                    "platform": self._data_frame.get("kx"),
                    "n_channels": self._data_frame["dataframes"]["channel_df"].shape[0],
                    "n_obs": self._data_frame["dataframes"]["diagbuf_df"].shape[0],
                }
            )
        return info

    def export_to_csv(
        self,
        path: str | Path,
        var: str | None = None,
        kx: int | None = None,
        channel: int | None = None,
    ) -> None:
        """
        Export a selected slice to CSV.

        Parameters
        ----------
        path : str or pathlib.Path
            Output CSV path.
        var : str, optional
            **Conventional only.** Variable key.
        kx : int, optional
            **Conventional only.** Observation type to export.
        channel : int, optional
            **Radiance only.** **1-based** channel index as returned by
            :meth:`get_channels`.

        Raises
        ------
        ValueError
            If required selectors are missing for the chosen file type.

        Examples
        --------
        Conventional:

        >>> rd = diagAccess('data/diag_conv_01.2024013018')
        >>> first_kx = rd.get_kx_list('t')[0]
        >>> rd.export_to_csv('t_kx.csv', var='t', kx=first_kx)

        Radiance (1-based channel):

        >>> rd = diagAccess('data/diag_amsua_n15_03.2024013018')
        >>> ch1 = rd.get_channels()[0]
        >>> rd.export_to_csv('ch01.csv', channel=ch1)
        """
        path = Path(path)
        if self._data_type == 1:
            if var is None or kx is None:
                raise ValueError("For conventional files, both var and kx must be provided.")
            df = self.get_dataframe(var, kx)
        else:
            if channel is None:
                raise ValueError("For radiance files, channel index must be provided.")
            # convert **1-based** -> internal 0-based list index
            idx0 = int(channel) - 1
            df = self._data_frame["dataframes"]["diagbufchan_df"][idx0]
        df.to_csv(path, index=False)

    # ---------------- deprecated bridges (kept for compatibility) ------------ #

    def overview(self):  # pragma: no cover
        """Deprecated: use :meth:`get_overview`."""
        import warnings
        warnings.warn("overview() is deprecated, use get_overview() instead",
                      DeprecationWarning, stacklevel=2)
        return self.get_overview()

    def pfileinfo(self):  # pragma: no cover
        """Deprecated: use :meth:`get_file_info`."""
        import warnings
        warnings.warn("pfileinfo() is deprecated, use get_file_info() instead",
                      DeprecationWarning, stacklevel=2)
        return self.get_file_info()

    def tocsv(self, *args, **kwargs):  # pragma: no cover
        """Deprecated: use :meth:`export_to_csv`."""
        import warnings
        warnings.warn("tocsv() is deprecated, use export_to_csv() instead",
                      DeprecationWarning, stacklevel=2)
        return self.export_to_csv(*args, **kwargs)

    # =============================== Internals =============================== #

    @staticmethod
    def _detect_format_file(file_name: str) -> str:
        """
        Sniff file type by reading the first big-endian int32.

        Parameters
        ----------
        file_name : str
            Path to the diagnostic file.

        Returns
        -------
        str
            ``'conv'`` if first big-endian int32 equals 4; otherwise ``'rad'``.

        Notes
        -----
        - Conventional diagnostics begin with a record marker ``4`` (big-endian).
        - Radiance diagnostics typically do not match this sentinel.
        """
        with open(file_name, "rb") as f:
            val = struct.unpack(">I", f.read(4))[0]
        return "conv" if val == 4 else "rad"


# Backward compatibility alias
DiagAccess = diagAccess

