"""
Module: readDiag.impact

Tools to quantify and visualize the *impact of observations* using GSI-style
OmF/OmA diagnostics. The central class :class:`ImpactAnalyzer` derives TI, FI and
FBI per group (conventional kx or radiance channel) and exposes convenience
plotting. Additional helpers support multi-experiment comparison and time-series
summaries.

Notes
-----
- This module **does not** alter diagnostic content. It consumes DataFrames
  produced by :class:`readDiag.reader.diagAccess`.
- Metrics follow the common definitions:

  *TI*  : Total Impact = sum((OMA² - OMF²) / σ²)

  *FI*  : Fractional Impact  = 100 · TI / ΣTI

  *FBI* : Fractional Background Impact = −FI

Examples
--------
>>> from readDiag.impact import ImpactAnalyzer
>>> ia = ImpactAnalyzer.from_pair('diag_conv_omf', 'diag_conv_oma', var='t')
>>> df = ia.compute_all_metrics()              # columns: ['kx', 'TI', 'FI', 'FBI']
>>> ax = ia.plot_impact_bar(metric='FI')       # horizontal bar plot per kx/channel

>>> # Compare two experiments over many cycles
>>> exp1 = [("omf_0000", "oma_0000"), ("omf_0006", "oma_0006")]
>>> exp2 = [("omf2_0000", "oma2_0000"), ("omf2_0006", "oma2_0006")]
>>> cmpx = ExperimentComparator(exp1, exp2, var='t')
>>> cmpx.compare()
>>> cp = ComparisonPlotter(cmpx.comparison_df)
>>> _ = cp.plot_diff(metric='mean_diff')
"""

from typing import Optional, List, Dict, Literal, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import skew, kurtosis, linregress, wilcoxon, ttest_rel, median_abs_deviation
from statsmodels.stats.multitest import multipletests
from sklearn.utils import resample

# Importação segura do teste binomial (SciPy >= 1.7 usa binomtest, versões antigas usam binom_test)
try:  # pragma: no cover - compat shim
    from scipy.stats import binomtest

    def binom_p(n_greater, n_total):
        """Return binomial p-value for n_greater successes in n_total trials (p=0.5)."""
        return binomtest(n_greater, n_total, p=0.5).pvalue if n_total > 0 else np.nan
except Exception:  # pragma: no cover - compat shim
    from scipy.stats import binom_test

    def binom_p(n_greater, n_total):
        """Return binomial p-value for n_greater successes in n_total trials (p=0.5)."""
        return binom_test(n_greater, n_total, p=0.5) if n_total > 0 else np.nan

from .reader import diagAccess

# Small constant to avoid division-by-zero in fractional metrics
EPSILON = 1e-15


