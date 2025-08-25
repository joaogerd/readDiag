"""
readDiag.reader (facade)
========================

This module keeps the public API stable (``diagAccess`` / ``DiagAccess``),
while delegating the heavy lifting to submodules:

- ``readDiag.conv``  – conventional diagnostics reader
- ``readDiag.rad``   – radiance diagnostics reader
- ``readDiag.utils`` – shared helpers (endianness, logging, timing)

The refactor isolates concerns, shortens files, and enables focused
unit tests and documentation.

Example
-------
>>> from readDiag.reader import diagAccess
>>> rd = diagAccess('data/diag_amsua_metop-a_01.2020010100')
>>> rd.get_data_type()
2
>>> meta = rd.get_file_info()
>>> sorted(meta.keys())[:3]
['data_type', 'date', 'file_name']
"""
from __future__ import annotations

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
    """Unified reader for GSI diagnostics (conventional and radiance).

    Parameters
    ----------
    file_name : str
        Path to a GSI diagnostic file (binary, not NetCDF).
    var : str, optional
        Variable to focus on for conventional files (e.g., ``'t'``, ``'q'``, ``'uv'``).
        Ignored for radiance files.
    use_memmap : bool, default ``False``
        If ``True``, use ``numpy.memmap`` for radiance payload (reduces RAM at the
        cost of slower random access on spinning disks).
    fast : bool, default ``True``
        Fast path for conventional data; enables optimized grouping and fewer copies.
    base20_only : bool, default ``True``
        For conventional data with ``nreal > 20``, read only the first 20 slots for
        speed and memory savings.
    read_sids : bool, default ``False``
        Decode and include station IDs from conventional files.
    compat_legacy : bool, default ``True``
        Populate legacy alias columns (e.g., ``end_err``) for downstream code.
    raw_numpy : bool, default ``False``
        Return raw NumPy arrays for conventional data instead of DataFrames.
    compact : bool, default ``False``
        For conventional data, return a single DataFrame per variable (no split by ``kx``).

    Notes
    -----
    - The constructor detects the file type automatically.
    - Public methods remain stable relative to previous versions.

    Examples
    --------
    Create a reader and inspect an AMSU-A radiance file::

        from readDiag.reader import diagAccess
        rd = diagAccess('data/diag_amsua_metop-a_01.2020010100')
        print(rd.get_overview())
        ch0 = rd.get_data_frame()['dataframes']['diagbufchan_df'][0]
        print(ch0[['tb_obs','omf','errinv']].head())

    Load a conventional file, split by ``kx``::

        rd = diagAccess('data/diag_conv_01.2024013018', var='t', read_sids=True)
        df_120 = rd.get_dataframe('t', kx=120)
        print(df_120[['sid','obs','omf','errinv_fin']].head())
    """

    # cache for radiance dtype tables
    _rad_inited: bool = False

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
        self.file_name = file_name
        self.var = var
        self.use_memmap = use_memmap
        self.fast = fast
        self.base20_only = base20_only
        self.read_sids = read_sids
        self.compat_legacy = compat_legacy
        self.raw_numpy = raw_numpy
        self.compact = compact

        size = os.path.getsize(file_name)
        if size < 4:
            raise ValueError(f"File too small to detect format: {file_name}")

        with open(file_name, 'rb') as f:
            sig = f.read(3)
        if sig == b'CDF':
            raise ValueError(
                "NetCDF detected. Provide binary diagnostics (netcdf_diag=.false.)\n"
                "or use a NetCDF reader."
            )

        fmt = self._detect_format_file(file_name)
        if fmt == 'conv':
            self._data_type = 1
            self._data_frame = read_conv_file(
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
        else:
            if not type(self)._rad_inited:
                init_rad_dtypes()
                type(self)._rad_inited = True
            self._data_type = 2
            with open(file_name, 'rb') as f:
                hdr, size = read_rad_header(f, file_name)
                chdf = read_rad_channels(f, hdr['nchanl'])
                diag = read_rad_payload(f, size, hdr, use_memmap)
                df1, df_list, df2 = extract_rad_dataframes(diag, hdr)
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

    # --- public API (unchanged) ---
    def get_date(self) -> datetime:
        """Return the analysis time embedded in the file.

        Returns
        -------
        datetime
            Datetime parsed from the diagnostic header.
        """
        if hasattr(self, '_idate'):
            return self._idate  # type: ignore[attr-defined]
        raise AttributeError("Date not set.")

    def get_data_type(self) -> int:
        """Return the data type code (1=conv, 2=rad)."""
        return self._data_type  # type: ignore[attr-defined]

    def get_data_frame(self) -> Any:
        """Return the decoded data structure.

        For radiances, a dict with keys ``sensor``, ``kx`` and ``dataframes``.
        For conventional data, either a nested dict of DataFrames or raw NumPy
        arrays depending on constructor flags.
        """
        return self._data_frame  # type: ignore[attr-defined]

    def get_variables(self) -> List[str]:
        """List conventional variables available in the file.

        Returns
        -------
        list of str
            Variables (e.g., ``['t', 'q', 'uv']``).

        Raises
        ------
        ValueError
            If the file is radiance-type.
        """
        if self._data_type != 1:
            raise ValueError("get_variables is only available for conventional data.")
        return list(self._data_frame.keys())

    def get_kx_list(self, var: str) -> List[int]:
        """List available ``kx`` codes for a given conventional variable.

        Parameters
        ----------
        var : str
            Variable key present in the dataset.

        Returns
        -------
        list of int
            Sorted list of observation types.
        """
        if self._data_type != 1:
            raise ValueError("get_kx_list is only available for conventional data.")
        if var not in self._data_frame:
            raise ValueError(f"Variable '{var}' not found.")
        return sorted(self._data_frame[var].keys())

    def get_channels(self) -> List[int]:
        """Return channel indices for a radiance file.

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
        """Basic metadata for the file (type, date, sensor/platform).

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
        """Return a conventional DataFrame for a given variable and ``kx``.

        Parameters
        ----------
        var : str
        kx : int

        Returns
        -------
        pandas.DataFrame
        """
        if self._data_type != 1:
            raise ValueError("get_dataframe only valid for conventional diagnostics.")
        return self._data_frame[var][kx]

    def get_overview(self) -> str:
        """Human-readable summary of the file contents."""
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
        """Machine-friendly metadata for programmatic use."""
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
        """Export a slice to CSV.

        Parameters
        ----------
        path : str or pathlib.Path
        var : str, optional
            Required for conventional files.
        kx : int, optional
            Required for conventional files.
        channel : int, optional
            Required for radiance files.
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

    # deprecated aliases (kept for compatibility)
    def overview(self):  # pragma: no cover - deprecation bridge
        import warnings
        warnings.warn("overview() is deprecated, use get_overview() instead",
                      DeprecationWarning, stacklevel=2)
        return self.get_overview()

    def pfileinfo(self):  # pragma: no cover - deprecation bridge
        import warnings
        warnings.warn("pfileinfo() is deprecated, use get_file_info() instead",
                      DeprecationWarning, stacklevel=2)
        return self.get_file_info()

    def tocsv(self, *args, **kwargs):  # pragma: no cover - deprecation bridge
        import warnings
        warnings.warn("tocsv() is deprecated, use export_to_csv() instead",
                      DeprecationWarning, stacklevel=2)
        return self.export_to_csv(*args, **kwargs)

    @staticmethod
    def _detect_format_file(file_name: str) -> str:
        """Sniff file type: conventional if first int32==4, otherwise radiance.

        Parameters
        ----------
        file_name : str

        Returns
        -------
        str
            ``'conv'`` or ``'rad'``.
        """
        with open(file_name, 'rb') as f:
            val = struct.unpack('>I', f.read(4))[0]
        return 'conv' if val == 4 else 'rad'


# Backward compatibility alias
DiagAccess = diagAccess


# --- readDiag.utils ---------------------------------------------------------
from __future__ import annotations

import functools
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler
from typing import Any

import numpy as np

__all__ = [
    "logger",
    "log_time",
    "needs_swap_dtype",
    "fix_endian",
]


def _build_logger() -> logging.Logger:
    """Create a module-level logger (console + rotating file).

    Environment
    -----------
    DIAGACCESS_LOG_LEVEL : {"DEBUG","INFO","WARNING","ERROR"}
        Defaults to "INFO".
    """
    lg = logging.getLogger("readDiag")
    if lg.hasHandlers():
        return lg
    formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s")
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    lg.addHandler(console)
    file_handler = RotatingFileHandler(
        "diagAccess.log", maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setFormatter(formatter)
    lg.addHandler(file_handler)
    level = os.getenv("DIAGACCESS_LOG_LEVEL", "INFO").upper()
    lg.setLevel(getattr(logging, level, logging.INFO))
    return lg


logger = _build_logger()


def log_time(func):
    """Decorator to log execution time of methods.

    Examples
    --------
    >>> @log_time
    ... def slow():
    ...     import time; time.sleep(0.01)
    ...
    ...
    >>> slow()  # doctest: +ELLIPSIS
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        logger.info(f"{func.__name__} completed in {duration:.3f}s")
        return result

    return wrapper


def needs_swap_dtype(dt: np.dtype) -> bool:
    """Return True if any field of a dtype is non-native-endian.

    Parameters
    ----------
    dt : numpy.dtype

    Returns
    -------
    bool
    """
    native = "<" if sys.byteorder == "little" else ">"
    if dt.fields is None:
        return dt.byteorder not in ("=", "|", native)
    for _name, (subdt, _off) in dt.fields.items():
        bo = subdt.byteorder
        if bo in ("|", "="):
            continue
        if bo != native:
            return True
    return False


def fix_endian(arr: np.ndarray) -> np.ndarray:
    """Convert simple/structured arrays to native endianness (idempotent).

    Compatible with NumPy < 2.0 and >= 2.0.

    Parameters
    ----------
    arr : numpy.ndarray

    Returns
    -------
    numpy.ndarray
        View with native endianness (copy only when needed).
    """
    dt = arr.dtype
    if not needs_swap_dtype(dt):
        return arr
    swapped = arr.byteswap(inplace=False)
    try:
        return swapped.view(dt.newbyteorder("="))
    except Exception:  # pragma: no cover - old NumPy fallback
        return swapped.newbyteorder("=")


# --- readDiag.conv ----------------------------------------------------------
from __future__ import annotations

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .utils import logger, log_time, fix_endian

BASE20_COLS: List[str] = [
    'kx','ksub','lat','lon','elev','prs','hgt','time','iqc',
    'qc_setup','iuse','analysis_use','rwgt',
    'errinv_inp','errinv_adj','errinv_fin',
    'obs','omf','omf_wob','spread'
]


def _columns_for(var: str, nreal: int, fast: bool) -> List[str]:
    if fast:
        if var == 'uv':
            # replace tail with U/V components up to nreal
            tail = ['obs_u','omf_u','omf_wob_u','obs_v','omf_v','omf_wob_v']
            return BASE20_COLS[:16] + tail[:max(0, nreal - 16)]
        if var == 'wst':
            cols = BASE20_COLS.copy()
            cols[-1] = 'factw'
            return cols[:min(20, nreal)]
        return BASE20_COLS[:min(20, nreal)]
    # TODO: implement full column map when fast=False
    return BASE20_COLS[:min(20, nreal)]


def _apply_legacy_aliases(df: pd.DataFrame) -> pd.DataFrame:
    alias = {
        'dhgt': 'hgt', 'pbqc': 'iqc', 'emark': 'iqc',
        'iusev': 'analysis_use', 'wpbqc': 'rwgt',
        'inp_err': 'errinv_inp', 'adj_err': 'errinv_adj', 'end_err': 'errinv_fin',
    }
    for old, new in alias.items():
        if new in df.columns and old not in df.columns:
            df[old] = df[new]
    return df


def _read_conv_header(f) -> Optional[Tuple[str, int, int, int, int, int, Dict[str, int]]]:
    head = f.read(4)
    if not head:
        return None
    rec_len = int.from_bytes(head, 'big', signed=True)
    payload = f.read(rec_len)
    tail = int.from_bytes(f.read(4), 'big', signed=True)
    if tail != rec_len:
        raise ValueError("Fortran record length mismatch in header")
    var_id = payload[:3].decode('ascii', errors='ignore')
    ints_bytes = payload[3:]
    n_ints = len(ints_bytes) // 4
    ints = np.frombuffer(ints_bytes, dtype='>i4', count=n_ints)
    if ints.size < 5:
        raise ValueError("Header too short for conventional block")
    nchar, nreal, nobs, mype, ioff0 = map(int, ints[:5])
    extra = ints[5:].tolist()
    extras: Dict[str, int] = {}
    if var_id == '  t':
        extras['idia0'] = extra[0] if len(extra) >= 1 else 0
        extras['iip']   = extra[1] if len(extra) >= 2 else 0
    elif var_id == '  q':
        extras['iip']   = extra[0] if len(extra) >= 1 else 0
    return var_id, nchar, nreal, nobs, mype, ioff0, extras


def _read_block_base20(f, nobs: int, nreal: int, read_sids: bool, rkind: str = '>f4'):
    rec_len = int.from_bytes(f.read(4), 'big', signed=True)
    sids = None
    if read_sids:
        sid_bytes = f.read(8 * nobs)
        sid_arr = np.frombuffer(sid_bytes, dtype='S8').copy()
        sids = np.char.decode(sid_arr, 'latin-1', errors='ignore')
        sids = np.char.replace(sids, ' ', '')
        sids = np.char.rstrip(sids)
    else:
        f.seek(8 * nobs, 1)
    itemsize = 4 if rkind.endswith('f4') else 8
    real_nbytes = nobs * nreal * itemsize
    buf = f.read(real_nbytes)
    if len(buf) != real_nbytes:
        raise EOFError("unexpected EOF in data")
    tail = int.from_bytes(f.read(4), 'big', signed=True)
    if tail != rec_len:
        raise ValueError("Fortran record length mismatch in data")
    arr = np.frombuffer(buf, dtype=np.dtype(rkind))
    arr = fix_endian(arr)
    mats = arr.reshape((nreal, nobs), order='F')
    head = mats[: min(20, nreal), :].T
    return sids, head


def _read_block_full(f, nobs: int, nreal: int, read_sids: bool, rkind: str = '>f4'):
    rec_len = int.from_bytes(f.read(4), 'big', signed=True)
    buf = bytearray(rec_len)
    nread = f.readinto(buf)
    if nread != rec_len:
        raise EOFError("unexpected EOF in data record")
    if int.from_bytes(f.read(4), 'big', signed=True) != rec_len:
        raise ValueError("Fortran record length mismatch in data")
    sids = None
    if read_sids:
        sid_arr = np.frombuffer(memoryview(buf)[: 8 * nobs], dtype='S8').copy()
        sids = np.char.decode(sid_arr, 'latin-1', errors='ignore')
        sids = np.char.replace(sids, ' ', '')
        sids = np.char.rstrip(sids)
    real_mv = memoryview(buf)[8 * nobs :]
    dt_be = np.dtype(rkind)
    rb = np.frombuffer(real_mv, dtype=dt_be, count=nreal * nobs)
    rb = fix_endian(rb)
    rb = rb.reshape((nreal, nobs), order='F').T
    return sids, rb


@log_time
def read_conv_file(
    file_name: str,
    var: Optional[str] = None,
    fast: bool = True,
    base20_only: bool = True,
    read_sids: bool = False,
    compat_legacy: bool = True,
    raw_numpy: bool = False,
    compact: bool = False,
    set_date_cb = lambda _d: None,
):
    """Read a conventional diagnostics file.

    Returns either raw NumPy (``raw_numpy=True``) or a nested mapping
    ``{var -> {kx -> DataFrame}}`` (or ``{var -> {'__ALL__': DataFrame}}`` when
    ``compact=True``).
    """
    stash: Dict[str, List[np.ndarray]] = {}
    stash_sid: Dict[str, List[np.ndarray]] = {}
    with open(file_name, 'rb', buffering=1 << 20) as f:
        # tolerant global header (idate)
        try:
            hdr_vals = np.fromfile(f, '>i4', 3)
            if hdr_vals.size >= 2:
                set_date_cb(datetime.strptime(str(int(hdr_vals[1])), '%Y%m%d%H'))
        except Exception:
            pass
        while True:
            hv = _read_conv_header(f)
            if hv is None:
                break
            var_id, nchar, nreal, nobs, mype, ioff0, extras = hv
            if nobs <= 0:
                continue
            reader = _read_block_base20 if (base20_only and nreal > 20) else _read_block_full
            sids, rb = reader(f, nobs, nreal, read_sids, rkind='>f4')
            vid = var_id.strip()
            stash.setdefault(vid, []).append(rb)
            if read_sids and sids is not None:
                stash_sid.setdefault(vid, []).append(np.asarray(sids))
            iip = extras.get('iip', 0)
            if vid in ('t', 'q') and iip > 0:
                sids_p, rb_p = reader(f, iip, nreal, read_sids, rkind='>f4')
                stash[vid].append(rb_p)
                if read_sids and sids_p is not None:
                    stash_sid.setdefault(vid, []).append(np.asarray(sids_p))

    if raw_numpy:
        out_raw: Dict[str, Dict[str, np.ndarray]] = {}
        for vid, parts in stash.items():
            arr = parts[0] if len(parts) == 1 else np.vstack(parts)
            sids = None
            if read_sids and vid in stash_sid:
                sids = np.concatenate(stash_sid[vid], axis=0)
            out_raw[vid] = {'data': arr, 'sids': sids}
        return out_raw

    out: Dict[str, Dict[str, pd.DataFrame]] = {}
    for vid, parts in stash.items():
        arr = parts[0] if len(parts) == 1 else np.vstack(parts)
        sids = None
        if read_sids and vid in stash_sid:
            sids = np.concatenate(stash_sid[vid], axis=0)
        cols = _columns_for(vid, arr.shape[1], fast)
        n_take = min(arr.shape[1], len(cols))
        a = arr[:, :n_take]
        if compact:
            df = pd.DataFrame(a, columns=cols[:n_take])
            if read_sids and sids is not None:
                df.insert(0, 'sid', sids)
            if compat_legacy:
                df = _apply_legacy_aliases(df)
            out[vid] = {'__ALL__': df.reset_index(drop=True)}
            continue
        kx = np.rint(a[:, 0]).astype(np.int32, copy=False)
        order = np.argsort(kx, kind='stable')
        a_sorted = a[order]
        kx_sorted = kx[order]
        sids_sorted = sids[order] if (read_sids and sids is not None) else None
        boundaries = np.flatnonzero(np.diff(kx_sorted)) + 1
        chunks = np.split(a_sorted, boundaries)
        kxs = np.split(kx_sorted, boundaries)
        out[vid] = {}
        offset = 0
        for k_arr, rows in zip(kxs, chunks):
            k = int(k_arr[0])
            df = pd.DataFrame(rows, columns=cols[:n_take])
            if sids_sorted is not None:
                nrows = rows.shape[0]
                df.insert(0, 'sid', sids_sorted[offset : offset + nrows])
                offset += nrows
            if compat_legacy:
                df = _apply_legacy_aliases(df)
            out[vid][k] = df.reset_index(drop=True)
    return out


# --- readDiag.rad -----------------------------------------------------------
from __future__ import annotations

from typing import Any, Dict, IO, List, Tuple

import numpy as np
import pandas as pd

from .utils import fix_endian

header_info_dtype = None
channel_info_dtype = None


def init_rad_dtypes() -> None:
    global header_info_dtype, channel_info_dtype
    if header_info_dtype is not None:
        return
    header_info_dtype = np.dtype([
        ('head','>i4'),
        ('isis','>S20'), ('dplat','>S10'), ('obstype','>S10'),
        ('jiter','>i4'), ('nchanl','>i4'), ('npred','>i4'), ('idate','>i4'),
        ('ireal','>i4'), ('ipchan','>i4'), ('iextra','>i4'), ('jextra','>i4'),
        ('idiag','>i4'), ('angord','>i4'), ('iversion','>i4'), ('inewpc','>i4'),
        ('ioff0','>i4'), ('ijacob','>i4'), ('tail','>i4')
    ])
    channel_info_dtype = np.dtype([
        ('head','>i4'),('freq','>f4'),('pol','>f4'),('wave','>f4'),
        ('varch','>f4'),('tlap','>f4'),('iuse','>i4'),('nuchan','>i4'),
        ('ich','>i4'),('tail','>i4')
    ])


def read_rad_header(f: IO[bytes], file_name: str) -> Tuple[Dict[str, Any], int]:
    rec = np.fromfile(f, header_info_dtype, 1)[0]
    hdr = {k: rec[k] for k in rec.dtype.names}
    size = os.path.getsize(file_name)
    return hdr, size


def read_rad_channels(f: IO[bytes], nchanl: int) -> pd.DataFrame:
    arr = np.fromfile(f, channel_info_dtype, nchanl)
    arr = fix_endian(arr)
    return pd.DataFrame(arr).drop(['head', 'tail'], axis=1)


def read_rad_payload(f: IO[bytes], file_size: int, header: Dict[str, Any], use_memmap: bool) -> np.ndarray:
    ipchan = int(header['ipchan'])
    idiag_base = ipchan + int(header['npred']) + 3
    idiag = int(header.get('idiag', idiag_base))
    if idiag < idiag_base:
        idiag = idiag_base
    dt = np.dtype([
        ('eh',  np.void, 4),
        ('db',  ('>f4', int(header['ireal']))),
        ('dbc', ('>f4', idiag * int(header['nchanl']))),
        ('dbe', ('>f4', int(header['jextra']))) if int(header['iextra']) > 0 else ('>f4', 0),
        ('et',  np.void, 4)
    ])
    offset = f.tell()
    num = (file_size - offset) // dt.itemsize
    if use_memmap:
        mm = np.memmap(f.fileno(), dtype=dt, mode='r', offset=offset, shape=(num,))
        f.seek(offset + num * dt.itemsize)
        return fix_endian(mm)
    buf = f.read(num * dt.itemsize)
    return fix_endian(np.frombuffer(buf, dtype=dt))


def extract_rad_dataframes(diag: np.ndarray, header: Dict[str, Any]):
    header_diagbuf = [
        'lat','lon','elev','time','iscanp','zasat','ilazi','pangs','isazi','sgagl',
        'sfcwc','sfclc','sfcic','sfcsc','sfcwt','sfclt','sfcit','sfcst','sfcstp',
        'sfcsmc','sfcltp','sfcvf','sfcsd','sfcws','clsORclw','cldpORtpwc'
    ]
    header_diagbufchan = ['tb_obs','omf','omf_nbc','errinv','idqc','emiss','tlach','ts']
    df1 = pd.DataFrame(diag['db'][:, :len(header_diagbuf)], columns=header_diagbuf)
    ipchan = int(header['ipchan'])
    npred  = int(header['npred'])
    idiag  = int(header.get('idiag', ipchan + npred + 3))
    cols = header_diagbufchan.copy()
    for i in range(1, npred + 3):
        cols.append(f'pred{i}')
    cols.append('spread')
    base = ipchan + npred + 3
    if idiag > base:
        for j in range(1, idiag - base + 1):
            cols.append(f'extra{j}')
    df_list: List[pd.DataFrame] = []
    for i in range(int(header['nchanl'])):
        s, e = i * idiag, (i + 1) * idiag
        dfc = pd.DataFrame(diag['dbc'][:, s:e], columns=cols[:idiag])
        if 'errinv' in dfc.columns and 'end_err' not in dfc.columns:
            inv = dfc['errinv'].replace(0, np.nan)
            dfc['end_err'] = 1.0 / inv
        if 'oma' not in dfc.columns:
            dfc['oma'] = np.nan
        df_list.append(dfc)
    df2 = pd.DataFrame(diag['dbe'])
    return df1, df_list, df2
