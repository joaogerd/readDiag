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

try:
    import cartopy.crs as ccrs
    import cartopy.feature as cfeature
    _HAS_CARTOPY = True
except Exception:  # cartopy opcional
    _HAS_CARTOPY = False

from ..surface.access_adapter import AccessAdapter
from ..surface.adapters.legacy import LegacyCompatAdapter
from ..surface.api import DiagnosticAPI
from ..io.reader import diagAccess as _DiagAccess
from .style import PlotConfig
from ..utils import deprecated, check_kind
from ..utils import extract_int, mask_to_query, nice_label, guess_cycle_token
try:
    from .._utils import get_cycle  # shim to modern utils
except Exception:
    def get_cycle(obj):
        try:
            m = getattr(obj, 'meta', lambda: None)()
            return getattr(m, 'date', None)
        except Exception:
            return None
from ._utils import wrap_lon, cmap_hex, ensure_axes_gpd, ensure_axes_cartopy, make_axes, wrap_label

def _get_conv_df(diag, var: str, kx: int) -> pd.DataFrame:
    return diag.get_dataframe(var, kx) if hasattr(diag, "get_dataframe") else diag.get_data_frame()[var][kx]

def _available_kx(diag, var: str) -> list[int]:
    """Lista de KX existentes para a variável."""
    try:
        return [int(k) for k in diag.get_kx_list(var)]
    except Exception:
        d = diag.get_data_frame().get(var, {})
        return [int(k) for k in getattr(d, "keys", lambda: [])()]
    
# ---------------------------------------------------------------------------
# Apply a global/default plotting configuration at import time
# (keeps figures visually consistent unless the user provides their own config)
# ---------------------------------------------------------------------------
_default_config = PlotConfig()
plt.style.use(_default_config.style)
mpl.rcParams.update(_default_config.rc_params)


