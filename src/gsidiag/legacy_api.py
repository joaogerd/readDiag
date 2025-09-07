from __future__ import annotations

"""
Legacy compatibility layer backed by the new readDiag engine.

This module provides a thin, well-documented shim class (:class:`read_diag`)
that **preserves the legacy public surface** (method names, return shapes and
defaults) while internally delegating all heavy work to the **new** engine:

- IO: :func:`readDiag.io.reader.diagAccess`
- Stable API: :class:`readDiag.surface.api.DiagnosticAPI`
- Adapter: :class:`readDiag.surface.access_adapter.AccessAdapter`
- Plot wrappers: :mod:`readDiag.plotting.wrappers`

The goal is to unblock users and tests that still import and use the legacy
entry points, while your codebase migrates towards the modern, typed API.

Notes
-----
- The class name intentionally matches the old one: :class:`read_diag`.
- Conventional (``file_type == 1``) diagnostics are materialized as a
  (Geo)DataFrame with a MultiIndex ``['idate','var','kx']`` in ``.obsInfo``.
- Radiance (``file_type == 2``) concatenates per-channel frames with a
  ``channel`` column and stores the result in ``.obsInfo`` (no MultiIndex).

Examples
--------
Quick open (conventional file) and summarize a subset:

>>> rg = read_diag("data/diag_conv_01.2024013018")  # doctest: +SKIP
>>> rg.varNames                               # doctest: +SKIP
['t', 'q', 'ps']
>>> rg.get_unique_kx()[:5]                    # doctest: +SKIP
[120, 130, 131, 132, 133]
>>> # Describe statistics for temperature/kx=120 at the file cycle:
>>> dt = rg.get_unique_dates()[0]             # doctest: +SKIP
>>> rg.summarize(varName="t", kx=120, idate=dt)  # doctest: +SKIP

Plotting via legacy names (mapped to new wrappers):

>>> rg.kxcount()                              # doctest: +SKIP
>>> rg.plot(varName="t", varType=120, param="omf")   # doctest: +SKIP
>>> rg.pvmap(varName="t", kx=120)                    # doctest: +SKIP
"""

from typing import Optional, Tuple, Dict, List, Any
from dataclasses import dataclass

import pandas as pd

try:
    import geopandas as gpd
    _HAS_GPD = True
except Exception:  # pragma: no cover - geopandas is optional
    _HAS_GPD = False
    gpd = None  # type: ignore

# --- New engine (NOT legacy) -------------------------------------------------
from readDiag.io.reader import diagAccess
from readDiag.surface.access_adapter import AccessAdapter
from readDiag.surface.api import DiagnosticAPI

# --- New plotting (simple wrappers) -----------------------------------------
try:
    from readDiag.plotting.wrappers import (
        plot_kx_count as _plot_kx_count,
        plot_omf_map as _plot_omf_map,
        plot_oma_map as _plot_oma_map,
    )
except Exception:  # pragma: no cover - plotting deps may be missing at runtime
    # Keep callables present so legacy code can import/instantiate without breaking.
    def _plot_kx_count(*args, **kwargs):
        """Fallback placeholder when plotting dependencies are unavailable."""
        raise RuntimeError("Plotting dependencies not available.")

    def _plot_omf_map(*args, **kwargs):
        """Fallback placeholder when plotting dependencies are unavailable."""
        raise RuntimeError("Plotting dependencies not available.")

    def _plot_oma_map(*args, **kwargs):
        """Fallback placeholder when plotting dependencies are unavailable."""
        raise RuntimeError("Plotting dependencies not available.")


# --------------------------------------------------------------------------- #
# Small helpers
# --------------------------------------------------------------------------- #
def _wrap_lon_to_180(series: pd.Series) -> pd.Series:
    """Wrap longitudes to the ``[-180, 180)`` range.

    Parameters
    ----------
    series : pandas.Series
        Series convertible to float, expressing longitudes in degrees East.

    Returns
    -------
    pandas.Series
        A float series with values mapped to ``[-180, 180)``.

    Notes
    -----
    This is a pure arithmetic wrap that does **not** change the order of
    observations; it only remaps the numeric values.
    """
    return (series.astype(float) + 180.0) % 360.0 - 180.0


