# --- readDiag/rad.py ---------------------------------------------------------
from __future__ import annotations

"""
Radiance diagnostics reader.

This module provides low-ceremony building blocks to parse GSI-style
*radiance* diagnostic files. It reads:

1) The top-level header record (fixed-length, big-endian).
2) The per-channel metadata table.
3) The bulk payload (db, dbc, dbe) as a structured NumPy array, with an
   optional fast path using ``numpy.memmap``.

It also includes a converter that materializes the payload into
pandas DataFrames (one per channel), adding a few compatibility columns.

Design goals
------------
- Keep binary I/O small and focused for testability.
- Centralize endian handling via :func:`readDiag.utils.fix_endian`.
- Avoid heavy abstractions: each function does exactly one thing well.

Notes
-----
- Strings in the header are stored as fixed-size bytes; we decode them
  to UTF-8 and strip trailing NULs/whitespace.
- All integer/float fields are read big-endian (``>``) and converted to
  native endianness using :func:`fix_endian`.

Examples
--------
Quick peek into a radiance file:

>>> from readDiag.rad import read_rad_header, init_rad_dtypes
>>> init_rad_dtypes()
>>> with open("diag_amsua_n15_01.2024013018", "rb") as f:
...     header, size = read_rad_header(f, "diag_amsua_n15_01.2024013018")
...     nchanl = int(header["nchanl"])

Read channels and the payload, then convert to DataFrames:

>>> from readDiag.rad import read_rad_channels, read_rad_payload, extract_rad_dataframes
>>> with open("diag_amsua_n15_01.2024013018", "rb") as f:
...     # 1) header already consumed
...     chan_df = read_rad_channels(f, nchanl)
...     # 2) payload starts here
...     diag = read_rad_payload(f, size, header, use_memmap=True)
...     diagbuf_df, channels_df_list, extra_df = extract_rad_dataframes(diag, header)
>>> len(channels_df_list) == int(header["nchanl"])
True

High-level convenience function:

>>> from readDiag.rad import read_radiance
>>> result = read_radiance("diag_amsua_n15_01.2024013018", use_memmap=True)
>>> result["diagbuf_df"].head()
>>> result["channels_df"][0].head()  # channel 1 frame
"""

from typing import Any, Dict, IO, List, Tuple, Optional
import os
import numpy as np
import pandas as pd
from datetime import datetime

from .utils import logger, log_time, fix_endian, replace_sentinels

# ---------------------------------------------------------------------------
# dtype caches (initialized on first use)
# Using Optional[np.dtype] to be explicit and mypy-friendly.
header_info_dtype: Optional[np.dtype] = None
channel_info_dtype: Optional[np.dtype] = None


def init_rad_dtypes() -> None:
    """
    Initialize NumPy dtypes used by the radiance reader.

    This function is idempotent and safe to call multiple times.

    Notes
    -----
    Must be called once before using :func:`read_rad_header` or
    :func:`read_rad_channels`. High-level helpers in this module call it
    automatically, but the low-level functions assume it is initialized.
    """
    global header_info_dtype, channel_info_dtype
    if header_info_dtype is not None and channel_info_dtype is not None:
        return

    # Header record: fixed layout in big-endian order.
    header_info_dtype = np.dtype([
        ('head',     '>i4'),
        ('isis',     '>S20'),
        ('dplat',    '>S10'),
        ('obstype',  '>S10'),
        ('jiter',    '>i4'),
        ('nchanl',   '>i4'),
        ('npred',    '>i4'),
        ('idate',    '>i4'),
        ('ireal',    '>i4'),
        ('ipchan',   '>i4'),
        ('iextra',   '>i4'),
        ('jextra',   '>i4'),
        ('idiag',    '>i4'),
        ('angord',   '>i4'),
        ('iversion', '>i4'),
        ('inewpc',   '>i4'),
        ('ioff0',    '>i4'),
        ('ijacob',   '>i4'),
        ('tail',     '>i4'),
    ])

    # Per-channel table, big-endian as well.
    channel_info_dtype = np.dtype([
        ('head',   '>i4'),
        ('freq',   '>f4'),
        ('pol',    '>f4'),
        ('wave',   '>f4'),
        ('varch',  '>f4'),
        ('tlap',   '>f4'),
        ('iuse',   '>i4'),
        ('nuchan', '>i4'),
        ('ich',    '>i4'),
        ('tail',   '>i4'),
    ])


# ---------------------------------------------------------------------------
# Small helpers

def _ensure_dtypes() -> None:
    """Internal guard to make sure dtypes are initialized."""
    if header_info_dtype is None or channel_info_dtype is None:
        init_rad_dtypes()


