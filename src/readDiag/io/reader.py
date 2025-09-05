# --- readDiag/reader.py ------------------------------------------------------
from __future__ import annotations

"""
readDiag.reader (facade)
========================

High-level facade that keeps the public API stable (``diagAccess`` / ``DiagAccess``)
while delegating heavy lifting to submodules:

- ``readDiag.conv``  – conventional diagnostics reader
- ``readDiag.rad``   – radiance diagnostics reader
- ``readDiag.utils`` – shared helpers (endianness, logging, timing)

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
from typing import Any, Dict, IO, List, Optional, Tuple, Union
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
from .conv import read_conv_file, BASE20_COLS
from .rad import (
    init_rad_dtypes,
    read_rad_header,
    read_rad_channels,
    read_rad_payload,
    extract_rad_dataframes,
)

__all__ = ["diagAccess", "DiagAccess"]


class diagAccess:
    """
    Unified reader for GSI diagnostics (conventional and radiance).

    Parameters
    ----------
    file_name : str
        Path to a GSI diagnostic file (binary, not NetCDF).
    var : str, optional
        Variable to focus on for conventional files (e.g., ``'t'``, ``'q'``, ``'uv'``).
        Ignored for radiance files.
    use_memmap : bool, default False
        If True, use ``numpy.memmap`` for radiance payload (lower RAM, potential disk I/O cost).
    fast : bool, default True
        Fast path for conventional data; enables optimized grouping and fewer copies.
    base20_only : bool, default True
        If ``nreal > 20``, read only the first 20 slots (speed & memory friendly).
    read_sids : bool, default False
        Decode and include station IDs from conventional files.
    compat_legacy : bool, default True
        Populate legacy alias columns for downstream code compatibility.
    raw_numpy : bool, default False
        For conventional data, return raw NumPy arrays instead of DataFrames.
    compact : bool, default False
        For conventional data, return one DataFrame per variable (no ``kx`` split).

    Notes
    -----
    The constructor detects the file type automatically and routes to the proper reader.
    Public methods are stable relative to previous versions.
    """

    _rad_inited: bool = False  # cache for radiance dtype tables

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
        size = os.path.getsize(file_name)
        if size < 4:
            raise ValueError(f"File too small to detect format: {file_name}")

        with open(file_name, 'rb') as f:
            sig = f.read(3)
        if sig == b'CDF':
            raise ValueError(
                "NetCDF detected. Provide binary diagnostics (netcdf_diag=.false.) "
                "or use a NetCDF reader."
            )

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
        if fmt == 'conv':
            # Read conventional diagnostics
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
                set_date_cb=lambda d: setattr(self, '_idate', d),
            )
            
            # Replace sentinel values with NaN for all DataFrames
            if not raw_numpy:
                for v in raw_data:
                    for kx in raw_data[v]:
                        raw_data[v][kx] = replace_sentinels(raw_data[v][kx])
            
            self._data_frame = raw_data

        else:
            # Initialize radiance dtypes only once
            if not type(self)._rad_inited:
                init_rad_dtypes()
                type(self)._rad_inited = True
            self._data_type = 2
            with open(file_name, 'rb') as f:
                hdr, size = read_rad_header(f, file_name)
                chdf = read_rad_channels(f, hdr['nchanl'])
                diag = read_rad_payload(f, size, hdr, use_memmap)
                df1, df_list, df2 = extract_rad_dataframes(diag, hdr)
                
            # Replace sentinel values in all radiance DataFrames
            df1 = replace_sentinels(df1)
            df2 = replace_sentinels(df2)
            df_list = [replace_sentinels(df) for df in df_list]
                
            self._idate = datetime.strptime(str(int(hdr['idate'])), "%Y%m%d%H")
            self._data_frame = {
                'sensor': hdr['obstype'],
                'kx': hdr['dplat'],
                'dataframes': {
                    'channel_df': chdf,
                    'diagbuf_df': df1,
                    'diagbufchan_df': df_list,
                    'diagbufex_df': df2,
                },
            }

    # ---------------- Public API ----------------

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
        if hasattr(self, '_idate'):
            return self._idate  # type: ignore[attr-defined]
        raise AttributeError("Date not set.")

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
            For radiances, a dict with keys ``sensor``, ``kx`` and ``dataframes``.
            For conventional data, either a nested dict of DataFrames or raw NumPy
            arrays depending on constructor flags.
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
        Return channel indices for a radiance file.

        Returns
        -------
        list of int

        Raises
        ------
        ValueError
            If the file is conventional.
        """
        if self._data_type != 2:
            raise ValueError("get_channels is only available for radiance data.")
        df_list = self._data_frame["dataframes"]["diagbufchan_df"]
        return list(range(len(df_list)))

    def get_metadata(self) -> Dict[str, Any]:
        """
        Return basic metadata for the file (type, date, sensor/platform).

        Returns
        -------
        dict
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
        kx : int

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
        """
        lines = [f"File: {self.file_name}",
                 f"Type: {'Radiance' if self._data_type == 2 else 'Conventional'}",
                 f"Date: {self.get_date()}"]
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
            Keys include ``file_name``, ``data_type``, ``date``; for radiances
            also ``sensor``, ``platform``, ``n_channels`` and ``n_obs``.
        """
        info: Dict[str, Any] = {
            "file_name": self.file_name,
            "data_type": "rad" if self._data_type == 2 else "conv",
            "date": self.get_date(),
        }
        if self._data_type == 2:
            info.update({
                "sensor": self._data_frame.get("sensor"),
                "platform": self._data_frame.get("kx"),
                "n_channels": self._data_frame["dataframes"]["channel_df"].shape[0],
                "n_obs": self._data_frame["dataframes"]["diagbuf_df"].shape[0],
            })
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
            Required for conventional files.
        kx : int, optional
            Required for conventional files.
        channel : int, optional
            Required for radiance files.

        Raises
        ------
        ValueError
            If required selectors are missing for the chosen file type.
        """
        path = Path(path)
        if self._data_type == 1:
            if var is None or kx is None:
                raise ValueError("For conventional files, both var and kx must be provided.")
            df = self.get_dataframe(var, kx)
        else:
            if channel is None:
                raise ValueError("For radiance files, channel index must be provided.")
            df = self._data_frame["dataframes"]["diagbufchan_df"][channel]
        df.to_csv(path, index=False)

    # ---- deprecated bridges (kept for compatibility) ---------------------

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

    # ---------------- Internals ----------------

    @staticmethod
    def _detect_format_file(file_name: str) -> str:
        """
        Sniff file type.

        Parameters
        ----------
        file_name : str

        Returns
        -------
        str
            ``'conv'`` if first big-endian int32 equals 4; otherwise ``'rad'``.
        """
        with open(file_name, 'rb') as f:
            val = struct.unpack('>I', f.read(4))[0]
        return 'conv' if val == 4 else 'rad'


# Backward compatibility alias
DiagAccess = diagAccess

