#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gsidiag legacy adapter & helpers

A light‑compatibility layer that mimics the *legacy* ``gsidiag`` public surface
while delegating file reading to the **new** :func:`readDiag.reader.diagAccess`
engine. It keeps old field names and shapes as much as practical (e.g.,
``obsInfo`` keyed by variable/sensor, MultiIndex for conventional *kx* or
radiance *SatId/points*), adds a few robust aliases (``obs``, ``omf_nobc``,
``inverr``), and injects ``oma`` from an optional *analysis* diagnostic file.

Design
------
- **No on-disk cache**: only in‑memory DataFrames/GeoDataFrames.
- **Handle manager**: provides a tiny registry to emulate the old ``_FNumber``
  behavior ("how many files are open?").
- **Backward‑compat shims**: ``obsInfo.df`` and ``gdf.df`` are kept for older
  scripts; alias ``channel``→``nchan`` is provided if needed.
- **Graceful fallbacks**: if Cartopy/geometry is unavailable, Pandas frames
  still work; missing columns are tolerated when building aliases.

Notes
-----
- This adapter **does not** expose the modern typed API (:class:`DiagnosticAPI`).
  Prefer using the new surface for new code.
- Error semantics try to be forgiving (``print`` warnings, skip injections) so
  legacy notebooks keep running.

Examples
--------
Load a *radiance* BG file and inject OMA from the matching *analysis* file:

>>> bg = read_diag("diag_amsua_n19_01.2024021000")
>>> anl = read_diag("diag_amsua_n19_01.2024021000.anl", diagFileAnl=None)
>>> with read_diag("diag_amsua_n19_01.2024021000",
...                diagFileAnl="diag_amsua_n19_01.2024021000.anl") as gdf:
...     df = gdf.obs  # long table with aliases 'obs', 'omf_nobc', 'inverr'
...     ch1 = df.query("channel == 1")

List variables and *kx* (conventional) or sensors (radiance):

>>> gdf = read_diag("diag_conv_01.2024021000")
>>> gdf.overview()  # doctest: +SKIP
{'t': [120, 130], 'q': [120]}

Get the number of open handles (legacy compatibility):

>>> get_open_read_diag_count()  # doctest: +ELLIPSIS
0

