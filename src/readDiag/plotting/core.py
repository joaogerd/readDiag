# ---------------------------------------------------------------------------
# Plotting utilities for GSI diagnostics (NumPy-style docstrings)
# ---------------------------------------------------------------------------
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, List, Dict, Any, Tuple, Sequence
import itertools
import re
from collections import defaultdict

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize, to_hex

import numpy as np
import pandas as pd
from textwrap import wrap

# Optional cartopy support (graceful fallback if missing)
try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    _HAS_CARTOPY = True
except Exception:  # cartopy is optional at runtime
    _HAS_CARTOPY = False

from ..surface.access_adapter import AccessAdapter
from ..surface.adapters.legacy import LegacyCompatAdapter
from ..surface.api import DiagnosticAPI
from ..io.reader import diagAccess as _DiagAccess
from .style import PlotConfig
from ..utils import deprecated, check_kind
from ..utils import extract_int, mask_to_query, nice_label, guess_cycle_token
from ..schema.naming import resolve_col_in_df, resolve_name

# Modern utils shim (preserve runtime robustness)
try:
    from .._utils import get_cycle  # shim to modern utils
except Exception:
    def get_cycle(obj):
        try:
            m = getattr(obj, 'meta', lambda: None)()
            return getattr(m, 'date', None)
        except Exception:
            return None

from ._utils import (
    wrap_lon,
    cmap_hex,
    ensure_axes_gpd,
    ensure_axes_cartopy,
    make_axes,
    wrap_label,
)


def _get_conv_df(diag, var: str, kx: int) -> pd.DataFrame:
    """Internal helper to retrieve a conventional frame regardless of backend quirks."""
    return diag.get_dataframe(var, kx) if hasattr(diag, "get_dataframe") else diag.get_data_frame()[var][kx]


def _available_kx(diag, var: str) -> list[int]:
    """Return available KX codes for a conventional variable (backend-agnostic)."""
    try:
        return [int(k) for k in diag.get_kx_list(var)]
    except Exception:
        d = diag.get_data_frame().get(var, {})
        return [int(k) for k in getattr(d, "keys", lambda: [])()]


# ---------------------------------------------------------------------------
# Apply a global/default plotting configuration at import time
# ---------------------------------------------------------------------------
_default_config = PlotConfig()
plt.style.use(_default_config.style)
mpl.rcParams.update(_default_config.rc_params)


