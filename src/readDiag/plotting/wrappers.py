"""
Legacy-friendly plotting wrappers
=================================

This module provides **compatibility wrappers** that map old-style plotting
function calls to the modern :class:`diagPlotter`. It ensures that legacy
scripts depending on functions such as ``plot_kx_count`` or ``plot_omf_map``
continue to work without modification.

Notes
-----
- Under the hood, all functions delegate to :class:`diagPlotter`.
- Only a subset of common plotting patterns is supported.
- New projects should use :class:`diagPlotter` directly.

Examples
--------
>>> from readDiag.legacy_plots import plot_kx_count, plot_omf_map
>>> from readDiag import read_diag
>>> diag = read_diag("diag_conv_01.2020010100")
>>> ax = plot_kx_count(diag)
>>> ax = plot_omf_map(diag, var="t", kx=120)
"""
from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING
import warnings

try:  # attempt to import matplotlib for type hints and Axes objects
    import matplotlib.pyplot as plt  # type: ignore
    if TYPE_CHECKING:
        from matplotlib.axes import Axes  # for type checkers only
except Exception:  # pragma: no cover - matplotlib may be unavailable
    plt = None  # matplotlib might not be installed
    if TYPE_CHECKING:  # define a soft alias to avoid NameErrors in type checking
        class Axes:  # type: ignore
            ...

# Modern centralized plotter
from .core import diagPlotter
# Canonical/legacy name resolver (allows passing legacy column names)
from readDiag.schema.naming import resolve_name

__all__ = [
    # legacy-compatible wrappers (conventional)
    "plot_kx_count",
    "plot_omf_map",
    "plot_oma_map",
    "plot_histogram_omf",
    "plot_histogram_oma",
    "plot_scatter",
    # new convenience wrappers (conventional)
    "plot_spatial_conv_auto",
    "plot_coverage_conv",
    "plot_scatter_conv",
    "plot_hist_conv",
    "plot_box_by_kx",
    # radiance wrappers
    "plot_hist_channel",
    "plot_scatter_channel",
    "plot_abs_omf_map_channel",
    "plot_qc_hist_channel",
]

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _as_plotter(diag: Any) -> "diagPlotter":
    """Return a :class:`diagPlotter` bound to ``diag``.

    Parameters
    ----------
    diag : Any
        Diagnostic handle (e.g., returned by :func:`readDiag.open_diagnostic`
        or legacy helpers).

    Returns
    -------
    diagPlotter
        Ready-to-use plotter object.
    """
    return diagPlotter(diag)


# ---------------------------------------------------------------------------
# Legacy wrappers — Conventional (conv)
# ---------------------------------------------------------------------------

def plot_kx_count(diag: Any, **kwargs) -> "Axes":
    """Legacy wrapper for :meth:`diagPlotter.plot_kx_count`.

    Parameters
    ----------
    diag : object
        Diagnostic handle (from :func:`readDiag.read_diag` or similar).
    **kwargs
        Extra keyword arguments passed to :meth:`diagPlotter.plot_kx_count`.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.

    Examples
    --------
    >>> ax = plot_kx_count(diag)
    """
    return _as_plotter(diag).plot_kx_count(**kwargs)


def plot_omf_map(diag: Any, var: str, kx: int, value: str = "omf", **kwargs) -> "Axes":
    """Legacy wrapper for OmF spatial maps (conventional diagnostics).

    This is equivalent to calling :meth:`diagPlotter.plot_spatial_conv` with
    ``param='omf'`` (or a canonical column that resolves to OmF).

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name (e.g., ``'t'``, ``'q'``).
    kx : int
        Observation type code (KX).
    value : str, default='omf'
        Column to use; both legacy and canonical names are accepted and
        normalized via :func:`resolve_name`.
    **kwargs
        Passed to :meth:`diagPlotter.plot_spatial_conv`.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    col = resolve_name(value, domain="conv")
    return _as_plotter(diag).plot_spatial_conv(var, kx, param=col, **kwargs)


def plot_oma_map(diag: Any, var: str, kx: int, value: str = "oma", **kwargs) -> "Axes":
    """Legacy wrapper for OmA spatial maps (conventional diagnostics).

    Equivalent to calling :meth:`diagPlotter.plot_spatial_conv` with
    ``param='oma'`` (or a canonical equivalent).

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        Observation type code (KX).
    value : str, default='oma'
        Column to use; normalized by :func:`resolve_name`.
    **kwargs
        Passed to :meth:`diagPlotter.plot_spatial_conv`.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    col = resolve_name(value, domain="conv")
    return _as_plotter(diag).plot_spatial_conv(var, kx, param=col, **kwargs)


