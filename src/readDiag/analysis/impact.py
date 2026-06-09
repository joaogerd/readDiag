# src/readDiag/impact.py
"""
Module: readDiag.impact
=======================

Tools to quantify and visualize the *impact of observations* using GSI-style
OmF/OmA diagnostics. The central class :class:`ImpactAnalyzer` derives TI, FI
and FBI per group (conventional KX or radiance channel) and exposes convenience
plotting. Additional helpers support multi-experiment comparison and
time-series summaries.

Notes
-----
- This module **does not** alter diagnostic content in files. It *consumes*
  :class:`~readDiag.reader.diagAccess` DataFrames produced by
  :mod:`readDiag.reader`.
- Metrics follow common definitions:

  ``TI``   (Total Impact)                = Σ ((OMA² − OMF²) / σ²)

  ``FI``   (Fractional Impact, %)        = 100 · TI / Σ|TI|

  ``FBI``  (Frac. Background Impact, %)  = −FI

  The sign of TI comes from (OMA² − OMF²). Positive TI indicates improvement
  (analysis closer to the observation than the background), while negative TI
  indicates degradation.

Examples
--------
Minimal one-cycle impact for conventional diagnostics:

>>> from readDiag.impact import ImpactAnalyzer
>>> ia = ImpactAnalyzer.from_pair("diag_conv_t_omf", "diag_conv_t_oma", var="t")
>>> table = ia.compute_all_metrics()
>>> table.head()
>>> ax = ia.plot_impact_bar(metric="FI", title="Fractional Impact (conv)")
>>> ax.figure.savefig("impact_conv_fi.png", dpi=150)

Radiance diagnostics (per channel), with 1-based channel indexing:

>>> ia = ImpactAnalyzer.from_pair("diag_amsua_omf", "diag_amsua_oma")
>>> ti = ia.compute_ti()          # {1: ..., 2: ..., 3: ...}
>>> ax = ia.plot_impact_bar("TI", top_k=10, title="Top-10 |TI| channels")

Compare two experiments over multiple cycles:

>>> exp1 = [("omf_0000", "oma_0000"), ("omf_0006", "oma_0006")]
>>> exp2 = [("omf2_0000", "oma2_0000"), ("omf2_0006", "oma2_0006")]
>>> from readDiag.impact import ExperimentComparator, ComparisonPlotter
>>> cmpx = ExperimentComparator(exp1, exp2, var="t")
>>> cmpx.compare()
>>> dfc = cmpx.comparison_df
>>> plotter = ComparisonPlotter(dfc)
>>> ax = plotter.plot_diff(metric="mean_diff")
>>> ax.figure.savefig("exp_comparison_mean_diff.png", dpi=150)
"""

from __future__ import annotations

from typing import Optional, List, Dict, Literal, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import (
    skew,
    kurtosis,
    linregress,
    wilcoxon,
    ttest_rel,
    median_abs_deviation,
)

# Multiple-testing correction for paired tests
from statsmodels.stats.multitest import multipletests

# Simple bootstrap via resampling
from sklearn.utils import resample

# Import a compatible binomial sign-test across SciPy versions
try:  # pragma: no cover - compat shim
    from scipy.stats import binomtest

    def binom_p(n_greater: int, n_total: int) -> float:
        """Return binomial p-value (two-sided) with p=0.5 null."""
        return binomtest(n_greater, n_total, p=0.5).pvalue if n_total > 0 else np.nan
except Exception:  # pragma: no cover - compat shim
    from scipy.stats import binom_test

    def binom_p(n_greater: int, n_total: int) -> float:
        """Return binomial p-value (two-sided) with p=0.5 null."""
        return float(binom_test(n_greater, n_total, p=0.5)) if n_total > 0 else np.nan

# Public reader (high-level) used by this module
from ..reader import diagAccess

# Small constant to avoid division-by-zero in fractional metrics
EPSILON: float = 1e-15

__all__ = [
    "ImpactAnalyzer",
    "plot_all_impact_subplots",
    "ExperimentComparator",
    "ComparisonPlotter",
    "plot_metric_series",
]