class diagPlotter:
    """Helper to generate Matplotlib figures from ``diagAccess`` objects.

    The plotter automatically detects whether the diagnostic is **conventional**
    or **radiance** and exposes convenience methods for common visualizations
    (histograms, counts, per-channel stats, etc.). Styling is centralized via a
    :class:`~readDiag.style.PlotConfig`, and per-plot overrides can be provided
    through keyword arguments.

    Parameters
    ----------
    diag : diagAccess
        A diagnostic object already loaded by :class:`~readDiag.reader.diagAccess`.
    config : PlotConfig, optional
        Custom plotting style. If omitted, a global default is used.

    Raises
    ------
    TypeError
        If ``diag`` is not an instance of :class:`~readDiag.reader.diagAccess`.

    Notes
    -----
    - **Graphical kwargs** (e.g., ``color``, ``alpha``, ``marker``, ``linewidth``)
      are forwarded directly to Matplotlib calls.
    - **Style kwargs** (``title``, ``xlabel``, ``ylabel``, ``rotation``,
      ``fontsize``, ``zero_line``) are handled by :meth:`_apply_plot_kwargs`.
    - All methods return the Matplotlib :class:`~matplotlib.axes.Axes` instance
      for further customization or testing.

    Examples
    --------
    >>> from readDiag.reader import diagAccess
    >>> from readDiag.plotting import diagPlotter
    >>> d = diagAccess("path/to/diag_conv_01.2020010100")
    >>> p = diagPlotter(d)
    >>> ax = p.plot_hist_conv("t", 120, bins=40, color="blue", title="Temp Histogram")
    >>> ax = p.plot_kx_count(title="Observations by KX")
    """

    # Keys that are *style* (handled by _apply_plot_kwargs) and not forwarded
    # to Matplotlib plotting functions directly.
    STYLE_KEYS = {"title", "xlabel", "ylabel", "rotation", "fontsize", "zero_line"}

    def __init__(self, diag, config: Optional[PlotConfig] = None):
        # 1) Se já expõe a surface completa, usa direto
        _has_surface = all(
            callable(getattr(diag, name, None))
            for name in ("meta", "kind", "variables", "kx_list", "frame_conv",
                         "channels", "frame_channel", "table")
        )
        if _has_surface:
            self.diag = diag
        else:
            # 2) Se parece com o backend moderno COMPLETO (diagAccess real),
            #    só então usa AccessAdapter. Exigimos também 'file_name'.
            if isinstance(diag, _DiagAccess) and callable(getattr(diag, "get_file_info", None)) \
               and hasattr(diag, "file_name"):
                try:
                    self.diag = AccessAdapter(diag)
                except Exception:
                    # Falhou? Adapta via legado.
                    self.diag = LegacyCompatAdapter(diag)
            else:
                # 3) Fakes/mocks/legados → LegacyCompatAdapter
                self.diag = LegacyCompatAdapter(diag)

        # Após o embrulho, sempre temos .kind()
        self.kind = self.diag.kind()

        self.config = config or _default_config
    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_ax(ax: Optional[plt.Axes]) -> plt.Axes:
        """Return an existing ``Axes`` or create a fresh one.

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Target axes. If ``None``, a new figure and axes are created.

        Returns
        -------
        matplotlib.axes.Axes
            The provided or newly created axes.
        """
        if ax is None:
            fig, ax = plt.subplots()
        return ax

    @staticmethod
    def _save(ax: plt.Axes, savepath: Optional[str]) -> None:
        """Save the figure to disk if a path is provided.

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Axes containing the figure.
        savepath : str, optional
            Destination file path. If ``None``, nothing is saved.
        """
        if not savepath:
            return
        p = Path(savepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        ax.get_figure().savefig(p, dpi=150, bbox_inches="tight")

    def _apply_plot_kwargs(self, ax: plt.Axes, style_kwargs: Dict[str, Any]) -> plt.Axes:
        """Apply axis-level styling (titles, labels, ticks, reference lines).

        Only cosmetic kwargs are handled here. Graphical properties should be
        passed directly to the plotting calls (e.g., ``color``, ``alpha``, ``bins``).

        Parameters
        ----------
        ax : matplotlib.axes.Axes
            Target axes to style.
        style_kwargs : dict
            Supported keys are:

            ``title`` : str
                Plot title.
            ``xlabel`` / ``ylabel`` : str
                Axis labels.
            ``rotation`` : int, default: 0
                Rotation for x tick labels.
            ``fontsize`` : int, default: 10
                Font size for labels and titles.
            ``zero_line`` : bool, default: True
                Draw a thin horizontal line at y=0.

        Returns
        -------
        matplotlib.axes.Axes
            The styled axes.
        """
        # Defensive copy so callers can reuse their dicts
        style_kwargs = dict(style_kwargs)

        title = style_kwargs.get("title")
        xlabel = style_kwargs.get("xlabel")
        ylabel = style_kwargs.get("ylabel")
        rotation = style_kwargs.get("rotation", 0)
        fontsize = style_kwargs.get("fontsize", 10)
        zero_line = style_kwargs.get("zero_line", True)

        # Apply global style (grid, spines, facecolor, etc.)
        self.config.apply_to_axes(ax)

        # Labels
        if isinstance(xlabel, str):
            ax.set_xlabel(xlabel, fontsize=fontsize)
        if isinstance(ylabel, str):
            ax.set_ylabel(ylabel, fontsize=fontsize)

        # Tick label cosmetics
        for lbl in ax.get_xticklabels():
            lbl.set_rotation(rotation)
            lbl.set_fontsize(fontsize)

        # Optional reference line at y = 0
        if zero_line:
            ax.axhline(**self.config.zero_line_kwargs)

        # Title last (explicitly centered so tests using get_title() work
        # regardless of rcParams like axes.titlelocation)
        if isinstance(title, str) and title.strip():
            ax.set_title(title, fontsize=fontsize, loc="center")
            # Safety net: if another hook cleared the title, re-apply it
            if not ax.get_title():
                ax.set_title(title, fontsize=fontsize, loc="center")

        return ax

    def _split_kwargs(self, kwargs: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Split kwargs into *data* vs *style* dictionaries.

        Parameters
        ----------
        kwargs : dict
            Arbitrary keyword arguments passed to a plotting method.

        Returns
        -------
        data_kwargs : dict
            Forwarded directly to Matplotlib plot calls (e.g., ``color``, ``alpha``, ``bins``).
        style_kwargs : dict
            Consumed by :meth:`_apply_plot_kwargs` (``title``, ``xlabel``, etc.).
        """
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
        col: str = "omf",
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
        col : str, default: "omf"
            Column in the DataFrame to histogram.
        bins : int, default: 50
            Number of bins.
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
            The axes containing the histogram.

        Raises
        ------
        ValueError
            If the variable/kx/column does not exist in the diagnostics.
        """
        df_dict = self.diag.get_data_frame()
        if var not in df_dict or kx not in df_dict[var]:
            raise ValueError(f"Variable '{var}' or kx '{kx}' not found.")
        df = df_dict[var][kx]
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not in data frame.")

        values = df[col].dropna().to_numpy()
        ax = self._ensure_ax(ax)

        # Separate kwargs into data-vs-style; ensure color/alpha stay with data
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        for key in ("color", "alpha"):
            if key in style_kwargs:
                data_kwargs[key] = style_kwargs.pop(key)

        # Plot and capture patches to enforce uniform facecolor/alpha (when given)
        _, _, patches = ax.hist(values, bins=bins, **data_kwargs)
        color = data_kwargs.get("color")
        alpha = data_kwargs.get("alpha")
        if color is not None or alpha is not None:
            base = patches[0].get_facecolor()
            rgba = mcolors.to_rgba(color if color is not None else base, alpha if alpha is not None else base[3])
            for p in patches:
                p.set_facecolor(rgba)

        # Default style
        style_kwargs.setdefault("title", f"Histogram of {col} for {var} (kx {kx})")
        style_kwargs.setdefault("xlabel", col)
        style_kwargs.setdefault("ylabel", "Frequency")

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @check_kind("conv")
    def plot_boxplot_kxs_conv(
        self,
        var: str,
        col: str = "omf",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Boxplots of a column across all KX for a conventional variable.

        Parameters
        ----------
        var : str
            Variable name.
        col : str, default: "omf"
            Column to extract from each KX frame.
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
            The axes with the boxplots.

        Raises
        ------
        ValueError
            If the variable or column is not available.
        """
        kxs = self.diag.kx_list(var)
        if not kxs:
            raise ValueError(f"Variable '{var}' not found or has no KX.")
        series_list: List[np.ndarray] = []
        for k in sorted(kxs):
            df = self.diag.frame_conv(var, k)
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not in data for kx {k}.")
            series_list.append(df[col].dropna().to_numpy())

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

        style_kwargs.setdefault("title", f"Boxplot of {col} for {var} across kxs")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", col)
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

        Parameters
        ----------
        varName : str
            Variable name (e.g., ``'t'``, ``'q'``, ``'uv'``).
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra arguments forwarded to :meth:`matplotlib.axes.Axes.bar` (e.g.,
            ``color``), plus style keys. If ``color`` is not provided, a discrete
            colormap (``Set3``) is used to generate bar colors.

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the bar chart.
        """
        ax = self._ensure_ax(ax)
        data = self.diag.get_data_frame()
        if varName not in data:
            raise ValueError(f"Variable '{varName}' not found in diagnostic data.")

        counts = [(k, df.shape[0]) for k, df in data[varName].items()]
        kx, y = zip(*sorted(counts))
        x = list(range(len(kx)))

        # Auto color per bar if not provided
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

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.bar` (e.g., ``color``), plus
            style keys (``title``, ``xlabel``, ``ylabel``, etc.). If ``color`` is
            not passed, a categorical colormap (``Set3``) is used.

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the bar chart.
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

        Parameters
        ----------
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.bar` and style keys.

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the bar chart.
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

        Parameters
        ----------
        vars : list of str, optional
            Variables to include (e.g., ``['t', 'q', 'ps']``). If ``None``,
            all variables found in the diagnostic are used.
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.bar` and style keys.

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the stacked bars.
        """
        ax = self._ensure_ax(ax)

        all_data = self.diag.get_data_frame()
        if vars is None:
            vars = list(all_data.keys())

        # Gather counts per (kx, var)
        kx_counts: Dict[int, Dict[str, int]] = defaultdict(dict)
        for var in vars:
            var_data = all_data.get(var, {})
            for kx, df in var_data.items():
                kx_counts[kx][var] = len(df)

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
        for idx, var in enumerate(df.columns):
            heights = df[var].values
            ax.bar(x, heights, bottom=bottoms, label=var, color=colors[idx], **data_kwargs)
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
            Column to use for coloring the points (e.g., ``'omf'``, ``'obs'``).
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
            The GeoAxes with the scatter plot.
        """
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        df = self.diag.get_dataframe(var, kx)

        # Optional query to select a subset
        if mask:
            try:
                df = df.query(mask)
            except Exception as e:
                raise ValueError(f"Invalid mask expression: {mask}") from e

        # Required columns
        for col in ["lat", "lon", param]:
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not found in the DataFrame.")

        # Optional geographic clip
        if area:
            lon1, lat1, lon2, lat2 = area
            df = df[(df["lon"] >= lon1) & (df["lon"] <= lon2) & (df["lat"] >= lat1) & (df["lat"] <= lat2)]

        lats = df["lat"].to_numpy()
        lons = wrap_lon(df["lon"].to_numpy(dtype=float), mode=lon_wrap)
        values = df[param].to_numpy()

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
            **data_kwargs,
        )

        # Colorbar
        cbar = plt.colorbar(sc, ax=ax, orientation="vertical", shrink=0.8)
        cbar.set_label(param)

        style_kwargs.setdefault("title", f"Spatial plot of {param} ({var}, kx={kx})")
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
        metric: str = "omf",
        agg: str = "mean",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
        **kwargs,
    ) -> plt.Axes:
        """Aggregate and plot a radiance metric across channels.

        Parameters
        ----------
        metric : str, default: "omf"
            Column present in each per-channel DataFrame (e.g., ``'omf'``).
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
            The axes with the line plot.
        """
        chan_list = self.diag.get_data_frame().get("dataframes", {}).get("diagbufchan_df", [])
        if not chan_list:
            raise ValueError("No radiance channel data available.")

        stats = [getattr(df[metric].dropna(), agg)() for df in chan_list if metric in df.columns]

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        data_kwargs.setdefault("marker", "o")
        ax.plot(range(1, len(stats) + 1), stats, **data_kwargs)

        style_kwargs.setdefault("title", f"Radiance channel {agg} of {metric}")
        style_kwargs.setdefault("xlabel", "Channel")
        style_kwargs.setdefault("ylabel", f"{agg}({metric})")
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
            Index of the channel within the channel list.
        corrected : bool, default: False
            If ``True`` and the column ``'omf_nbc'`` exists, use it instead of ``'omf'``.
        bins : int, default: 50
            Number of histogram bins.
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        savepath : str, optional
            If provided, the figure is saved to this path.
        **kwargs
            Extra args to :meth:`matplotlib.axes.Axes.hist` and style keys.

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the histogram.
        """
        chan_list = self.diag.get_data_frame().get("dataframes", {}).get("diagbufchan_df", [])
        if channel_index < 0 or channel_index >= len(chan_list):
            raise IndexError("Channel index out of range.")
        df = chan_list[channel_index]

        key = "omf_nbc" if corrected and "omf_nbc" in df.columns else "omf"
        values = df[key].dropna().to_numpy()

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)
        ax.hist(values, bins=bins, **data_kwargs)

        style_kwargs.setdefault("title", f"O-F distribution for channel {channel_index}")
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

        Notes
        -----
        Accepts positional or keyword variable names for smoother compatibility.
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
        """Deprecated alias for :meth:`plot_kx_count`."""
        deprecated("kxcount() is deprecated; use plot_kx_count().")
        return self.plot_kx_count(*args, **kwargs)

    def vcount(self, *args, **kwargs):
        """Deprecated alias for a conventional histogram (use :meth:`plot_hist_conv`).

        Notes
        -----
        Accepts legacy patterns like ``vcount('t', kx=187, column='omf', bins=50)``.
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

        col = kwargs.pop("column", kwargs.pop("col", "omf"))
        bins = kwargs.pop("bins", 50)
        return self.plot_hist_conv(var, kx, col=col, bins=bins, **kwargs)

    def plot_value_counts(self, *args, **kwargs):
        """Deprecated alias for :meth:`plot_variable_count`."""
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

        Args:
            varName: For conventional, the variable key (e.g., "t", "uv", "ps").
                For radiance, a label for the title (e.g., "amsua").
            varType: Free text for title (e.g., "n19").
            param: Column to color. For radiance accepts {"obs","omf","oma"} mapping to
                {"tb_obs","omf","oma"}. For conventional, must exist in the DataFrame
                (typical: "omf", "oma", "end_err", etc.).
            minVal: Colormap min bound.
            maxVal: Colormap max bound.
            mask: Legacy-like expression, e.g. "(nchan==14) & (iuse >= 1 & idqc == 0)"
                or "(kx==181) & (iuse >= 1)" for conventional. Parsed into pandas.query.
            area: (lon_min, lon_max, lat_min, lat_max) to set extent.
            channel: 1-based channel number (radiance). If None, will try parse from mask.
            kx: KX code (conventional). If None, will try parse from mask.
            basemap: Add Cartopy basemap (if available). Default True.
            resolution: Cartopy NaturalEarth scale ("110m"/"50m"/"10m").
            cmap: Matplotlib colormap.
            s: Scatter marker size.
            **scatter_kwargs: Forwarded to plt.scatter.

        Returns:
            matplotlib.axes.Axes: The axes used for the plot.

        Raises:
            ValueError: When required columns are missing or selection is invalid.
        """
        data_type = self.diag.get_data_type()  # 1=conv, else=rad (conforme teu reader)
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

            col_map = {"obs": "tb_obs", "omf": "omf", "oma": "oma"}
            color_col = col_map.get(param.lower(), None)
            if color_col is None or color_col not in df.columns:
                raise ValueError(f"Unsupported param='{param}' for radiance.")

            # Apply mask (remove nchan==N since already selected)
            if mask:
                q = mask_to_query(mask, drop_token="nchan")
                df = df.query(q)

            title_left = f"Radiance - {str(varName or '').upper()} - {str(varType or '').upper()}."
            title_center = f"Channel ={ch}"
            cycle_dt, cycle_token = get_cycle(self.diag)
            cycle = cycle_token or ""   # string vazia se nada encontrado

        # --------------------------------------------------------------- CONV
        else:
            # Resolve variable/kx
            var = varName or self.diag.get_variables()[0]
            if kx is None:
                kx = extract_int(mask, r"kx\s*==\s*(\d+)", default=None)
            # Data is organized as {var: {kx: DataFrame}}
            df_map = self.diag.get_data_frame()[var]
            if kx is None:
                # pick first non-empty
                kx = next((int(k) for k, v in df_map.items() if hasattr(v, "empty") and not v.empty), None)
            if kx is None or kx not in df_map:
                raise ValueError(f"KX not found (var={var}, kx={kx}).")
            df = df_map[kx]
            if "lat" not in df.columns or "lon" not in df.columns:
                raise ValueError("Conventional DF missing 'lat'/'lon' columns.")

            # param must be a column in conv DF
            color_col = param if param in df.columns else None
            if color_col is None:
                raise ValueError(f"param='{param}' not found in conventional columns: {list(df.columns)}")

            if mask:
                q = mask_to_query(mask, drop_token="kx")
                df = df.query(q)

            title_left = f"Conventional - {var.upper()} (kx={kx})"
            title_center = color_col
            cycle_dt, cycle_token = get_cycle(self.diag)
            cycle = cycle_token or ""   # string vazia se nada encontrado

        # --------------------------------------------------------------- PLOT
        ax, transform = make_axes(basemap=basemap, resolution=resolution)
        sc = ax.scatter(
            df["lon"], df["lat"], c=df[color_col],
            s=s, cmap=cmap, transform=transform, **scatter_kwargs
        )
        cb = plt.colorbar(sc, ax=ax, pad=0.02)
        cb.set_label(nice_label(color_col))
        if (minVal is not None) or (maxVal is not None):
            sc.set_clim(vmin=minVal, vmax=maxVal)

        if area:
            lon_min, lon_max, lat_min, lat_max = area
            if transform is not None:
                ax.set_extent([lon_min, lon_max, lat_min, lat_max], crs=transform)
            else:
                ax.set_xlim(lon_min, lon_max); ax.set_ylim(lat_min, lat_max)

        # Titles (left/center/right)
        ax.set_title(title_center, loc="center", fontsize=11, fontweight="bold")
        ax.set_title(title_left,   loc="left",   fontsize=9)
        ax.set_title(cycle,        loc="right",  fontsize=9)

        plt.tight_layout()
        return ax
    # ------------------------------------------------------------------
    # ptmap (conv) — multi-KX, estilo legacy, rápido
    # ------------------------------------------------------------------
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

        Parameters
        ----------
        varName : str
            Variable key (e.g., ``"t"``, ``"q"``, ``"ps"``).
        varType : int or list of int, optional
            One or multiple KX codes. If ``None``, plot all available KX.
        mask : str, optional
            Pandas ``query`` expression to filter rows.
        area : list of float, optional
            Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
        backend : {"auto", "gpd", "cartopy"}, default: "auto"
            Preferred basemap engine.
        world_path : str, optional
            Path to world polygons (GeoPandas).
        style : str, default: "seaborn-v0_8"
            Matplotlib style to apply for this plot.
        legend : bool, optional
            If ``None``, auto-enable when multiple KX are plotted.
        strict : bool, default: False
            If ``True``, error on missing KX; otherwise skip.
        verbose : bool, default: True
            Print skips for missing/empty KX.
        ax : matplotlib.axes.Axes, optional
            Existing axes or ``None``.
        lon_wrap : {"auto", "pm180", "360", "none"}, default: "auto"
            Longitude wrapping mode.
        **kwargs
            Forwarded to the underlying ``Axes.plot`` (marker, alpha, etc.).

        Returns
        -------
        matplotlib.axes.Axes
            The axes with the point map.
        """
        # (1) estilo e defaults visuais (comentário PT-BR)
        plt.style.use(style)
        kwargs.setdefault("alpha", 0.5)
        kwargs.setdefault("marker", "*")
        kwargs.setdefault("markersize", 5)
        kwargs.setdefault("linewidth", 1)
        want_legend = True if legend is None else bool(legend)

        # (2) resolve KX requeridos e disponíveis
        def _available_kx(diag, var: str) -> list[int]:
            try:
                return [int(k) for k in diag.get_kx_list(var)]
            except Exception:
                d = diag.get_data_frame().get(var, {})
                return [int(k) for k in getattr(d, "keys", lambda: [])()]

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

        # (3) prepara basemap e função de plot
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

        # (4) itera KX, aplica mask e plota
        patches: List = []
        for i, kx in enumerate(kxs):
            df = (
                self.diag.get_dataframe(varName, kx)
                if hasattr(self.diag, "get_dataframe")
                else self.diag.get_data_frame()[varName][kx]
            )
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
    # pvmap (conv) — por variável, com `mask` em todos os KX
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
        lon_wrap: str = "auto",         # "auto" | "pm180" | "360" | "none"
        verbose: bool = True,
        **kwargs,
    ) -> plt.Axes:
        """Point-map por variável (soma todos os KX de cada variável)."""
        plt.style.use(style)
        # defaults do legado
        kwargs.setdefault("alpha", 0.5)
        kwargs.setdefault("marker", "*")
        kwargs.setdefault("markersize", 5)
        kwargs.setdefault("linewidth", 1)
        want_legend = True if legend is None else bool(legend)
    
        # decidir backend e função de plot
        use = backend
        if use == "auto":
            try:
                import geopandas  # noqa: F401
                use = "gpd"
            except Exception:
                use = "cartopy"
    
        if use == "gpd":
            ax = _ensure_axes_gpd(ax, area, world_path=world_path)
            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)
        else:
            ax, _ = _ensure_axes_cartopy(ax, area)
            def scatter_fn(x, y, color):
                ax.plot(x, y, linestyle="None", c=color, **kwargs)
    
        # resolver quais variáveis usar
        if varName is None:
            # ordena por contagem total usando a API de KX para cada var
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
    
        # paleta fixa (igual ao legacy)
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
                  '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
    
        patches: list = []
        for i, var in enumerate(var_list):
            # junta todos os KX existentes da variável
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
                        # máscara inválida para esta var → ignora este KX
                        continue
                if df.empty or not {"lat", "lon"}.issubset(df.columns):
                    continue
                frames.append(df[["lon", "lat"]])
    
            if not frames:
                if verbose:
                    print(f"[pvmap] nenhum ponto para var={var} (após mask/lon check)")
                continue
    
            dfv = pd.concat(frames, ignore_index=True)
            # wrap 0..360 → -180..180 se necessário
            x = _wrap_lon(dfv["lon"].to_numpy(dtype=float), mode=lon_wrap)
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
