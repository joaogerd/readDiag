# --- readDiag/rad.py ---------------------------------------------------------
from __future__ import annotations

"""
Radiance diagnostics reader.

Parses radiance header and channel tables, reads the structured payload
(with ``memmap`` option), and converts the bulk arrays into pandas DataFrames
(one per channel) with compatibility columns (e.g., ``end_err``).

Functions here are low-ceremony and focused on the specific GSI binary layout.
"""

from typing import Any, Dict, IO, List, Tuple
import os
import numpy as np
import pandas as pd

from .utils import fix_endian

# dtype caches (initialized on first use)
header_info_dtype = None
channel_info_dtype = None


def init_rad_dtypes() -> None:
    """
    Initialize NumPy dtypes used by the radiance reader.

    Notes
    -----
    Must be called once before using :func:`read_rad_header` or
    :func:`read_rad_channels`.
    """
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
    """
    Read top-level radiance header.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream starting at the beginning of the file.
    file_name : str
        Path to the file (used to compute file size).

    Returns
    -------
    (header, size) : tuple
        Parsed header as ``dict`` and file size in bytes.

    Raises
    ------
    ValueError
        If the file is too small or not a valid radiance header.
    """
    arr = np.fromfile(f, header_info_dtype, 1)
    if arr.size == 0:
        raise ValueError("Malformed radiance file: header record not found.")
    rec = arr[0]
    hdr = {k: rec[k] for k in rec.dtype.names}
    size = os.path.getsize(file_name)
    return hdr, size

def read_rad_channels(f: IO[bytes], nchanl: int) -> pd.DataFrame:
    """
    Read channel metadata table.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the channel section.
    nchanl : int
        Number of channels.

    Returns
    -------
    pandas.DataFrame
        Channel metadata with technical fields dropped (``head``, ``tail``).
    """
    arr = np.fromfile(f, channel_info_dtype, nchanl)
    arr = fix_endian(arr)
    return pd.DataFrame(arr).drop(['head', 'tail'], axis=1)


def read_rad_payload(
    f: IO[bytes],
    file_size: int,
    header: Dict[str, Any],
    use_memmap: bool,
) -> np.ndarray:
    """
    Read the bulk payload into a structured array.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the start of the payload.
    file_size : int
        Total file size in bytes.
    header : dict
        Parsed radiance header (must contain ``ipchan``, ``npred``, ``ireal``,
        ``nchanl``, ``iextra``, ``jextra``, and optionally ``idiag``).
    use_memmap : bool
        If True and a real file path is available, use ``numpy.memmap``.

    Returns
    -------
    numpy.ndarray
        Structured array with fields ``'db'``, ``'dbc'`` and ``'dbe'``.

    Notes
    -----
    ``idiag`` is at least ``ipchan + npred + 3``. When ``use_memmap`` is used,
    the file pointer is advanced to the end of the mapped region.
    """
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
        ('et',  np.void, 4),
    ])

    offset = f.tell()
    num = (file_size - offset) // dt.itemsize

    if use_memmap:
        filename = getattr(f, "name", None)
        if isinstance(filename, (str, os.PathLike)) and filename:
            mm = np.memmap(filename, dtype=dt, mode='r', offset=offset, shape=(num,))
            f.seek(offset + num * dt.itemsize)  # sync pointer
            arr = np.asarray(mm)                # detach from memmap
            return fix_endian(arr)

        # fallback: file-like with no name attribute
        buf = f.read(num * dt.itemsize)
        return fix_endian(np.frombuffer(buf, dtype=dt))

    # standard path (no memmap)
    buf = f.read(num * dt.itemsize)
    return fix_endian(np.frombuffer(buf, dtype=dt))


def extract_rad_dataframes(diag: np.ndarray, header: Dict[str, Any]):
    """
    Convert a structured radiance payload into pandas objects.

    Parameters
    ----------
    diag : numpy.ndarray
        Structured array returned by :func:`read_rad_payload`.
    header : dict
        Parsed header containing at least ``ipchan``, ``npred``, ``idiag`` and ``nchanl``.

    Returns
    -------
    tuple of (diagbuf_df, channels_df_list, extra_df)
        - ``diagbuf_df``: per-record header/geometry DataFrame (``diag['db']``).
        - ``channels_df_list``: list of per-channel DataFrames from ``diag['dbc']``.
        - ``extra_df``: DataFrame from ``diag['dbe']`` (may be empty if not present).

    Notes
    -----
    For compatibility, the function adds:
    - ``end_err = 1 / errinv`` when ``errinv != 0`` (NaN otherwise).
    - ``oma`` column filled with NaN if absent in input layout.
    """
    header_diagbuf = [
        'lat','lon','elev','time','iscanp','zasat','ilazi','pangs','isazi','sgagl',
        'sfcwc','sfclc','sfcic','sfcsc','sfcwt','sfclt','sfcit','sfcst','sfcstp',
        'sfcsmc','sfcltp','sfcvf','sfcsd','sfcws','clsORclw','cldpORtpwc'
    ]
    header_diagbufchan = ['tb_obs','omf','omf_nbc','errinv','idqc','emiss','tlach','ts']

    # per-record DB
    db  = fix_endian(diag['db'][:, :len(header_diagbuf)])
    df1 = pd.DataFrame(db, columns=header_diagbuf)

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

    # per-channel DBC
    df_list: List[pd.DataFrame] = []
    for i in range(int(header['nchanl'])):
        s, e = i * idiag, (i + 1) * idiag
        dbc = fix_endian(diag['dbc'][:, s:e])
        dfc = pd.DataFrame(dbc, columns=cols[:idiag])
        if 'errinv' in dfc.columns and 'end_err' not in dfc.columns:
            inv = dfc['errinv'].replace(0, np.nan)
            dfc['end_err'] = 1.0 / inv
        if 'oma' not in dfc.columns:
            dfc['oma'] = np.nan
        df_list.append(dfc)

    # extras
    dbe = fix_endian(diag['dbe'])
    df2 = pd.DataFrame(dbe)
    return df1, df_list, df2