class ImpactAnalyzer:
    """Analyze observation impact (TI/FI/FBI) from OmF/OmA diagnostics.

    Operates on a :class:`~readDiag.reader.diagAccess` instance and supports both
    **conventional** (conv) and **radiance** (rad) diagnostics. For conv files,
    metrics are computed per *KX*; for rad files, per *channel* (1-based).

    Parameters
    ----------
    diag : diagAccess
        An initialized diagnostic reader instance (already opened).

    Raises
    ------
    ValueError
        If the diagnostic is conventional but ``diag.var`` is not set (required
        to access the per-variable KX dictionary).

    See Also
    --------
    ImpactAnalyzer.from_pair : Convenience constructor to merge OmF/OmA fields.
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
        Conventional diagnostics (``get_data_type() == 1``) require a selected
        variable (``diag.var``) to reach the KX→DataFrame mapping.
        """
        if self.diag.get_data_type() == 1 and not getattr(self.diag, "var", None):
            raise ValueError(
                "diagAccess must be initialized with a var for conventional files."
            )

    @classmethod
    def from_pair(
        cls,
        omf_file: str,
        oma_file: str,
        var: Optional[str] = None,
    ) -> "ImpactAnalyzer":
        """Build an analyzer from a pair of OmF and OmA diagnostic files.

        This constructor loads both files via :class:`diagAccess`, then **injects
        the OmA values** into the OmF structure (new column ``'oma'`` in the same
        per-KX or per-channel frames). The returned :class:`ImpactAnalyzer` holds
        a single reader instance containing both OmF and OmA.

        Parameters
        ----------
        omf_file : str
            Path to the diagnostic file containing OmF.
        oma_file : str
            Path to the diagnostic file containing OmA (stored as ``'omf'`` on disk).
        var : str, optional
            Variable of interest (required for conventional diagnostics).

        Returns
        -------
        ImpactAnalyzer
            Analyzer whose internal ``diag`` holds both OmF and OmA.

        Raises
        ------
        ValueError
            If the two files are not the same diagnostic type (conv vs. rad).
        """
        omf = diagAccess(omf_file, var=var)
        oma = diagAccess(oma_file, var=var)

        if omf.get_data_type() != oma.get_data_type():
            raise ValueError("Files must be of the same type (conv or rad).")

        dtype = omf.get_data_type()
        if dtype == 1:
            # Conventional: dict[var][kx] -> DataFrame with columns incl. 'omf'
            v = omf.var
            df_omf = omf.get_data_frame()[v]
            df_oma = oma.get_data_frame()[v]
            # Inject per-KX 'oma' alongside 'omf'
            for kx, frame in df_omf.items():
                if isinstance(frame, pd.DataFrame) and kx in df_oma:
                    if "omf" in df_oma[kx]:
                        frame["oma"] = df_oma[kx]["omf"]
            omf._data_frame[v] = df_omf  # type: ignore[attr-defined]
        else:
            # Radiance: list-like of channel DataFrames under 'diagbufchan_df'
            list_omf = omf.get_data_frame()["dataframes"]["diagbufchan_df"]
            list_oma = oma.get_data_frame()["dataframes"]["diagbufchan_df"]
            for df1, df2 in zip(list_omf, list_oma):
                if isinstance(df1, pd.DataFrame) and isinstance(df2, pd.DataFrame):
                    if "omf" in df2:
                        df1["oma"] = df2["omf"]

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
        for col in ("error", "end_err"):
            if col in df.columns:
                return col
        return None

    def _calc_ti_component(
        self, oma: pd.Series, omf: pd.Series, err: pd.Series
    ) -> float:
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
            Σ((OMA² − OMF²) / σ²) over finite entries with positive error.
        """
        valid = (err > 0) & np.isfinite(oma) & np.isfinite(omf)
        return ((oma[valid] ** 2 - omf[valid] ** 2) / (err[valid] ** 2)).sum()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def compute_ti(self) -> Dict[int, float]:
        """Compute Total Impact (TI) per *KX* (conv) or per channel (rad).

        Returns
        -------
        dict[int, float]
            Mapping from integer key (``kx`` or 1-based channel index) to TI value.
        """
        is_conv = self.diag.get_data_type() == 1
        ti: Dict[int, float] = {}

        if is_conv:
            v = self.diag.var
            df_dict = self.diag.get_data_frame()[v]
            for kx, df in df_dict.items():
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                if not {"omf", "oma"}.issubset(df.columns):
                    continue
                error_col = self._find_error_col(df)
                if error_col is None:
                    continue
                err = df[error_col].replace(0, np.nan)
                ti[int(kx)] = self._calc_ti_component(df["oma"], df["omf"], err)
        else:
            # Radiance: make channels **1-based** to match typical practice/tests
            df_list = self.diag.get_data_frame()["dataframes"]["diagbufchan_df"]
            for ch, df in enumerate(df_list, start=1):
                if not isinstance(df, pd.DataFrame) or df.empty:
                    continue
                if not {"omf", "oma", "errinv"}.issubset(df.columns):
                    continue
                # errinv = 1/σ → σ = 1/errinv (guard zeros)
                err = 1.0 / df["errinv"].replace(0, np.nan)
                ti[int(ch)] = self._calc_ti_component(df["oma"], df["omf"], err)

        return ti

    def compute_all_metrics(self) -> pd.DataFrame:
        """Compute TI, FI and FBI per group.

        Returns
        -------
        pandas.DataFrame
            Sorted table with columns ``['kx', 'TI', 'FI', 'FBI']``.

        Notes
        -----
        ``FI`` and ``FBI`` are computed relative to ``Σ|TI|`` to ensure a
        meaningful partition of *magnitude* of impact across groups, even when
        positive and negative TI coexist.
        """
        ti_dict = self.compute_ti()
        if not ti_dict:
            return pd.DataFrame(columns=["kx", "TI", "FI", "FBI"])

        df = pd.DataFrame([{"kx": k, "TI": v} for k, v in ti_dict.items()])
        # Sum of absolute impacts avoids near-cancellation across groups
        denom = np.abs(df["TI"]).sum()
        denom = denom if denom > EPSILON else EPSILON
        df["FI"] = df["TI"] / denom * 100.0
        df["FBI"] = -df["FI"]
        # Sort: TI by ascending (often useful to see degradation→improvement)
        return df.sort_values(by="TI", ascending=True, ignore_index=True)

    def plot_impact_bar(
        self,
        metric: Literal["TI", "FI", "FBI"] = "TI",
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
            Axis texts (applied with ``loc='center'`` for tests compatibility).
        rotation : int, default: 45
            Rotation applied to Y tick labels (group identifiers).
        fontsize : int, default: 12
            Base font size for labels and title.
        top_k : int, optional
            If set, keep only the *k* largest absolute values for the chosen metric.

        Returns
        -------
        matplotlib.axes.Axes
            The axes containing the bar chart.

        Examples
        --------
        >>> ia = ImpactAnalyzer.from_pair("omf", "oma", var="t")
        >>> _ = ia.plot_impact_bar(metric="FI", top_k=10)
        """
        df = self.compute_all_metrics()
        if df.empty:
            ax = ax or plt.subplots(figsize=(10, 2))[1]
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            return ax

        # For TI, descending by magnitude can be more informative; FI/FBI keep natural order
        df = df.sort_values(by=metric, ascending=(metric != "TI"))
        if top_k is not None and top_k > 0:
            # Keep items with largest absolute metric
            df = df.loc[df[metric].abs().sort_values(ascending=False).head(top_k).index]

        ax = ax or plt.subplots(figsize=(10, 6))[1]
        y_labels = df["kx"].astype(str)
        ax.barh(y_labels, df[metric], color=color)

        ax.set_title(title or f"{metric} per KX/Channel", fontsize=fontsize + 2, loc="center")
        ax.set_xlabel(xlabel or metric, fontsize=fontsize)
        ax.set_ylabel(ylabel or "KX / Channel", fontsize=fontsize)
        ax.tick_params(axis="x", labelsize=fontsize)
        ax.tick_params(axis="y", labelsize=fontsize)
        for tick in ax.get_yticklabels():
            tick.set_rotation(rotation)
        ax.grid(True, linestyle="--", alpha=0.6)
        return ax