def _decode_str(b: Any) -> Any:
    """
    Decode fixed-size bytes to str (UTF-8), stripping NULs/whitespace.
    Non-bytes are returned unchanged.
    """
    if isinstance(b, (bytes, np.bytes_)):
        return b.decode("utf-8", errors="replace").rstrip("\x00").strip()
    return b


def _decode_header_strings(hdr: Dict[str, Any]) -> Dict[str, Any]:
    """
    Decode known fixed-size string fields in the header mapping.
    """
    out = dict(hdr)
    for key in ("isis", "dplat", "obstype"):
        if key in out:
            out[key] = _decode_str(out[key])
    return out


# ---------------------------------------------------------------------------

def read_rad_header(f: IO[bytes], file_name: str) -> Tuple[Dict[str, Any], int]:
    """
    Read top-level radiance header.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the beginning of the file.
    file_name : str
        Path to the file (used to compute file size).

    Returns
    -------
    (header, size) : tuple
        Parsed header as ``dict`` (with native-endian numbers and decoded
        string fields) and the file size in bytes.

    Raises
    ------
    ValueError
        If the file is empty or the header record is malformed.

    Notes
    -----
    The returned mapping preserves all original fields found in the header
    record. Integer/float fields are converted to native endianness via
    :func:`fix_endian`. Known fixed-size strings (``isis``, ``dplat``,
    ``obstype``) are decoded to Python ``str``.
    """
    _ensure_dtypes()

    # Read exactly one structured record from the stream
    arr = np.fromfile(f, header_info_dtype, 1)
    if arr.size == 0:
        raise ValueError("Malformed radiance file: header record not found or truncated.")

    # Convert to native endianness and map to a dict
    rec = fix_endian(arr)[0]
    hdr = {k: rec[k].item() if hasattr(rec[k], "item") else rec[k] for k in rec.dtype.names}

    # Decode fixed-size byte strings to str
    hdr = _decode_header_strings(hdr)

    # Compute physical file size
    try:
        size = os.path.getsize(file_name)
    except OSError as exc:
        raise ValueError(f"Could not stat file size for {file_name!r}: {exc}") from exc

    return hdr, size


def read_rad_channels(f: IO[bytes], nchanl: int) -> pd.DataFrame:
    """
    Read channel metadata table.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the channel section (right after the header).
    nchanl : int
        Number of channels.

    Returns
    -------
    pandas.DataFrame
        Channel metadata with technical fields dropped (``head``, ``tail``).
        String-like columns (if any) are returned as decoded Python strings.

    Raises
    ------
    ValueError
        If the channel table is truncated.

    Examples
    --------
    >>> with open("diag_amsua_n15_01.2024013018", "rb") as f:
    ...     # assume the header has already been read
    ...     chan_df = read_rad_channels(f, 15)
    ...     list(chan_df.columns)[:5]
    ... # ['freq', 'pol', 'wave', 'varch', 'tlap']
    """
    _ensure_dtypes()

    arr = np.fromfile(f, channel_info_dtype, nchanl)
    if arr.size != nchanl:
        raise ValueError(f"Channel table truncated: expected {nchanl} rows, got {arr.size}")

    arr = fix_endian(arr)
    df = pd.DataFrame(arr).drop(['head', 'tail'], axis=1)

    # Decode any fixed-size bytes columns that might be present (future-proof)
    for c in df.columns:
        if pd.api.types.is_object_dtype(df[c]) and isinstance(df[c].iloc[0], (bytes, np.bytes_)):
            df[c] = df[c].map(_decode_str)
    return df


