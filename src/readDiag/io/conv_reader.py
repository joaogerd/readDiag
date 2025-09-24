# --- readDiag/conv.py --------------------------------------------------------
from __future__ import annotations

"""
Conventional diagnostics reader.

Fast, block-wise reader for GSI *conventional* diagnostics with optional
base-20 skim, station-ID decoding, and legacy alias columns to keep
downstream workflows stable.

This module performs both binary reading and high-level materialization
into pandas objects (split/compact). Pure I/O helpers are kept small and
focused for testability.

Notes
-----
- **Record format**: GSI conventional diagnostics are stored in Fortran
  unformatted records with big-endian integers/reals. Each block starts
  with a small ASCII var-id and integer header, followed by an optional
  station-ID (S8) strip and a real-valued matrix shaped
  ``(nreal, nobs)`` in column-major order.
- **Base-20 skim**: Many workflows only need the first 20 real slots per
  observation; the "fast path" reads only those to reduce I/O and memory.
- **Split vs. compact**:
  - *Split* (default) returns a mapping ``{kx -> DataFrame}``.
  - *Compact* returns a single DataFrame per variable.
- **Raw NumPy mode**: For maximum speed, set ``raw_numpy=True`` to return
  the stacked NumPy buffers without any DataFrame materialization.

Examples
--------
Basic usage (split by ``kx``):

>>> from readDiag.conv import read_conv_file
>>> out = read_conv_file("diag_conv_01.2024013018")
>>> sorted(out.keys())[:3]               # variables present
['ps', 'q', 't']
>>> t_groups = out['t']                  # dict: kx -> DataFrame
>>> list(t_groups)[:3]                   # first kx present
[120, 130, 131]
>>> t120 = t_groups[120]
>>> t120.columns[:8].tolist()
['kx', 'ksub', 'lat', 'lon', 'elev', 'prs', 'hgt', 'time']

Compact mode (single DataFrame per variable):

>>> out = read_conv_file("diag_conv_01.2024013018", compact=True)
>>> out['q']['__ALL__'].head(2)

Raw NumPy buffers (fastest):

>>> out = read_conv_file("diag_conv_01.2024013018", raw_numpy=True)
>>> out['t']['data'].shape
(12345, 20)

With station IDs (SIDs):

>>> out = read_conv_file("diag_conv_01.2024013018", read_sids=True, compact=True)
>>> df = out['ps']['__ALL__']
>>> 'sid' in df.columns
True
"""

from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .utils import logger, log_time, fix_endian

# Canonical base-20 column layout used in the fast path
BASE20_COLS: List[str] = [
    'kx','ksub','lat','lon','elev','prs','hgt','time','iqc',
    'qc_setup','iuse','analysis_use','rwgt',
    'errinv_inp','errinv_adj','errinv_fin',
    'obs','omf','omf_wob','spread'
]


def _columns_for(var: str, nreal: int, fast: bool) -> List[str]:
    """
    Resolve output columns for a given variable and layout mode.

    Parameters
    ----------
    var : str
        Variable short id (e.g., ``'t'``, ``'q'``, ``'uv'``, ``'ps'``, ``'wst'``).
        The special case ``'uv'`` expands the tail to U/V-specific columns.
    nreal : int
        Number of real-valued slots in the record (from file header).
    fast : bool
        If ``True``, assume base-20 skim layout; otherwise, fall back to
        the canonical 20-name set (until a full map is provided).

    Returns
    -------
    list of str
        Column names up to ``min(nreal, len(layout))``.

    Notes
    -----
    - For ``'uv'`` we expose: ``obs_u, omf_u, omf_wob_u, obs_v, omf_v, omf_wob_v``.
    - For ``'wst'`` the last canonical field ``'spread'`` is exposed as ``'factw'``.
    """
    if fast:
        if var == 'uv':
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
    """
    Add legacy-compatible aliases when canonical columns are present.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame with canonical columns.

    Returns
    -------
    pandas.DataFrame
        The *same* DataFrame (mutated in-place) with alias columns added
        if they were missing.

    Aliases
    -------
    - ``dhgt -> hgt``
    - ``pbqc`` / ``emark`` -> ``iqc``
    - ``iusev -> analysis_use``
    - ``wpbqc -> rwgt``
    - ``inp_err -> errinv_inp``
    - ``adj_err -> errinv_adj``
    - ``end_err -> errinv_fin``

    Notes
    -----
    This keeps old downstream code working without forcing a rename step.
    """
    alias = {
        'dhgt': 'hgt', 'pbqc': 'iqc', 'emark': 'iqc',
        'iusev': 'analysis_use', 'wpbqc': 'rwgt',
        'inp_err': 'errinv_inp', 'adj_err': 'errinv_adj', 'end_err': 'errinv_fin',
    }
    for old, new in alias.items():
        if new in df.columns and old not in df.columns:
            df[old] = df[new]
    return df


