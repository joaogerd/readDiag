import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from typing import Optional, List, Dict, Literal, Tuple
from scipy.stats import skew, kurtosis, linregress, wilcoxon, ttest_rel, median_abs_deviation
from statsmodels.stats.multitest import multipletests
from sklearn.utils import resample

# Importação segura do teste binomial (compatível com qualquer SciPy)
try:
    from scipy.stats import binomtest
    def binom_p(n_greater, n_total):
        return binomtest(n_greater, n_total, p=0.5).pvalue if n_total > 0 else np.nan
except ImportError:
    from scipy.stats import binom_test
    def binom_p(n_greater, n_total):
        return binom_test(n_greater, n_total, p=0.5) if n_total > 0 else np.nan
from .reader import diagAccess


EPSILON = 1e-15  # To avoid division by zero

class ImpactAnalyzer:
    """
    Class for analyzing the impact of observations using OmA and OmF diagnostics.

    This class operates on a diagAccess instance and supports both conventional
    and radiance diagnostic files from GSI. It provides methods to compute
    total impact (TI), fractional impact (FI), and fractional background impact (FBI)
    for each observation group or channel.

    Example:
        >>> ia = ImpactAnalyzer.from_pair("omf_file", "oma_file", var="t")
        >>> metrics_df = ia.compute_all_metrics()
        >>> ia.plot_impact_bar()
    """

    def __init__(self, diag: diagAccess):
        """
        Initialize an ImpactAnalyzer with a diagAccess instance.

        Args:
            diag (diagAccess): Initialized diagAccess object with loaded data.

        Raises:
            ValueError: If diag is conventional and the variable is not set.
        """

        self.diag = diag
        self._validate()

    def _validate(self):
        """
        Validate if diagAccess instance has the required variable for conventional data.

        Raises:
            ValueError: If diagAccess is conventional but variable is missing.
        """

        if self.diag.get_data_type() == 1 and not self.diag.var:
            raise ValueError("diagAccess must be initialized with a var for conventional files.")

    @classmethod
    def from_pair(cls, omf_file: str, oma_file: str, var: Optional[str] = None) -> "ImpactAnalyzer":
        """
        Create an ImpactAnalyzer instance from a pair of OmF and OmA diagnostic files.

        Args:
            omf_file (str): Path to the diagnostic file with OmF.
            oma_file (str): Path to the diagnostic file with OmA (in the omf field).
            var (Optional[str]): Variable of interest (for conv files).

        Returns:
            ImpactAnalyzer: A new instance with merged OmF/OmA data.
        """
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
                    df_omf[kx]['oma'] = df_oma[kx]['omf']
            omf._data_frame[var] = df_omf
        else:
            list_omf = omf.get_data_frame()['dataframes']['diagbufchan_df']
            list_oma = oma.get_data_frame()['dataframes']['diagbufchan_df']
            for df1, df2 in zip(list_omf, list_oma):
                df1['oma'] = df2['omf']

        return cls(omf)

    def _find_error_col(self, df: pd.DataFrame) -> Optional[str]:
        """
        Find the appropriate error column in a DataFrame.

        Args:
            df (pd.DataFrame): DataFrame from diagnostic data.

        Returns:
            Optional[str]: Name of the error column if present, else None.
        """

        for col in ['error', 'end_err']:
            if col in df.columns:
                return col
        return None

    def _calc_ti_component(self, oma: pd.Series, omf: pd.Series, err: pd.Series) -> float:
        """
        Compute the component of total impact (TI) for valid data.

        Args:
            oma (pd.Series): Analysis minus observation vector.
            omf (pd.Series): Forecast minus observation vector.
            err (pd.Series): Error vector (standard deviation).

        Returns:
            float: Total impact numerator for the observation group.
        """

        valid = (err > 0) & np.isfinite(oma) & np.isfinite(omf)
        return ((oma[valid] ** 2 - omf[valid] ** 2) / (err[valid] ** 2)).sum()

    def compute_ti(self) -> Dict[int, float]:
        """
        Compute Total Impact (TI) per kx (conv) or per channel (rad).

        Returns:
            Dict[int, float]: Mapping from kx/channel to total impact (TI).
        """
        is_conv = self.diag.get_data_type() == 1
        ti = {}

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
        """
        Compute TI, FI, and FBI for each observation group.

        Returns:
            pd.DataFrame: Table with kx/channel, TI, FI (%) and FBI (%).
        """
        ti_dict = self.compute_ti()
        total = sum(ti_dict.values())
        total = total if abs(total) > EPSILON else EPSILON

        df = pd.DataFrame([{'kx': k, 'TI': v} for k, v in ti_dict.items()])
        df['FI'] = df['TI'] / total * 100
        df['FBI'] = -df['TI'] / total * 100
        return df.sort_values(by='TI', ascending=True, ignore_index=True)

    def plot_impact_bar(self,
                        metric: Literal['TI', 'FI', 'FBI'] = 'TI',
                        ax: Optional[plt.Axes] = None,
                        color: Optional[str] = None,
                        title: Optional[str] = None,
                        xlabel: Optional[str] = None,
                        ylabel: Optional[str] = None,
                        rotation: int = 45,
                        fontsize: int = 12) -> plt.Axes:
        """
        Plot a horizontal bar chart for a specified impact metric.

        Args:
            metric (Literal['TI', 'FI', 'FBI']): Metric to plot.
            ax (Optional[plt.Axes]): Existing axes object (or None to create).
            color (Optional[str]): Bar color.
            title (Optional[str]): Plot title.
            xlabel (Optional[str]): X-axis label.
            ylabel (Optional[str]): Y-axis label.
            rotation (int): Y-axis tick label rotation.
            fontsize (int): Font size for labels.

        Returns:
            plt.Axes: The matplotlib Axes object.
        """

        df = self.compute_all_metrics()
        df = df.sort_values(by=metric, ascending=(metric != 'TI'))
        ax = ax or plt.subplots(figsize=(10, 6))[1]

        y_labels = df['kx'].astype(str)
        ax.barh(y_labels, df[metric], color=color)

        ax.set_title(title or f"{metric} per kx/channel", fontsize=fontsize + 2)
        ax.set_xlabel(xlabel or metric, fontsize=fontsize)
        ax.set_ylabel(ylabel or "KX / Channel", fontsize=fontsize)
        ax.tick_params(axis='x', labelsize=fontsize)
        ax.tick_params(axis='y', labelsize=fontsize, rotation=rotation)
        ax.grid(True, linestyle='--', alpha=0.6)

        return ax