class diagPlotter:
    """High-level plotting helper for ``diagAccess`` diagnostics.

    The plotter detects whether the diagnostic is **conventional** or **radiance**
    and exposes convenience methods for common visualizations (histograms,
    counts, per-channel stats, spatial plots, etc.). Styling is centralized via
    :class:`~readDiag.style.PlotConfig`. Per-plot overrides can be passed as
    keyword arguments.

    Parameters
    ----------
    diag : diagAccess or DiagnosticAPI-like
        A diagnostic object opened by :class:`~readDiag.io.reader.diagAccess`
        **or** any object implementing the modern surface API (``meta()``,
        ``kind()``, ``variables()``, ``kx_list()``, ``frame_conv()``,
        ``channels()``, ``frame_channel()``, ``table()``).
        Legacy-like backends are automatically wrapped by adapters.
    config : PlotConfig, optional
        Custom plotting style. If omitted, a global default is used.

    Raises
    ------
    TypeError
        If a completely incompatible object is provided.

    Notes
    -----
    - **Graphical kwargs** (e.g., ``color``, ``alpha``, ``marker``, ``linewidth``)
      are forwarded directly to Matplotlib calls.
    - **Style kwargs** (``title``, ``xlabel``, ``ylabel``, ``rotation``,
      ``fontsize``, ``zero_line``) are handled by :meth:`_apply_plot_kwargs`.
    - All methods return the Matplotlib :class:`~matplotlib.axes.Axes` instance.

    Examples
    --------
    Basic usage (conventional)::

        >>> from readDiag.io.reader import diagAccess
        >>> from readDiag.plotting import diagPlotter
        >>> d = diagAccess("path/to/diag_conv_01.2020010100")
        >>> p = diagPlotter(d)
        >>> ax = p.plot_hist_conv("t", 120, param="omf", bins=40, color="C0",
        ...                       title="Temp O−F Histogram")

    Counts across KX for all variables::

        >>> ax = p.plot_kx_count(title="Total observations by KX", rotation=45)

    Radiance channel statistics::

        >>> d = diagAccess("path/to/diag_amsua_n19_01.2020010100")
        >>> p = diagPlotter(d)
        >>> ax = p.plot_channel_stats_rad(param="omf", agg="mean", marker="o")

    Spatial scatter (conventional)::

        >>> ax = p.plot_spatial_conv("t", 120, param="omf", cmap="coolwarm",
        ...                          area=[-90, -60, 0, 15], zero_line=False)
    """

    # Keys that are *style* (handled by _apply_plot_kwargs) and not forwarded
    # to Matplotlib plotting functions directly.
    STYLE_KEYS = {"title", "xlabel", "ylabel", "rotation", "fontsize", "zero_line"}

    def __init__(self, diag, config: Optional[PlotConfig] = None):
        # 1) If the object already exposes the full modern surface, use it directly
        _has_surface = all(
            callable(getattr(diag, name, None))
            for name in ("meta", "kind", "variables", "kx_list", "frame_conv",
                         "channels", "frame_channel", "table")
        )
        if _has_surface:
            self.diag = diag
        else:
            # 2) If it looks like the modern backend (diagAccess), try AccessAdapter
            if isinstance(diag, _DiagAccess) and callable(getattr(diag, "get_file_info", None)) \
               and hasattr(diag, "file_name"):
                try:
                    self.diag = AccessAdapter(diag)
                except Exception:
                    # Fallback to legacy adapter
                    self.diag = LegacyCompatAdapter(diag)
            else:
                # 3) Fakes/mocks/legacies → LegacyCompatAdapter
                self.diag = LegacyCompatAdapter(diag)

        # After wrapping, .kind() must exist ("conv" or "rad")
        self.kind = self.diag.kind()
        self.config = config or _default_config

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_ax(ax: Optional[plt.Axes]) -> plt.Axes:
        """Return an existing ``Axes`` or create a fresh one."""
        if ax is None:
            fig, ax = plt.subplots()
        return ax

    @staticmethod
    def _save(ax: plt.Axes, savepath: Optional[str]) -> None:
        """Save the figure to disk if a path is provided."""
        if not savepath:
            return
        p = Path(savepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        ax.get_figure().savefig(p, dpi=150, bbox_inches="tight")

    def _apply_plot_kwargs(self, ax: plt.Axes, style_kwargs: Dict[str, Any]) -> plt.Axes:
        """Apply axis-level styling (titles, labels, ticks, reference lines).

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Target axes to style.
        style_kwargs : dict
            Supported keys:
            ``title`` : str
            ``xlabel`` / ``ylabel`` : str
            ``rotation`` : int, default 0
            ``fontsize`` : int, default 10
            ``zero_line`` : bool, default True

        Returns
        -------
        matplotlib.axes.Axes
        """
        style_kwargs = dict(style_kwargs)  # defensive copy

        title = style_kwargs.get("title")
        xlabel = style_kwargs.get("xlabel")
        ylabel = style_kwargs.get("ylabel")
        rotation = style_kwargs.get("rotation", 0)
        fontsize = style_kwargs.get("fontsize", 10)
        zero_line = style_kwargs.get("zero_line", True)

        # Apply global style (grid, spines, facecolor, etc.)
        self.config.apply_to_axes(ax)

        if isinstance(xlabel, str):
            ax.set_xlabel(xlabel, fontsize=fontsize)
        if isinstance(ylabel, str):
            ax.set_ylabel(ylabel, fontsize=fontsize)

        for lbl in ax.get_xticklabels():
            lbl.set_rotation(rotation)
            lbl.set_fontsize(fontsize)

        if zero_line:
            ax.axhline(**self.config.zero_line_kwargs)

        if isinstance(title, str) and title.strip():
            ax.set_title(title, fontsize=fontsize, loc="center")
            if not ax.get_title():  # safety
                ax.set_title(title, fontsize=fontsize, loc="center")

        return ax

    def _split_kwargs(self, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Split kwargs into *data* vs *style* dictionaries."""
        data_kwargs = {k: v for k, v in kwargs.items() if k not in self.STYLE_KEYS}
        style_kwargs = {k: v for k, v in kwargs.items() if k in self.STYLE_KEYS}
        return data_kwargs, style_kwargs

    # ------------------------------------------------------------------
    # Conventional diagnostics plots
    # ------------------------------------------------------------------
    @check_kind("conv")
    def plot_hist_conv(
        self,
        var: str,
        kx: int,
        param: str = "omf",
        bins: int = 50,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Histogram of a conventional diagnostic column.

        Parameters
        ----------
        var : str
            Variable name (e.g., ``'t'``, ``'q'``, ``'uv'``).
        kx : int
            Sensor (data source) index inside the variable dictionary.
        param : str, default: "omf"
            Column in the DataFrame to histogram (legacy or canonical).
        bins : int, default: 50
            Number of histogram bins.
        ax : matplotlib.axes.Axes, optional
            Existing axes. If ``None``, a new one is created.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra arguments forwarded to :meth:`matplotlib.axes.Axes.hist` (e.g.,
            ``color``, ``alpha``), plus style keys (``title``, ``xlabel``, ``ylabel``,
            ``fontsize``, ``zero_line``).

        Returns
        -------
        matplotlib.axes.Axes

        Raises
        ------
        ValueError
            If the variable/kx/column does not exist in the diagnostics.

        Examples
        --------
        >>> p.plot_hist_conv("t", 120, param="omf", bins=60, color="C1",
        ...                  title="T@120 O−F")
        """
        df_dict = self.diag.get_data_frame()
        if var not in df_dict or kx not in df_dict[var]:
            raise ValueError(f"Variable '{var}' or kx '{kx}' not found.")
        df = df_dict[var][kx]

        # Resolve the requested parameter name against available columns
        param_resolved = resolve_col_in_df(df.columns, param, domain="conv")
        if param_resolved not in df.columns:
            raise ValueError(f"Column '{param_resolved}' not in data frame.")

        values = df[param_resolved].dropna().to_numpy()
        ax = self._ensure_ax(ax)

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        for key in ("color", "alpha"):
            if key in style_kwargs:
                data_kwargs[key] = style_kwargs.pop(key)

        _, _, patches = ax.hist(values, bins=bins, **data_kwargs)
        color = data_kwargs.get("color")
        alpha = data_kwargs.get("alpha")
        if (color is not None or alpha is not None) and patches:
            base = patches[0].get_facecolor()
            rgba = mcolors.to_rgba(color if color is not None else base, alpha if alpha is not None else base[3])
            for pch in patches:
                pch.set_facecolor(rgba)

        style_kwargs.setdefault("title", f"Histogram of {param_resolved} for {var} (kx {kx})")
        style_kwargs.setdefault("xlabel", param_resolved)
        style_kwargs.setdefault("ylabel", "Frequency")

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_boxplot_kxs_conv(
        self,
        var: str,
        param: str = "omf",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Boxplots of a column across all KX for a conventional variable.

        Parameters
        ----------
        var : str
            Variable name.
        param : str, default: "omf"
            Column to extract from each KX frame (legacy or canonical).
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra arguments forwarded to :meth:`matplotlib.axes.Axes.boxplot`.
            You may pass ``color`` to recolor box/whisker/caps/median uniformly,
            plus style keys (``title``, ``xlabel``, ``ylabel``, ``fontsize``, etc.).

        Returns
        -------
        matplotlib.axes.Axes

        Raises
        ------
        ValueError
            If the variable or column is not available.

        Examples
        --------
        >>> p.plot_boxplot_kxs_conv("q", param="omf", color="0.3",
        ...                         title="q O−F by KX")
        """
        kxs = self.diag.kx_list(var)
        if not kxs:
            raise ValueError(f"Variable '{var}' not found or has no KX.")
        series_list: List[np.ndarray] = []
        # Keep the resolved name for labels/titles
        param_resolved: Optional[str] = None

        for k in sorted(kxs):
            df = self.diag.frame_conv(var, k)
            pr = resolve_col_in_df(df.columns, param, domain="conv")
            param_resolved = pr  # update (same mapping across KXs ideally)
            series_list.append(df[pr].dropna().to_numpy())

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        if "color" in data_kwargs:
            c = data_kwargs.pop("color")
            data_kwargs.setdefault("boxprops", dict(color=c))
            data_kwargs.setdefault("whiskerprops", dict(color=c))
            data_kwargs.setdefault("capprops", dict(color=c))
            data_kwargs.setdefault("medianprops", dict(color=c))
        ax.boxplot(series_list, **data_kwargs)
        ax.set_xticks(range(1, len(kxs) + 1))
        ax.set_xticklabels(sorted(kxs))

        param_label = param_resolved or param
        style_kwargs.setdefault("title", f"Boxplot of {param_label} for {var} across KX")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", param_label)
        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_observation_counts(
        self,
        varName: str,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Number of observations per KX for a given variable (bars).

        Examples
        --------
        >>> p.plot_observation_counts("t", title="Counts by KX", rotation=45)
        """
        ax = self._ensure_ax(ax)
        data = self.diag.get_data_frame()
        if varName not in data:
            raise ValueError(f"Variable '{varName}' not found in diagnostic data.")

        counts = [(k, df.shape[0]) for k, df in data[varName].items()]
        kx, y = zip(*sorted(counts))
        x = list(range(len(kx)))

        if "color" not in kwargs:
            cmap = kwargs.pop("colormap", cm.Set3)
            kwargs["color"] = [cmap(i % cmap.N) for i in range(len(kx))]

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        ax.bar(x, y, **data_kwargs)
        ax.set_xticks(x)
        ax.set_xticklabels([str(k) for k in kx])

        style_kwargs.setdefault("title", f"Counts for {varName}")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", "Number of Observations")
        style_kwargs.setdefault("rotation", 45)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_kx_count(
        self,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Total observations per KX across all variables (bars).

        Examples
        --------
        >>> p.plot_kx_count(title="Total per KX", rotation=45)
        """
        from collections import Counter

        ax = self._ensure_ax(ax)
        counter = Counter()

        for var_data in self.diag.get_data_frame().values():
            for kx, df in var_data.items():
                counter[kx] += len(df)

        ks, counts = zip(*sorted(counter.items()))
        x = list(range(len(ks)))

        if "color" not in kwargs:
            cmap = kwargs.pop("colormap", cm.Set3)
            kwargs["color"] = [cmap(i % cmap.N) for i in range(len(ks))]

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        ax.bar(x, counts, **data_kwargs)

        ax.set_xticks(x)
        ax.set_xticklabels([str(k) for k in ks])

        style_kwargs.setdefault("title", "Total Observations by KX")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", "Observations")
        style_kwargs.setdefault("rotation", 45)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_variable_count(
        self,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Total observations per variable (bars).

        Examples
        --------
        >>> p.plot_variable_count(title="Total per variable")
        """
        ax = self._ensure_ax(ax)
        var_counts = {
            var: sum(df.shape[0] for df in data.values())
            for var, data in self.diag.get_data_frame().items()
        }
        ks, ys = zip(*var_counts.items())

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        ax.bar(ks, ys, **data_kwargs)

        style_kwargs.setdefault("title", "Total observations per variable")
        style_kwargs.setdefault("xlabel", "Variable")
        style_kwargs.setdefault("ylabel", "Count")

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_kx_count_stacked(
        self,
        vars: Optional[List[str]] = None,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Stacked bar chart of observations per KX, split by variable.

        Examples
        --------
        >>> p.plot_kx_count_stacked(vars=["t","q","uv"], title="Stacked counts")
        """
        ax = self._ensure_ax(ax)

        all_data = self.diag.get_data_frame()
        if vars is None:
            vars = list(all_data.keys())

        # Gather counts per (kx, var)
        kx_counts: Dict[int, Dict[str, int]] = defaultdict(dict)
        for v in vars:
            var_data = all_data.get(v, {})
            for kx, df in var_data.items():
                kx_counts[kx][v] = len(df)

        # Wide DataFrame indexed by kx, columns = variables
        df = pd.DataFrame.from_dict(kx_counts, orient="index").fillna(0).astype(int)
        df = df[sorted(df.columns)]  # stable column order
        df = df.sort_index()         # sort by KX

        ks = list(df.index)
        x = np.arange(len(ks))

        # Default discrete colors for each variable
        cmap = kwargs.pop("colormap", cm.Set3)
        colors = [cmap(i % cmap.N) for i in range(len(df.columns))]

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)

        # Stack bars per variable
        bottoms = np.zeros(len(df))
        for idx, v in enumerate(df.columns):
            heights = df[v].values
            ax.bar(x, heights, bottom=bottoms, label=v, color=colors[idx], **data_kwargs)
            bottoms += heights

        ax.set_xticks(x)
        ax.set_xticklabels([str(k) for k in ks])
        ax.legend(title="Variable", fontsize=10)

        style_kwargs.setdefault("title", "Stacked Observations by KX and Variable")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", "Total Observations")
        style_kwargs.setdefault("rotation", 45)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_spatial_conv(
        self,
        var: str,
        kx: int,
        param: str = "omf",
        mask: Optional[str] = None,
        area: Optional[List[float]] = None,
        lon_wrap: str = "auto",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Spatial scatter of a parameter for a given variable/KX.

        Requires ``cartopy`` to draw coastlines/borders.

        Parameters
        ----------
        var : str
            Variable name (e.g., ``'t'``, ``'q'``, ``'uv'``).
        kx : int
            Data source index within the variable.
        param : str, default: "omf"
            Column used to color the points.
        mask : str, optional
            Pandas query expression to filter the DataFrame (e.g., ``"iusev == 1"``).
        area : list of float, optional
            Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
        lon_wrap : {"auto", "pm180", "360", "none"}, default: "auto"
            Longitude wrapping mode.
        ax : matplotlib.axes.Axes (cartopy), optional
            Existing GeoAxes. If ``None``, a new figure/axes in PlateCarree is created.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.scatter` and style keys.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_spatial_conv("t", 120, param="omf", cmap="coolwarm",
        ...                     area=[-90, -60, 0, 15])
        """
        if not _HAS_CARTOPY:
            raise RuntimeError("Cartopy is required for spatial plotting. Please install cartopy.")

        df = self.diag.get_dataframe(var, kx)

        # Optional query to select a subset
        if mask:
            try:
                df = df.query(mask)
            except Exception as e:
                raise ValueError(f"Invalid mask expression: {mask}") from e

        # Resolve the requested parameter *first* and check required columns
        param_resolved = resolve_col_in_df(df.columns, param, domain="conv")
        for required in ("lat", "lon", param_resolved):
            if required not in df.columns:
                raise ValueError(f"Column '{required}' not found in the DataFrame.")

        # Optional geographic clip
        if area:
            lon1, lat1, lon2, lat2 = area
            df = df[(df["lon"] >= lon1) & (df["lon"] <= lon2) & (df["lat"] >= lat1) & (df["lat"] <= lat2)]

        lats = df["lat"].to_numpy()
        lons = wrap_lon(df["lon"].to_numpy(dtype=float), mode=lon_wrap)
        values = df[param_resolved].to_numpy()

        if ax is None:
            plt.figure(figsize=(12, 6))
            ax = plt.axes(projection=ccrs.PlateCarree())

        # Basic map features
        ax.add_feature(cfeature.COASTLINE, linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, linewidth=0.4)
        ax.add_feature(cfeature.LAND, facecolor="lightgray", zorder=0)
        ax.gridlines(draw_labels=True, linewidth=0.3, linestyle="--", color="gray")

        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        cmap = data_kwargs.pop("cmap", "jet")
        norm = data_kwargs.pop("norm", None)

        sc = ax.scatter(
            lons,
            lats,
            c=values,
            cmap=cmap,
            s=20,
            edgecolor="k",
            linewidth=0.2,
            norm=norm,
            transform=ccrs.PlateCarree(),
            **data_kwargs,
        )

        # Colorbar
        cbar = plt.colorbar(sc, ax=ax, orientation="vertical", shrink=0.8)
        cbar.set_label(param_resolved)

        style_kwargs.setdefault("title", f"Spatial plot of {param_resolved} ({var}, kx={kx})")
        style_kwargs.setdefault("xlabel", "Longitude")
        style_kwargs.setdefault("ylabel", "Latitude")

        ax = self._apply_plot_kwargs(ax, style_kwargs)

        if area:
            ax.set_extent([lon1, lon2, lat1, lat2], crs=ccrs.PlateCarree())

        self._save(ax, savepath)
        return ax

    # ------------------------------------------------------------------
    # Radiance diagnostics plots
    # ------------------------------------------------------------------
    @check_kind("rad")
    def plot_channel_stats_rad(
        self,
        param: str = "omf",
        agg: str = "mean",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Aggregate and plot a radiance metric across channels.

        Parameters
        ----------
        param : str, default: "omf"
            Column present in each per-channel DataFrame (e.g., ``'omf'`` or legacy alias).
        agg : {"mean", "std", "median", ...}, default: "mean"
            Aggregation method applied to the selected column.
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.plot` and style keys. The
            marker defaults to ``'o'`` if not provided.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_channel_stats_rad(param="omf", agg="std", marker="s")
        """
        chan_list = self.diag.get_data_frame().get("dataframes", {}).get("diagbufchan_df", [])
        if not chan_list:
            raise ValueError("No radiance channel data available.")

        # Resolve param against each channel DF as they may differ (legacy vs canonical)
        stats: List[float] = []
        for df in chan_list:
            try:
                param_resolved = resolve_col_in_df(df.columns, param, domain="rad")
            except ValueError:
                continue  # this channel lacks the requested param
            s = df[param_resolved].dropna()
            if not hasattr(s, agg):
                raise ValueError(f"Aggregation '{agg}' is not valid for a pandas Series.")
            stats.append(getattr(s, agg)())

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        data_kwargs.setdefault("marker", "o")
        ax.plot(range(1, len(stats) + 1), stats, **data_kwargs)

        style_kwargs.setdefault("title", f"Radiance channel {agg} of {param}")
        style_kwargs.setdefault("xlabel", "Channel")
        style_kwargs.setdefault("ylabel", f"{agg}({param})")
        style_kwargs.setdefault("zero_line", False)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("rad")
    def plot_omf_distribution_rad(
        self,
        channel_index: int,
        corrected: bool = False,
        bins: int = 50,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Histogram of O–F values for a single radiance channel.

        Parameters
        ----------
        channel_index : int
            Index of the channel within the channel list (0-based).
        corrected : bool, default: False
            If ``True`` and the column ``'omf_nbc'`` exists, use it instead of ``'omf'``.
        bins : int, default: 50
            Number of histogram bins.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_omf_distribution_rad(0, corrected=True, bins=80, color="0.2")
        """
        chan_list = self.diag.get_data_frame().get("dataframes", {}).get("diagbufchan_df", [])
        if channel_index < 0 or channel_index >= len(chan_list):
            raise IndexError("Channel index out of range.")
        df = chan_list[channel_index]

        key = "omf_nbc" if corrected and "omf_nbc" in df.columns else "omf"
        values = df[key].dropna().to_numpy() if key in df.columns else np.asarray([], dtype=float)

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        ax.hist(values, bins=bins, **data_kwargs)

        style_kwargs.setdefault("title", f"O−F distribution for channel {channel_index}")
        style_kwargs.setdefault("xlabel", key)
        style_kwargs.setdefault("ylabel", "Frequency")
        style_kwargs.setdefault("zero_line", False)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    # ------------------------------------------------------------------
    # Backwards compatible aliases (deprecated)
    # ------------------------------------------------------------------
    def pcount(self, *args, **kwargs):
        """Deprecated alias for :meth:`plot_observation_counts`.

        Examples
        --------
        >>> # Old: p.pcount("t")
        >>> p.pcount("t")
        """
        deprecated("pcount() is deprecated; use plot_observation_counts().")
        if args:
            return self.plot_observation_counts(*args, **kwargs)
        var = kwargs.pop("var", None) or kwargs.pop("varName", None)
        if var is None:
            try:
                var = self.diag.get_variables()[0]
            except Exception as e:
                raise TypeError("pcount requires a variable, e.g., pcount('t')") from e
        return self.plot_observation_counts(var, **kwargs)

    def kxcount(self, *args, **kwargs):
        """Deprecated alias for :meth:`plot_kx_count`.

        Examples
        --------
        >>> p.kxcount()
        """
        deprecated("kxcount() is deprecated; use plot_kx_count().")
        return self.plot_kx_count(*args, **kwargs)

    def vcount(self, *args, **kwargs):
        """Deprecated alias for a conventional histogram (use :meth:`plot_hist_conv`).

        Notes
        -----
        Accepts legacy patterns like ``vcount('t', kx=187, param='omf', bins=50)``.

        Examples
        --------
        >>> p.vcount("t", kx=120, param="omf", bins=30, color="C2")
        """
        deprecated("vcount() is deprecated; use plot_hist_conv().")

        var = None
        if args and isinstance(args[0], str):
            var = args[0]
        var = var or kwargs.pop("var", None) or kwargs.pop("varName", None)
        if var is None:
            try:
                var = self.diag.get_variables()[0]
            except Exception as e:
                raise TypeError("vcount requires a variable (e.g., vcount('t', kx=...)).") from e

        kx = kwargs.pop("kx", None)
        if kx is None:
            try:
                kx = int(self.diag.get_kx_list(var)[0])
            except Exception as e:
                raise ValueError(f"No kx available for variable '{var}'.") from e

        # accept legacy 'column'/'col' but normalize to 'param'
        param = kwargs.pop("param", kwargs.pop("column", kwargs.pop("col", "omf")))
        bins = kwargs.pop("bins", 50)
        return self.plot_hist_conv(var, kx, param=param, bins=bins, **kwargs)

    def plot_value_counts(self, *args, **kwargs):
        """Deprecated alias for :meth:`plot_variable_count`.

        Examples
        --------
        >>> p.plot_value_counts()
        """
        deprecated("plot_value_counts() is deprecated; use plot_variable_count() instead")
        return self.plot_variable_count(*args, **kwargs)

    def plot(
        self,
        varName: Optional[str] = None,
        varType: Optional[str] = None,
        param: str = "omf",
        minVal: Optional[float] = None,
        maxVal: Optional[float] = None,
        mask: Optional[str] = None,
        area: Optional[Tuple[float, float, float, float]] = None,
        *,
        channel: Optional[int] = None,
        kx: Optional[int] = None,
        basemap: bool = True,
        resolution: str = "110m",
        cmap: str = "jet",
        s: float = 6.0,
        **scatter_kwargs,
    ):
        """Unified legacy-style plot for both conventional and radiance diagnostics.

        This method preserves the legacy signature while supporting modern kwargs.
        It dispatches by data type and plots a global swath (rad) or point map (conv).

        Parameters
        ----------
        varName : str, optional
            Conventional: the variable key (e.g., ``"t"``, ``"uv"``, ``"ps"``).
            Radiance: label for the title (e.g., sensor name like ``"amsua"``).
        varType : str, optional
            Free text for title (e.g., platform ``"n19"``).
        param : {"obs","omf","oma",...}, default: "omf"
            Radiance: ``"obs"→"tb_obs"``; ``"omf"`` and ``"oma"`` as-is (resolved against DF).
            Conventional: any DF column (legacy or canonical) resolved via :func:`resolve_col_in_df`.
        minVal, maxVal : float, optional
            Colormap bounds (``vmin``, ``vmax``).
        mask : str, optional
            Legacy-like expression, e.g. ``"(nchan==14) & (iuse >= 1 & idqc == 0)"`` or
            ``"(kx==181) & (iuse >= 1)"`` for conventional. Parsed into ``pandas.query``.
        area : tuple of float, optional
            (lon_min, lon_max, lat_min, lat_max) to set extent.
        channel : int, optional
            1-based channel number (radiance). If None, try to parse from ``mask``.
        kx : int, optional
            Conventional KX. If None, try to parse from ``mask`` or take the first non-empty.
        basemap : bool, default: True
            Add Cartopy basemap if available.
        resolution : {"110m","50m","10m"}, default: "110m"
            NaturalEarth scale for the basemap.
        cmap : str, default: "jet"
            Matplotlib colormap name.
        s : float, default: 6.0
            Scatter marker size.
        **scatter_kwargs
            Forwarded to ``Axes.scatter``.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> # Radiance:
        >>> p.plot(varName="amsua", varType="n19", param="omf", channel=5,
        ...        cmap="coolwarm", s=4.0)
        >>> # Conventional:
        >>> p.plot(varName="t", kx=120, param="omf", cmap="coolwarm")
        """
        data_type = self.diag.get_data_type()  # 1=conv, else=rad (as per reader)
        # ------------------------------------------------------------------ RAD
        if data_type != 1:
            # Resolve channel (1-based)
            ch = channel or extract_int(mask, r"nchan\s*==\s*(\d+)", default=1)
            ch_idx = ch - 1

            df_all = self.diag.get_data_frame()["dataframes"]
            chan_list = df_all["diagbufchan_df"]
            if ch_idx < 0 or ch_idx >= len(chan_list):
                raise ValueError(f"Invalid channel {ch}; file has {len(chan_list)} channels.")

            # Merge geometry (lat/lon) + selected channel (no replication in memory)
            df_geo = df_all["diagbuf_df"][["lat", "lon"]].reset_index(drop=True)
            df_ch = chan_list[ch_idx].reset_index(drop=True)
            df = pd.concat([df_geo, df_ch], axis=1)

            # Map legacy-friendly 'param' to actual radiance column
            radiance_map = {"obs": "tb_obs", "omf": "omf", "oma": "oma"}
            param_candidate = radiance_map.get(param.lower(), param)
            # IMPORTANT: resolve in *radiance* domain
            param_resolved = resolve_col_in_df(df.columns, param_candidate, domain="rad")
            if param_resolved not in df.columns:
                raise ValueError(f"Unsupported param='{param}' for radiance (resolved='{param_resolved}')")

            # Apply mask (remove nchan==N since already selected)
            if mask:
                q = mask_to_query(mask, drop_token="nchan")
                df = df.query(q)

            title_left = f"Radiance - {str(varName or '').upper()} - {str(varType or '').upper()}."
            title_center = f"Channel = {ch}"
            cycle_dt, cycle_token = get_cycle(self.diag)
            cycle = cycle_token or ""   # empty string if nothing found

        # --------------------------------------------------------------- CONV
        else:
            # Resolve variable/kx
            var = varName or self.diag.get_variables()[0]
            if kx is None:
                kx = extract_int(mask, r"kx\s*==\s*(\d+)", default=None)
            df_map = self.diag.get_data_frame()[var]
            if kx is None:
                # pick first non-empty
                kx = next((int(k) for k, v in df_map.items() if hasattr(v, "empty") and not v.empty), None)
            if kx is None or kx not in df_map:
                raise ValueError(f"KX not found (var={var}, kx={kx}).")
            df = df_map[kx]
            if "lat" not in df.columns or "lon" not in df.columns:
                raise ValueError("Conventional DF missing 'lat'/'lon' columns.")

            # Resolve 'param' in *conventional* domain
            param_resolved = resolve_col_in_df(df.columns, param, domain="conv")
            if param_resolved not in df.columns:
                raise ValueError(f"param='{param}' not found in conventional columns: {list(df.columns)}")

            if mask:
                q = mask_to_query(mask, drop_token="kx")
                df = df.query(q)

            title_left = f"Conventional - {var.upper()} (kx={kx})"
            title_center = param_resolved
            cycle_dt, cycle_token = get_cycle(self.diag)
            cycle = cycle_token or ""   # empty string if nothing found

        # --------------------------------------------------------------- PLOT
        ax, transform = make_axes(basemap=basemap, resolution=resolution)
        sc = ax.scatter(
            df["lon"], df["lat"], c=df[param_resolved],
            s=s, cmap=cmap, transform=transform, **scatter_kwargs
        )
        cb = plt.colorbar(sc, ax=ax, pad=0.02)
        cb.set_label(nice_label(param_resolved))
        if (minVal is not None) or (maxVal is not None):
            sc.set_clim(vmin=minVal, vmax=maxVal)

        if area:
            lon_min, lon_max, lat_min, lat_max = area
            if transform is not None:
                ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=transform)
            else:
                ax.set_xlim(lon_min, lon_max)
                ax.set_ylim(lat_min, lat_max)

        # Titles (left/center/right)
        ax.set_title(title_center, loc="center", fontsize=11, fontweight="bold")
        ax.set_title(title_left,   loc="left",   fontsize=9)
        ax.set_title(cycle,        loc="right",  fontsize=9)

        plt.tight_layout()
        return ax

    # ------------------------------------------------------------------
    # ptmap (conv) — multi-KX, legacy-style, fast
    # ------------------------------------------------------------------
    @check_kind("conv")
    def plot_ptmap(
        self,
        varName: str,
        varType: int | list[int] | None = None,
        *,
        mask: str | None = None,
        area: list[float] | None = None,
        backend: str = "auto",
        world_path: str | None = None,
        style: str = "seaborn-v0_8",
        legend: bool | None = None,
        strict: bool = False,
        verbose: bool = True,
        ax: plt.Axes | None = None,
        lon_wrap: str = "auto",
        **kwargs,
    ) -> plt.Axes:
        """Point-map by KX for a conventional variable.

        Examples
        --------
        >>> p.plot_ptmap("t", varType=[120,130], mask="iuse >= 1", legend=True)
        """
        # (1) style and visual defaults
        plt.style.use(style)
        kwargs.setdefault("alpha", 0.5)
        kwargs.setdefault("marker", "*")
        kwargs.setdefault("markersize", 5)
        kwargs.setdefault("linewidth", 1)
        want_legend = True if legend is None else bool(legend)

        # (2) resolve required vs available KX
        req = (
            _available_kx(self.diag, varName)
            if varType is None
            else ([int(varType)] if isinstance(varType, int) else [int(k) for k in varType])
        )
        avail = set(_available_kx(self.diag, varName))
        missing = [k for k in req if k not in avail]
        kxs = [k for k in req if k in avail]
        if missing and strict:
            raise ValueError(f"[ptmap] missing KX for var={varName}: {missing}. Available: {sorted(avail)[:30]}")
        if missing and verbose:
            print(f"[ptmap] skipping missing KX for {varName}: {missing}")
        if not kxs:
            raise ValueError(f"[ptmap] no KX to plot for var={varName}. Available: {sorted(avail)[:30]}")

        # (3) prepare basemap and plotting function
        use = backend
        if use == "auto":
            try:
                import geopandas  # noqa: F401
                use = "gpd"
            except Exception:
                use = "cartopy"

        if use == "gpd":
            ax = ensure_axes_gpd(ax, area, world_path=world_path)

            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)
        else:
            ax, _ = ensure_axes_cartopy(ax, area)

            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)

        # (4) iterate KX, apply mask, and plot
        patches: List = []
        for i, kx in enumerate(kxs):
            df = _get_conv_df(self.diag, varName, kx)
            if mask:
                try:
                    df = df.query(mask)
                except Exception:
                    continue
            if df.empty or not {"lat", "lon"}.issubset(df.columns):
                continue

            x = wrap_lon(df["lon"].to_numpy(dtype=float), mode=lon_wrap)
            y = df["lat"].to_numpy(dtype=float)
            color = cmap_hex(i, len(kxs), "Paired")
            label = f"{varName}-{kx}"
            from matplotlib.patches import Patch

            patches.append(Patch(color=color, label=wrap_label(label, 30)))
            scatter_fn(x, y, color)

        if want_legend and patches:
            plt.subplots_adjust(bottom=0.30)
            ax.legend(
                handles=patches,
                loc="upper center",
                bbox_to_anchor=(0.5, -0.08),
                frameon=False,
                ncol=4,
                prop={"size": 9},
                labelspacing=1.0,
            )

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        return ax

    # ------------------------------------------------------------------
    # pvmap (conv) — per variable, with `mask` applied to all KX
    # ------------------------------------------------------------------
    @check_kind("conv")
    def plot_pvmap(
        self,
        varName: list[str] | str | None = None,
        *,
        mask: str | None = None,
        area: List[float] | None = None,
        backend: str = "auto",
        world_path: str | None = None,
        style: str = "seaborn-v0_8",
        legend: bool | None = None,
        ax: plt.Axes | None = None,
        lon_wrap: str = "auto",
        verbose: bool = True,
        **kwargs,
    ) -> plt.Axes:
        """Point-map grouped by variable (sums all KX per variable).

        Examples
        --------
        >>> p.plot_pvmap(["t","q"], mask="iuse>=1 and idqc==0", legend=True)
        """
        plt.style.use(style)
        kwargs.setdefault("alpha", 0.5)
        kwargs.setdefault("marker", "*")
        kwargs.setdefault("markersize", 5)
        kwargs.setdefault("linewidth", 1)
        want_legend = True if legend is None else bool(legend)

        use = backend
        if use == "auto":
            try:
                import geopandas  # noqa: F401
                use = "gpd"
            except Exception:
                use = "cartopy"

        if use == "gpd":
            ax = ensure_axes_gpd(ax, area, world_path=world_path)
            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)
        else:
            ax, _ = ensure_axes_cartopy(ax, area)
            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)

        if varName is None:
            vars_all: list[str] = list(getattr(self.diag, "get_variables", lambda: [])())
            def _total(v: str) -> int:
                cnt = 0
                for kx in _available_kx(self.diag, v):
                    try:
                        cnt += len(_get_conv_df(self.diag, v, kx))
                    except Exception:
                        pass
                return cnt
            var_list = sorted(vars_all, key=_total, reverse=True)
        else:
            var_list = varName if isinstance(varName, list) else [varName]

        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']

        patches: list = []
        for i, var in enumerate(var_list):
            frames: list[pd.DataFrame] = []
            for kx in _available_kx(self.diag, var):
                try:
                    df = _get_conv_df(self.diag, var, kx)
                except Exception:
                    continue
                if mask:
                    try:
                        df = df.query(mask)
                    except Exception:
                        continue
                if df.empty or not {"lat", "lon"}.issubset(df.columns):
                    continue
                frames.append(df[["lon", "lat"]])

            if not frames:
                if verbose:
                    print(f"[pvmap] no points for var={var} (after mask/lon check)")
                continue

            dfv = pd.concat(frames, ignore_index=True)
            x = wrap_lon(dfv["lon"].to_numpy(dtype=float), mode=lon_wrap)
            y = dfv["lat"].to_numpy(dtype=float)

            color = colors[i % len(colors)]
            patches.append(plt.matplotlib.patches.Patch(color=color, label=var))
            scatter_fn(x, y, color)

        if want_legend and patches:
            ax.legend(
                handles=patches, numpoints=1, loc="best",
                bbox_to_anchor=(1.1, 0.6), frameon=False, ncol=1, prop={"size": 10}
            )

        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        return ax

    # -----------------------------
    # NEW PLOTS - CONVENTIONAL
    # -----------------------------
    def plot_spatial_conv_auto(self, var: str, kx: int, prefer=None, **kwargs):
        """Quick spatial map for the *first available* conventional parameter.

        Parameters
        ----------
        var : str
        kx : int
        prefer : list of str, optional
            Ordered list of parameter candidates. Defaults to
            ``["oma", "omf", "obs", "ges", "hofx"]``.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_spatial_conv_auto("t", 120, area=[-90,-60,0,15])
        """
        prefer = prefer or ["oma", "omf", "obs", "ges", "hofx"]
        df = self.diag.frame_conv(var, kx)
        cols = set(df.columns)
        param_found = next((c for c in prefer if c in cols), None)
        if param_found is None:
            raise ValueError(f"None of {prefer} found in columns: {sorted(cols)}")
        return self.plot_spatial_conv(var, kx, param=param_found, **kwargs)

    @check_kind("conv")
    def plot_coverage_conv(self, var: str, kx: int, s: int = 2):
        """Quick coverage map (lat/lon) for conventional diagnostics.

        Examples
        --------
        >>> p.plot_coverage_conv("t", 120, s=1)
        """
        df = self.diag.frame_conv(var, kx)
        need = {"lat", "lon"}
        if not need <= set(df.columns):
            raise ValueError(f"Missing columns {need} in {sorted(df.columns)}")
        ax = plt.gca()
        ax.scatter(df["lon"], df["lat"], s=s)
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
        ax.set_title(f"Coverage ({var}, kx={kx})")
        return ax

    @check_kind("conv")
    def plot_scatter_conv(self, var: str, kx: int, x: str, y: str, s: int = 3, **kwargs):
        """Generic scatter for conventional diagnostics (e.g., ``hofx`` vs ``omf``).

        Parameters
        ----------
        var : str
        kx : int
        x, y : str
            Column names (legacy or canonical). Resolved against DataFrame.
        s : int, default 3
            Marker size.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_scatter_conv("t", 120, x="hofx", y="omf", s=2, alpha=0.6)
        """
        df = self.diag.frame_conv(var, kx)
        x_res = resolve_col_in_df(df.columns, x, domain="conv")
        y_res = resolve_col_in_df(df.columns, y, domain="conv")
        need = {x_res, y_res}
        if not need <= set(df.columns):
            raise ValueError(f"Missing {need} in {sorted(df.columns)}")
        ax = df.plot.scatter(x=x_res, y=y_res, s=s, **kwargs)
        ax.set_title(f"{y_res} vs {x_res} ({var}, kx={kx})")
        return ax

    @check_kind("conv")
    def plot_box_by_kx(self, var: str, param: str, kx_limit: int | None = None):
        """Boxplot of a parameter by KX (for a single variable).

        Parameters
        ----------
        var : str
        param : str
            Column to plot (legacy or canonical).
        kx_limit : int, optional
            If provided, limit the number of KX boxes.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_box_by_kx("q", param="omf", kx_limit=10)
        """
        kxs = self.diag.kx_list(var)
        if kx_limit:
            kxs = kxs[:kx_limit]
        data, labels = [], []
        param_label: Optional[str] = None
        for k in kxs:
            df = self.diag.frame_conv(var, k)
            pr = resolve_col_in_df(df.columns, param, domain="conv")
            param_label = pr
            if pr in df.columns and len(df[pr]) > 0:
                data.append(df[pr].values)
                labels.append(str(k))
        if not data:
            raise ValueError(f"No data for '{param}' in var={var}")
        ax = plt.gca()
        ax.boxplot(data, labels=labels, showfliers=False)
        ax.set_title(f"{param_label or param} by KX — {var}")
        ax.set_xlabel("KX"); ax.set_ylabel(param_label or param)
        return ax

    # -----------------------------
    # NEW PLOTS - RADIANCE
    # -----------------------------
    @check_kind("rad")
    def plot_hist_channel(self, channel: int, param: str | None = None, bins: int = 50):
        """Histogram of a parameter for a single radiance channel.

        Parameters
        ----------
        channel : int
            1-based channel number.
        param : str, optional
            If ``None``, prefer ``"omf"`` then fallback to ``"oma"``.
        bins : int, default 50

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_hist_channel(5, param="omf", bins=40)
        """
        df = self.diag.frame_channel(channel)
        if param is None:
            # prefer 'omf', fallback 'oma'
            param_candidate = "omf" if "omf" in df.columns else ("oma" if "oma" in df.columns else None)
            if param_candidate is None:
                raise ValueError(f"None of ['omf','oma'] available in {sorted(df.columns)}")
            param_resolved = param_candidate
        else:
            param_resolved = resolve_col_in_df(df.columns, param, domain="rad")

        ax = df[param_resolved].plot.hist(bins=bins)
        ax.set_title(f"Histogram of {param_resolved} (channel {channel})")
        ax.set_xlabel(param_resolved); ax.set_ylabel("count")
        return ax

    def plot_scatter_channel(self, channel: int, x: str, y: str, s: int = 3, **kwargs):
        """Generic scatter for a radiance channel (e.g., ``omf`` vs ``sat_zen``).

        Parameters
        ----------
        channel : int
        x, y : str
            Column names (legacy or canonical). Resolved per-channel.
        s : int, default 3

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_scatter_channel(7, x="omf", y="sat_zen", s=2, alpha=0.5)
        """
        # Bring DF first (may be legacy-named)
        df = self.diag.bring(channel, [x, y])

        # Resolve *to the actual column names present in df*
        x_res = resolve_col_in_df(df.columns, x, domain="rad")
        y_res = resolve_col_in_df(df.columns, y, domain="rad")

        ax = df.plot.scatter(x=x_res, y=y_res, s=s, **kwargs)
        ax.set_title(f"{y} vs {x} (channel {channel})")  # keep semantic labels for the title
        return ax

    @check_kind("rad")
    def plot_abs_omf_map_channel(self, channel: int, param: str | None = None, s: int = 3):
        """Quick map of absolute O–F (or fallback to O–A) per channel.

        Parameters
        ----------
        channel : int
        param : str, optional
            If provided, resolved against DF. If ``None``, prefer ``"omf"`` then ``"oma"``.
        s : int, default 3
            Marker size.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_abs_omf_map_channel(10, s=1)
        """
        df = self.diag.bring(channel, ["lat", "lon"])
        if {"lat", "lon"} - set(df.columns):
            raise ValueError("lat/lon missing in the DataFrame")

        if param is None:
            param_resolved = None
            for cand in ("omf", "oma"):
                try:
                    param_resolved = resolve_col_in_df(df.columns, cand, domain="rad")
                    break
                except ValueError:
                    continue
            if param_resolved is None:
                raise ValueError("neither 'omf' nor 'oma' available for mapping")
        else:
            param_resolved = resolve_col_in_df(df.columns, param, domain="rad")

        ax = plt.gca()
        sc = ax.scatter(df["lon"], df["lat"], s=s, c=np.abs(df[param_resolved].values))
        ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
        ax.set_title(f"|{param_resolved}| map (channel {channel})")
        plt.colorbar(sc, label=f"|{param_resolved}|")
        return ax

    def plot_qc_hist_channel(self, channel: int, param: str = "qcflag"):
        """Bar distribution of a QC-like column for a radiance channel.

        Parameters
        ----------
        channel : int
        param : str, default "qcflag"
            Column name (legacy/canonical) resolved per-channel.

        Returns
        -------
        matplotlib.axes.Axes

        Examples
        --------
        >>> p.plot_qc_hist_channel(4, param="idqc")
        """
        df = self.diag.frame_channel(channel)
        param_resolved = resolve_col_in_df(df.columns, param, domain="rad")
        if param_resolved not in df.columns:
            raise ValueError(f"Column '{param_resolved}' missing in {sorted(df.columns)}")
        counts = df[param_resolved].value_counts().sort_index()
        ax = counts.plot.bar()
        ax.set_xlabel(param_resolved); ax.set_ylabel("count")
        ax.set_title(f"{param_resolved} distribution (channel {channel})")
        return ax