def _apply_uv_magnitude(df: pd.DataFrame) -> pd.DataFrame:
    """
    For UV variables, compute vector magnitudes to provide legacy-compatible columns.

    Adds (when columns are present):
    - ``obs``     = sqrt(obs_u^2 + obs_v^2)
    - ``omf_wob`` = sqrt(omf_wob_u^2 + omf_wob_v^2)
    """
    import numpy as _np  # local import to avoid top-level changes

    if all(c in df.columns for c in ("obs_u", "obs_v")) and "obs" not in df.columns:
        df["obs"] = _np.sqrt(df["obs_u"] ** 2 + df["obs_v"] ** 2)

    if all(c in df.columns for c in ("omf_wob_u", "omf_wob_v")) and "omf_wob" not in df.columns:
        df["omf_wob"] = _np.sqrt(df["omf_wob_u"] ** 2 + df["omf_wob_v"] ** 2)

    return df


def _read_conv_header(f) -> Optional[Tuple[str, int, int, int, int, int, Dict[str, int]]]:
    """
    Read a single conventional block header.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the block header (Fortran record).

    Returns
    -------
    tuple or None
        ``(var_id, nchar, nreal, nobs, mype, ioff0, extras)`` or ``None`` at EOF.
        ``extras`` may include keys such as ``'idia0'`` or ``'iip'`` depending
        on the variable.

    Raises
    ------
    ValueError
        If the Fortran record markers mismatch or the header is too short.

    Notes
    -----
    The small ASCII ``var_id`` is 3 bytes (e.g., ``b'  t'`` for temperature)
    and is followed by 32-bit big-endian integers.
    """
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
    """
    Fast-path reader that returns only the first 20 reals per observation.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the start of the data record.
    nobs : int
        Number of observations in the block.
    nreal : int
        Number of real-valued fields per observation.
    read_sids : bool
        Whether to read and decode the 8-char station IDs (S8).
    rkind : str, default ``'>f4'``
        Real dtype (big-endian). GSI diagnostics commonly use 32-bit floats.

    Returns
    -------
    tuple
        ``(sids, head20)`` where ``sids`` is an array of decoded IDs (or ``None``),
        and ``head20`` is a ``(nobs, min(20, nreal))`` float array.

    Raises
    ------
    EOFError
        If the data record is truncated.
    ValueError
        If the Fortran record markers mismatch.

    See Also
    --------
    _read_block_full : Read the entire real matrix when more than 20 columns are needed.
    """
    rec_len = int.from_bytes(f.read(4), 'big', signed=True)
    sids = None
    if read_sids:
        # Station IDs are stored first, as S8 (8 bytes per obs)
        sid_bytes = f.read(8 * nobs)
        sid_arr = np.frombuffer(sid_bytes, dtype='S8').copy()
        sids = np.char.decode(sid_arr, 'latin-1', errors='ignore')
        sids = np.char.replace(sids, '\00', '')
        sids = np.char.rstrip(sids)
    else:
        # Skip the SID strip without materializing it
        f.seek(8 * nobs, 1)

    itemsize = 4 if rkind.endswith('f4') else 8
    real_nbytes = nobs * nreal * itemsize
    buf = f.read(real_nbytes)
    if len(buf) != real_nbytes:
        raise EOFError("unexpected EOF in data")
    tail = int.from_bytes(f.read(4), 'big', signed=True)
    if tail != rec_len:
        raise ValueError("Fortran record length mismatch in data")

    # Reals are column-major (Fortran). Fix endianness if needed.
    arr = np.frombuffer(buf, dtype=np.dtype(rkind))
    arr = fix_endian(arr)
    mats = arr.reshape((nreal, nobs), order='F')
    head = mats[: min(20, nreal), :].T
    return sids, head