def read_rad_payload(
    f: IO[bytes],
    file_size: int,
    header: Dict[str, Any],
    use_memmap: bool,
) -> np.ndarray:
    """
    Read the bulk payload into a structured array (db, dbc, dbe).

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the start of the payload (after channels).
    file_size : int
        Total file size in bytes.
    header : dict
        Parsed radiance header (must contain ``ipchan``, ``npred``, ``ireal``,
        ``nchanl``, ``iextra``, ``jextra``, and optionally ``idiag``).
    use_memmap : bool
        If ``True`` and a real file path is available, use ``numpy.memmap`` for
        zero-copy reads. Otherwise falls back to a ``read()`` into memory.

    Returns
    -------
    numpy.ndarray
        Structured array with fields:
        - ``'db'``  : shape ``(record_count, ireal)``
        - ``'dbc'`` : shape ``(record_count, idiag * nchanl)``
        - ``'dbe'`` : shape ``(record_count, jextra)`` (may be 0-width)
        The array includes 4-byte paddings ``eh`` and ``et`` (ignored by clients).

    Notes
    -----
    ``idiag`` is at least ``ipchan + npred + 3``. When ``use_memmap`` is used,
    the file pointer is advanced to the end of the mapped region.
    """
    # Compute idiag with safety floor
    ipchan = int(header['ipchan'])
    npred  = int(header['npred'])
    ireal  = int(header['ireal'])
    nchanl = int(header['nchanl'])
    iextra = int(header['iextra'])
    jextra = int(header['jextra'])

    idiag_base = ipchan + npred + 3
    idiag = int(header.get('idiag', idiag_base))
    if idiag < idiag_base:
        idiag = idiag_base

    # Build the structured dtype for one "record" (db, dbc, [dbe])
    # Use big-endian float32 as per GSI diagnostics.
    dt = np.dtype([
        ('eh',  np.void, 4),                         # 4-byte padding (record head)
        ('db',  ('>f4', ireal)),                     # per-record header/geometry
        ('dbc', ('>f4', idiag * nchanl)),            # per-channel block (flattened)
        ('dbe', ('>f4', jextra) if iextra > 0 else ('>f4', 0)),  # optional extras
        ('et',  np.void, 4),                         # 4-byte padding (record tail)
    ])

    # How many full records fit the remaining bytes?
    offset = f.tell()
    remaining = max(0, file_size - offset)
    if dt.itemsize == 0:
        raise ValueError("Computed dtype has zero itemsize, cannot proceed.")
    num = remaining // dt.itemsize
    if num <= 0:
        # This might still be valid for empty payloads, but in practice indicates an error.
        raise ValueError("No payload records found (empty or truncated file).")

    # Fast path: memory-map if possible
    if use_memmap:
        filename = getattr(f, "name", None)
        if isinstance(filename, (str, os.PathLike)) and filename:
            mm = np.memmap(filename, dtype=dt, mode='r', offset=offset, shape=(num,))
            # Detach from the memmap to avoid holding the file handle
            arr = np.asarray(mm)
            # Advance the stream pointer to the end of the mapped region
            f.seek(offset + num * dt.itemsize)
            return fix_endian(arr)

        # Fallback for file-like objects without a real path
        buf = f.read(num * dt.itemsize)
        return fix_endian(np.frombuffer(buf, dtype=dt))

    # Standard path: read into memory
    buf = f.read(num * dt.itemsize)
    return fix_endian(np.frombuffer(buf, dtype=dt))


def extract_rad_dataframes(
    diag: np.ndarray,
    header: Dict[str, Any],
) -> Tuple[pd.DataFrame, List[pd.DataFrame], pd.DataFrame]:
    """
    Convert a structured radiance payload into pandas objects.

    Parameters
    ----------
    diag : numpy.ndarray
        Structured array returned by :func:`read_rad_payload`.
    header : dict
        Parsed header containing at least ``ipchan``, ``npred``, ``idiag`` (or enough
        fields to compute it), and ``nchanl``.

    Returns
    -------
    (diagbuf_df, channels_df_list, extra_df) : tuple
        diagbuf_df : pandas.DataFrame
            Per-record header/geometry frame (derived from ``diag['db']``).
        channels_df_list : list of pandas.DataFrame
            One DataFrame per channel, sliced from ``diag['dbc']`` using the
            computed ``idiag`` stride. Columns include::
                ['tb_obs','omf','omf_nbc','errinv','idqc','emiss','tlach','ts',
                 'pred1', ..., f'pred{npred+3}', 'spread', 'extra1', ...]
            For compatibility, we add:
            - ``end_err = 1 / errinv`` when ``errinv != 0`` (NaN otherwise)
            - ``oma``     filled with NaN if not present in the input layout
        extra_df : pandas.DataFrame
            DataFrame built from ``diag['dbe']``. It may be empty if the extra
            block is not present (``iextra == 0``).

    Notes
    -----
    The function does not attempt to interpret the physical meaning of columns;
    it reflects the serialized layout with minimal derivations (``end_err``, ``oma``).

    Examples
    --------
    >>> # Continuing from the previous example:
    >>> diagbuf_df, channels, extra = extract_rad_dataframes(diag, header)
    >>> channels[0].filter(['tb_obs', 'omf', 'errinv']).head()
    """
    # Canonical column layout for the per-record DB slice (header/geometry)
    header_diagbuf = [
        'lat','lon','elev','time','iscanp','zasat','ilazi','pangs','isazi','sgagl',
        'sfcwc','sfclc','sfcic','sfcsc','sfcwt','sfclt','sfcit','sfcst','sfcstp',
        'sfcsmc','sfcltp','sfcvf','sfcsd','sfcws','clsORclw','cldpORtpwc'
    ]

    header_diagbufchan = ['tb_obs','omf','omf_nbc','errinv','idqc','emiss','tlach','ts']

    # 1) Per-record DB frame
    db = fix_endian(diag['db'][:, :len(header_diagbuf)])
    diagbuf_df = pd.DataFrame(db, columns=header_diagbuf)

    # 2) Build the per-channel column names for DBC
    ipchan = int(header['ipchan'])
    npred  = int(header['npred'])
    nchanl = int(header['nchanl'])
    idiag_base = ipchan + npred + 3
    idiag = int(header.get('idiag', idiag_base))
    if idiag < idiag_base:
        idiag = idiag_base

    # Start with canonical part, then preds, spread, and any extras
    cols = header_diagbufchan.copy()
    for i in range(1, npred + 3):
        cols.append(f'pred{i}')
    cols.append('spread')

    base = ipchan + npred + 3
    if idiag > base:
        for j in range(1, idiag - base + 1):
            cols.append(f'extra{j}')

    # 3) Slice the flattened DBC (shape: [nrec, idiag * nchanl]) into per-channel frames
    df_list: List[pd.DataFrame] = []
    for i in range(nchanl):
        s, e = i * idiag, (i + 1) * idiag
        dbc = fix_endian(diag['dbc'][:, s:e])
        dfc = pd.DataFrame(dbc, columns=cols[:idiag])

        # Compatibility helpers:
        if 'errinv' in dfc.columns and 'end_err' not in dfc.columns:
            inv = dfc['errinv'].replace(0, np.nan)
            dfc['end_err'] = 1.0 / inv
        if 'oma' not in dfc.columns:
            dfc['oma'] = np.nan

        df_list.append(dfc)

    # 4) Extras block (may be 0-width if iextra == 0)
    dbe = fix_endian(diag['dbe'])
    extra_df = pd.DataFrame(dbe)

    return diagbuf_df, df_list, extra_df