def plot_all_impact_subplots(
    analyzers: List[ImpactAnalyzer],
    labels: Optional[List[str]] = None,
    metric: Literal["TI", "FI", "FBI"] = "TI",
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
        The last axes created (convenience for callers).

    Raises
    ------
    RuntimeError
        If no analyzer yields valid data.

    Examples
    --------
    >>> axs_last = plot_all_impact_subplots([ia1, ia2], labels=["EXP1", "EXP2"], metric="FBI")
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

    Two lists of ``(OmF, OmA)`` file pairs are provided for experiment 1 and
    experiment 2. The comparator computes per-cycle TI, aggregates per KX/
    channel, and then produces a set of descriptive and inferential statistics.

    Parameters
    ----------
    exp1_files, exp2_files : list of (str, str)
        Pairs of ``(omf_file, oma_file)`` in chronological order.
    var : str, optional
        Variable name for conventional diagnostics.

    Attributes
    ----------
    per_cycle_df : pandas.DataFrame
        Columns: ``['cycle', 'experiment', 'kx', 'TI']``.
    comparison_df : pandas.DataFrame or None
        Summary metrics per KX/channel filled after :meth:`compare`.
    """

    def __init__(
        self,
        exp1_files: List[Tuple[str, str]],
        exp2_files: List[Tuple[str, str]],
        var: Optional[str] = None,
    ):
        self.exp1_files = exp1_files
        self.exp2_files = exp2_files
        self.var = var
        self.per_cycle_df = self._gather_per_cycle()
        self.comparison_df: Optional[pd.DataFrame] = None

    def _gather_per_cycle(self) -> pd.DataFrame:
        """Load TI values per cycle and per KX/channel for both experiments.

        Returns
        -------
        pandas.DataFrame
            Columns: ``['cycle', 'experiment', 'kx', 'TI']``.
        """
        rows: List[Dict[str, float]] = []
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
                rows.append({"cycle": idx, "experiment": 1, "kx": int(kx), "TI": float(ti1[kx])})
                rows.append({"cycle": idx, "experiment": 2, "kx": int(kx), "TI": float(ti2[kx])})
        return pd.DataFrame(rows)

    def compare(self) -> None:
        """Compute statistics comparing experiment 2 vs. experiment 1.

        For each KX/channel, the method derives:

        - Descriptive stats (mean, std, median, IQR, skewness, kurtosis, MAD)
          for both experiments and for their difference (exp2 − exp1).
        - Effect size (Cohen's d), Pearson correlation, and linear trend (slope)
          of the per-cycle differences.
        - Proportion of cycles where exp2 > exp1 and the corresponding binomial
          sign-test p-value.
        - Paired t-test and Wilcoxon signed-rank test with FDR correction.
        - Bootstrap 95% CI for the mean difference.

        Results are stored in :attr:`comparison_df`.
        """
        df = self.per_cycle_df
        all_kx = sorted(df["kx"].unique())
        results: List[Dict[str, float]] = []

        for kx in all_kx:
            d1 = df[(df["experiment"] == 1) & (df["kx"] == kx)].sort_values("cycle")["TI"].values
            d2 = df[(df["experiment"] == 2) & (df["kx"] == kx)].sort_values("cycle")["TI"].values
            n = min(len(d1), len(d2))
            if n < 2:
                continue

            diffs = d2[:n] - d1[:n]

            # Bootstrap CI for mean difference (2.5–97.5%)
            boots = [resample(diffs, n_samples=n) for _ in range(1000)]
            means = np.asarray([b.mean() for b in boots])
            ci_low = float(np.percentile(means, 2.5))
            ci_high = float(np.percentile(means, 97.5))

            # Descriptive statistics (per experiment)
            mean1, mean2 = float(d1[:n].mean()), float(d2[:n].mean())
            std1, std2 = float(d1[:n].std()), float(d2[:n].std())
            median1, median2 = float(np.median(d1[:n])), float(np.median(d2[:n]))
            iqr1 = float(np.percentile(d1[:n], 75) - np.percentile(d1[:n], 25))
            iqr2 = float(np.percentile(d2[:n], 75) - np.percentile(d2[:n], 25))
            skew1, skew2 = float(skew(d1[:n])), float(skew(d2[:n]))
            kurt1, kurt2 = float(kurtosis(d1[:n])), float(kurtosis(d2[:n]))
            mad1, mad2 = float(median_abs_deviation(d1[:n])), float(median_abs_deviation(d2[:n]))

            # Descriptive statistics (differences)
            mean_diff = float(diffs.mean())
            std_diff = float(diffs.std())
            median_diff = float(np.median(diffs))
            iqr_diff = float(np.percentile(diffs, 75) - np.percentile(diffs, 25))
            skew_diff = float(skew(diffs))
            kurt_diff = float(kurtosis(diffs))
            mad_diff = float(median_abs_deviation(diffs))

            # Effect size (Cohen's d) based on difference distribution
            cohens_d = float(mean_diff / (std_diff if std_diff > 0 else 1e-12))

            # Correlation across cycles (guard zero-variance)
            if std1 > 0 and std2 > 0:
                corr_pearson = float(np.corrcoef(d1[:n], d2[:n])[0, 1])
            else:
                corr_pearson = np.nan

            # Temporal trend (slope of differences across cycles)
            slope = float(linregress(np.arange(n), diffs).slope) if n >= 2 else np.nan

            # Proportion & binomial sign-test
            n_greater = int(np.sum(d2[:n] > d1[:n]))
            n_less = int(np.sum(d2[:n] < d1[:n]))
            n_total = int(n_greater + n_less)
            sign_p = float(binom_p(n_greater, n_total))

            # Paired tests
            t_stat, t_p = ttest_rel(d1[:n], d2[:n])
            try:
                w_stat, w_p = wilcoxon(d1[:n], d2[:n])
            except ValueError:
                w_stat, w_p = np.nan, np.nan

            results.append(
                {
                    "kx": int(kx),
                    "mean_TI_exp1": mean1,
                    "mean_TI_exp2": mean2,
                    "std_TI_exp1": std1,
                    "std_TI_exp2": std2,
                    "median_TI_exp1": median1,
                    "median_TI_exp2": median2,
                    "iqr_TI_exp1": iqr1,
                    "iqr_TI_exp2": iqr2,
                    "skew_TI_exp1": skew1,
                    "skew_TI_exp2": skew2,
                    "kurt_TI_exp1": kurt1,
                    "kurt_TI_exp2": kurt2,
                    "mad_TI_exp1": mad1,
                    "mad_TI_exp2": mad2,
                    "mean_diff": mean_diff,
                    "std_diff": std_diff,
                    "median_diff": median_diff,
                    "iqr_diff": iqr_diff,
                    "skew_diff": skew_diff,
                    "kurt_diff": kurt_diff,
                    "mad_diff": mad_diff,
                    "cohens_d": cohens_d,
                    "corr_pearson": corr_pearson,
                    "slope": slope,
                    "perc_exp2_maior": float(np.mean(d2[:n] > d1[:n]) * 100.0),
                    "sign_p": sign_p,
                    "CI_low": ci_low,
                    "CI_high": ci_high,
                    "t_stat": float(t_stat),
                    "t_p": float(t_p),
                    "w_stat": float(w_stat) if pd.notna(w_stat) else np.nan,
                    "w_p": float(w_p) if pd.notna(w_p) else np.nan,
                    "n_cycles": int(n),
                }
            )

        dfres = pd.DataFrame(results)
        if not dfres.empty:
            # Multiple testing correction (FDR) for paired tests
            t_corrected = multipletests(dfres["t_p"].fillna(1.0), method="fdr_bh")[1]
            w_corrected = multipletests(dfres["w_p"].fillna(1.0), method="fdr_bh")[1]
            dfres["signif_t"] = t_corrected < 0.05
            dfres["signif_w"] = w_corrected < 0.05

        self.comparison_df = dfres


class ComparisonPlotter:
    """Visualization helper for :class:`ExperimentComparator` outputs.

    Parameters
    ----------
    comparison_df : pandas.DataFrame
        Output of :meth:`ExperimentComparator.compare` with per-KX/channel stats.

    Notes
    -----
    The input DataFrame is expected to contain at least the columns
    ``['kx', 'mean_diff']``. Additional columns such as ``CI_low``, ``CI_high``,
    ``signif_t``/``signif_w`` (booleans) are optionally used for CI/errorbars and
    significance highlights.
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

        Examples
        --------
        >>> plotter = ComparisonPlotter(cmpx.comparison_df)
        >>> _ = plotter.plot_diff(metric="cohens_d", ci=False)
        """
        df = self.df.sort_values("kx")
        if df.empty:
            fig, ax = plt.subplots(figsize=figsize)
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            return ax

        x = df["kx"].astype(str)
        y = df[metric]

        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(x, y, alpha=0.7, label="Difference")

        if ci and {"CI_low", "CI_high"}.issubset(df.columns):
            ax.errorbar(
                x,
                y,
                yerr=[y - df["CI_low"], df["CI_high"] - y],
                fmt="none",
                ecolor="black",
                capsize=4,
                label="95% CI",
            )

        if highlight_significance and {"signif_t", "signif_w"}.issubset(df.columns):
            sig = df["signif_t"] | df["signif_w"]
            for xi, yi, is_sig in zip(x[sig], y[sig], sig[sig]):
                if bool(is_sig):
                    ax.text(str(xi), float(yi), "*", ha="center", va="bottom", fontsize=14)

        ax.axhline(0, color="gray", linestyle="--")
        ax.set_ylabel(f"Δ {metric}")
        ax.set_xlabel("KX / Channel")
        ax.set_title("Impact Comparison Between Experiments", loc="center")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, linestyle="--", alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return ax


def plot_metric_series(
    analyzers: List[ImpactAnalyzer],
    label: str,
    metric: Literal["TI", "FI", "FBI"] = "TI",
    color: Optional[str] = None,
) -> plt.Axes:
    """Plot mean ± std envelopes of a metric across a series of analyzers.

    Parameters
    ----------
    analyzers : list of ImpactAnalyzer
        One analyzer per cycle/time index (all must share the same groups).
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

    Examples
    --------
    >>> axs = [ImpactAnalyzer.from_pair(o, a, var="t") for (o, a) in cycles]
    >>> _ = plot_metric_series(axs, "EXP1", metric="FI")
    """
    # Concatenate per-cycle tables and extract the selected metric
    dfs = [a.compute_all_metrics().set_index("kx") for a in analyzers]
    if not dfs:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    # Ensure consistent ordering by index (KX/channel)
    dfs = [df.sort_index() for df in dfs]
    # Stack into (n_cycles, n_groups); raises if groups differ
    vals = [df[metric] for df in dfs]
    arr = np.stack([v.values for v in vals])  # shape: n_cycles x n_groups
    kx = dfs[0].index.values

    fig, ax = plt.subplots(figsize=(12, 6))
    # All individual series in light gray for context
    for row in arr:
        ax.plot(kx, row, color="lightgray", alpha=0.6, zorder=1)

    # Mean ± std envelope
    mu = arr.mean(axis=0)
    sd = arr.std(axis=0)
    base_color = color or "C0"
    ax.plot(kx, mu, marker="o", color=base_color, label="Mean", zorder=2)
    ax.fill_between(kx, mu - sd, mu + sd, color=base_color, alpha=0.25, label="±1 STD", zorder=1)

    ax.set_title(f"{label} — {metric} (mean ± std)", loc="center")
    ax.set_xlabel("Channel/KX")
    ax.set_ylabel(metric)
    ax.grid(True, linestyle="--", alpha=0.6)
    ax.legend()
    plt.tight_layout()
    return ax


# ---------------------------------------------------------------------------
# Back-compatibility shims
# ---------------------------------------------------------------------------

# Accept alias `n=` for `top_k=` in plot_impact_bar (old callers)
try:
    _orig_plot_impact_bar = ImpactAnalyzer.plot_impact_bar  # type: ignore[attr-defined]

    def _plot_impact_bar_shim(
        self: ImpactAnalyzer,
        metric: Literal["TI", "FI", "FBI"] = "TI",
        *args,
        n: Optional[int] = None,
        **kwargs,
    ):
        # If old code passes `n=`, map it to the modern `top_k=`
        if n is not None and "top_k" not in kwargs:
            kwargs["top_k"] = n
        return _orig_plot_impact_bar(self, metric, *args, **kwargs)

    ImpactAnalyzer.plot_impact_bar = _plot_impact_bar_shim  # type: ignore[assignment]
except Exception:
    # If anything goes wrong, keep the original method intact.
    pass