def plot_histogram_omf(diag: Any, var: str, kx: int, **kwargs) -> "Axes":
    """Legacy wrapper for OmF histograms.

    Equivalent to calling :meth:`diagPlotter.plot_hist_conv` with
    ``col='omf'`` after canonical resolution.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        Observation type code (KX).
    **kwargs
        Passed to :meth:`diagPlotter.plot_hist_conv`.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    col = resolve_name("omf", domain="conv")
    return _as_plotter(diag).plot_hist_conv(var, kx, col=col, **kwargs)


def plot_histogram_oma(diag: Any, var: str, kx: int, **kwargs) -> "Axes":
    """Legacy wrapper for OmA histograms.

    Equivalent to calling :meth:`diagPlotter.plot_hist_conv` with
    ``col='oma'`` after canonical resolution.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        Observation type code (KX).
    **kwargs
        Passed to :meth:`diagPlotter.plot_hist_conv`.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    col = resolve_name("oma", domain="conv")
    return _as_plotter(diag).plot_hist_conv(var, kx, col=col, **kwargs)


def plot_scatter(
    diag: Any,
    var: str,
    kx: int,
    x: str,
    y: str,
    **kwargs,
) -> "Axes":
    """Legacy wrapper for simple XY scatter plots (conventional diagnostics).

    The function retrieves the dataframe for the pair ``(var, kx)`` and
    scatters ``x`` vs. ``y``. Column names are normalized via
    :func:`resolve_name`, allowing legacy aliases.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        Observation type code (KX).
    x, y : str
        Column names for X and Y axes (legacy or canonical).
    **kwargs
        Plot styling (e.g., ``s``, ``alpha``, etc.) plus optional labels
        handled by :meth:`diagPlotter._apply_plot_kwargs` such as
        ``title``, ``xlabel``, ``ylabel``, ``zero_line``, ``fontsize``,
        ``rotation``.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.

    Examples
    --------
    >>> ax = plot_scatter(diag, "t", 120, "omf", "oma", s=10, alpha=0.4)
    """
    plotter = _as_plotter(diag)
    df = plotter.diag.frame_conv(var, kx)

    # Resolve names (accept legacy or canonical)
    x_col = resolve_name(x, domain="conv")
    y_col = resolve_name(y, domain="conv")

    # Get or create axes
    ax = kwargs.pop("ax", None)
    ax = plotter._ensure_ax(ax)

    # Filter kwargs destined for scatter only (labels/formatting handled later)
    scatter_kwargs = {
        k: v
        for k, v in kwargs.items()
        if k
        not in (
            "title",
            "xlabel",
            "ylabel",
            "zero_line",
            "fontsize",
            "rotation",
            "ax",
        )
    }
    ax.scatter(df[x_col], df[y_col], **scatter_kwargs)

    # Apply labels and formatting
    title = kwargs.pop("title", f"Scatter: {x_col} vs {y_col} ({var}, KX={kx})")
    plotter._apply_plot_kwargs(ax, title=title, xlabel=x_col, ylabel=y_col, **kwargs)
    return ax


# ---------------------------------------------------------------------------
# Newer convenience wrappers — Conventional (conv)
# ---------------------------------------------------------------------------