class ImpactAnalyzer:
    """Analyze observation impact (TI/FI/FBI) from OmF/OmA diagnostics.

    Operates on a :class:`~readDiag.reader.diagAccess` instance and supports both
    **conventional** (conv) and **radiance** (rad) diagnostics. For conv files,
    metrics are computed per *kx*; for rad files, per *channel*.

    Parameters
    ----------
    diag : diagAccess
        An initialized diagnostic reader instance.

    Raises
    ------
    ValueError
        If the diagnostic is conventional but ``diag.var`` is not set (required
        to address the selected variable's KX dictionary).

    See Also
    --------
    ImpactAnalyzer.from_pair : Convenience constructor to merge OmF/OmA.
    ExperimentComparator : Multi-cycle comparison between two experiments.
    """

    def __init__(self, diag: diagAccess):
        self.diag = diag
        self._validate()

    # ------------------------------------------------------------------
    # Internal validation / helpers
    # ------------------------------------------------------------------
    def _validate(self) -> None:
        """Validate prerequisite fields on the underlying ``diagAccess``.

        Notes
        -----
        Conventional diagnostics (``get_data_type()==1``) require a selected
        variable (``diag.var``) so we can access the per-``kx`` frames.
        """
        if self.diag.get_data_type() == 1 and not getattr(self.diag, 'var', None):
            raise ValueError("diagAccess must be initialized with a var for conventional files.")

    @classmethod
    def from_pair(cls, omf_file: str, oma_file: str, var: Optional[str] = None) -> "ImpactAnalyzer":
        """Build an analyzer from a pair of OmF and OmA diagnostic files.

        The OmA values are copied into a new column ``'oma'`` alongside the
        OmF column ``'omf'`` within the same :class:`diagAccess` data structure.

        Parameters
        ----------
        omf_file : str
            Path to the diagnostic file containing OmF.
        oma_file : str
            Path to the diagnostic file containing OmA (stored in ``'omf'`` field).
        var : str, optional
            Variable of interest (required for conventional diagnostics).

        Returns
        -------
        ImpactAnalyzer
            An analyzer whose internal ``diag`` holds both OmF and the injected
            OmA in a consistent structure.

        Raises
        ------
        ValueError
            If the two inputs are not the same diagnostic type (conv vs rad).
        """
        omf = diagAccess(omf_file, var=var)
        oma = diagAccess(oma_file, var=var)

        if omf.get_data_type() != oma.get_data_type():
            raise ValueError("Files must be of the same type (conv or rad).")

        dtype = omf.get_data_type()
        if dtype == 1:  # conventional: per-variable dict of KX -> DataFrame
            var = omf.var
            df_omf = omf.get_data_frame()[var]
            df_oma = oma.get_data_frame()[var]
            for kx in df_omf:
                if kx in df_oma and 'omf' in df_oma[kx]:
                    # Write OmA alongside OmF into the same frame
                    df_omf[kx]['oma'] = df_oma[kx]['omf']
            omf._data_frame[var] = df_omf
        else:  # radiance: list of per-channel DataFrames
            list_omf = omf.get_data_frame()['dataframes']['diagbufchan_df']
            list_oma = oma.get_data_frame()['dataframes']['diagbufchan_df']
            for df1, df2 in zip(list_omf, list_oma):
                df1['oma'] = df2['omf']

        return cls(omf)

    def _find_error_col(self, df: pd.DataFrame) -> Optional[str]:
        """Return the best-matching error column name for a DataFrame.

        Parameters
        ----------
        df : pandas.DataFrame
            Source frame where the error column should be located.

        Returns
        -------
        str or None
            One of ``'error'`` or ``'end_err'`` if present; otherwise ``None``.
        """
        for col in ('error', 'end_err'):
            if col in df.columns:
                return col
        return None

    def _calc_ti_component(self, oma: pd.Series, omf: pd.Series, err: pd.Series) -> float:
        """Compute TI contribution for a subset of valid entries.

        Parameters
        ----------
        oma : pandas.Series
            Analysis-minus-observation values.
        omf : pandas.Series
            Forecast-minus-observation values.
        err : pandas.Series
            Standard deviation (σ) of observation error for each entry.

        Returns
        -------
        float
            Sum((OMA² − OMF²) / σ²) over finite entries with positive error.
        """
        valid = (err > 0) & np.isfinite(oma) & np.isfinite(omf)
        return ((oma[valid] ** 2 - omf[valid] ** 2) / (err[valid] ** 2)).sum()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_ti(self) -> Dict[int, float]:
        """Compute Total Impact (TI) per *kx* (conv) or per channel (rad).

        Returns
        -------
        dict[int, float]
            Mapping from integer key (``kx`` or channel index) to TI value.
        """
        is_conv = self.diag.get_data_type() == 1
        ti: Dict[int, float] = {}

        if is_conv:
            var = self.diag.var
            df_dict = self.diag.get_data_frame()[var]
            for kx, df in df_dict.items():
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                if not {'omf', 'oma'}.issubset(df.columns):
                    continue
                error_col = self._find_error_col(df)
                if error_col is None:
                    continue
                err = df[error_col].replace(0, np.nan)
                ti[kx] = self._calc_ti_component(df['oma'], df['omf'], err)
        else:
            df_list = self.diag.get_data_frame()['dataframes']['diagbufchan_df']
            for ch, df in enumerate(df_list):
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                if not {'omf', 'oma', 'errinv'}.issubset(df.columns):
                    continue
                err = 1.0 / df['errinv'].replace(0, np.nan)
                ti[ch] = self._calc_ti_component(df['oma'], df['omf'], err)
        return ti

    def compute_all_metrics(self) -> pd.DataFrame:
        """Compute TI, FI and FBI per group.

        Returns
        -------
        pandas.DataFrame
            A sorted table with columns ``['kx', 'TI', 'FI', 'FBI']``.
        """
        ti_dict = self.compute_ti()
        total = sum(ti_dict.values())
        total = total if abs(total) > EPSILON else EPSILON

        df = pd.DataFrame([{'kx': k, 'TI': v} for k, v in ti_dict.items()])
        if df.empty:
            return df
        df['FI'] = df['TI'] / total * 100.0
        df['FBI'] = -df['TI'] / total * 100.0
        return df.sort_values(by='TI', ascending=True, ignore_index=True)

    def plot_impact_bar(
        self,
        metric: Literal['TI', 'FI', 'FBI'] = 'TI',
        ax: Optional[plt.Axes] = None,
        color: Optional[str] = None,
        title: Optional[str] = None,
        xlabel: Optional[str] = None,
        ylabel: Optional[str] = None,
        rotation: int = 45,
        fontsize: int = 12,
        top_k: Optional[int] = None,
    ) -> plt.Axes:
        """Plot a horizontal bar chart for the selected metric.

        Parameters
        ----------
        metric : {'TI', 'FI', 'FBI'}, default: 'TI'
            Which metric to display per bar.
        ax : matplotlib.axes.Axes, optional
            Existing axes to draw on. If ``None``, a new figure/axes is created.
        color : str, optional
            Bar color. If ``None``, Matplotlib default is used.
        title, xlabel, ylabel : str, optional
            Axis texts (applied with ``loc='center'`` for compatibility with tests).
        rotation : int, default: 45
            Rotation applied to y tick labels (labels are the group identifiers).
        fontsize : int, default: 12
            Base font size for labels and title.
        top_k : int, optional
            If set, keep only the *k* largest absolute values for the chosen metric.

        Returns
        -------
        matplotlib.axes.Axes
            The axes containing the bar chart.
        """
        df = self.compute_all_metrics()
        if df.empty:
            ax = ax or plt.subplots(figsize=(10, 2))[1]
            ax.text(0.5, 0.5, "No data", ha='center', va='center', transform=ax.transAxes)
            ax.set_axis_off()
            return ax

        # For TI we typically want descending by magnitude; for FI/FBI ascending is fine
        df = df.sort_values(by=metric, ascending=(metric != 'TI'))
        if top_k is not None and top_k > 0:
            # Keep largest absolute values first, then truncate
            df = df.reindex(df[metric].abs().sort_values(ascending=False).index).head(top_k)

        ax = ax or plt.subplots(figsize=(10, 6))[1]
        y_labels = df['kx'].astype(str)
        ax.barh(y_labels, df[metric], color=color)

        ax.set_title(title or f"{metric} per kx/channel", fontsize=fontsize + 2, loc='center')
        ax.set_xlabel(xlabel or metric, fontsize=fontsize)
        ax.set_ylabel(ylabel or "KX / Channel", fontsize=fontsize)
        ax.tick_params(axis='x', labelsize=fontsize)
        ax.tick_params(axis='y', labelsize=fontsize, rotation=rotation)
        ax.grid(True, linestyle='--', alpha=0.6)
        return ax


