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
import geopandas as gpd

# --- Project (local) ---
from readDiag.reader import diagAccess
from readDiag.schema.naming import resolve_col_in_df
from ..datasources import getVarInfo

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
    """Copy ``anl_df['omf']`` into ``bg_df['oma']`` **positionally**.

    This helper supports **two modes** to remain compatible with legacy calls
    already present in older scripts:

    - **Radiance mode**: pass ``sat_id`` and ``channel_value`` to target rows
      belonging to a given satellite (``SatId``) and channel number (``nchan``).
    - **Conventional mode**: pass ``lvl0`` with the *kx* integer. In this case
      ``bg_df`` is expected to be a stacked frame with level‑0 ``'kx'``.

    Parameters
    ----------
    bg_df : pandas.DataFrame
        The *background* concatenated DataFrame into which ``oma`` will be
        injected. If the ``oma`` column does not exist, it will be created.
    anl_df : pandas.DataFrame
        The *analysis* DataFrame (same variable/channel or kx) from which the
        ``omf`` values will be copied.
    sat_id : str, optional
        Satellite/platform id used as level‑0 in radiance tables (e.g., ``'n19'``).
        Required in **radiance mode**.
    channel_value : int, optional
        Channel number (``1..N``). Required in **radiance mode**.
    channel_col : str, default ``"nchan"``
        Column that encodes the channel number in the radiance table.
    lvl0 : int, optional
        *kx* value for **conventional mode** when level‑0 is ``'kx'``.

    Notes
    -----
    - The copy is **positional** (first *N* rows) to preserve the legacy shape
      assumptions; lengths may differ and we copy ``min(len(bg_slice), len(anl))``.
    - Missing inputs, columns, or index keys are tolerated silently.
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
    """Read a **GSI diagnostic** file and expose legacy‑shaped tables.

    Parameters
    ----------
    diagFile : str or path-like
        Path to the *background* (or single) GSI diagnostic file.
    diagFileAnl : str or path-like, optional
        Path to the matching *analysis* diagnostic file. If supplied, the
        function will copy ``omf(ANL)`` into ``oma(BG)`` positionally for the
        same variable/kx (conventional) or channel (radiance).
    isisList : Any, optional
        Kept for signature compatibility; currently unused.
    zlevs : sequence of float, optional
        Pressure levels (hPa) used by some legacy routines. If omitted, a
        default set is provided.
    zchan : Any, optional
        Kept for signature compatibility; currently unused.

    Attributes
    ----------
    obsInfo : mapping
        Dict-like object keyed by variable name (conventional) or sensor name
        (radiance). It also exposes a ``.df`` attribute that points to the
        concatenated long table (``self.obs``) for convenience.
    obs : pandas.DataFrame
        Concatenated long table across variables/sensors with legacy aliases
        (``obs``, ``omf_nobc``, ``inverr``) when resolvable.
    df : pandas.DataFrame
        Alias to :attr:`obs` for older scripts.
    varNames : list[str]
        Variables (conventional) or sensor names (radiance) present in the file.
    _FNumber : int or None
        Synthetic handle id used to emulate the legacy "open file" counter.

    Notes
    -----
    - The constructor attempts to **reuse** an already opened instance for the
      same ``(diagFile, diagFileAnl)`` pair within the same process.
    - Undefined fill values from older readers are normalized to ``NaN``.
    - When ``lat/lon`` exist, a ``GeoDataFrame`` is created with normalized
      longitudes in ``[-180, 180)``.
    """

    def __init__(self, diagFile, diagFileAnl=None, isisList=None, zlevs=None, zchan=None):

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
                print(f"[WARN] Failed to read analysis file '{diagFileAnl}': {e}")
                rd_anl = None

        # File type and undef normalization
        self._FileType = rd.get_data_type()  # 1=conv, 2=rad
        self._undef = np.nan
        self._idate = rd._idate

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

                    if {"lat", "lon"}.issubset(d.columns):
                        lon = (d["lon"] + 180) % 360 - 180
                        lat = d["lat"]
                        d = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon, lat))

                    frames.append(d)
                    keys.append(kx)

                out = pd.concat(frames, keys=keys, names=["kx", "points"]) if frames else pd.DataFrame()

                # Inject OMA from ANL (copy posicional): kx by kx
                if rd_anl is not None and not out.empty:
                    try:  # pragma: no cover - tolerant path
                        for kx in keys:
                            d_anl = rd_anl.get_dataframe(obsName, kx).copy()
                            if d_anl is None or d_anl.empty:
                                continue
                            _inject_oma_from_anl(out, d_anl, lvl0=kx)
                    except Exception as e:
                        print(f"[WARN] OMA injection failed (conv, var={obsName}): {e}")

                self.obsInfo[obsName] = out
                
            # ------------- Concatenated table (previous behavior) -----------------
            self.obs = (
                pd.concat(self.obsInfo, sort=False).reset_index(level=2, drop=True)
                if self.obsInfo else pd.DataFrame()
            )

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
                print(f"[WARN] 'chan' has no iuse values for channels: {sorted(not_covered)}")
            
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
                if {"lat", "lon"}.issubset(d.columns) and _has_gpd:
                    lon = ((d["lon"] + 180) % 360) - 180  # wrap to [-180, 180)
                    lat = d["lat"]
                    d = gpd.GeoDataFrame(d, geometry=gpd.points_from_xy(lon, lat))
            
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
                    print(f"[WARN] OMA injection failed (radiance): {e}")
            
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
        """Logically close this object (drop big tables and unregister handle).

        Returns
        -------
        int
            Always ``0`` (legacy status value).

        Examples
        --------
        >>> gdf = read_diag("diag_conv_01.2024021000")  # doctest: +SKIP
        >>> gdf.close()  # doctest: +SKIP
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

    def __del__(self):  # pragma: no cover - destructor best effort
        try:
            self.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.close()
        finally:
            return False  # propagate exceptions

    # ---------------------------------------------------------------------
    # Introspection (legacy)
    # ---------------------------------------------------------------------
    def overview(self) -> Dict[str, List[Any]]:
        """Summarize variables and available *types* (kx or SatId).

        Returns
        -------
        dict
            Mapping ``{var_name: [types...]}`` where *types* are *kx* values for
            conventional files and, for radiance, the first‑level keys (often a
            single SatId like ``'n19'``).

        Examples
        --------
        >>> gdf = read_diag("diag_conv_01.2024021000")  # doctest: +SKIP
        >>> ov = gdf.overview()  # doctest: +SKIP
        >>> isinstance(ov, dict)
        True
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
        """Print a simple list of variables and available *kx* values.

        Notes
        -----
        - This is a convenience **printing** routine kept for legacy parity.
        - For programmatic use prefer :meth:`overview`.
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
        """Export time-series aggregates to CSV (legacy routine, optimized).
    
        This preserves the legacy calling convention where the first positional
        argument (named ``self`` for historical reasons) is actually a **sequence**
        of per-cycle ``read_diag`` objects. Only performance/robustness were improved.
    
        Parameters
        ----------
        self : Sequence[read_diag]
            Sequence of per-cycle objects (e.g., BG files sampled each ``nHour``).
        varName : str, optional
            Conventional variable or sensor name key inside ``.obsInfo``.
        varType : str or int, optional
            For conventional files, this is the *kx*; for radiance, the SatId
            (e.g., ``'n19'``) or equivalent key.
        dateIni, dateFin : str or int
            Bounds as ``YYYYMMDDHH`` (must match the number of items in ``self``
            when stepping by ``nHour``).
        nHour : str or int, default ``"06"``
            Step (hours) between successive objects in ``self``.
        Level : int or str, optional
            If ``None`` or ``"Zlevs"``, aggregate by standard z-levels. Otherwise,
            use the provided level (hPa).
        Lay : int, optional
            Half-width for layer selection around ``Level`` when
            ``SingleL == "OneL"``.
        SingleL : {None, "All", "OneL"}, optional
            Layer aggregation mode (entire atmosphere vs. a single layer).
        outdir : str | pathlib.Path, optional
            Output directory for CSV files. Defaults to current directory.
        na_value : float, default -99.0
            Fill value for missing aggregates.
        verbose : bool, default True
            If True, prints legacy progress messages; if False, runs silent.
    
        Returns
        -------
        tuple[str, str]
            Filenames of the two CSV files written (``OmF`` and ``OmA``).
    
        Notes
        -----
        - Keeps legacy column layout: for each level, exports ``mean``, ``std`` and
          ``count`` triplets.
        - Uses vectorized grouping and minimizes Python-level loops.
        """
        import numpy as np
        import pandas as pd
        from datetime import datetime, timedelta
        from pathlib import Path
    
        def _p(msg: str) -> None:
            if verbose:
                print(msg)
    
        # ---------- setup & banner ----------
        outdir = Path(outdir)
        outdir.mkdir(parents=True, exist_ok=True)
    
        omflag, omflaga = "OmF", "OmA"
        Laydef = 50
        delta_h = int(nHour)
        sep = " " + "=" * 100
    
        varInfo = None
        try:
            # getVarInfo pode não existir em todos os ambientes/variáveis
            from .datasources import getVarInfo  # type: ignore
            varInfo = getVarInfo(varType, varName, "instrument")
        except Exception:
            pass
    
        _p("\n" + sep)
        _p(
            f" Analyzing data of variable: {varName}  ||  type: {varType}  ||  "
            f"{(varInfo if varInfo is not None else 'Unknown instrument')}  ||  check: {omflag}"
        )
        _p(sep + "\n")
    
        # ---------- range & consistency ----------
        datei = datetime.strptime(str(dateIni), "%Y%m%d%H")
        datef = datetime.strptime(str(dateFin), "%Y%m%d%H")
        if datef < datei:
            raise ValueError("dateFin < dateIni")
    
        # constrói a linha do tempo esperada pelo passo
        dates = []
        d = datei
        while d <= datef:
            dates.append(d)
            d += timedelta(hours=delta_h)
    
        if len(dates) != len(self):
            # Mantém compatibilidade, mas reclama se houver divergência de contagem
            _p(
                f"[WARN] Number of dates ({len(dates)}) != number of objects in self ({len(self)}). "
                "Proceeding with min length."
            )
        n = min(len(dates), len(self))
        dates = dates[:n]
        seq = list(self[:n])
    
        # ---------- níveis padrão ----------
        try:
            zlevs_def = list(map(int, seq[0].zlevs))  # legado
        except Exception:
            zlevs_def = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30]
    
        # ---------- utilitários de filtragem ----------
        def _mk_df(obj) -> pd.DataFrame | None:
            """Retorna DataFrame com colunas padronizadas ou None se indisponível."""
            try:
                data = obj.obsInfo[varName].loc[varType]
            except Exception:
                return None
            # Esperado: arrays/Series p/ 'prs', 'omf', 'oma'
            try:
                df = pd.DataFrame({"prs": data["prs"], "omf": data["omf"], "oma": data["oma"]})
                # força inteiros nos níveis para chavear corretamente
                df["prs"] = df["prs"].astype(int, copy=False)
                return df
            except Exception:
                return None
    
        def _select_values(df: pd.DataFrame, level_sel, lay, single_mode) -> dict[int, pd.DataFrame]:
            """Seleciona dados por nível conforme regras de Level/Lay/SingleL."""
            if Level is None or Level == "Zlevs":
                # agrega por cada nível presente
                return {int(p): g for p, g in df.groupby("prs")}
            # Level específico
            L = int(level_sel)
            if single_mode is None:
                return {L: df[df["prs"] == L]}
            if single_mode == "All":
                # tudo num único balde com rótulo L
                return {L: df}
            if single_mode == "OneL":
                if lay is None:
                    _p(f"\n Variable Lay is None, resetting to default: {Laydef} hPa.\n")
                    lay = Laydef
                lo, hi = L - int(lay), L + int(lay)
                return {L: df[(df["prs"] >= lo) & (df["prs"] < hi)]}
            # modo inválido: retorna vazio para cair no preenchimento com NA
            _p(" Wrong value for variable SingleL. Please, check it and rerun the script.")
            return {int(L): df.iloc[0:0]}
    
        # ---------- primeira passada: descobrir níveis efetivos e datas com info ----------
        info_ok = []
        levs_seen: set[int] = set()
        for d, obj in zip(dates, seq):
            df = _mk_df(obj)
            if df is None or df.empty:
                info_ok.append(False)
                _p(d.strftime("  >>> No information on this date: %Y-%m-%d:%H"))
                continue
    
            if "prs" in df:
                if Level is None or Level == "Zlevs":
                    levs_seen.update(map(int, df["prs"].unique()))
                    _p(d.strftime(" Preparing data for: %Y-%m-%d:%H"))
                    _p(f" Levels: {sorted(levs_seen)}\n")
                else:
                    if isinstance(Level, str) and Level == "Zlevs":
                        levs_seen.update(map(int, df["prs"].unique()))
                    else:
                        levs_seen.add(int(Level))
                        _p(d.strftime(" Preparing data for: %Y-%m-%d:%H") + f" - Level: {Level}")
            info_ok.append(True)
    
        # ordem final de níveis (mantém padrão + garante colunas “vazias” para ausentes)
        if Level is None or Level == "Zlevs":
            levs = sorted(set(levs_seen) | set(zlevs_def))
        else:
            levs = sorted(set([int(Level)]) | set(zlevs_def))
    
        # cabeçalhos (datetime + tripletas por nível)
        head_levs = ["datetime"]
        for lv in levs:
            head_levs.extend([f"mean{lv}", f"std{lv}", f"count{lv}"])
    
        # ---------- segunda passada: agrega por data ----------
        rows_f, rows_a = [], []
        for ok, d, obj in zip(info_ok, dates, seq):
            _p(d.strftime(" Calculating for %Y-%m-%d:%H"))
            stamp = d.strftime("%Y%m%d%H")
            if not ok:
                # linha só com NA
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
    
            # pré-computa estatísticas por nível disponível
            stats_f: dict[int, tuple[float, float, int]] = {}
            stats_a: dict[int, tuple[float, float, int]] = {}
    
            for lv, g in buckets.items():
                if g.empty:
                    stats_f[lv] = (na_value, na_value, -99)
                    stats_a[lv] = (na_value, na_value, -99)
                    continue
                omf = g["omf"].to_numpy()
                oma = g["oma"].to_numpy()
                # estatística robusta e vetorizada
                if omf.size:
                    stats_f[lv] = (float(np.mean(omf)), float(np.std(omf)), int(omf.size))
                else:
                    stats_f[lv] = (na_value, na_value, -99)
                if oma.size:
                    stats_a[lv] = (float(np.mean(oma)), float(np.std(oma)), int(oma.size))
                else:
                    stats_a[lv] = (na_value, na_value, -99)
    
            # monta linha garantindo todos os níveis em `levs`
            row_f = [stamp]
            row_a = [stamp]
            for lv in levs:
                m, s, c = stats_f.get(lv, (na_value, na_value, -99))
                row_f.extend([m, s, c])
                m, s, c = stats_a.get(lv, (na_value, na_value, -99))
                row_a.extend([m, s, c])
            rows_f.append(row_f)
            rows_a.append(row_a)
    
        _p("\n" + sep + "\n")
    
        # ---------- gravação ----------
        _p("\n Saving Dataset in CSV File...  ")
        dataout_file = outdir / f"dataout_{varName}_{varType}_{omflag}.csv"
        dataout_filea = outdir / f"dataout_{varName}_{varType}_{omflaga}.csv"
    
        pd.DataFrame.from_records(rows_f, columns=head_levs).to_csv(dataout_file, index=False)
        pd.DataFrame.from_records(rows_a, columns=head_levs).to_csv(dataout_filea, index=False)
    
        _p(" Done \n")
        return str(dataout_file), str(dataout_filea)