def _read_block_full(f, nobs: int, nreal: int, read_sids: bool, rkind: str = '>f4'):
    """
    Read the full record (all reals), returning a ``(nobs, nreal)`` array.

    Parameters
    ----------
    f : IO[bytes]
        Open binary stream positioned at the start of the data record.
    nobs : int
        Number of observations in the block.
    nreal : int
        Number of real-valued fields per observation.
    read_sids : bool
        Whether to read and decode the 8-char station IDs (S8).
    rkind : str, default ``'>f4'``
        Real dtype (big-endian).

    Returns
    -------
    tuple
        ``(sids, matrix)`` where ``matrix`` is shaped ``(nobs, nreal)`` (float).

    Raises
    ------
    EOFError
        If the data record is truncated.
    ValueError
        If the Fortran record markers mismatch.

    Notes
    -----
    This path reads the entire column-major buffer into a contiguous
    ``(nobs, nreal)`` matrix, preserving the original column order.
    """
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
        sids = np.char.replace(sids, '\00', '')
        sids = np.char.rstrip(sids)

    real_mv = memoryview(buf)[8 * nobs :]
    rb = np.frombuffer(real_mv, dtype=np.dtype(rkind), count=nreal * nobs)
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
    set_date_cb: Callable[[datetime], None] = lambda _d: None,
):
    """
    Read a conventional diagnostics file into NumPy/Pandas structures.

    Parameters
    ----------
    file_name : str
        Path to the binary conventional diagnostic file (e.g., ``diag_conv_*``).
    var : str, optional
        If provided, only this variable is materialized in split/compact modes.
        Ignored by ``raw_numpy=True`` (all variables are returned).
    fast : bool, default True
        Use base-20 column skim naming for ``_columns_for`` resolution.
    base20_only : bool, default True
        When ``nreal > 20``, read only the first 20 slots (fast path). If set to
        ``False``, the full matrix is read for variables whose ``nreal > 20``.
    read_sids : bool, default False
        Decode and include 8-character station IDs into the output DataFrames
        (column ``'sid'``) or in the raw mapping.
    compat_legacy : bool, default True
        Add legacy aliases (column names) for downstream compatibility.
    raw_numpy : bool, default False
        If ``True``, return raw NumPy buffers per variable (fastest path).
    compact : bool, default False
        If ``True``, return one DataFrame per variable (no split by ``kx``).
        When ``False`` (default), returns a mapping ``{kx -> DataFrame}``.
    set_date_cb : Callable[[datetime], None], optional
        Optional callback to receive the file's analysis datetime, if available.

    Returns
    -------
    dict
        - If ``raw_numpy=True``:
          ``{var -> {'data': ndarray[float], 'sids': ndarray[str] | None}}``
          where ``data`` has shape ``(nobs_total, n_take)`` and
          ``n_take = min(nreal, 20)`` if ``base20_only`` else ``nreal``.
        - Otherwise (pandas mode):
          - ``compact=True`` → ``{var -> {'__ALL__': DataFrame}}``
          - default (split) → ``{var -> {kx -> DataFrame}}``

    Raises
    ------
    ValueError
        If Fortran record markers mismatch (header or data).
    EOFError
        If a data record is truncated on read.

    Notes
    -----
    - The function reads all blocks and vertically stacks them per variable.
    - For variables ``'t'`` and ``'q'``, optional PBL pseudo-obs are appended
      when ``extras['iip'] > 0`` in the file, preserving order.
    - The first column is assumed to be ``'kx'``; split-mode sorts by ``kx``
      (stable sort) and returns contiguous chunks per code.

    Examples
    --------
    Read and split by ``kx``:

    >>> out = read_conv_file("diag_conv_01.2024013018")
    >>> sorted(out.keys())
    ['ps', 'q', 't', 'uv', 'wst']
    >>> df_t_120 = out['t'][120]
    >>> df_t_120[['kx', 'lat', 'lon', 'obs', 'omf']].head(3)

    Compact per variable:

    >>> out = read_conv_file("diag_conv_01.2024013018", compact=True, read_sids=True)
    >>> df_q = out['q']['__ALL__']
    >>> df_q.columns[:5].tolist()
    ['sid', 'kx', 'ksub', 'lat', 'lon']

    Raw NumPy:

    >>> out = read_conv_file("diag_conv_01.2024013018", raw_numpy=True)
    >>> out['ps']['data'].ndim
    2

    Filtering a single variable (materialization):

    >>> out = read_conv_file("diag_conv_01.2024013018", var='t', compact=True)
    >>> list(out.keys())
    ['t']
    """
    stash: Dict[str, List[np.ndarray]] = {}
    stash_sid: Dict[str, List[np.ndarray]] = {}

    with open(file_name, 'rb', buffering=1 << 20) as f:
        # Tolerant global header (idate). Not all files will have it.
        try:
            hdr_vals = np.fromfile(f, '>i4', 3)
            if hdr_vals.size >= 2:
                set_date_cb(datetime.strptime(str(int(hdr_vals[1])), '%Y%m%d%H'))
        except Exception:
            pass

        # Iterate over Fortran records, each describing a (var, block)
        while True:
            hv = _read_conv_header(f)
            if hv is None:
                break
            var_id, nchar, nreal, nobs, mype, ioff0, extras = hv
            if nobs <= 0:
                continue

            # Choose fast skim (<=20) or full matrix
            reader = _read_block_base20 if (base20_only and nreal > 20) else _read_block_full
            sids, rb = reader(f, nobs, nreal, read_sids, rkind='>f4')
            vid = var_id.strip()
            stash.setdefault(vid, []).append(rb)
            if read_sids and sids is not None:
                stash_sid.setdefault(vid, []).append(np.asarray(sids))

            # Optional PBL pseudo-obs (t/q) controlled by 'iip'
            iip = extras.get('iip', 0)
            if vid in ('t', 'q') and iip > 0:
                sids_p, rb_p = reader(f, iip, nreal, read_sids, rkind='>f4')
                stash[vid].append(rb_p)
                if read_sids and sids_p is not None:
                    stash_sid.setdefault(vid, []).append(np.asarray(sids_p))

    # Raw mode (ultra-fast): return stacked NumPy arrays per variable
    if raw_numpy:
        out_raw: Dict[str, Dict[str, np.ndarray]] = {}
        for vid, parts in stash.items():
            arr = parts[0] if len(parts) == 1 else np.vstack(parts)
            sids = None
            if read_sids and vid in stash_sid:
                sids = np.concatenate(stash_sid[vid], axis=0)
            out_raw[vid] = {'data': arr, 'sids': sids}
        return out_raw

    # Materialize pandas DataFrames
    out: Dict[str, Dict[str, pd.DataFrame]] = {}
    for vid, parts in stash.items():
        arr = parts[0] if len(parts) == 1 else np.vstack(parts)
        sids = None
        if read_sids and vid in stash_sid:
            sids = np.concatenate(stash_sid[vid], axis=0)

        cols = _columns_for(vid, arr.shape[1], fast)
        n_take = min(arr.shape[1], len(cols))
        a = arr[:, :n_take]

        # Compact: one DataFrame per variable
        if compact:
            df = pd.DataFrame(a, columns=cols[:n_take])
            if read_sids and sids is not None:
                df.insert(0, 'sid', sids)
            if vid == 'uv':
                df = _apply_uv_magnitude(df)
            df = _apply_legacy_aliases(df) if compat_legacy else df
            out[vid] = {'__ALL__': df.reset_index(drop=True)}
            continue

        # Split by kx efficiently:
        # 1) compute integer kx; 2) stable sort; 3) split along boundaries
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
            if vid == 'uv':
                df = _apply_uv_magnitude(df)
            df = _apply_legacy_aliases(df) if compat_legacy else df
            out[vid][k] = df.reset_index(drop=True)

    return out