def plot_all_impact_subplots(
    analyzers: List[ImpactAnalyzer],
    labels: Optional[List[str]] = None,
    metric: Literal['TI', 'FI', 'FBI'] = 'TI',
    suptitle: Optional[str] = None,
) -> plt.Axes:
    """Plot aligned horizontal bar charts for multiple analyzers.

    Parameters
    ----------
    analyzers : list of ImpactAnalyzer
        One analyzer per subplot (row).
    labels : list of str, optional
        Optional per-subplot label suffix.
    metric : {'TI', 'FI', 'FBI'}, default: 'TI'
        Metric rendered in each bar chart.
    suptitle : str, optional
        Figure super-title.

    Returns
    -------
    matplotlib.axes.Axes
        The axes (or array of axes) created by Matplotlib.

    Raises
    ------
    RuntimeError
        If no analyzer yields valid data.
    """
    dfs = [a.compute_all_metrics() for a in analyzers]
    all_vals = [df[metric] for df in dfs if not df.empty]

    if not all_vals:
        raise RuntimeError("No valid data found in any analyzer.")

    n = len(analyzers)
    fig, axs = plt.subplots(n, 1, figsize=(10, 3.5 * n), sharex=True)
    if n == 1:
        axs = [axs]

    for i, (ax, analyzer) in enumerate(zip(axs, analyzers)):
        label = labels[i] if labels and i < len(labels) else f"Plot {i+1}"
        analyzer.plot_impact_bar(metric=metric, ax=ax, title=f"Impact {label}")

    if suptitle:
        fig.suptitle(suptitle, fontsize=16)
    plt.tight_layout()
    return axs[-1]