def plot_all_impact_subplots(
    analyzers: List[ImpactAnalyzer],
    labels: Optional[List[str]] = None,
    metric: str = 'TI',
    suptitle: Optional[str] = None
):
    """
    Plot horizontal bar charts for a list of ImpactAnalyzer objects, aligned for comparison.

    Args:
        analyzers (List[ImpactAnalyzer]): List of ImpactAnalyzer instances.
        labels (Optional[List[str]]): Optional labels for each analyzer.
        metric (str): Metric to plot ('TI', 'FI', 'FBI').
        suptitle (Optional[str]): Optional supertitle for the figure.

    Raises:
        RuntimeError: If no valid data is found for any analyzer.
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
        analyzer.plot_impact_bar(metric=metric, ax=ax, title=f"Impacto {label}")

    if suptitle:
        fig.suptitle(suptitle, fontsize=16)
    plt.tight_layout()
    plt.show()

class ExperimentComparator:
    """
    Compare the impact of two experiments over multiple cycles for a specified variable.

    This class builds statistics for each kx/channel by comparing TI values between
    two sets of experiments (exp1 and exp2). Supports calculation of multiple
    statistics (mean, std, median, IQR, skewness, kurtosis, effect size, correlation,
    temporal trend, proportion, binomial test, significance, etc).

    Args:
        exp1_files (List[Tuple[str, str]]): List of (omf, oma) files for experiment 1.
        exp2_files (List[Tuple[str, str]]): List of (omf, oma) files for experiment 2.
        var (Optional[str]): Variable name (for conventional data).

    Attributes:
        per_cycle_df (pd.DataFrame): DataFrame of TI per experiment, cycle, and kx.
        comparison_df (Optional[pd.DataFrame]): DataFrame of summary statistics per kx.
    """


    def __init__(self, exp1_files: List[Tuple[str, str]],
                       exp2_files: List[Tuple[str, str]],
                       var: Optional[str] = None):
        """
        Initialize an ExperimentComparator.

        Args:
            exp1_files (List[Tuple[str, str]]): List of (omf, oma) for experiment 1.
            exp2_files (List[Tuple[str, str]]): List of (omf, oma) for experiment 2.
            var (Optional[str]): Variable name (for conventional diagnostics).
        """

        self.exp1_files = exp1_files
        self.exp2_files = exp2_files
        self.var = var

        # DataFrame multi-index: ciclo, experimento, kx, TI
        self.per_cycle_df = self._gather_per_cycle()
        self.comparison_df: Optional[pd.DataFrame] = None

    def _gather_per_cycle(self) -> pd.DataFrame:
        """
        Load TI values per cycle and channel/kx for both experiments.

        Returns:
            pd.DataFrame: DataFrame with columns ['cycle', 'experiment', 'kx', 'TI'].
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
            # Assume canais/kx alinhados; pode adaptar para interseção
            for kx in sorted(set(ti1) & set(ti2)):
                rows.append({'cycle': idx, 'experiment': 1, 'kx': kx, 'TI': ti1[kx]})
                rows.append({'cycle': idx, 'experiment': 2, 'kx': kx, 'TI': ti2[kx]})
        return pd.DataFrame(rows)

    def compare(self):
        """
        Compare the two experiments channel by channel, computing comprehensive
        statistical diagnostics and tests.

        For each kx/channel:
            - Computes mean, std, median, IQR, skewness, kurtosis, MAD for both experiments.
            - Computes mean, std, median, IQR, skewness, kurtosis, MAD for the difference (exp2-exp1).
            - Computes Cohen's d effect size, Pearson correlation, and linear trend (slope).
            - Calculates the percentage of cycles where exp2 > exp1, and binomial test.
            - Performs paired t-test and Wilcoxon test (with FDR correction).
            - Estimates bootstrap confidence interval for the mean difference.
            - Flags significance for both t and Wilcoxon tests.

        Returns:
            None. Results are stored in self.comparison_df.
        """

        df = self.per_cycle_df
        all_kx = sorted(df['kx'].unique())
        results = []

        for kx in all_kx:
            d1 = df[(df['experiment']==1) & (df['kx']==kx)].sort_values("cycle")['TI'].values
            d2 = df[(df['experiment']==2) & (df['kx']==kx)].sort_values("cycle")['TI'].values
            n = min(len(d1), len(d2))
            if n < 2:
                continue
            diffs = d2[:n] - d1[:n]
        
            # Bootstrap para CI média
            boots = [resample(diffs, n_samples=n) for _ in range(1000)]
            means = [b.mean() for b in boots]
            ci_low = np.percentile(means, 2.5)
            ci_high = np.percentile(means, 97.5)
        
            # Estatísticas clássicas
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
        
            # Tamanho do efeito (Cohen's d)
            cohens_d = mean_diff / (std_diff if std_diff > 0 else 1e-12)
        
            # Correlação
            if std1 > 0 and std2 > 0:
                corr_pearson = np.corrcoef(d1[:n], d2[:n])[0,1]
            else:
                corr_pearson = np.nan
        
            # Tendência temporal (slope da diferença)
            slope = linregress(np.arange(n), diffs).slope if n >= 2 else np.nan
        
            # % de vezes que exp2 > exp1
            perc_exp2_maior = np.mean(d2[:n] > d1[:n]) * 100
        
            # Teste de sinal binomial
            n_greater = np.sum(d2[:n] > d1[:n])
            n_less = np.sum(d2[:n] < d1[:n])
            n_total = n_greater + n_less
            sign_p = binom_p(n_greater, n_total)
            
            # Testes estatísticos
            t_stat, t_p = ttest_rel(d1[:n], d2[:n])
            try:
                w_stat, w_p = wilcoxon(d1[:n], d2[:n])
            except ValueError:
                w_stat, w_p = np.nan, np.nan
        
            results.append({
                'kx': kx,
                'mean_TI_exp1': mean1,
                'mean_TI_exp2': mean2,
                'std_TI_exp1': std1,
                'std_TI_exp2': std2,
                'median_TI_exp1': median1,
                'median_TI_exp2': median2,
                'iqr_TI_exp1': iqr1,
                'iqr_TI_exp2': iqr2,
                'skew_TI_exp1': skew1,
                'skew_TI_exp2': skew2,
                'kurt_TI_exp1': kurt1,
                'kurt_TI_exp2': kurt2,
                'mad_TI_exp1': mad1,
                'mad_TI_exp2': mad2,
        
                'mean_diff': mean_diff,
                'std_diff': std_diff,
                'median_diff': median_diff,
                'iqr_diff': iqr_diff,
                'skew_diff': skew_diff,
                'kurt_diff': kurt_diff,
                'mad_diff': mad_diff,
                'cohens_d': cohens_d,
                'corr_pearson': corr_pearson,
                'slope': slope,
                'perc_exp2_maior': perc_exp2_maior,
                'sign_p': sign_p,
        
                'CI_low': ci_low,
                'CI_high': ci_high,
                't_stat': t_stat, 't_p': t_p,
                'w_stat': w_stat, 'w_p': w_p,
                'n_cycles': n
            })
        # Correção múltiplos testes
        dfres = pd.DataFrame(results)
        if not dfres.empty:
            t_corrected = multipletests(dfres['t_p'].fillna(1), method="fdr_bh")[1]
            w_corrected = multipletests(dfres['w_p'].fillna(1), method="fdr_bh")[1]
            dfres['signif_t'] = t_corrected < 0.05
            dfres['signif_w'] = w_corrected < 0.05

        self.comparison_df = dfres

