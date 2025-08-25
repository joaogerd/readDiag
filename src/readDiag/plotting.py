# ---------------------------------------------------------------------------
# Plotting utilities for GSI diagnostics (NumPy-style docstrings)
# ---------------------------------------------------------------------------
from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, List, Dict, Any, Tuple
from collections import defaultdict

import matplotlib as mpl
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np
import pandas as pd

from .reader import diagAccess
from .style import PlotConfig
from .utils import deprecated


def _check_kind(kind: str):
    """Decorator ensuring a plotting method is only called for a specific
    diagnostic kind.

    Parameters
    ----------
    kind : {"conv", "rad"}
        The diagnostic type required by the decorated method.
    """

    def decorator(func):
        def wrapper(self, *args, **kwargs):
            if self.kind != kind:
                raise ValueError(f"{func.__name__} only valid for {kind} diagnostics")
            return func(self, *args, **kwargs)

        return wrapper

    return decorator


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

    def __init__(self, diag: diagAccess, config: Optional[PlotConfig] = None):
        if not isinstance(diag, diagAccess):
            raise TypeError("`diag` must be an instance of diagAccess")
        self.diag = diag
        self.kind = "conv" if diag.get_data_type() == 1 else "rad"
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
    @_check_kind("conv")
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

    @_check_kind("conv")
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
        data_dict = self.diag.get_data_frame()
        if var not in data_dict:
            raise ValueError(f"Variable '{var}' not found.")

        kxs = sorted(data_dict[var].keys())
        series_list: List[Iterable[float]] = []
        for k in kxs:
            df = data_dict[var][k]
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not in data for kx {k}.")
            series_list.append(df[col].dropna().to_numpy())

        ax = self._ensure_ax(ax)
        data_kwargs, style_kwargs = self._split_kwargs(kwargs)

        # Allow a single "color" to color all box components
        if "color" in data_kwargs:
            c = data_kwargs.pop("color")
            data_kwargs.setdefault("boxprops", dict(color=c))
            data_kwargs.setdefault("whiskerprops", dict(color=c))
            data_kwargs.setdefault("capprops", dict(color=c))
            data_kwargs.setdefault("medianprops", dict(color=c))

        ax.boxplot(series_list, **data_kwargs)
        ax.set_xticks(range(1, len(kxs) + 1))
        ax.set_xticklabels(kxs)

        style_kwargs.setdefault("title", f"Boxplot of {col} for {var} across kxs")
        style_kwargs.setdefault("xlabel", "KX")
        style_kwargs.setdefault("ylabel", col)

        ax = self._apply_plot_kwargs(ax, style_kwargs)
        self._save(ax, savepath)
        return ax

    @_check_kind("conv")
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

    @_check_kind("conv")
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

    @_check_kind("conv")
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

    @_check_kind("conv")
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

    @_check_kind("conv")
    def plot_spatial_conv(
        self,
        var: str,
        kx: int,
        param: str = "omf",
        mask: Optional[str] = None,
        area: Optional[List[float]] = None,
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
            Pandas query expression to filter the DataFrame (e.g., ``"iuse == 1"``).
        area : list of float, optional
            Bounding box ``[lon_min, lat_min, lon_max, lat_max]``.
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
        lons = df["lon"].to_numpy()
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
    @_check_kind("rad")
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

    @_check_kind("rad")
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

