# --- readDiag/legacy.py ------------------------------------------------------
from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd

from readDiag.io.reader import diagAccess
from .impact_legacy import ImpactAnalyzer
from .plotting import diagPlotter
from .utils import deprecated




class read_diag:
    """
    Legacy compatibility wrapper.

    Parameters
    ----------
    files : str | Path | list[str | Path]
        Single file (conv/rad) or a pair of files (impact use-cases).
    **kwargs : Any
        Passed to :class:`readDiag.reader.diagAccess` for each file.

    Notes
    -----
    Deprecated. Prefer the functional API (`read_conv`, `read_rad`, `read_any`)
    and :class:`ImpactAnalyzer.from_pair` for impact.
    """

    def __init__(self, files: str | Path | list[str | Path], **kwargs: Any) -> None:
        deprecated(
            "read_diag (legacy) is deprecated; use diagAccess (single file) or "
            "ImpactAnalyzer.from_pair(file1, file2, ...) for impact."
        )
        if isinstance(files, (str, Path)):
            files = [files]
        self.paths: List[str] = [str(Path(p)) for p in files]
        if not self.paths:
            raise ValueError("No files provided to read_diag().")

        # Instâncias do leitor moderno
        self._diags: List[diagAccess] = [diagAccess(p, **kwargs) for p in self.paths]
        # Plotter baseado no primeiro arquivo (igual ao legacy)
        self.plotter = diagPlotter(self._diags[0])

    # --- handles legacy-friendly ---
    @property
    def diag1(self) -> diagAccess:
        return self._diags[0]

    @property
    def diag2(self) -> Optional[diagAccess]:
        return self._diags[1] if len(self._diags) > 1 else None

    # --- acesso a dados (atalhos legacy) ---
    def get_variables(self) -> List[str]:
        deprecated("get_variables() is deprecated; use diag1.get_variables().")
        return self.diag1.get_variables()

    def get_kx_list(self, var: str) -> List[int]:
        deprecated("get_kx_list() is deprecated; use diag1.get_kx_list(var).")
        return self.diag1.get_kx_list(var)

    def to_dataframe(self, var: str, kx: int) -> pd.DataFrame:
        deprecated("to_dataframe() is deprecated; use diag1.get_dataframe(var, kx).")
        return self.diag1.get_dataframe(var, kx)

    # --- impacto (2 arquivos) ---
    def impact(self, var: Optional[str] = None, **opts: Any) -> ImpactAnalyzer:
        deprecated("read_diag.impact() is deprecated; use ImpactAnalyzer.from_pair().")
        if self.diag2 is None:
            raise ValueError("Two files required for impact().")
        return ImpactAnalyzer.from_pair(self.paths[0], self.paths[1], var=var, **opts)

    # --- plotagem: nomes exatamente como o legacy ---
    def plot(self, var: str, **kwargs):
        """
        Legacy generic plot. Por padrão, encaminha para plot_observation_counts.
        """
        deprecated("plot() legacy; use diagPlotter(...).plot_observation_counts().")
        return self.plotter.plot_observation_counts(var, **kwargs)

    def ptmap(self, varName: str, varType: Optional[int | List[int]] = None, **kwargs):
        """
        Point map (conv): encaminha para plot_spatial_conv.
        Mantém assinatura (varName, varType, ...).
        """
        deprecated("ptmap() is deprecated; use plot_ptmap().")
        return self.plotter.plot_ptmap(varName=varName, varType=varType, **kwargs)

    def pvmap(self, varName: Optional[str | List[str]] = None, **kwargs):
        """
        Value map (conv): spatial colored by `column` (default=omf).
        """
        deprecated("pvmap() is deprecated; use plot_pvmap().")
        return self.plotter.plot_pvmap(varName=varName, **kwargs)

    def pcount(self, var: str, **kwargs):
        """
        Legacy: observation counts por kx.
        """
        deprecated("pcount() is deprecated; use plot_observation_counts().")
        return self.plotter.plot_observation_counts(var, **kwargs)

    def kxcount(self, var: str | None = None, **kwargs):
        """
        Legacy: total count by KX (bar chart).
    
        """
        deprecated("kxcount() is deprecated; use plot_kx_count().")
        # Evita que 'var' ou 'varName' escapem dentro de kwargs e cheguem no Axes.bar(...)
        kwargs.pop("var", None)
        kwargs.pop("varName", None)
        return self.plotter.plot_kx_count(**kwargs)
    
    def vcount(self, var: str, kx: int | None = None, column: str = "omf", bins: int = 50, **kwargs):
        """
        Legacy: histogram/distribution of a column for a variable (optionally a kx).
        Compat behavior: if kx is None, pick the first available kx for the variable.
        """
        deprecated("vcount() is deprecated; use plot_hist_conv() instead")
        if kx is None:
            kxs = self.diag1.get_kx_list(var)
            if not kxs:
                raise ValueError(f"No kx available for variable '{var}'.")
            kx = int(kxs[0])
        return self.plotter.plot_hist_conv(var=var, kx=kx, col=column, bins=bins, **kwargs)


    # --- timeseries do legacy: versões compat usando pandas ---
    def plot_time_series_mean(
        self,
        var: str,
        kx: Optional[int] = None,
        column: str = "omf",
        res: str = "1H",
        **kwargs,
    ):
        """
        Série temporal (média) para conv: agrupa por timestamp arredondado (`res`).

        Compat: se `kx` for None, agrega sobre todos os kx da variável.
        """
        deprecated("plot_time_series_mean() legacy; substituir por painel custom.")
        import matplotlib.pyplot as plt

        def _df_for_kx(k: int) -> pd.DataFrame:
            df = self.diag1.get_dataframe(var, k)
            t = pd.to_datetime(df["time"], errors="coerce", unit="h", origin="unix")
            g = df.assign(ts=t).set_index("ts").resample(res)[column].mean()
            return g.to_frame(name=f"{var}-{k}")

        if kx is None:
            kxs = self.diag1.get_kx_list(var)
        else:
            kxs = [kx]

        series = []
        for k in kxs:
            try:
                series.append(_df_for_kx(k))
            except Exception:
                continue
        if not series:
            raise ValueError("No time series could be created for the given selection.")

        df_ts = pd.concat(series, axis=1)
        ax = df_ts.plot(**kwargs)
        ax.set_title(kwargs.get("title", f"Mean {column} over time - {var}"))
        ax.set_ylabel(f"{column} (mean)")
        return ax

    def plot_time_series_mean_std(
        self,
        var: str,
        kx: Optional[int] = None,
        column: str = "omf",
        res: str = "1H",
        **kwargs,
    ):
        """
        Série temporal (média ± desvio) para conv (legacy compat).
        """
        deprecated("plot_time_series_mean_std() legacy; substituir por painel custom.")
        import matplotlib.pyplot as plt

        # usa o método acima para obter a média
        ax = self.plot_time_series_mean(var=var, kx=kx, column=column, res=res, **kwargs)

        # re-agrega para std e plota com fill_between
        def _std_for_kx(k: int) -> pd.Series:
            df = self.diag1.get_dataframe(var, k)
            t = pd.to_datetime(df["time"], errors="coerce", unit="h", origin="unix")
            return df.assign(ts=t).set_index("ts").resample(res)[column].std().rename(k)

        kxs = [kx] if kx is not None else self.diag1.get_kx_list(var)
        stds = pd.concat([_std_for_kx(k) for k in kxs], axis=1)
        std = stds.mean(axis=1)

        mean_df = ax.lines[0].get_xdata(), ax.lines[0].get_ydata()
        # tentativa simples de “desenhar envelope” com mesmo index
        try:
            x = std.index.intersection(ax.lines[0].get_xdata())
            m = pd.Series(ax.lines[0].get_ydata(), index=ax.lines[0].get_xdata()).reindex(x)
            s = std.reindex(x).values
            ax.fill_between(x, m - s, m + s, alpha=0.2)
        except Exception:
            pass

        ax.set_title(kwargs.get("title", f"Mean ± Std {column} over time - {var}"))
        ax.set_ylabel(f"{column} (mean ± std)")
        return ax

    # --- utilitário legacy frequente ---
    @staticmethod
    def filter_multiindex(df: pd.DataFrame, **levels) -> pd.DataFrame:
        """
        Legacy helper: filtra DataFrame com MultiIndex por valores de níveis.
        Ex.: filter_multiindex(df, var='t', kx=187)
        """
        deprecated("filter_multiindex() legacy; use df.xs(...) ou df.query(...).")
        if not isinstance(df.index, pd.MultiIndex):
            return df
        idx = pd.IndexSlice
        # cria um tuple com None para níveis não filtrados
        keys = []
        for name in df.index.names:
            keys.append(levels.get(name, slice(None)))
        return df.loc[tuple(keys)]

