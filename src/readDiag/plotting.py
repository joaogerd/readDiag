# ---------------------------------------------------------------------------
# Plotting utilities for GSI diagnostics
# ---------------------------------------------------------------------------
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Iterable, List

import matplotlib.pyplot as plt

from .reader import diagAccess


class diagPlotter:
    """Matplotlib-based plotting helper for :class:`diagAccess` output.

    It inspects the diagnostic type (conventional vs radiance) and provides
    convenience methods to generate common figures.

    Parameters
    ----------
    diag : diagAccess
        An already loaded diagnostic instance.
    """

    def __init__(self, diag: diagAccess):
        if not isinstance(diag, diagAccess):
            raise TypeError("`diag` must be an instance of diagAccess")
        self.diag = diag
        self.kind = "conv" if diag.get_data_type() == 1 else "rad"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _ensure_ax(ax: Optional[plt.Axes]) -> plt.Axes:
        if ax is None:
            fig, ax = plt.subplots()
        return ax

    @staticmethod
    def _save(ax: plt.Axes, savepath: Optional[str]) -> None:
        if not savepath:
            return
        p = Path(savepath)
        p.parent.mkdir(parents=True, exist_ok=True)
        ax.get_figure().savefig(p, dpi=150, bbox_inches="tight")

    # ------------------------------------------------------------------
    # Conventional diagnostics plots
    # ------------------------------------------------------------------
    def plot_hist_conv(
        self,
        var: str,
        channel: int,
        col: str = "omf",
        bins: int = 50,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
    ) -> plt.Axes:
        """Histogram of a conventional diagnostic column.

        Parameters
        ----------
        var : str
            Variable name (e.g. 't', 'q', 'uv', ...).
        channel : int
            Channel / sensor index within the variable dict.
        col : str, default 'omf'
            Column from the dataframe to histogram.
        bins : int, default 50
            Number of histogram bins.
        ax : matplotlib.axes.Axes, optional
            Existing axes to draw on. If *None*, a new figure/axes is created.
        savepath : str, optional
            If provided, path to save the figure as PNG.
        """
        if self.kind != "conv":
            raise ValueError("plot_hist_conv only valid for conventional diagnostics")

        df_dict = self.diag.get_data_frame()
        if var not in df_dict or channel not in df_dict[var]:
            raise ValueError(f"Variable '{var}' or channel '{channel}' not found.")
        df = df_dict[var][channel]
        if col not in df.columns:
            raise ValueError(f"Column '{col}' not in data frame.")

        values = df[col].dropna().to_numpy()
        ax = self._ensure_ax(ax)
        ax.hist(values, bins=bins)
        ax.set_title(f"Histogram of {col} for {var} (channel {channel})")
        ax.set_xlabel(col)
        ax.set_ylabel("Frequency")
        self._save(ax, savepath)
        return ax

    def plot_boxplot_channels_conv(
        self,
        var: str,
        col: str = "omf",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
    ) -> plt.Axes:
        """Boxplot of a column across all channels of a conventional variable.

        Parameters
        ----------
        var : str
            Variable name inside the conventional dictionary.
        col : str, default 'omf'
            Column from each channel frame to include in the boxplot.
        ax : matplotlib.axes.Axes, optional
            Axes to draw on.
        savepath : str, optional
            Save path for the figure.
        """
        if self.kind != "conv":
            raise ValueError("plot_boxplot_channels_conv only valid for conventional diagnostics")

        data_dict = self.diag.get_data_frame()
        if var not in data_dict:
            raise ValueError(f"Variable '{var}' not found.")

        channels = sorted(data_dict[var].keys())
        data: List[Iterable[float]] = []
        for ch in channels:
            df = data_dict[var][ch]
            if col not in df.columns:
                raise ValueError(f"Column '{col}' not in data frame for channel {ch}.")
            data.append(df[col].dropna().to_numpy())

        ax = self._ensure_ax(ax)
        ax.boxplot(data)
        ax.set_xticks(range(1, len(channels) + 1))
        ax.set_xticklabels(channels)
        ax.set_title(f"Boxplot of {col} for {var} across channels")
        ax.set_xlabel("Channel")
        ax.set_ylabel(col)
        self._save(ax, savepath)
        return ax

    # ------------------------------------------------------------------
    # Radiance diagnostics plots
    # ------------------------------------------------------------------
    def plot_channel_stats_rad(
        self,
        metric: str = "omf",
        agg: str = "mean",
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
    ) -> plt.Axes:
        """Aggregate a radiance metric across all channels and plot it.

        Parameters
        ----------
        metric : str, default 'omf'
            Column in the per-channel dataframe (e.g. 'omf', 'omf_nbc', 'errinv').
        agg : str, default 'mean'
            Pandas Series aggregation method name (mean, median, std, ...).
        ax : matplotlib.axes.Axes, optional
        savepath : str, optional
        """
        if self.kind != "rad":
            raise ValueError("plot_channel_stats_rad only valid for radiance diagnostics")

        data = self.diag.get_data_frame().get("dataframes", {})
        chan_list = data.get("diagbufchan_df", [])
        if not chan_list:
            raise ValueError("No radiance channel data available.")

        stats = []
        for df in chan_list:
            if metric not in df.columns:
                raise ValueError(f"Metric '{metric}' not in channel data.")
            stats.append(getattr(df[metric].dropna(), agg)())

        ax = self._ensure_ax(ax)
        ax.plot(range(1, len(stats) + 1), stats, marker="o")
        ax.set_title(f"Radiance channel {agg} of {metric}")
        ax.set_xlabel("Channel")
        ax.set_ylabel(f"{agg}({metric})")
        self._save(ax, savepath)
        return ax

    def plot_omf_distribution_rad(
        self,
        channel_index: int,
        corrected: bool = False,
        bins: int = 50,
        ax: Optional[plt.Axes] = None,
        savepath: Optional[str] = None,
    ) -> plt.Axes:
        """Histogram of O-F values for a single radiance channel.

        Parameters
        ----------
        channel_index : int
            Index in the radiance channel list (0-based).
        corrected : bool, default False
            If True, use 'omf_nbc' when available.
        bins : int, default 50
        ax : matplotlib.axes.Axes, optional
        savepath : str, optional
        """
        if self.kind != "rad":
            raise ValueError("plot_omf_distribution_rad only valid for radiance diagnostics")

        data = self.diag.get_data_frame().get("dataframes", {})
        chan_list = data.get("diagbufchan_df", [])
        if channel_index < 0 or channel_index >= len(chan_list):
            raise IndexError("Channel index out of range.")
        df = chan_list[channel_index]

        key = "omf_nbc" if corrected and "omf_nbc" in df.columns else "omf"
        if key not in df.columns:
            raise ValueError(f"Column '{key}' not in channel data.")

        values = df[key].dropna().to_numpy()
        ax = self._ensure_ax(ax)
        ax.hist(values, bins=bins)
        ax.set_title(f"O-F distribution for channel {channel_index}")
        ax.set_xlabel(key)
        ax.set_ylabel("Frequency")
        self._save(ax, savepath)
        return ax