class ComparisonPlotter:
    """
    Visualization utility for plotting experiment impact comparisons.

    Attributes:
        df (pd.DataFrame): DataFrame with statistics for each kx/channel.

    Methods:
        plot_diff(...): Plots the difference in impact per kx/channel, with confidence intervals
                        and significance highlighting.
    """


    def __init__(self, comparison_df: pd.DataFrame):
        """
        Initialize a ComparisonPlotter.

        Args:
            comparison_df (pd.DataFrame): DataFrame with statistics per kx/channel.
        """

        self.df = comparison_df

    def plot_diff(self, metric: str = "diff", ci: bool = True, highlight_significance: bool = True, figsize=(12, 6)) -> plt.Axes:
        """
        Plot the difference in impact (or any metric) between two experiments,
        including confidence intervals and significance markers.

        Args:
            metric (str): Name of the column to plot (e.g., 'mean_diff', 'cohens_d').
            ci (bool): Whether to show the confidence interval as error bars.
            highlight_significance (bool): Whether to highlight significant differences.
            figsize (tuple): Figure size.

        Returns:
            plt.Axes: The matplotlib Axes object.
        """

        df = self.df.sort_values("kx")
        x = df["kx"].astype(str)
        y = df[metric]

        fig, ax = plt.subplots(figsize=figsize)
        ax.bar(x, y, color='steelblue', alpha=0.7, label="Difference")

        if ci:
            ax.errorbar(x, y,
                        yerr=[y - df["CI_low"], df["CI_high"] - y],
                        fmt='none', ecolor='black', capsize=4, label="95% CI")

        if highlight_significance:
            sig = df["signif_t"] | df["signif_w"]
            for xi, yi, is_sig in zip(x[sig], y[sig], sig[sig]):
                if is_sig:
                    ax.text(xi, yi, "*", ha='center', va='bottom', fontsize=14, color='darkred')

        ax.axhline(0, color='gray', linestyle='--')
        ax.set_ylabel(f"Δ {metric}")
        ax.set_xlabel("KX / Channel")
        ax.set_title("Impact Comparison Between Experiments")
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, linestyle='--', alpha=0.5)
        ax.legend()
        plt.tight_layout()
        return ax

