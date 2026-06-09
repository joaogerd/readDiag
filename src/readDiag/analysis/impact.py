# src/readDiag/analysis/impact.py
"""
Observation-impact analysis utilities for readDiag.

This module computes GSI-style observation impact metrics from OmF/OmA
pairs. It supports:

- conventional diagnostics, either for one selected variable or for the full
  ``diag_conv`` file when ``var=None``;
- radiance diagnostics, grouped by 1-based channel;
- simple plotting helpers and multi-experiment comparison utilities.

Notes
-----
For conventional diagnostics, the default reader returns a nested mapping with
shape ``{var -> {kx -> DataFrame}}``. When ``var=None``, impact is accumulated
across all common variables and grouped by KX. When ``var`` is provided, only
that variable is used.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Literal, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import (
    kurtosis,
    linregress,
    median_abs_deviation,
    skew,
    ttest_rel,
    wilcoxon,
)

from statsmodels.stats.multitest import multipletests
from sklearn.utils import resample

try:  # pragma: no cover - SciPy compatibility shim
    from scipy.stats import binomtest

    def binom_p(n_greater: int, n_total: int) -> float:
        """Return a two-sided binomial p-value under p=0.5."""
        return binomtest(n_greater, n_total, p=0.5).pvalue if n_total > 0 else np.nan

except Exception:  # pragma: no cover - older SciPy compatibility shim
    from scipy.stats import binom_test

    def binom_p(n_greater: int, n_total: int) -> float:
        """Return a two-sided binomial p-value under p=0.5."""
        return float(binom_test(n_greater, n_total, p=0.5)) if n_total > 0 else np.nan

from ..reader import diagAccess

EPSILON: float = 1e-15

__all__ = [
    "ImpactAnalyzer",
    "plot_all_impact_subplots",
    "ExperimentComparator",
    "ComparisonPlotter",
    "plot_metric_series",
]


class ImpactAnalyzer:
    """Analyze observation impact from OmF/OmA diagnostic pairs.

    Parameters
    ----------
    diag : diagAccess
        Diagnostic reader instance already containing OmF and injected OmA
        columns. For conventional diagnostics this may represent either one
        variable or a complete ``diag_conv`` file.
    """

    def __init__(self, diag: diagAccess):
        self.diag = diag
        self._validate()

    def _validate(self) -> None:
        """Validate the underlying diagnostic object."""
        dtype = self.diag.get_data_type()
        if dtype not in (1, 2):
            raise ValueError("Unsupported diagnostic type. Expected conv=1 or rad=2.")

        data = self.diag.get_data_frame()
        if data is None:
            raise ValueError("Diagnostic object does not contain decoded data.")

        if dtype == 1 and not isinstance(data, dict):
            raise ValueError("Conventional diagnostics must expose a variable mapping.")

    @classmethod
    def from_pair(
        cls,
        omf_file: str,
        oma_file: str,
        var: Optional[str] = None,
    ) -> "ImpactAnalyzer":
        """Build an analyzer from paired OmF and OmA diagnostic files.

        Parameters
        ----------
        omf_file : str
            Path to the diagnostic file containing OmF values.
        oma_file : str
            Path to the diagnostic file containing OmA values. In GSI diagnostic
            files this value is stored in the same ``omf``-style column layout.
        var : str, optional
            Conventional variable to analyze. If omitted for conventional files,
            all common variables are analyzed and accumulated by KX.

        Returns
        -------
        ImpactAnalyzer
            Analyzer whose internal diagnostic contains both OmF and OmA columns.
        """
        omf = diagAccess(omf_file, var=var)
        oma = diagAccess(oma_file, var=var)

        if omf.get_data_type() != oma.get_data_type():
            raise ValueError("Files must be of the same type (conv or rad).")

        if omf.get_data_type() == 1:
            cls._inject_conv_oma(omf, oma, var=var)
        else:
            cls._inject_rad_oma(omf, oma)

        return cls(omf)

    @staticmethod
    def _common_conv_variables(
        omf_data: Dict[str, Dict[int, pd.DataFrame]],
        oma_data: Dict[str, Dict[int, pd.DataFrame]],
        var: Optional[str],
    ) -> List[str]:
        """Return variables that can be paired between OmF and OmA data."""
        if var is not None:
            if var not in omf_data:
                raise ValueError(f"Variable {var!r} not found in OmF diagnostic.")
            if var not in oma_data:
                raise ValueError(f"Variable {var!r} not found in OmA diagnostic.")
            return [var]

        variables = sorted(set(omf_data) & set(oma_data))
        if not variables:
            raise ValueError("No common conventional variables found between OmF and OmA.")
        return variables

    @staticmethod
    def _inject_conv_oma(omf: diagAccess, oma: diagAccess, var: Optional[str]) -> None:
        """Inject OmA columns into conventional OmF frames in-place."""
        omf_data = omf.get_data_frame()
        oma_data = oma.get_data_frame()
        variables = ImpactAnalyzer._common_conv_variables(omf_data, oma_data, var)

        for variable in variables:
            omf_groups = omf_data[variable]
            oma_groups = oma_data[variable]
            for kx, frame in omf_groups.items():
                oma_frame = oma_groups.get(kx)
                if not isinstance(frame, pd.DataFrame):
                    continue
                if not isinstance(oma_frame, pd.DataFrame):
                    continue

                # Scalar conventional variables: t, q, ps, wst, etc.
                if "omf" in frame.columns and "omf" in oma_frame.columns:
                    frame["oma"] = oma_frame["omf"].to_numpy(copy=False)

                # Vector wind conventional variable. Depending on reader settings,
                # both components may or may not be available.
                for component in ("u", "v"):
                    omf_col = f"omf_{component}"
                    oma_col = f"oma_{component}"
                    if omf_col in frame.columns and omf_col in oma_frame.columns:
                        frame[oma_col] = oma_frame[omf_col].to_numpy(copy=False)

            omf._data_frame[variable] = omf_groups  # type: ignore[attr-defined]

    @staticmethod
    def _inject_rad_oma(omf: diagAccess, oma: diagAccess) -> None:
        """Inject OmA columns into radiance channel frames in-place."""
        omf_data = omf.get_data_frame()
        oma_data = oma.get_data_frame()
        list_omf = omf_data["dataframes"]["diagbufchan_df"]
        list_oma = oma_data["dataframes"]["diagbufchan_df"]

        for df_omf, df_oma in zip(list_omf, list_oma):
            if not isinstance(df_omf, pd.DataFrame):
                continue
            if not isinstance(df_oma, pd.DataFrame):
                continue
            if "omf" in df_omf.columns and "omf" in df_oma.columns:
                df_omf["oma"] = df_oma["omf"].to_numpy(copy=False)

    @staticmethod
    def _iter_conv_frames(
        data: Dict[str, Dict[int, pd.DataFrame]],
        var: Optional[str],
    ) -> Iterable[Tuple[str, int, pd.DataFrame]]:
        """Yield ``(variable, kx, DataFrame)`` tuples from conventional data."""
        variables = [var] if var is not None else sorted(data.keys())

        for variable in variables:
            if variable not in data:
                continue
            groups = data[variable]
            for kx, frame in groups.items():
                if not isinstance(frame, pd.DataFrame) or frame.empty:
                    continue

                if kx == "__ALL__" and "kx" in frame.columns:
                    for group_kx, group_df in frame.groupby(frame["kx"].astype(int)):
                        yield variable, int(group_kx), group_df
                    continue

                try:
                    kx_int = int(kx)
                except (TypeError, ValueError):
                    if "kx" not in frame.columns:
                        continue
                    for group_kx, group_df in frame.groupby(frame["kx"].astype(int)):
                        yield variable, int(group_kx), group_df
                    continue

                yield variable, kx_int, frame

    @staticmethod
    def _omf_oma_pairs(df: pd.DataFrame) -> List[Tuple[str, str]]:
        """Return OmF/OmA column pairs available in a frame."""
        pairs: List[Tuple[str, str]] = []

        if {"omf", "oma"}.issubset(df.columns):
            pairs.append(("omf", "oma"))

        for component in ("u", "v"):
            omf_col = f"omf_{component}"
            oma_col = f"oma_{component}"
            if {omf_col, oma_col}.issubset(df.columns):
                pairs.append((omf_col, oma_col))

        return pairs

    @staticmethod
    def _find_error_weight(df: pd.DataFrame) -> Tuple[Optional[str], bool]:
        """Return an error column and whether it is inverse-error.

        Returns
        -------
        tuple
            ``(column_name, is_inverse_error)``. For inverse-error columns, TI is
            computed as ``(OMA² - OMF²) * errinv²``. For sigma/error columns, TI
            is computed as ``(OMA² - OMF²) / sigma²``.
        """
        inverse_candidates = (
            "errinv",
            "errinv_fin",
            "end_err",
            "errinv_adj",
            "adj_err",
            "errinv_inp",
            "inp_err",
        )
        sigma_candidates = (
            "error",
            "obs_error",
            "obserr",
            "sigma",
            "stddev",
        )

        for col in inverse_candidates:
            if col in df.columns:
                return col, True

        for col in sigma_candidates:
            if col in df.columns:
                return col, False

        return None, False

    @staticmethod
    def _calc_ti_component(
        oma: pd.Series,
        omf: pd.Series,
        error_value: pd.Series,
        *,
        inverse_error: bool,
    ) -> float:
        """Compute one TI contribution from aligned OmA/OmF/error vectors."""
        oma_arr = pd.to_numeric(oma, errors="coerce")
        omf_arr = pd.to_numeric(omf, errors="coerce")
        err_arr = pd.to_numeric(error_value, errors="coerce").replace(0, np.nan)

        valid = np.isfinite(oma_arr) & np.isfinite(omf_arr) & np.isfinite(err_arr)
        valid &= err_arr > 0

        if not valid.any():
            return 0.0

        diff = oma_arr[valid] ** 2 - omf_arr[valid] ** 2
        if inverse_error:
            return float((diff * (err_arr[valid] ** 2)).sum())

        return float((diff / (err_arr[valid] ** 2)).sum())

    def compute_ti(self) -> Dict[int, float]:
        """Compute Total Impact (TI) by KX or channel.

        Returns
        -------
        dict[int, float]
            For conventional diagnostics, keys are KX codes. If ``diag.var`` is
            ``None``, TI is accumulated across all conventional variables. For
            radiance diagnostics, keys are 1-based channel numbers.
        """
        ti: Dict[int, float] = {}

        if self.diag.get_data_type() == 1:
            data = self.diag.get_data_frame()
            selected_var = getattr(self.diag, "var", None)

            for _variable, kx, df in self._iter_conv_frames(data, selected_var):
                pairs = self._omf_oma_pairs(df)
                if not pairs:
                    continue

                err_col, inverse_error = self._find_error_weight(df)
                if err_col is None:
                    continue

                group_ti = 0.0
                for omf_col, oma_col in pairs:
                    group_ti += self._calc_ti_component(
                        df[oma_col],
                        df[omf_col],
                        df[err_col],
                        inverse_error=inverse_error,
                    )

                ti[kx] = ti.get(kx, 0.0) + group_ti

            return ti

        df_list = self.diag.get_data_frame()["dataframes"]["diagbufchan_df"]
        for ch, df in enumerate(df_list, start=1):
            if not isinstance(df, pd.DataFrame) or df.empty:
                continue
            if not {"omf", "oma", "errinv"}.issubset(df.columns):
                continue
            ti[int(ch)] = self._calc_ti_component(
                df["oma"],
                df["omf"],
                df["errinv"],
                inverse_error=True,
            )

        return ti

    def compute_all_metrics(self) -> pd.DataFrame:
        """Compute TI, FI and FBI per group."""
        ti_dict = self.compute_ti()
        if not ti_dict:
            return pd.DataFrame(columns=["kx", "TI", "FI", "FBI"])

        df = pd.DataFrame([{"kx": int(k), "TI": float(v)} for k, v in ti_dict.items()])
        denom = np.abs(df["TI"]).sum()
        denom = denom if denom > EPSILON else EPSILON
        df["FI"] = df["TI"] / denom * 100.0
        df["FBI"] = -df["FI"]
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
        """Plot a horizontal bar chart for the selected metric."""
        df = self.compute_all_metrics()
        if df.empty:
            ax = ax or plt.subplots(figsize=(10, 2))[1]
            ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
            ax.set_axis_off()
            return ax

        df = df.sort_values(by=metric, ascending=(metric != "TI"))
        if top_k is not None and top_k > 0:
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
    """Plot aligned horizontal bar charts for multiple analyzers."""
    dfs = [a.compute_all_metrics() for a in analyzers]
    all_vals = [df[metric] for df in dfs if not df.empty]
    if not all_vals:
        raise RuntimeError("No valid data found in any analyzer.")

    n = len(analyzers)
    fig, axs = plt.subplots(n, 1, figsize=(10, 3.5 * n), sharex=True)
    if n == 1:
        axs = [axs]

    for i, (ax, analyzer) in enumerate(zip(axs, analyzers)):
        label = labels[i] if labels and i < len(labels) else f"Plot {i + 1}"
        analyzer.plot_impact_bar(metric=metric, ax=ax, title=f"Impact {label}")

    if suptitle:
        fig.suptitle(suptitle, fontsize=16)
    plt.tight_layout()
    return axs[-1]


class ExperimentComparator:
    """Compare impact between two experiments across cycles."""

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
        """Load TI values per cycle and per KX/channel for both experiments."""
        rows: List[Dict[str, float]] = []
        n_cycles = min(len(self.exp1_files), len(self.exp2_files))

        for idx in range(n_cycles):
            omf1, oma1 = self.exp1_files[idx]
            omf2, oma2 = self.exp2_files[idx]
            ia1 = ImpactAnalyzer.from_pair(omf1, oma1, var=self.var)
            ia2 = ImpactAnalyzer.from_pair(omf2, oma2, var=self.var)
            ti1 = ia1.compute_ti()
            ti2 = ia2.compute_ti()

            for kx in sorted(set(ti1) & set(ti2)):
                rows.append({"cycle": idx, "experiment": 1, "kx": int(kx), "TI": float(ti1[kx])})
                rows.append({"cycle": idx, "experiment": 2, "kx": int(kx), "TI": float(ti2[kx])})

        return pd.DataFrame(rows)

    def compare(self) -> None:
        """Compute statistics comparing experiment 2 against experiment 1."""
        df = self.per_cycle_df
        if df.empty:
            self.comparison_df = pd.DataFrame()
            return

        all_kx = sorted(df["kx"].unique())
        results: List[Dict[str, float]] = []

        for kx in all_kx:
            d1 = df[(df["experiment"] == 1) & (df["kx"] == kx)].sort_values("cycle")["TI"].values
            d2 = df[(df["experiment"] == 2) & (df["kx"] == kx)].sort_values("cycle")["TI"].values
            n = min(len(d1), len(d2))
            if n < 2:
                continue

            d1 = d1[:n]
            d2 = d2[:n]
            diffs = d2 - d1

            boots = [resample(diffs, n_samples=n) for _ in range(1000)]
            means = np.asarray([b.mean() for b in boots])
            ci_low = float(np.percentile(means, 2.5))
            ci_high = float(np.percentile(means, 97.5))

            mean1, mean2 = float(d1.mean()), float(d2.mean())
            std1, std2 = float(d1.std()), float(d2.std())
            median1, median2 = float(np.median(d1)), float(np.median(d2))
            iqr1 = float(np.percentile(d1, 75) - np.percentile(d1, 25))
            iqr2 = float(np.percentile(d2, 75) - np.percentile(d2, 25))
            skew1, skew2 = float(skew(d1)), float(skew(d2))
            kurt1, kurt2 = float(kurtosis(d1)), float(kurtosis(d2))
            mad1, mad2 = float(median_abs_deviation(d1)), float(median_abs_deviation(d2))

            mean_diff = float(diffs.mean())
            std_diff = float(diffs.std())
            median_diff = float(np.median(diffs))
            iqr_diff = float(np.percentile(diffs, 75) - np.percentile(diffs, 25))
            skew_diff = float(skew(diffs))
            kurt_diff = float(kurtosis(diffs))
            mad_diff = float(median_abs_deviation(diffs))
            cohens_d = float(mean_diff / (std_diff if std_diff > 0 else 1e-12))

            corr_pearson = float(np.corrcoef(d1, d2)[0, 1]) if std1 > 0 and std2 > 0 else np.nan
            slope = float(linregress(np.arange(n), diffs).slope) if n >= 2 else np.nan

            n_greater = int(np.sum(d2 > d1))
            n_less = int(np.sum(d2 < d1))
            n_total = int(n_greater + n_less)
            sign_p = float(binom_p(n_greater, n_total))

            t_stat, t_p = ttest_rel(d1, d2)
            try:
                w_stat, w_p = wilcoxon(d1, d2)
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
                    "perc_exp2_maior": float(np.mean(d2 > d1) * 100.0),
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
            t_corrected = multipletests(dfres["t_p"].fillna(1.0), method="fdr_bh")[1]
            w_corrected = multipletests(dfres["w_p"].fillna(1.0), method="fdr_bh")[1]
            dfres["signif_t"] = t_corrected < 0.05
            dfres["signif_w"] = w_corrected < 0.05

        self.comparison_df = dfres


class ComparisonPlotter:
    """Visualization helper for :class:`ExperimentComparator` outputs."""

    def __init__(self, comparison_df: pd.DataFrame):
        self.df = comparison_df

    def plot_diff(
        self,
        metric: str = "mean_diff",
        ci: bool = True,
        highlight_significance: bool = True,
        figsize: Tuple[int, int] = (12, 6),
    ) -> plt.Axes:
        """Plot differences between experiments with CI and significance markers."""
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
    """Plot mean ± std envelopes of a metric across a series of analyzers."""
    dfs = [a.compute_all_metrics().set_index("kx") for a in analyzers]
    if not dfs:
        fig, ax = plt.subplots(figsize=(10, 2))
        ax.text(0.5, 0.5, "No data", ha="center", va="center", transform=ax.transAxes)
        ax.set_axis_off()
        return ax

    dfs = [df.sort_index() for df in dfs]
    vals = [df[metric] for df in dfs]
    arr = np.stack([v.values for v in vals])
    kx = dfs[0].index.values

    fig, ax = plt.subplots(figsize=(12, 6))
    for row in arr:
        ax.plot(kx, row, color="lightgray", alpha=0.6, zorder=1)

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
# Backward-compatibility shims
# ---------------------------------------------------------------------------
try:
    _orig_plot_impact_bar = ImpactAnalyzer.plot_impact_bar  # type: ignore[attr-defined]

    def _plot_impact_bar_shim(
        self: ImpactAnalyzer,
        metric: Literal["TI", "FI", "FBI"] = "TI",
        *args,
        n: Optional[int] = None,
        **kwargs,
    ):
        if n is not None and "top_k" not in kwargs:
            kwargs["top_k"] = n
        return _orig_plot_impact_bar(self, metric, *args, **kwargs)

    ImpactAnalyzer.plot_impact_bar = _plot_impact_bar_shim  # type: ignore[assignment]
except Exception:
    pass
