import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Literal

from .reader import diagAccess

class ImpactAnalyzer:
    """
    Analyze the impact of observations based on OmA and OmF diagnostics
    from a diagAccess instance.

    Supports both conventional and radiance files.
    """
    def __init__(self, diag: diagAccess):
        self.diag = diag
        self._validate()

    def _validate(self):
        if self.diag.get_data_type() == 1 and not self.diag.var:
            raise ValueError("diagAccess must be initialized with a var for conventional files.")

    @classmethod
    def from_pair(cls, omf_file: str, oma_file: str, var: Optional[str] = None) -> "ImpactAnalyzer":
        omf = diagAccess(omf_file, var=var)
        oma = diagAccess(oma_file, var=var)

        if omf.get_data_type() != oma.get_data_type():
            raise ValueError("Files must be of the same type (conv or rad).")

        dtype = omf.get_data_type()
        if dtype == 1:
            var = omf.var
            df_omf = omf.get_data_frame()[var]
            df_oma = oma.get_data_frame()[var]

            for kx in df_omf:
                if kx in df_oma and 'omf' in df_oma[kx]:
                    df_omf[kx] = df_omf[kx].copy()
                    df_omf[kx]['oma'] = df_oma[kx]['omf']
                    if 'end_err' in df_omf[kx]:
                        errinv = df_omf[kx]['end_err'].replace(0, np.nan)
                        df_omf[kx]['error'] = 1.0 / errinv
            omf._data_frame[var] = df_omf

        else:
            list_omf = omf.get_data_frame()['dataframes']['diagbufchan_df']
            list_oma = oma.get_data_frame()['dataframes']['diagbufchan_df']
            for i, (df1, df2) in enumerate(zip(list_omf, list_oma)):
                list_omf[i] = df1.copy()
                list_omf[i]['oma'] = df2['omf']
                if 'errinv' in list_omf[i]:
                    errinv = list_omf[i]['errinv'].replace(0, np.nan)
                    list_omf[i]['error'] = 1.0 / errinv
            omf._data_frame['dataframes']['diagbufchan_df'] = list_omf

        return cls(omf)

    def compute_ti(self) -> Dict[int, float]:
        is_conv = self.diag.get_data_type() == 1
        ti = {}

        if is_conv:
            var = self.diag.var
            df_dict = self.diag.get_data_frame()[var]
            for kx, df in df_dict.items():
                if 'omf' not in df or 'oma' not in df or 'error' not in df:
                    continue
                valid = (df['error'] > 0) & np.isfinite(df['oma']) & np.isfinite(df['omf'])
                if valid.any():
                    num = ((df.loc[valid, 'oma'] ** 2 - df.loc[valid, 'omf'] ** 2) / (df.loc[valid, 'error'] ** 2)).sum()
                    ti[kx] = num
        else:
            df_list = self.diag.get_data_frame()['dataframes']['diagbufchan_df']
            for ch, df in enumerate(df_list):
                if 'omf' not in df or 'oma' not in df or 'error' not in df:
                    continue
                valid = (df['error'] > 0) & np.isfinite(df['oma']) & np.isfinite(df['omf'])
                if valid.any():
                    num = ((df.loc[valid, 'oma'] ** 2 - df.loc[valid, 'omf'] ** 2) / (df.loc[valid, 'error'] ** 2)).sum()
                    ti[ch] = num

        return ti

    def compute_all_metrics(self) -> pd.DataFrame:
        ti_dict = self.compute_ti()
        if not ti_dict:
            return pd.DataFrame(columns=['kx', 'TI', 'FI', 'FBI'])

        total = sum(ti_dict.values()) or 1e-15
        df = pd.DataFrame(list(ti_dict.items()), columns=['kx', 'TI'])
        df['FI'] = df['TI'] / total * 100
        df['FBI'] = -df['TI'] / total * 100
        return df.sort_values(by='kx', ascending=True, ignore_index=True)

    def plot_impact_bar(self,
                        metric: Literal['TI', 'FI', 'FBI'] = 'TI',
                        ax: Optional[plt.Axes] = None,
                        color: Optional[str] = None,
                        title: Optional[str] = None,
                        xlabel: Optional[str] = None,
                        ylabel: Optional[str] = None,
                        rotation: int = 0,
                        fontsize: int = 12,
                        xlim: Optional[tuple] = None) -> plt.Axes:
        """
        Plot a horizontal bar chart for a given impact metric.

        Args:
            metric: 'TI', 'FI', or 'FBI'
            ax: Optional Axes object
            color: Bar color
            title: Plot title
            xlabel: X-axis label
            ylabel: Y-axis label
            rotation: Tick label rotation (y-axis)
            fontsize: Font size for labels
            xlim: Optional (min, max) tuple to unify axes across subplots

        Returns:
            Matplotlib Axes with the plot.
        """
        df = self.compute_all_metrics()
        if df.empty:
            raise ValueError("No impact metrics available to plot.")

        df = df.sort_values("kx", ascending=True, ignore_index=True)
        y_labels = df["kx"].astype(str)
        values = df[metric]

        ax = ax or plt.subplots(figsize=(10, 6))[1]
        ax.barh(y_labels, values, color=color)

        ax.set_title(title or f"{metric} per kx/channel", fontsize=fontsize + 2)
        ax.set_xlabel(xlabel or metric, fontsize=fontsize)
        ax.set_ylabel(ylabel or "KX / Channel", fontsize=fontsize)

        if xlim:
            ax.set_xlim(xlim)
        else:
            limit = max(abs(values.min()), abs(values.max()))
            ax.set_xlim(-limit * 1.05, limit * 1.05)

        ax.tick_params(axis="x", labelsize=fontsize)
        ax.tick_params(axis="y", labelsize=fontsize, rotation=rotation)
        ax.grid(True, linestyle="--", alpha=0.6)

        return ax

def plot_all_impact_subplots(
    analyzers: List[ImpactAnalyzer],
    labels: Optional[List[str]] = None,
    metric: str = 'TI',
    suptitle: Optional[str] = None
):
    """
    Plot aligned horizontal bar charts for a list of ImpactAnalyzer instances.

    Args:
        analyzers: List of ImpactAnalyzer objects
        labels: Optional list of labels corresponding to each analyzer
        metric: One of 'TI', 'FI', 'FBI'
        suptitle: Optional super title
    """
    dfs = [a.compute_all_metrics() for a in analyzers]
    all_vals = [df[metric] for df in dfs if not df.empty]

    if not all_vals:
        raise RuntimeError("No valid data found in any pair.")

    global_min = min(v.min() for v in all_vals)
    global_max = max(v.max() for v in all_vals)
    global_limit = max(abs(global_min), abs(global_max)) * 1.05
    xlim = (-global_limit, global_limit)

    n = len(analyzers)
    fig, axs = plt.subplots(n, 1, figsize=(10, 3.5 * n), sharex=True)
    if n == 1:
        axs = [axs]

    for i, (ax, analyzer) in enumerate(zip(axs, analyzers)):
        label = labels[i] if labels and i < len(labels) else f"Plot {i+1}"
        analyzer.plot_impact_bar(metric=metric, ax=ax, title=f"Impacto {label}", xlim=xlim)

    if suptitle:
        fig.suptitle(suptitle, fontsize=16)
    plt.tight_layout()
    plt.show()