def _to_gdf_if_available(df: pd.DataFrame) -> pd.DataFrame:
    """Optionally return a GeoDataFrame with point geometries.

    If GeoPandas is available **and** the input has ``'lat'`` and ``'lon'``
    columns, convert to :class:`geopandas.GeoDataFrame` with a ``Point`` geometry.

    Parameters
    ----------
    df : pandas.DataFrame
        Input table; if it contains ``lat``/``lon``, geometry is created.

    Returns
    -------
    pandas.DataFrame
        The original DataFrame or a GeoDataFrame (same columns + ``geometry``).

    Notes
    -----
    - Longitudes are wrapped to ``[-180, 180)`` before constructing points.
    - The CRS is not set; callers should assign one if needed.
    """
    if _HAS_GPD and {"lat", "lon"} <= set(df.columns):
        lon = _wrap_lon_to_180(df["lon"])
        lat = df["lat"].astype(float)
        return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(lon, lat))
    return df


# --------------------------------------------------------------------------- #
# Legacy-compatible facade (backed by the new engine)
# --------------------------------------------------------------------------- #
class read_diag:
    """Legacy class preserved for backwards compatibility.

    This adapter keeps the *legacy shape* (public methods and attribute names)
    while driving the **new** implementation under the hood:
    ``diagAccess`` → :class:`AccessAdapter` → :class:`DiagnosticAPI`.

    For **conventional** diagnostics (``file_type == 1``), ``.obsInfo`` is a
    (Geo)DataFrame indexed by ``['idate', 'var', 'kx']`` with all variables and
    KX groups concatenated. For **radiance** diagnostics (``file_type == 2``),
    per-channel frames are concatenated with a ``channel`` column.

    Parameters
    ----------
    diag_file : str or list of str
        Path (or list of paths) to diagnostic files.
    diag_file_anl : str or list of str, optional
        Analysis file(s) paired with ``diag_file``; accepted for signature
        compatibility but not used internally by this adapter.
    isis_list : list of str, optional
        Preserved for compatibility with older code; not used here.
    zlevs : list of float, optional
        Preserved for compatibility with older code; not used here.

    Attributes
    ----------
    obsInfo : pandas.DataFrame
        Materialized table of observations (GeoDataFrame if GeoPandas present
        and ``lat``/``lon`` columns are available).
    varNames : list of str
        List of variables detected (``['radiance']`` for radiance files).
    _variablesList : dict[str, list[int]]
        Mapping ``var -> [kx...]`` constructed from ``obsInfo`` (conventional).
    _file_type : int
        GSI data type reported by the reader (``1=conv``, ``2=rad``).
    _idate : Any
        Cycle timestamp returned by the reader.

    Examples
    --------
    Open a single conventional file and list variables/KX:

    >>> rd = read_diag("data/diag_conv_01.2024013018")  # doctest: +SKIP
    >>> rd.varNames                                     # doctest: +SKIP
    ['t', 'q', 'ps']
    >>> rd._variablesList['t'][:5]                      # doctest: +SKIP
    [120, 130, 131, 132, 133]

    Summaries and time-sliced summaries:

    >>> dt = rd.get_unique_dates()[0]                   # doctest: +SKIP
    >>> rd.summarize("t", 120, idate=dt)                # doctest: +SKIP
    >>> rd.tmsummarize("t", 120)                        # doctest: +SKIP

    Plot counts and maps via legacy names:

    >>> rd.kxcount()                                    # doctest: +SKIP
    >>> rd.plot("t", 120, param="omf")                  # doctest: +SKIP
    >>> rd.pvmap(varName="t", kx=120)                   # doctest: +SKIP
    """

    # ------------------------ opening / materialization ------------------------
    def __init__(
        self,
        diag_file: str | List[str],
        diag_file_anl: Optional[str | List[str]] = None,
        isis_list: Optional[List[str]] = None,
        zlevs: Optional[List[float]] = None,
    ) -> None:
        # Normalize input to a list of “primary” files, mirroring legacy behavior.
        if isinstance(diag_file, str):
            self._diag_files = [diag_file]
        elif isinstance(diag_file, list):
            self._diag_files = diag_file
        else:
            raise ValueError("diag_file must be a string or a list of strings")

        # Keep the analysis counterpart list aligned (unused here but preserved).
        if diag_file_anl is None:
            self._diag_files_anl = [None] * len(self._diag_files)
        elif isinstance(diag_file_anl, str):
            self._diag_files_anl = [diag_file_anl] * len(self._diag_files)
        else:
            if len(diag_file_anl) != len(self._diag_files):
                raise ValueError("diag_file_anl list must have the same length as diag_file list")
            self._diag_files_anl = diag_file_anl

        # Compatibility placeholders (not used by the new engine).
        self._isis_list = isis_list if isis_list is not None else ["None"]
        self._zlevs = zlevs if zlevs is not None else [
            1000.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0,
            250.0, 200.0, 150.0, 100.0, 50.0, 0.0
        ]

        gdfs: List[pd.DataFrame] = []  # accumulate per-file tables

        # Iterate over files and build a unified obsInfo consistent with legacy.
        for f, f_anl in zip(self._diag_files, self._diag_files_anl):
            raw = diagAccess(f)                     # new low-level engine
            self._file_type = raw.get_data_type()   # 1=conv, 2=rad
            self._idate     = raw.get_date()
            api: DiagnosticAPI = AccessAdapter(raw) # stable, typed surface

            if self._file_type == 1:
                # CONV: concatenate (var, kx) frames, add MultiIndex.
                frames: List[pd.DataFrame] = []
                for v in api.variables():
                    for kx in api.kx_list(v):
                        df = api.frame_conv(v, kx).copy()
                        df["var"] = v
                        df["kx"] = kx
                        frames.append(df)

                if frames:
                    conv_df = pd.concat(frames, ignore_index=True)
                    conv_df["idate"] = self._idate
                    conv_df = conv_df.set_index(["idate", "var", "kx"]).sort_index()
                    # turn into GeoDataFrame when geopandas is available
                    gdfs.append(_to_gdf_if_available(conv_df.reset_index()).set_index(["idate", "var", "kx"]))
                else:
                    gdfs.append(pd.DataFrame())

            elif self._file_type == 2:
                # RAD: concatenate channels; keep a simple flat schema.
                frames: List[pd.DataFrame] = []
                for ch in api.channels():
                    df = api.frame_channel(ch).copy()
                    df["channel"] = ch
                    frames.append(df)
                rad_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
                gdfs.append(rad_df)
            else:
                # Unknown type: keep empty shell for robustness.
                gdfs.append(pd.DataFrame())

        # Merge all materialized tables into a single obsInfo.
        if gdfs:
            # If all frames share the same MultiIndex (conventional), align by index.
            is_multi = all(hasattr(df, "index") and isinstance(df.index, pd.MultiIndex) for df in gdfs)
            if is_multi:
                self.obsInfo = pd.concat(gdfs, axis=0, ignore_index=False).sort_index()
            else:
                self.obsInfo = pd.concat(gdfs, axis=0, ignore_index=True)
        else:
            self.obsInfo = pd.DataFrame()

        # Legacy-facing metadata views.
        if getattr(self, "_file_type", None) == 1:
            self.varNames = [] if self.obsInfo.empty else self.obsInfo.index.get_level_values("var").unique().tolist()
            self._nVars = len(self.varNames)
            self._variablesList: Dict[str, List[int]] = {}
            for v in self.varNames:
                try:
                    kxs = self.obsInfo.xs(v, level="var").index.get_level_values("kx").unique().tolist()
                except Exception:
                    kxs = []
                self._variablesList[v] = kxs
        else:
            self.varNames = ["radiance"] if not self.obsInfo.empty else []
            self._nVars = len(self.varNames)
            self._variablesList = {"radiance": []}

    # ------------------------ legacy helpers ------------------------
    def _overview(self) -> None:
        """No-op kept for compatibility."""
        return

    def pfileinfo(self) -> None:
        """Print a compact list of variables and their KX groups (legacy style).

        Side Effects
        ------------
        Writes to ``stdout``.

        Examples
        --------
        >>> rg = read_diag("data/diag_conv_01.2024013018")  # doctest: +SKIP
        >>> rg.pfileinfo()                                  # doctest: +SKIP
        Variable Name : t
                      └── kx => 120 130 131 ...
        """
        for name in self._variablesList.keys():
            print("Variable Name :", name)
            print("              └── kx => ", end="", flush=True)
            for kx in self._variablesList[name]:
                print(kx, " ", end="", flush=True)
            print("\n")

    @staticmethod
    def filter_multiindex(df: pd.DataFrame, level_values: List[Tuple[str, object]]) -> pd.DataFrame:
        """Return a row filter over a MultiIndex DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            A DataFrame indexed by a :class:`pandas.MultiIndex`.
        level_values : list of (str, object)
            Pairs of ``(level_name, desired_value)`` to be matched.

        Returns
        -------
        pandas.DataFrame
            A view filtered to matching rows. If no criteria are given, the
            input is returned unchanged.

        Raises
        ------
        KeyError
            If any level name is missing from the DataFrame index.
        """
        # Validate levels exist
        if isinstance(df.index, pd.MultiIndex):
            missing = {lvl for (lvl, _) in level_values} - set(df.index.names)
            if missing:
                raise KeyError(f"Missing index levels: {sorted(missing)}")

        mask = None
        for level, value in level_values:
            lv = df.index.get_level_values(level)
            current_mask = lv == value
            mask = current_mask if mask is None else (mask & current_mask)
        return df[mask] if mask is not None else df

    def summarize(self, varName: Optional[str] = None, kx: Optional[int] = None, idate=None) -> pd.DataFrame:
        """Describe a subset (conventional only) using ``DataFrame.describe()``.

        Parameters
        ----------
        varName : str, optional
            Variable to select (e.g., ``'t'``, ``'q'``). If omitted, no filter.
        kx : int, optional
            WMO KX code to select (e.g., 120 for TEMP). If omitted, no filter.
        idate : Any, optional
            Cycle timestamp to select. If omitted, no filter.

        Returns
        -------
        pandas.DataFrame
            Descriptive statistics (count, mean, std, percentiles) for the
            filtered rows. Returns an empty DataFrame if not conventional or
            if no rows match.

        Raises
        ------
        KeyError
            If a provided value is not present in the corresponding index level.
        """
        if self._file_type != 1 or self.obsInfo is None or self.obsInfo.empty or not isinstance(self.obsInfo.index, pd.MultiIndex):
            return pd.DataFrame()
        data = self.obsInfo
        crit: List[Tuple[str, object]] = []

        def add(level: str, value) -> None:
            if value is not None:
                if value not in data.index.get_level_values(level).unique():
                    raise KeyError(f"{level.title()} '{value}' not found in the data.")
                crit.append((level, value))

        add("var", varName); add("kx", kx); add("idate", idate)
        filtered = self.filter_multiindex(data, crit)
        return filtered.describe() if not filtered.empty else pd.DataFrame()

    def tmsummarize(self, varName: Optional[str] = None, kx: Optional[int] = None) -> Dict[Any, pd.DataFrame]:
        """Describe a subset **per cycle** (time-sliced summaries, conventional).

        Parameters
        ----------
        varName : str, optional
            Variable to select (required).
        kx : int, optional
            WMO KX code to select (required).

        Returns
        -------
        dict[Any, pandas.DataFrame]
            Mapping ``idate -> describe(table for var/kx at that idate)``.

        Raises
        ------
        KeyError
            If ``varName`` or ``kx`` are missing or not present in the data.
        """
        if self._file_type != 1 or self.obsInfo is None or self.obsInfo.empty or not isinstance(self.obsInfo.index, pd.MultiIndex):
            return {}
        if varName is None or varName not in self.obsInfo.index.get_level_values("var").unique():
            raise KeyError(f"Variable {varName} not found in the data.")
        if kx is None or kx not in self.obsInfo.index.get_level_values("kx").unique():
            raise KeyError(f"kx {kx} not found in the data.")
        out: Dict[Any, pd.DataFrame] = {}
        for dt in self.obsInfo.index.get_level_values("idate").unique():
            df = self.filter_multiindex(self.obsInfo, [("var", varName), ("kx", kx), ("idate", dt)])
            out[dt] = df.describe()
        return out

    # ------------------------ convenience getters ------------------------
    def get_unique_dates(self) -> List[Any]:
        """Return all unique cycle timestamps present in ``.obsInfo``."""
        if self.obsInfo is None or self.obsInfo.empty:
            return []
        if isinstance(self.obsInfo.index, pd.MultiIndex) and "idate" in self.obsInfo.index.names:
            return self.obsInfo.index.get_level_values("idate").unique().tolist()
        return []

    def get_unique_kx(self, date=None) -> List[int]:
        """Return all unique KX codes (optionally for a single ``idate``)."""
        if self.obsInfo is None or self.obsInfo.empty:
            return []
        if not (isinstance(self.obsInfo.index, pd.MultiIndex) and "kx" in self.obsInfo.index.names):
            return []
        data = self.obsInfo.loc[date] if date is not None else self.obsInfo
        return data.index.get_level_values("kx").unique().tolist()

    def get_unique_vars(self, date=None) -> List[str]:
        """Return all unique variable names (optionally for a single ``idate``)."""
        if self.obsInfo is None or self.obsInfo.empty:
            return []
        if not (isinstance(self.obsInfo.index, pd.MultiIndex) and "var" in self.obsInfo.index.names):
            return []
        data = self.obsInfo.loc[date] if date is not None else self.obsInfo
        return data.index.get_level_values("var").unique().tolist()

    # ------------------------ plotting compat (maps to new wrappers) ------------------------
    def plot(self, varName, varType, param, mask=None, area=None, **kwargs):
        """Legacy plotting dispatcher mapped to modern wrappers.

        Parameters
        ----------
        varName : str
            Variable name (e.g., ``'t'``).
        varType : int
            KX code (e.g., ``120``).
        param : {"omf", "oma"}
            Which field to plot. ``"omf"`` and ``"oma"`` are mapped to the
            modern spatial plotting wrappers.
        mask, area : Any, optional
            Accepted for signature compatibility; ignored here.
        **kwargs
            Forwarded to the underlying plotting wrapper.

        Returns
        -------
        matplotlib.Axes or Any
            Whatever the modern wrapper returns.

        Raises
        ------
        NotImplementedError
            If ``param`` does not map to a known wrapper.
        """
        if param == "omf":
            return _plot_omf_map(self, var=varName, kx=varType, **kwargs)
        elif param == "oma":
            return _plot_oma_map(self, var=varName, kx=varType, **kwargs)
        else:
            raise NotImplementedError(f"Legacy plot param '{param}' not mapped.")

    def ptmap(self, varName, varType=None, mask=None, area=None, **kwargs):
        """Legacy alias: point map of OMF by default."""
        return _plot_omf_map(self, var=varName, kx=varType or kwargs.get("kx", 0), **kwargs)

    def pvmap(self, varName=None, mask=None, area=None, **kwargs):
        """Legacy alias: choose OMA by default; requires ``var`` and ``kx``."""
        var = varName or kwargs.get("var")
        kx = kwargs.get("kx")
        if var is None or kx is None:
            raise ValueError("pvmap requires 'var' and 'kx'.")
        return _plot_oma_map(self, var=var, kx=kx, **kwargs)

    def pcount(self, varName, **kwargs):
        """Legacy alias for KX count plot (``diagPlotter.plot_kx_count``)."""
        return _plot_kx_count(self, **kwargs)

    def vcount(self, **kwargs):
        """Legacy alias for KX count plot."""
        return _plot_kx_count(self, **kwargs)

    def kxcount(self, **kwargs):
        """Legacy alias for KX count plot."""
        return _plot_kx_count(self, **kwargs)

    # ------------------------ resource management ------------------------
    def close(self) -> int:
        """No explicit resources to close in the new engine.

        Returns
        -------
        int
            Always ``0`` (success), kept for drop-in compatibility.
        """
        return 0