# ---------------------------------------------------------------------------
# High-level convenience wrapper

@log_time
def read_radiance(path: str | os.PathLike, use_memmap: bool = True) -> Dict[str, Any]:
    """
    Read a complete GSI radiance diagnostic file.

    This convenience function orchestrates header, channels, and payload reads,
    then materializes the payload into pandas DataFrames.

    Parameters
    ----------
    path : str or os.PathLike
        Path to the GSI radiance diagnostic file.
    use_memmap : bool, default=True
        If ``True``, attempt to use memory mapping for the payload.

    Returns
    -------
    dict
        A mapping with the following keys:
        - ``'header'``      : dict with decoded strings and native-endian numbers
        - ``'file_size'``   : int, file size in bytes
        - ``'channels'``    : pandas.DataFrame (per-channel metadata)
        - ``'diagbuf_df'``  : pandas.DataFrame (per-record geometry/header)
        - ``'channels_df'`` : List[pandas.DataFrame] (one per channel)
        - ``'extra_df'``    : pandas.DataFrame (may be empty)

    Raises
    ------
    ValueError
        On malformed or truncated files.

    Examples
    --------
    >>> out = read_radiance("diag_amsua_n15_01.2024013018")
    >>> out['header']['nchanl']  # number of channels
    >>> len(out['channels_df'])  # equals nchanl
    """
    _ensure_dtypes()

    path = os.fspath(path)
    with open(path, "rb") as f:
        hdr, rec_size = read_rad_header(f, path)
        chdf = read_rad_channels(f, hdr["nchanl"])
        diag = read_rad_payload(f, rec_size, hdr, use_memmap)
        df1, df_list, df2 = extract_rad_dataframes(diag, hdr)

    # Normalize sentinels to NaN
    df1 = replace_sentinels(df1)
    df2 = replace_sentinels(df2)
    df_list = [replace_sentinels(df) for df in df_list]

    # Header date is an integer like 2024013018
    idate = datetime.strptime(str(int(hdr["idate"])), "%Y%m%d%H")

    # Public structure for radiances: keep it explicit and predictable
    data_frame = {
        "sensor": hdr["obstype"],            # e.g., "amsua"
        "kx": hdr["dplat"],                  # platform (legacy "kx"-ish slot)
        "dataframes": {
            "channel_df": chdf,              # channel metadata
            "diagbuf_df": df1,               # main payload ("bulk")
            "diagbufchan_df": df_list,       # list of per-channel DFs
            "diagbufex_df": df2,             # extended payload (when present)
        },
    }

    return idate, data_frame


__all__ = [
    "init_rad_dtypes",
    "read_rad_header",
    "read_rad_channels",
    "read_rad_payload",
    "extract_rad_dataframes",
    "read_radiance",
]