class ExperimentComparator:
    """Compare the impact between **two experiments** across cycles.

    Two lists of (OmF, OmA) files are provided for experiment 1 and experiment 2.
    The comparator computes per-cycle TI, aggregates per kx/channel, and then
    produces a comprehensive set of descriptive and inferential statistics.

    Parameters
    ----------
    exp1_files, exp2_files : list of (str, str)
        Pairs of ``(omf_file, oma_file)`` in chronological order.
    var : str, optional
        Variable name for conventional diagnostics.

    Attributes
    ----------
    per_cycle_df : pandas.DataFrame
        Table with columns ``['cycle', 'experiment', 'kx', 'TI']``.
    comparison_df : pandas.DataFrame or None
        Summary metrics per kx/channel filled after :meth:`compare`.
    """

    def __init__(self, exp1_files: List[Tuple[str, str]], exp2_files: List[Tuple[str, str]], var: Optional[str] = None):
        self.exp1_files = exp1_files
        self.exp2_files = exp2_files
        self.var = var
        self.per_cycle_df = self._gather_per_cycle()
        self.comparison_df: Optional[pd.DataFrame] = None

    def _gather_per_cycle(self) -> pd.DataFrame:
        """Load TI values per cycle and per kx/channel for both experiments.

        Returns
        -------
        pandas.DataFrame
            Columns: ``['cycle', 'experiment', 'kx', 'TI']``.
        """
        rows = []
        n_cycles = min(len(self.exp1_files), len(self.exp2_files))
        for idx in range(n_cycles):
            omf1, oma1 = self.exp1_files[idx]
            omf2, oma2 = self.exp2_files[idx]
            ia1 = ImpactAnalyzer.from_pair(omf1, oma1, var=self.var)
            ia2 = ImpactAnalyzer.from_pair(omf2, oma2, var=self.var)
            ti1 = ia1.compute_ti()
            ti2 = ia2.compute_ti()
            # Only intersect keys to ensure aligned comparison
            for kx in sorted(set(ti1) & set(ti2)):
                rows.append({'cycle': idx, 'experiment': 1, 'kx': kx, 'TI': ti1[kx]})
                rows.append({'cycle': idx, 'experiment': 2, 'kx': kx, 'TI': ti2[kx]})
        return pd.DataFrame(rows)

    def compare(self) -> None:
        """Compute statistics comparing experiment 2 vs experiment 1.

        For each kx/channel, the method derives:

        - Descriptive stats (mean, std, median, IQR, skewness, kurtosis, MAD)
          for both experiments and for their difference (exp2 − exp1).
        - Effect size (Cohen's d), Pearson correlation, and linear trend (slope)
          of the per-cycle differences.
        - Proportion of cycles where exp2 > exp1 and the corresponding binomial
          test p-value.
        - Paired t-test and Wilcoxon signed-rank test with FDR correction.
        - Bootstrap 95% CI for the mean difference.

        Results are stored in :attr:`comparison_df`.
        """
        df = self.per_cycle_df
        all_kx = sorted(df['kx'].unique())
        results: List[Dict[str, float]] = []

        for kx in all_kx:
            d1 = df[(df['experiment'] == 1) & (df['kx'] == kx)].sort_values("cycle")['TI'].values
            d2 = df[(df['experiment'] == 2) & (df['kx'] == kx)].sort_values("cycle")['TI'].values
            n = min(len(d1), len(d2))
            if n < 2:
                continue
            diffs = d2[:n] - d1[:n]

            # Bootstrap CI for mean difference
            boots = [resample(diffs, n_samples=n) for _ in range(1000)]
            means = [b.mean() for b in boots]
            ci_low = np.percentile(means, 2.5)
            ci_high = np.percentile(means, 97.5)

            # Descriptive statistics
            mean1, mean2 = d1[:n].mean(), d2[:n].mean()
            std1, std2 = d1[:n].std(), d2[:n].std()
            median1, median2 = np.median(d1[:n]), np.median(d2[:n])
            iqr1 = np.percentile(d1[:n], 75) - np.percentile(d1[:n], 25)
            iqr2 = np.percentile(d2[:n], 75) - np.percentile(d2[:n], 25)
            skew1, skew2 = skew(d1[:n]), skew(d2[:n])
            kurt1, kurt2 = kurtosis(d1[:n]), kurtosis(d2[:n])
            mad1, mad2 = median_abs_deviation(d1[:n]), median_abs_deviation(d2[:n])

            mean_diff = diffs.mean()
            std_diff = diffs.std()
            median_diff = np.median(diffs)
            iqr_diff = np.percentile(diffs, 75) - np.percentile(diffs, 25)
            skew_diff = skew(diffs)
            kurt_diff = kurtosis(diffs)
            mad_diff = median_abs_deviation(diffs)

            # Effect size (Cohen's d)
            cohens_d = mean_diff / (std_diff if std_diff > 0 else 1e-12)

            # Correlation
            if std1 > 0 and std2 > 0:
                corr_pearson = np.corrcoef(d1[:n], d2[:n])[0, 1]
            else:
                corr_pearson = np.nan

            # Temporal trend (slope of the differences)
            slope = linregress(np.arange(n), diffs).slope if n >= 2 else np.nan

            # Proportion & binomial sign test
            n_greater = np.sum(d2[:n] > d1[:n])
            n_less = np.sum(d2[:n] < d1[:n])
            n_total = n_greater + n_less
            sign_p = binom_p(n_greater, n_total)

            # Paired tests
            t_stat, t_p = ttest_rel(d1[:n], d2[:n])
            try:
                w_stat, w_p = wilcoxon(d1[:n], d2[:n])
            except ValueError:
                w_stat, w_p = np.nan, np.nan

            results.append({
                'kx': kx,
                'mean_TI_exp1': mean1, 'mean_TI_exp2': mean2,
                'std_TI_exp1': std1,  'std_TI_exp2': std2,
                'median_TI_exp1': median1, 'median_TI_exp2': median2,
                'iqr_TI_exp1': iqr1, 'iqr_TI_exp2': iqr2,
                'skew_TI_exp1': skew1, 'skew_TI_exp2': skew2,
                'kurt_TI_exp1': kurt1, 'kurt_TI_exp2': kurt2,
                'mad_TI_exp1': mad1, 'mad_TI_exp2': mad2,
                'mean_diff': mean_diff, 'std_diff': std_diff,
                'median_diff': median_diff, 'iqr_diff': iqr_diff,
                'skew_diff': skew_diff, 'kurt_diff': kurt_diff, 'mad_diff': mad_diff,
                'cohens_d': cohens_d, 'corr_pearson': corr_pearson, 'slope': slope,
                'perc_exp2_maior': np.mean(d2[:n] > d1[:n]) * 100.0,
                'sign_p': sign_p,
                'CI_low': ci_low, 'CI_high': ci_high,
                't_stat': t_stat, 't_p': t_p,
                'w_stat': w_stat, 'w_p': w_p,
                'n_cycles': n,
            })

        dfres = pd.DataFrame(results)
        if not dfres.empty:
            # Multiple testing correction (FDR)
            t_corrected = multipletests(dfres['t_p'].fillna(1), method="fdr_bh")[1]
            w_corrected = multipletests(dfres['w_p'].fillna(1), method="fdr_bh")[1]
            dfres['signif_t'] = t_corrected < 0.05
            dfres['signif_w'] = w_corrected < 0.05

        self.comparison_df = dfres


