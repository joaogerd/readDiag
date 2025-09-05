"""
Legacy-friendly plotting wrappers for convenience.
These call the modern diagPlotter under the hood.
"""
from typing import Any
import warnings

try:
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # type: ignore

from .core import diagPlotter  # modern plotter

def _as_plotter(diag: Any) -> "diagPlotter":
    return diagPlotter(diag)

def plot_kx_count(diag, **kwargs):
    """Compat wrapper for diagPlotter.plot_kx_count()."""
    return _as_plotter(diag).plot_kx_count(**kwargs)

def plot_omf_map(diag, var: str, kx: int, **kwargs):
    """Compat wrapper for diagPlotter.plot_spatial_conv(..., param='omf')."""
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="omf", **kwargs)

def plot_oma_map(diag, var: str, kx: int, **kwargs):
    """Compat wrapper for diagPlotter.plot_spatial_conv(..., param='oma')."""
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="oma", **kwargs)

def plot_histogram_omf(diag, var: str, kx: int, **kwargs):
    """Compat wrapper for diagPlotter.plot_hist_conv(..., col='omf')."""
    return _as_plotter(diag).plot_hist_conv(var, kx, col="omf", **kwargs)

def plot_histogram_oma(diag, var: str, kx: int, **kwargs):
    """Compat wrapper for diagPlotter.plot_hist_conv(..., col='oma')."""
    return _as_plotter(diag).plot_hist_conv(var, kx, col="oma", **kwargs)

def plot_scatter(diag, var: str, kx: int, x: str, y: str, **kwargs):
    """Compat simple XY scatter from frame_conv(var, kx)."""
    plotter = _as_plotter(diag)
    df = plotter.diag.frame_conv(var, kx)
    ax = kwargs.pop("ax", None)
    ax = plotter._ensure_ax(ax)
    ax.scatter(df[x], df[y], **{k:v for k,v in kwargs.items()
                                if k not in ("title","xlabel","ylabel","zero_line","fontsize","rotation")})
    title = kwargs.pop("title", f"Scatter: {x} vs {y} ({var}, KX={kx})")
    plotter._apply_plot_kwargs(ax, title=title, xlabel=x, ylabel=y, **kwargs)
    return ax