def plot_metric_series(analyzers, label, metric="TI", color=None):
    
    """
    Plot the mean and standard deviation of a specified metric for a series of analyzers.

    Args:
        analyzers (List[ImpactAnalyzer]): List of ImpactAnalyzer instances.
        label (str): Series label.
        metric (str): Metric to plot ('TI', 'FI', or 'FBI').
        color (Optional[str]): Color for mean/STD band.
    """

    # Empilha DataFrames para fazer média e erro
    dfs = [a.compute_all_metrics().set_index('kx') for a in analyzers]
    df_all = pd.concat(dfs, axis=1, keys=range(len(dfs)))
    # Extrai apenas as colunas do metric
    vals = [df[metric] for df in dfs]
    # Organiza em matriz (shape: n_ciclos x n_canais)
    arr = np.stack([v.values for v in vals])
    kx = dfs[0].index.values

    plt.figure(figsize=(12, 6))
    # Todas as séries, cinza claro
    for row in arr:
        plt.plot(kx, row, color='lightgray', alpha=0.6, zorder=1)
    # Média + erro
    plt.plot(kx, arr.mean(axis=0), marker='o', color='C0', label="Média", zorder=2)
    plt.fill_between(kx, arr.mean(axis=0) - arr.std(axis=0), arr.mean(axis=0) + arr.std(axis=0),
                     color='C0', alpha=0.25, label="±1 STD", zorder=1)
    plt.title(f"{label} - {metric} (média ± std)")
    plt.xlabel("Channel/KX")
    plt.ylabel(metric)
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.show()