class ComparisonPlotter:
    """Visualization helper for experiment comparison outputs.

    Parameters
    ----------
    comparison_df : pandas.DataFrame
        Output of :meth:`ExperimentComparator.compare` with per-kx/channel stats.
    """

    def __init__(self, comparison_df: pd.DataFrame):
        self.df = comparison_df

    def plot_diff(
        self,
        metric: str = "mean_diff",
        ci: bool = True,
        highlight_significance: bool = True,
        figsize: Tuple[int, int] = (12, 6),
    ) -> plt.Axes:
        """Plot differences between experiments with CI and significance markers.

        Parameters
        ----------
        metric : str, default: 'mean_diff'
            Column to render as bar heights (e.g., ``'mean_diff'``, ``'cohens_d'``).
        ci : bool, default: True
            Show 95% confidence intervals if ``CI_low``/``CI_high`` are present.
        highlight_significance : bool, default: True
            Draw an asterisk above bars where either ``signif_t`` or ``signif_w`` is True.
        figsize : tuple of int, default: (12, 6)
            Figure size passed to Matplotlib.

        Returns
        -------
        matplotlib.axes.Axes
            The axes containing the bar plot.
        """
        df = self.df.sort_values("kx")
        x = df["kx"].astype(str)
        y = df[metric]

        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(x, y, color='steelblue', alpha=0.7, label="Difference")

        if ci and {'CI_low', 'CI_high'}.issubset(df.columns):
            ax.errorbar(
                x, y,
                yerr=[y - df["CI_low"], df["CI_high"] - y],
                fmt='none', ecolor='black', capsize=4, label="95% CI",
            )

        if highlight_significance and {'signif_t', 'signif_w'}.issubset(df.columns):
            sig = df["signif_t"] | df["signif_w"]
            for xi, yi, is_sig in zip(x[sig], y[sig], sig[sig]):
                if is_sig:
                    ax.text(xi, yi, "*", ha='center', va='bottom', fontsize=14, color='darkred')

        ax.axhline(0, color='gray', linestyle='--')
        ax.set_ylabel(f"Δ {metric}")
        ax.set_xlabel("KX / Channel")
        ax.set_title("Impact Comparison Between Experiments", loc='center')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return ax