def plot_spatial_conv_auto(diag: Any, var: str, kx: int, **kwargs) -> "Axes":
    """Convenience wrapper for :meth:`diagPlotter.plot_spatial_conv_auto`.

    Accepts optional ``param`` as a legacy or canonical name and resolves it
    with :func:`resolve_name` prior to plotting.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        Observation type code (KX).
    **kwargs
        Additional keyword arguments, including ``param``.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    if "param" in kwargs and isinstance(kwargs["param"], str):
        kwargs["param"] = resolve_name(kwargs["param"], domain="conv")
    return _as_plotter(diag).plot_spatial_conv_auto(var, kx, **kwargs)


def plot_coverage_conv(diag: Any, var: str, kx: int, **kwargs) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_coverage_conv` (conventional).

    Resolves an optional ``param`` (legacy or canonical) before plotting.
    """
    if "param" in kwargs and isinstance(kwargs["param"], str):
        kwargs["param"] = resolve_name(kwargs["param"], domain="conv")
    return _as_plotter(diag).plot_coverage_conv(var, kx, **kwargs)


def plot_scatter_conv(
    diag: Any, var: str, kx: int, x: str, y: str, **kwargs
) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_scatter_conv`.

    Columns ``x`` and ``y`` accept legacy aliases and are normalized via
    :func:`resolve_name`.
    """
    x_col = resolve_name(x, domain="conv")
    y_col = resolve_name(y, domain="conv")
    return _as_plotter(diag).plot_scatter_conv(var, kx, x_col, y_col, **kwargs)


def plot_hist_conv(diag: Any, var: str, kx: int, param: str, **kwargs) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_hist_conv` with name resolution."""
    col = resolve_name(param, domain="conv")
    return _as_plotter(diag).plot_hist_conv(var, kx, col, **kwargs)


def plot_box_by_kx(diag: Any, var: str, param: str, **kwargs) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_box_by_kx` with name resolution."""
    col = resolve_name(param, domain="conv")
    return _as_plotter(diag).plot_box_by_kx(var, col, **kwargs)


# ---------------------------------------------------------------------------
# Radiance (rad) wrappers
# ---------------------------------------------------------------------------

def plot_hist_channel(
    diag: Any, channel: int, param: Optional[str] = None, **kwargs
) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_hist_channel` (radiance).

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    channel : int
        Channel number.
    param : str, optional
        Column name (legacy or canonical). If provided, it is normalized via
        :func:`resolve_name` with ``domain='rad'``.
    **kwargs
        Forwarded to :meth:`diagPlotter.plot_hist_channel`.
    """
    if isinstance(param, str):
        param = resolve_name(param, domain="rad")
    return _as_plotter(diag).plot_hist_channel(channel, param, **kwargs)


def plot_scatter_channel(
    diag: Any, channel: int, x: str, y: str, **kwargs
) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_scatter_channel` (radiance).

    Columns ``x`` and ``y`` accept legacy aliases and are normalized through
    :func:`resolve_name` with ``domain='rad'``.
    """
    return _as_plotter(diag).plot_scatter_channel(channel, x, y, **kwargs)


def plot_abs_omf_map_channel(diag: Any, channel: int, **kwargs) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_abs_omf_map_channel` (radiance)."""
    # This method uses internal standardized columns already handled by the plotter
    return _as_plotter(diag).plot_abs_omf_map_channel(channel, **kwargs)


def plot_qc_hist_channel(
    diag: Any, channel: int, param: str = "qc_flag", **kwargs
) -> "Axes":
    """Wrapper for :meth:`diagPlotter.plot_qc_hist_channel` with name resolution.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    channel : int
        Channel number.
    param : str, default='qc_flag'
        Column to histogram (legacy or canonical). Normalized via
        :func:`resolve_name` with ``domain='rad'``.
    **kwargs
        Forwarded to :meth:`diagPlotter.plot_qc_hist_channel`.
    """
    col_resolved = resolve_name(param, domain="rad")
    return _as_plotter(diag).plot_qc_hist_channel(channel, col_resolved, **kwargs)