"""
from __future__ import annotations

# --- Standard library ---
from pathlib import Path
from datetime import datetime, timedelta
import itertools
import gc
import weakref
from typing import Any, Dict, List, Optional  # só o que é usado

# --- Third-party (hard deps para este módulo) ---
import numpy as np
import pandas as pd

# GeoDataFrame para lat/lon → geometry (se quiser tornar opcional, ver nota abaixo)
try:
    import geopandas as gpd
except Exception:  # ImportError, RuntimeError…
    gpd = None

# --- Project (local) ---
from readDiag.reader import diagAccess
from readDiag.schema.naming import resolve_col_in_df
from ..datasources import getVarInfo

# --- Logging ---
import logging
logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

__all__ = [
    "read_diag",
    "get_open_read_diag_count",
]

# ============================================================================
# Handle Manager (compatibility with legacy `_FNumber`)
# ============================================================================
_RD_HANDLE_COUNTER = itertools.count(1)
_RD_OPEN_HANDLES: dict[int, weakref.ReferenceType] = {}  # fid -> weakref(instance)
_RD_BY_PATH: dict[tuple[str, str], weakref.ReferenceType] = {}  # (bg, anl) -> weakref(instance)


def _register_handle(instance) -> int:
    """Register an opened instance and return a synthetic *file id* (fid).

    Parameters
    ----------
    instance : object
        The newly created :class:`read_diag` instance.

    Returns
    -------
    int
        A monotonically increasing synthetic identifier used to emulate the
        legacy ``_FNumber`` behavior.
    """
    fid = next(_RD_HANDLE_COUNTER)
    _RD_OPEN_HANDLES[fid] = weakref.ref(instance)
    return fid


def _unregister_handle(fid: int) -> None:
    """Remove a *fid* from the open‑handles registry if present.

    This is automatically called by :meth:`read_diag.close`.

    Parameters
    ----------
    fid : int
        The synthetic file identifier returned by :func:`_register_handle`.
    """
    _RD_OPEN_HANDLES.pop(fid, None)


def get_open_read_diag_count() -> int:
    """Return the number of currently alive ``read_diag`` objects.

    Dead weakrefs are cleaned up on the fly.

    Returns
    -------
    int
        Number of alive instances tracked by the registry.

    Examples
    --------
    >>> n0 = get_open_read_diag_count()
    >>> with read_diag("diag_conv_01.2024021000") as gdf:  # doctest: +SKIP
    ...     pass
    >>> _ = isinstance(n0, int)
    """
    stale = [k for k, w in _RD_OPEN_HANDLES.items() if w() is None]
    for k in stale:
        _RD_OPEN_HANDLES.pop(k, None)
    return len(_RD_OPEN_HANDLES)


# ============================================================================
# Helpers to inject OMA from an *analysis* file
# ============================================================================

def _inject_oma_from_anl(
    bg_df: pd.DataFrame,
    anl_df: pd.DataFrame,
    *,
    # Radiance mode (stacked table indexed by SatId/points):
    sat_id: Optional[str] = None,
    channel_value: Optional[int] = None,
    channel_col: str = "nchan",
    # Conventional mode (stacked by kx/points):
    lvl0: Optional[int] = None,
) -> None:
    """
    Copy ``omf`` from an analysis diagnostic into ``oma`` in the background table.

    Supports two legacy-compatible modes, copying values **positionally** and
    tolerating minor shape differences:

    Conventional mode
        Set ``lvl0`` to a *kx* integer. The function targets rows in ``bg_df``
        whose level-0 index matches ``lvl0`` and copies the first
        ``min(len(bg_slice), len(anl_df))`` values from ``anl_df['omf']`` into
        ``bg_df['oma']``.

    Radiance mode
        Set both ``sat_id`` and ``channel_value`` (``nchan``). The function
        locates rows for ``sat_id`` (level-0 index) filtered by the given
        channel and copies the first ``min(#dest, len(anl_df))`` values.

    Parameters
    ----------
    bg_df : pandas.DataFrame
        Background, stacked long table (conventional or radiance). If ``'oma'``
        is missing, the column is created and filled with ``NaN`` before
        injection.
    anl_df : pandas.DataFrame
        Analysis table providing the ``'omf'`` values.
    sat_id : str, optional
        Radiance mode level-0 key (e.g., ``'n19'``).
    channel_value : int, optional
        Channel number for radiance mode (``1..N``).
    channel_col : str, default "nchan"
        Column name carrying the channel number.
    lvl0 : int, optional
        Conventional mode level-0 key (``kx``).

    Notes
    -----
    The copy is strictly **positional** to preserve legacy assumptions. Missing
    inputs, columns, or index keys are tolerated silently. If neither ``lvl0``
    nor ``(sat_id, channel_value)`` is provided, the function returns without
    modifying ``bg_df``.

    Returns
    -------
    None
    """
    if bg_df is None or anl_df is None or bg_df.empty or anl_df.empty:
        return
    if "omf" not in anl_df.columns:
        return

    if "oma" not in bg_df.columns:
        bg_df["oma"] = np.nan

    # Conventional mode -----------------------------------------------------
    if lvl0 is not None:
        try:
            bg_slice = bg_df.loc[(lvl0, slice(None)), :]
        except Exception:
            return
        # Absolute start offset of this block in the base df
        loc = bg_df.index.get_loc(lvl0)
        start_pos = loc.start if isinstance(loc, slice) else (np.min(loc) if len(loc) else 0)
        n = min(len(bg_slice), len(anl_df))
        if n:
            bg_df.iloc[start_pos : start_pos + n, bg_df.columns.get_loc("oma")] = (
                anl_df["omf"].values[:n]
            )
        return

    # Radiance mode ---------------------------------------------------------
    if sat_id is None or channel_value is None:
        return

    # Slice by SatId (level‑0) and filter by channel column
    try:
        bg_slice = bg_df.loc[(sat_id, slice(None)), :]
    except KeyError:
        return

    if channel_col not in bg_slice.columns:
        return

    mask_ch = (bg_slice[channel_col] == channel_value).to_numpy()
    if not mask_ch.any():
        return

    loc = bg_df.index.get_loc(sat_id)
    start_pos = loc.start if isinstance(loc, slice) else (np.min(loc) if len(loc) else 0)
    dest = start_pos + np.flatnonzero(mask_ch)
    n = min(len(dest), len(anl_df))
    if n:
        bg_df.iloc[dest[:n], bg_df.columns.get_loc("oma")] = anl_df["omf"].values[:n]


# Backward‑compatible alias kept for clarity in radiance context
_inject_oma_from_anl_rad = _inject_oma_from_anl


# ============================================================================
# Public class: read_diag (legacy‑shaped facade)
# ============================================================================
class read_diag(object):


    def __init__(self, diagFile, diagFileAnl=None, isisList=None, zlevs=None, zchan=None):
        """
        Initialize a legacy-shaped view of a GSI diagnostic file.
    
        Opens a background (*BG*) diagnostic and, optionally, a matching analysis
        (*ANL*) diagnostic. Exposes legacy-friendly tables under ``obsInfo`` and a
        concatenated long table in ``obs``, keeping common aliases (``obs``,
        ``omf_nobc``, ``inverr``). When an analysis file is provided, attempts to
        inject ``oma`` into the background table **positionally** (same kx/channel).
    
        Parameters
        ----------
        diagFile : str or path-like
            Path to the background (or single) GSI diagnostic file.
        diagFileAnl : str or path-like, optional
            Path to the matching analysis diagnostic. If provided, ``omf(ANL)`` is
            copied into ``oma(BG)`` for corresponding variable/kx (conventional) or
            channel (radiance). Default is ``None``.
        isisList : Any, optional
            Kept for compatibility with older call signatures. Currently unused.
        zlevs : sequence of float, optional
            Pressure levels (hPa) required by some legacy routines. If ``None``,
            a default set is used.
        zchan : Any, optional
            Kept for compatibility with older call signatures. Currently unused.
    
        Attributes
        ----------
        obsInfo : Mapping[str, pandas.DataFrame]
            Mapping from variable/sensor to a stacked table indexed by level-0 key
            (``kx`` or ``SatId``) and point number. Provides a ``.df`` attribute
            for very old code.
        obs : pandas.DataFrame
            Concatenated long table across variables/sensors with common aliases
            when resolvable (``obs``, ``omf_nobc``, ``inverr``).
        df : pandas.DataFrame
            Alias to :attr:`obs` for legacy parity.
        varNames : list of str
            Variables (conventional) or sensor names (radiance).
        _FNumber : int or None
            Synthetic handle id used to emulate the legacy "open file" counter.
    
        Notes
        -----
        * The constructor may **reuse** a previously opened instance for the same
          ``(diagFile, diagFileAnl)`` pair within the process, shallow-copying its
          internal state to avoid duplicate I/O.
        * Undefined/fill values from older readers are normalized to ``NaN``.
        * If ``lat/lon`` are present and GeoPandas is available, a ``GeoDataFrame``
          is created with longitudes wrapped to ``[-180, 180)``.
    
        Raises
        ------
        FileNotFoundError
            If a provided path does not exist.
        KeyError
            If required channel metadata is missing in radiance mode.
        Exception
            Any error propagated by the low-level reader.
    
        Examples
        --------
        Conventional
            >>> # doctest: +SKIP
            >>> gdf = read_diag("diag_conv_01.2024021000")
            >>> list(gdf.varNames)
            ['t', 'q', 'uv']
    
        Radiance with OMA injection
            >>> # doctest: +SKIP
            >>> gdf = read_diag("diag_amsua_n19_01.2024021000",
            ...                 "diag_amsua_n19_01.2024021000.anl")
            >>> 'oma' in gdf.obs.columns
            True
        """
        self._diagFile = diagFile
        self._diagFileAnl = diagFileAnl

        # Avoid reopening the same pair (bg, anl) within this process
        pkey = (str(diagFile), str(diagFileAnl) if diagFileAnl is not None else "")
        w = _RD_BY_PATH.get(pkey)
        inst = w() if w is not None else None
        if inst is not None and getattr(inst, "_FNumber", None) is not None:
            # Light clone: share internal state to preserve legacy behavior
            self.__dict__.update(inst.__dict__)
            return

        extraInfo = diagFileAnl is not None  # store richer set of columns if ANL is given

        # Canonical legacy column sets
        convIndex_full = [
            "lat", "lon", "elev", "prs", "hgt", "press", "time", "idqc", "iuse", "iusev",
            "wpbqc", "inp_err", "adj_err", "inverr", "oer", "obs", "omf", "oma", "imp", "dfs",
        ]
        convIndex_min = convIndex_full[:17]

        radIndex_full = [
            "lat", "lon", "elev", "nchan", "time", "iuse", "idqc", "inverr", "oer", "obs",
            "omf", "omf_nobc", "emiss", "oma", "oma_nobc", "imp", "dfs",
        ]
        radIndex_min = radIndex_full[:13]

        # Read with the new engine (compat mode: legacy‑friendly columns)
        rd = diagAccess(diagFile, compat_legacy=True, base20_only=True, read_sids=False)
        rd_anl = None
        if diagFileAnl is not None:
            try:
                rd_anl = diagAccess(diagFileAnl, compat_legacy=True, base20_only=True, read_sids=False)
            except Exception as e:  # pragma: no cover - warn only
                logger.warning("Failed to read analysis file '%s': %s", diagFileAnl, e)

                rd_anl = None

        # File type and undef normalization
        self._FileType = rd.get_data_type()  # 1=conv, 2=rad
        self._undef = np.nan
        self._idate = rd._idate

        logger.info(
            "Opened diagnostic: type=%s idate=%s file=%s",
            "conventional" if self._FileType == 1 else "radiance",
            getattr(self, "_idate", None),
            self._diagFile,
        )

        # Default z‑levels (legacy callers may use self.zlevs)
        self.zlevs = (
            [1000.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0, 250.0, 200.0, 150.0, 100.0, 50.0, 0.0]
            if zlevs is None else zlevs
        )

        self.varNames: List[str] = []
        self.obsInfo: Dict[str, pd.DataFrame] = {}

        if self._FileType == 1:
            # --------------------------- CONVENTIONAL ------------------------
            vars_ = rd.get_variables()
            self.varNames.extend(vars_)

            for obsName in vars_:
                kx_list = rd.get_kx_list(obsName)
                frames, keys = [], []
                for kx in kx_list:
                    d = rd.get_dataframe(obsName, kx).copy()

                    cols = [c for c in (convIndex_full if extraInfo else convIndex_min) if c in d.columns]
                    if cols:
                        d = d[cols + [c for c in d.columns if c not in cols]]

                    d.replace(to_replace=[-9.99e8, -9.0e33], value=np.nan, inplace=True)

                    if gpd is not None and {"lon", "lat"}.issubset(d.columns):
                        lon = (d["lon"] + 180) % 360 - 180
                        lat = d["lat"]
                        d = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon, lat))

                    frames.append(d)
                    keys.append(kx)

                out = pd.concat(frames, keys=keys, names=["kx", "points"]) if frames else pd.DataFrame()

                logger.debug(
                    "Built conventional var=%s with kx=%s (rows=%d)",
                    obsName, keys, sum(len(f) for f in frames)
                )

                # Inject OMA from ANL (copy posicional): kx by kx
                if rd_anl is not None and not out.empty:
                    logger.info("Injecting OMA from ANL for var=%s over %d kx blocks", obsName, len(keys))
                    try:  # pragma: no cover - tolerant path
                        for kx in keys:
                            d_anl = rd_anl.get_dataframe(obsName, kx).copy()
                            if d_anl is None or d_anl.empty:
                                continue
                            _inject_oma_from_anl(out, d_anl, lvl0=kx)
                    except Exception as e:
                        logger.warning("OMA injection failed (radiance): %s", e)

                self.obsInfo[obsName] = out

                logger.debug("Built conventional var=%s with kx=%s (rows=%d)",
                             obsName, keys, sum(len(f) for f in frames) )
            # ------------- Concatenated table (previous behavior) -----------------
            self.obs = (
                pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)
                if self.obsInfo else pd.DataFrame()
            )

            logger.debug("Concatenated table shape: %s", tuple(self.obs.shape))

        else:
            # ---------------------------- RADIANCE ---------------------------
            bundle = rd.get_dataframe()
            sensor = bundle.get("sensor", "radiance")
            self.varNames.append(sensor)
            
            d_geom = bundle["dataframes"]["diagbuf_df"].reset_index(drop=True)
            dlist = bundle["dataframes"]["diagbufchan_df"]  # one DF per channel
            chan   = bundle["dataframes"]["channel_df"]
            
            # SatId (e.g., 'n19') inferred from file name by convention
            bn = Path(self._diagFile).name
            parts = bn.split("_")
            varType_from_name = parts[2] if len(parts) >= 3 else "unknown"
            
            # -----------------------------------------------------------------
            # Build a lookup (mapping) from channel number (nuchan) -> iuse
            # -----------------------------------------------------------------
            required = {"nuchan", "iuse"}
            missing = required - set(chan.columns)
            if missing:
                raise KeyError(f"Missing required columns in 'chan': {sorted(missing)}")
            
            # Drop duplicates if present (keep last), then index by 'nuchan' for O(1) access
            iuse_map = (
                chan.drop_duplicates(subset=["nuchan"], keep="last")
                    .set_index("nuchan")["iuse"]
            )
            
            # Validate expected coverage: channel IDs from 1..len(dlist)
            expected = set(range(1, len(dlist) + 1))
            not_covered = expected - set(iuse_map.index)
            if not_covered:
                # Be tolerant: warn and fill missing with NaN during assignment
                logger.warning("'chan' has no iuse values for channels: %s", sorted(not_covered))

            
            # Precompute whether we can make a GeoDataFrame
            _has_gpd = "gpd" in globals() and getattr(gpd, "GeoDataFrame", None) is not None
            
            long_list: list[pd.DataFrame] = []
            for ich, dfc in enumerate(dlist, start=1):
                # Work on a deep copy to avoid chained assignment surprises
                d = dfc.reset_index(drop=True).copy()
                d["nchan"] = ich
            
                # Fast lookup; missing -> NaN (no crash)
                d["iuse"] = iuse_map.get(ich, np.nan)
            
                # Restrict/ordering of columns while preserving all others at the end
                cols_allowed = (radIndex_full if extraInfo else radIndex_min)
                # keep columns that actually exist, in desired order first
                keep_first = [c for c in cols_allowed if c in d.columns]
                keep_rest  = [c for c in d.columns if c not in keep_first]
                d = d.loc[:, keep_first + keep_rest].copy()
            
                # Align/overlay common geotemporal fields from d_geom by row index
                common = [c for c in ("lat", "lon", "time") if c in d_geom.columns]
                if common:
                    n = min(len(d), len(d_geom))
                    if n > 0:
                        # assign using numpy to avoid alignment overhead
                        d.loc[: n - 1, common] = d_geom.loc[: n - 1, common].to_numpy()
            
                # Build geometry if both lat/lon are available and geopandas is present
                if gpd is not None and {"lat", "lon"}.issubset(d.columns) and _has_gpd:
                    lon = ((d["lon"] + 180) % 360) - 180  # wrap to [-180, 180)
                    lat = d["lat"]
                    d = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon, lat))

                logger.debug("Radiance sensor=%s satId=%s channel=%d rows=%d",
                             sensor, varType_from_name, ich, len(d))

                long_list.append(d)
            
            # Concatenate long table across channels
            rad_long = pd.concat(long_list, ignore_index=True) if long_list else pd.DataFrame()
            
            # Provide 'channel' alias from 'nchan' if missing
            if not rad_long.empty and "channel" not in rad_long.columns and "nchan" in rad_long.columns:
                rad_long["channel"] = rad_long["nchan"]
            
            # Store under sensor -> SatId
            self.obsInfo[sensor] = (
                pd.concat({varType_from_name: rad_long}, names=["SatId"])
                  .rename_axis(["SatId", "points"])
                  .copy()
            )
            
            # -----------------------------------------------------------------
            # Inject OMA from ANL (channel by channel within this SatId)
            # -----------------------------------------------------------------
            if rd_anl is not None:
                try:  # tolerant path
                    bundle_anl = rd_anl.get_dataframe()
                    dlist_anl  = bundle_anl["dataframes"]["diagbufchan_df"]
            
                    for ich, dfc_anl in enumerate(dlist_anl, start=1):
                        d_anl = dfc_anl.reset_index(drop=True).copy()
                        if d_anl is None or d_anl.empty or "omf" not in d_anl.columns:
                            continue
            
                        _inject_oma_from_anl_rad(
                            self.obsInfo[sensor],
                            d_anl,
                            sat_id=varType_from_name,
                            channel_value=ich,
                            channel_col="nchan",
                        )
                except Exception as e:
                    # don't reference 'ich' here: it may be undefined if the failure happened before the loop
                    logger.warning("OMA injection failed (radiance): %s", e)

            # --- Legacy aliases via schema.naming ---------------------------------
            _rad_df = self.obsInfo[sensor]
            
            try:
                src_obs = resolve_col_in_df(_rad_df.columns, "obs_value", "rad")
                if "obs" not in _rad_df.columns and src_obs in _rad_df.columns:
                    _rad_df["obs"] = _rad_df[src_obs]
            except Exception:
                pass
            
            try:
                src_omn = resolve_col_in_df(_rad_df.columns, "omf_nobc", "rad")
                if "omf_nobc" not in _rad_df.columns and src_omn in _rad_df.columns:
                    _rad_df["omf_nobc"] = _rad_df[src_omn]
            except Exception:
                pass
            
            try:
                src_inv = resolve_col_in_df(_rad_df.columns, "errinv", "rad")
                if "inverr" not in _rad_df.columns and src_inv in _rad_df.columns:
                    _rad_df["inverr"] = _rad_df[src_inv]
            except Exception:
                pass
            
            self.obsInfo[sensor] = _rad_df  # clarity
            
            # ------------- Concatenated table (previous behavior) -----------------
            self.obs = (
                pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)
                if self.obsInfo else pd.DataFrame()
            )

            logger.debug("Concatenated table shape: %s", tuple(self.obs.shape))

            # Add aliases at the concatenated level as well
            if not self.obs.empty:
                try:
                    src_obs = resolve_col_in_df(self.obs.columns, "obs_value", "rad")
                    if "obs" not in self.obs.columns and src_obs in self.obs.columns:
                        self.obs["obs"] = self.obs[src_obs]
                except Exception:
                    pass
                try:
                    src_omn = resolve_col_in_df(self.obs.columns, "omf_nobc", "rad")
                    if "omf_nobc" not in self.obs.columns and src_omn in self.obs.columns:
                        self.obs["omf_nobc"] = self.obs[src_omn]
                except Exception:
                    pass
                try:
                    src_inv = resolve_col_in_df(self.obs.columns, "errinv", "rad")
                    if "inverr" not in self.obs.columns and src_inv in self.obs.columns:
                        self.obs["inverr"] = self.obs[src_inv]
                except Exception:
                    pass
            
            # ------------- Backward-compat: provide obsInfo.df and gdf.df ----------
            class _ObsInfoCompat(dict):
                """Mapping with an attached `.df` exposing the concatenated table.
            
                Keeps very old scripts working:
                  - `obsInfo[name]` access by key, and
                  - `obsInfo.df` shortcut (DataFrame-like methods forwarded via __getattr__)
                """
            
                def __init__(self, by_name: dict[str, pd.DataFrame], df_concat: pd.DataFrame):
                    super().__init__(by_name)
                    self.df = df_concat
            
                @property
                def columns(self):
                    return self.df.columns
            
                def __getattr__(self, name):  # e.g., .head(), .query(), ...
                    return getattr(self.df, name)
            
            self.obsInfo = _ObsInfoCompat(self.obsInfo, getattr(self, "obs", pd.DataFrame()))
            self.df      = getattr(self, "obs", pd.DataFrame())
            
            # --- Register as an "opened file" (legacy compat) ----------------------
            self._FileName = str(self._diagFile)
            self._FNumber  = _register_handle(self)     # assumes your legacy handle registry
            _RD_BY_PATH[pkey] = weakref.ref(self)       # assumes pkey/_RD_BY_PATH are defined earlier

    # ---------------------------------------------------------------------
    # Lifecycle helpers (close/context manager)
    # ---------------------------------------------------------------------
    def close(self) -> int:
        """
        Release resources and unregister this handle.
    
        Drops large internal tables (``obsInfo``, ``obs``, ``df``), unregisters the
        synthetic file id, and triggers a garbage collection pass.
    
        Returns
        -------
        int
            Always ``0`` (legacy status value).
    
        Examples
        --------
        >>> # doctest: +SKIP
        >>> gdf = read_diag("diag_conv_01.2024021000")
        >>> gdf.close()
        0
        """
        fid = getattr(self, "_FNumber", None)
        if fid is None:
            return 0

        _unregister_handle(fid)

        for attr in ("obsInfo", "obs", "df"):
            try:
                setattr(self, attr, None)
            except Exception:
                pass

        self._nVars = None
        self.varNames = None
        self.nObs = None

        self._FNumber = None
        gc.collect()
        return 0

    def __enter__(self):
        """
        Enter the context manager and return ``self``.
    
        Returns
        -------
        read_diag
            This instance, ready for use inside a ``with`` block.
    
        Examples
        --------
        >>> # doctest: +SKIP
        >>> with read_diag("diag_conv_01.2024021000") as gdf:
        ...     df = gdf.obs
        """
        return self

    def __exit__(self, exc_type, exc, tb):
        """
        Ensure resources are released when leaving a context.
    
        Calls :meth:`close` unconditionally and returns ``False`` so that any
        exception raised inside the context is propagated to the caller.
    
        Parameters
        ----------
        exc_type : type or None
            Exception type, if any.
        exc : BaseException or None
            Exception instance, if any.
        tb : traceback or None
            Traceback object, if any.
    
        Returns
        -------
        bool
            Always ``False`` to propagate exceptions.
        """
        try:
            self.close()
        finally:
            return False

    def __del__(self):  # pragma: no cover - destructor best effort
        """
        Best-effort destructor that releases large tables and unregisters the handle.
    
        Notes
        -----
        Destructors are not guaranteed to run immediately or at interpreter
        shutdown time. Prefer explicit ``close()`` calls or context managers
        (``with read_diag(...) as gdf: ...``) in production code.
        """
        try:
            self.close()
        except Exception:
            pass
    # ---------------------------------------------------------------------
    # Introspection (legacy)
    # ---------------------------------------------------------------------
    def overview(self) -> Dict[str, List[Any]]:
        """
        Summarize variables and their available level-0 keys.
    
        Returns
        -------
        dict of {str: list}
            Mapping ``{var_name: [keys...]}`` where:
            * For conventional diagnostics, keys are *kx* values (``int``).
            * For radiance diagnostics, keys are first-level indices such as
              satellite/platform identifiers (e.g., ``'n19'``).
    
        Examples
        --------
        >>> # doctest: +SKIP
        >>> gdf = read_diag("diag_conv_01.2024021000")
        >>> gdf.overview()
        {'t': [120, 130], 'q': [120]}
        """
        variablesList: Dict[str, List[Any]] = {}
        for var in self.varNames or []:
            types_: List[Any] = []
            try:
                types_.extend(list(self.obsInfo[var].index.levels[0]))
            except Exception:
                pass
            variablesList.update({var: types_})
        return variablesList

    def pfileinfo(self) -> None:
        """
        Print a simple list of variables and available level-0 keys.
    
        For conventional files, the level-0 key is the *kx* integer.
        For radiance files, it is typically the ``SatId`` (e.g., ``'n19'``).
    
        Notes
        -----
        This is a convenience **printing** routine for ad-hoc inspection.
        For programmatic access, prefer :meth:`overview`.
    
        Returns
        -------
        None
        """
        for name in self.varNames or []:
            print("Variable Name :", name)
            print("              └── kx => ", end="", flush=True)
            try:
                for kx in self.obsInfo[name].index.levels[0]:
                    print(kx, " ", end="", flush=True)
            except Exception:
                pass
            print("\n")

    # ---------------------------------------------------------------------
    # CSV export (legacy shape)
    # ---------------------------------------------------------------------
    @staticmethod
    def tocsv(
        self,
        varName=None,
        varType=None,
        dateIni=None,
        dateFin=None,
        nHour="06",
        Level=None,
        Lay=None,
        SingleL=None,
        *,
        outdir: str | Path = ".",
        na_value: float = -99.0,
        verbose: bool = True,
    ):
        """
        Export legacy time-series aggregates to CSV.
    
        Preserves the legacy calling convention where the first positional argument
        (historically named ``self``) is a **sequence** of per-cycle ``read_diag``
        objects. Computes OmF/OmA statistics by pressure level (or a single level/
        layer) for each date in the requested range.
    
        Parameters
        ----------
        self : sequence of read_diag
            Sequence of per-cycle objects (e.g., BG files sampled every ``nHour``).
        varName : str, optional
            Conventional variable or sensor key inside ``.obsInfo``.
        varType : str or int, optional
            For conventional, the *kx*; for radiance, the ``SatId`` (e.g., ``'n19'``).
        dateIni, dateFin : str or int
            Bounds as ``YYYYMMDDHH``. The number of generated timestamps should
            match the number of items in ``self`` when stepping by ``nHour``.
        nHour : str or int, default "06"
            Step (hours) between successive objects in ``self``.
        Level : int or str, optional
            If ``None`` or ``"Zlevs"``, aggregate by all available levels.
            Otherwise, use the provided level (hPa).
        Lay : int, optional
            Half-width (hPa) for layer selection around ``Level`` when
            ``SingleL == "OneL"``.
        SingleL : {None, "All", "OneL"}, optional
            Layer aggregation mode. ``None``/``"Zlevs"`` means per-level; ``"All"``
            aggregates everything into a single bucket; ``"OneL"`` selects a band
            around ``Level`` with half-width ``Lay``.
        outdir : str or path-like, optional
            Output directory for CSV files. Default is current directory.
        na_value : float, default -99.0
            Fill value for missing aggregates.
        verbose : bool, default True
            If ``True``, log at INFO level; otherwise, log at DEBUG.
    
        Returns
        -------
        tuple of (str, str)
            Filenames of the two CSV files written (``OmF`` and ``OmA``).
    
        Notes
        -----
        Keeps the legacy layout: for each level, exports triplets ``mean``, ``std``,
        and ``count``. Uses vectorized grouping and minimizes Python-level loops.
        """
        import numpy as np
        import pandas as pd
        from datetime import datetime, timedelta
        from pathlib import Path
        import logging
    
        # Use module-level logger if available, otherwise create one
        log = logging.getLogger(__name__)
    
        def _log_info(msg: str) -> None:
            # preserve "verbosity switch": INFO when verbose, DEBUG otherwise
            if verbose:
                log.info(msg)
            else:
                log.debug(msg)
    
        # ---------- setup ----------
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
    
        omflag, omflaga = "OmF", "OmA"
        Laydef = 50
        delta_h = int(nHour)
    
        logger.info(
            "Exporting CSV var=%s type=%s range=%s..%s step=%sh",
            varName, varType, dateIni, dateFin, nHour
        )
        
        varInfo = None
        try:
            # getVarInfo may not exist in all environments
            from .datasources import getVarInfo  # type: ignore
            varInfo = getVarInfo(varType, varName, "instrument")
        except Exception:
            pass
    
        _log_info(
            f"Analyzing var={varName} type={varType} "
            f"instrument={varInfo if varInfo is not None else 'Unknown'} "
            f"metric={omflag}"
        )
    
        # ---------- range & consistency ----------
        datei = datetime.strptime(str(dateIni), "%Y%m%d%H")
        datef = datetime.strptime(str(dateFin), "%Y%m%d%H")
        if datef < datei:
            raise ValueError("dateFin < dateIni")
    
        # Build expected timeline by step
        dates = []
        d = datei
        while d <= datef:
            dates.append(d)
            d += timedelta(hours=delta_h)
    
        if len(dates) != len(self):
            log.warning(
                "Number of dates (%d) != number of objects in self (%d). Proceeding with min length.",
                len(dates), len(self)
            )
        n = min(len(dates), len(self))
        dates = dates[:n]
        seq = list(self[:n])
    
        # ---------- default pressure levels ----------
        try:
            zlevs_def = list(map(int, seq[0].zlevs))  # legacy
        except Exception:
            zlevs_def = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30]
    
        # ---------- helpers ----------
        def _mk_df(obj) -> pd.DataFrame | None:
            """Return standardized DataFrame or None if unavailable."""
            try:
                data = obj.obsInfo[varName].loc[varType]
            except Exception:
                return None
            try:
                df = pd.DataFrame({"prs": data["prs"], "omf": data["omf"], "oma": data["oma"]})
                df["prs"] = df["prs"].astype(int, copy=False)
                return df
            except Exception:
                return None
    
        def _select_values(df: pd.DataFrame, level_sel, lay, single_mode) -> dict[int, pd.DataFrame]:
            """Select rows by level according to Level/Lay/SingleL rules."""
            if Level is None or Level == "Zlevs":
                return {int(p): g for p, g in df.groupby("prs")}
            L = int(level_sel)
            if single_mode is None:
                return {L: df[df["prs"] == L]}
            if single_mode == "All":
                return {L: df}
            if single_mode == "OneL":
                if lay is None:
                    log.warning("Variable Lay is None; resetting to default: %d hPa.", Laydef)
                    lay = Laydef
                lo, hi = L - int(lay), L + int(lay)
                return {L: df[(df["prs"] >= lo) & (df["prs"] < hi)]}
            log.warning("Wrong value for SingleL=%r. Please check and rerun.", single_mode)
            return {int(L): df.iloc[0:0]}
    
        # ---------- first pass: discover effective levels and dates ----------
        info_ok = []
        levs_seen: set[int] = set()
        for d, obj in zip(dates, seq):
            df = _mk_df(obj)
            if df is None or df.empty:
                info_ok.append(False)
                _log_info(d.strftime("No data on %Y-%m-%d:%H"))
                continue
    
            if "prs" in df:
                if Level is None or Level == "Zlevs":
                    levs_seen.update(map(int, df["prs"].unique()))
                    _log_info(d.strftime("Preparing %Y-%m-%d:%H"))
                    _log_info(f"Levels so far: {sorted(levs_seen)}")
                else:
                    if isinstance(Level, str) and Level == "Zlevs":
                        levs_seen.update(map(int, df["prs"].unique()))
                    else:
                        levs_seen.add(int(Level))
                        _log_info(d.strftime(f"Preparing %Y-%m-%d:%H - Level: {Level}"))
            info_ok.append(True)
    
        # final level order (keep defaults + ensure consistent columns)
        if Level is None or Level == "Zlevs":
            levs = sorted(set(levs_seen) | set(zlevs_def))
        else:
            levs = sorted(set([int(Level)]) | set(zlevs_def))
    
        # headers (datetime + triplets per level)
        head_levs = ["datetime"]
        for lv in levs:
            head_levs.extend([f"mean{lv}", f"std{lv}", f"count{lv}"])
    
        # ---------- second pass: aggregate per date ----------
        rows_f, rows_a = [], []
        for ok, d, obj in zip(info_ok, dates, seq):
            _log_info(d.strftime("Calculating %Y-%m-%d:%H"))
            stamp = d.strftime("%Y%m%d%H")
            if not ok:
                vals = [stamp] + list(np.r_[np.repeat([na_value, na_value, -99], len(levs))])
                rows_f.append(vals)
                rows_a.append(vals.copy())
                continue
    
            df = _mk_df(obj)
            if df is None or df.empty:
                vals = [stamp] + list(np.r_[np.repeat([na_value, na_value, -99], len(levs))])
                rows_f.append(vals)
                rows_a.append(vals.copy())
                continue
    
            buckets = _select_values(df, Level, Lay, SingleL)
    
            # precompute stats per available level
            stats_f: dict[int, tuple[float, float, int]] = {}
            stats_a: dict[int, tuple[float, float, int]] = {}
    
            for lv, g in buckets.items():
                if g.empty:
                    stats_f[lv] = (na_value, na_value, -99)
                    stats_a[lv] = (na_value, na_value, -99)
                    continue
                omf = g["omf"].to_numpy()
                oma = g["oma"].to_numpy()
                stats_f[lv] = (
                    float(np.mean(omf)) if omf.size else na_value,
                    float(np.std(omf)) if omf.size else na_value,
                    int(omf.size) if omf.size else -99,
                )
                stats_a[lv] = (
                    float(np.mean(oma)) if oma.size else na_value,
                    float(np.std(oma)) if oma.size else na_value,
                    int(oma.size) if oma.size else -99,
                )
    
            # build row guaranteeing all levels in `levs`
            row_f = [stamp]
            row_a = [stamp]
            for lv in levs:
                m, s, c = stats_f.get(lv, (na_value, na_value, -99))
                row_f.extend([m, s, c])
                m, s, c = stats_a.get(lv, (na_value, na_value, -99))
                row_a.extend([m, s, c])
            rows_f.append(row_f)
            rows_a.append(row_a)
    
        # ---------- write ----------
        log.info(
            "Saving CSVs for var=%s type=%s to directory: %s", varName, varType, outdir.as_posix()
        )
        dataout_file = outdir / f"dataout_{varName}_{varType}_{omflag}.csv"
        dataout_filea = outdir / f"dataout_{varName}_{varType}_{omflaga}.csv"
    
        pd.DataFrame.from_records(rows_f, columns=head_levs).to_csv(dataout_file, index=False)
        pd.DataFrame.from_records(rows_a, columns=head_levs).to_csv(dataout_filea, index=False)
    
        log.info("CSV written: %s", dataout_file.as_posix())
        log.info("CSV written: %s", dataout_filea.as_posix())
    
        return str(dataout_file), str(dataout_filea)
    