def plot_metric_series(
    analyzers: List[ImpactAnalyzer],
    label: str,
    metric: Literal['TI', 'FI', 'FBI'] = 'TI',
    color: Optional[str] = None,
) -> plt.Axes:
    """Plot mean ± std envelopes of a metric across a series of analyzers.

    Parameters
    ----------
    analyzers : list of ImpactAnalyzer
        One analyzer per cycle/time index.
    label : str
        Series label used in the plot title.
    metric : {'TI', 'FI', 'FBI'}, default: 'TI'
        Which metric to summarize.
    color : str, optional
        Base color for the mean line and the ±1 STD fill area.

    Returns
    -------
    matplotlib.axes.Axes
        The axes containing the plot.
    """
    # Concatenate per-cycle tables and extract the selected metric
    dfs = [a.compute_all_metrics().set_index('kx') for a in analyzers]
    if not dfs:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.text(0.5, 0.5, "No data", ha='center', va='center', transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    vals = [df[metric] for df in dfs]
    arr = np.stack([v.values for v in vals])  # shape: n_cycles x n_groups
    kx = dfs[0].index.values

    fig, ax = plt.subplots(figsize=(12, 6))
    # All individual series in light gray for context
    for row in arr:
        ax.plot(kx, row, color='lightgray', alpha=0.6, zorder=1)

    # Mean ± std envelope
    mu = arr.mean(axis=0)
    sd = arr.std(axis=0)
    ax.plot(kx, mu, marker='o', color=(color or 'C0'), label="Mean", zorder=2)
    ax.fill_between(kx, mu - sd, mu + sd, color=(color or 'C0'), alpha=0.25, label="±1 STD", zorder=1)

    ax.set_title(f"{label} — {metric} (mean ± std)", loc='center')
    ax.set_xlabel("Channel/KX")
    ax.set_ylabel(metric)
    ax.grid(True, linestyle='--', alpha=0.6)
    ax.legend()
    plt.tight_layout()
    return ax


# --- backcompat shim: aceitar alias "top_k" em plot_impact_bar ---
try:
    _rd_orig_plot_impact_bar = ImpactAnalyzer.plot_impact_bar  # type: ignore[name-defined]
    def _rd_plot_impact_bar_shim(self, metric: str, *args, top_k=None, **kwargs):
        if top_k is not None and "n" not in kwargs:
            kwargs["n"] = top_k
        return _rd_orig_plot_impact_bar(self, metric, *args, **kwargs)
    ImpactAnalyzer.plot_impact_bar = _rd_plot_impact_bar_shim  # type: ignore[name-defined]
except Exception:
    pass
