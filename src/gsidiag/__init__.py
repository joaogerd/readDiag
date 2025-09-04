# src/gsidiag/__init__.py
"""
Legacy compatibility layer for old scripts that used `gsidiag`.

Example (legacy):
    import gsidiag as gd
    conv = gd.read_diag("path/to/diag_conv_01.YYYYMMDDHH")
    conv.pfileinfo()
    conv.plot("t", "120", "omb")

This shim delegates to `readDiag`'s current API and will be removed in 3.0.0.
"""

from __future__ import annotations
from warnings import warn
from typing import Optional, List, Dict, Any
import pandas as pd

# Import new API
from readDiag import AccessAdapter, diagAccess

# Try to wire the modern plotter if available
try:
    # in many trees it's exported at package top-level
    from readDiag import diagPlotter as _PlotterClass  # type: ignore
except Exception:
    _PlotterClass = None  # plotting will be unavailable

__all__ = ["read_diag", "LegacyHandle"]


class LegacyHandle:
    """
    Wrapper that emulates the legacy `read_diag` public API.

    Notes
    -----
    - This class wraps a new `AccessAdapter` instance (self._d).
    - Plotting methods delegate to the modern plotter when present.
    - Some time-series helpers are approximations since the new API
      may not expose exactly the same internal structures.
    """

    # ---------- lifecycle ----------
    def __init__(self, adapter: AccessAdapter):
        self._d = adapter
        self._plotter = _PlotterClass(self._d) if _PlotterClass else None

    # ---------- core (“surface contract”) ----------
    def kind(self) -> str:
        return self._d.kind()

    def variables(self) -> List[str]:
        return list(self._d.variables())

    def kx_list(self, var: Optional[str] = None) -> List[Any]:
        # legacy accepted optional var; new API may require it for conv
        return list(self._d.kx_list(var)) if var is not None else list(self._d.kx_list())

    def frame_conv(self, var: str, kx: Any) -> pd.DataFrame:
        return self._d.frame_conv(var, kx)

    def channels(self) -> List[int]:
        return list(self._d.channels())

    def frame_channel(self, ch: int) -> pd.DataFrame:
        return self._d.frame_channel(ch)

    def table(self, name: str) -> pd.DataFrame:
        return self._d.table(name)

    def meta(self):
        return self._d.meta()

    # ---------- convenience used by legacy helpers ----------
    def _collect_conv_frames(
        self,
        var: Optional[str] = None,
        kx: Optional[Any] = None,
    ) -> pd.DataFrame:
        """
        Build a (possibly filtered) DataFrame concatenating conv frames.
        Adds 'var' and 'kx' columns if missing.
        """
        dfs = []
        vars_iter = [var] if var else self.variables()
        for v in vars_iter:
            kxs = [kx] if kx is not None else self.kx_list(v)
            for k in kxs:
                try:
                    df = self.frame_conv(v, k).copy()
                except Exception:
                    continue
                if "var" not in df.columns:
                    df["var"] = v
                if "kx" not in df.columns:
                    df["kx"] = k
                # Try to ensure we have a datetime column if provided in meta
                if "idate" not in df.columns:
                    try:
                        df["idate"] = self.meta().date  # may be a single cycle
                    except Exception:
                        pass
                dfs.append(df)

        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    # ---------- legacy informational ----------
    def pfileinfo(self) -> None:
        """
        Pretty-print variables and their available kx (legacy behavior).
        """
        for v in self.variables():
            kxs = self.kx_list(v)
            print(f"Variable Name : {v}")
            print("              └── kx => ", end="", flush=True)
            for k in kxs:
                print(f"{k} ", end="", flush=True)
            print("\n")

    # ---------- legacy summaries ----------
    def summarize(
        self,
        varName: Optional[str] = None,
        kx: Optional[Any] = None,
        idate: Optional[pd.Timestamp] = None,
    ) -> pd.DataFrame:
        """
        Return DataFrame.describe() for filtered conv observations.
        """
        df = self._collect_conv_frames(var=varName, kx=kx)
        if df.empty:
            return pd.DataFrame()
        # Optional filter by idate if column exists
        if idate is not None and "idate" in df.columns:
            df = df[df["idate"] == idate]
        # Drop non-numerical before describe
        num = df.select_dtypes(include=["number"])
        return num.describe() if not num.empty else pd.DataFrame()

    def tmsummarize(self, varName: str, kx: Any) -> Dict[Any, pd.DataFrame]:
        """
        Time-series of .describe() grouped by 'idate'.
        """
        df = self._collect_conv_frames(var=varName, kx=kx)
        if df.empty or "idate" not in df.columns:
            return {}
        out: Dict[Any, pd.DataFrame] = {}
        for t, g in df.groupby("idate"):
            num = g.select_dtypes(include=["number"])
            out[t] = num.describe() if not num.empty else pd.DataFrame()
        return out

    def calculate_mean(self, varName: Optional[str] = None) -> pd.Series | pd.DataFrame:
        """
        Mean over numeric columns, optionally filtered by variable.
        """
        df = self._collect_conv_frames(var=varName)
        if df.empty:
            return pd.Series(dtype="float64")
        num = df.select_dtypes(include=["number"])
        if "idate" in df.columns:
            return num.groupby(df["idate"]).mean(numeric_only=True)
        return num.mean(numeric_only=True)

    # ---------- legacy “unique” getters ----------
    def get_unique_dates(self) -> List[Any]:
        df = self._collect_conv_frames()
        if "idate" in df.columns:
            return sorted(df["idate"].dropna().unique().tolist())
        try:
            # fallback to single date from meta
            return [self.meta().date]
        except Exception:
            return []

    def get_unique_kx(self, date: Optional[Any] = None) -> List[Any]:
        # For conv, KX does not vary by date in typical use; ignore date if no time axis
        # If a time axis exists and date is given, we could filter, but we keep simple.
        uniq = set()
        for v in self.variables():
            for k in self.kx_list(v):
                uniq.add(k)
        return sorted(uniq)

    def get_unique_vars(self, date: Optional[Any] = None) -> List[str]:
        # As with kx, var set typically independent of date in files
        return sorted(self.variables())

    # ---------- plotting (delegates to modern plotter if present) ----------
    def _need_plotter(self):
        if not self._plotter:
            raise RuntimeError(
                "Plotting backend not available in this build of readDiag."
            )

    def plot(self, varName, varType, param, mask=None, area=None, **kwargs):
        self._need_plotter()
        return self._plotter.plot(varName, varType, param, mask=mask, area=area, **kwargs)

    def ptmap(self, varName, varType=None, mask=None, area=None, **kwargs):
        self._need_plotter()
        return self._plotter.ptmap(varName, varType=varType, mask=mask, area=area, **kwargs)

    def pvmap(self, varName=None, mask=None, area=None, **kwargs):
        self._need_plotter()
        return self._plotter.pvmap(varName=varName, mask=mask, area=area, **kwargs)

    def pcount(self, varName, **kwargs):
        self._need_plotter()
        return self._plotter.pcount(varName=varName, **kwargs)

    def vcount(self, **kwargs):
        self._need_plotter()
        return self._plotter.vcount(**kwargs)

    def kxcount(self, **kwargs):
        self._need_plotter()
        return self._plotter.kxcount(**kwargs)

    def plot_time_series_mean(self, varName=None, kx=None, column_name="robs"):
        self._need_plotter()
        return self._plotter.plot_time_series_mean(varName=varName, kx=kx, column_name=column_name)

    def plot_time_series_mean_std(self, varName=None, kx=None, column_name="robs", ax=None, **kwargs):
        self._need_plotter()
        return self._plotter.plot_time_series_mean_std(
            varName=varName, kx=kx, column_name=column_name, ax=ax, **kwargs
        )

    # ---------- legacy close ----------
    def close(self) -> int:
        """
        Best-effort close. New backends may handle resources automatically.
        Returns 0 for success-like semantics.
        """
        # If backend exposes a close(), call it. Otherwise no-op.
        try:
            close = getattr(self._d, "close", None)
            if callable(close):
                close()
        except Exception:
            pass
        return 0


def read_diag(path: str, **kwargs) -> LegacyHandle:
    """
    Legacy entry point. Returns a LegacyHandle.

    Deprecated
    ----------
    Use: `from readDiag import diagAccess, AccessAdapter`.
    """
    warn(
        "gsidiag.read_diag() is DEPRECATED and will be removed in 3.0.0. "
        "Migrate to `readDiag.diagAccess` + `AccessAdapter`.",
        DeprecationWarning,
        stacklevel=2,
    )
    backend = diagAccess(path, **kwargs)
    return LegacyHandle(AccessAdapter(backend))

