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

from typing import Any
import warnings

try:  # tentativa de importar matplotlib
    import matplotlib.pyplot as plt  # type: ignore
except Exception:  # pragma: no cover
    plt = None  # matplotlib pode não estar disponível

from .core import diagPlotter  # plotter moderno centralizado


def _as_plotter(diag: Any) -> "diagPlotter":
    """Internal helper: wrap a diagnostic object in a :class:`diagPlotter`."""
    return diagPlotter(diag)


def plot_kx_count(diag, **kwargs):
    """
    Legacy wrapper for :meth:`diagPlotter.plot_kx_count`.

    Parameters
    ----------
    diag : object
        Diagnostic handle (from :func:`readDiag.read_diag` or similar).
    **kwargs : dict
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


def plot_omf_map(diag, var: str, kx: int, **kwargs):
    """
    Legacy wrapper for OmF spatial plots.

    Equivalent to calling
    :meth:`diagPlotter.plot_spatial_conv` with ``param='omf'``.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name (e.g., 't', 'q').
    kx : int
        KX (observation type code).
    **kwargs : dict
        Additional options for the plotting routine.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="omf", **kwargs)


def plot_oma_map(diag, var: str, kx: int, **kwargs):
    """
    Legacy wrapper for OmA spatial plots.

    Equivalent to calling
    :meth:`diagPlotter.plot_spatial_conv` with ``param='oma'``.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        KX (observation type).
    **kwargs : dict
        Additional options.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the plot.
    """
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="oma", **kwargs)


def plot_histogram_omf(diag, var: str, kx: int, **kwargs):
    """
    Legacy wrapper for OmF histogram plots.

    Equivalent to calling
    :meth:`diagPlotter.plot_hist_conv` with ``col='omf'``.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        KX code.
    **kwargs : dict
        Extra options.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the histogram.
    """
    return _as_plotter(diag).plot_hist_conv(var, kx, col="omf", **kwargs)


def plot_histogram_oma(diag, var: str, kx: int, **kwargs):
    """
    Legacy wrapper for OmA histogram plots.

    Equivalent to calling
    :meth:`diagPlotter.plot_hist_conv` with ``col='oma'``.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        KX code.
    **kwargs : dict
        Extra options.

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the histogram.
    """
    return _as_plotter(diag).plot_hist_conv(var, kx, col="oma", **kwargs)


def plot_scatter(diag, var: str, kx: int, x: str, y: str, **kwargs):
    """
    Legacy wrapper for simple XY scatter plots.

    Extracts the dataframe for ``(var, kx)`` from the diagnostic object
    and plots a scatter of ``x`` vs ``y``.

    Parameters
    ----------
    diag : object
        Diagnostic handle.
    var : str
        Variable name.
    kx : int
        KX code.
    x : str
        Column name for X axis.
    y : str
        Column name for Y axis.
    **kwargs : dict
        Additional styling arguments. Special keys include:
        - ``title`` : str, optional
        - ``xlabel`` : str, optional
        - ``ylabel`` : str, optional
        - ``zero_line`` : bool, optional
        - ``fontsize`` : int, optional
        - ``rotation`` : float, optional

    Returns
    -------
    matplotlib.axes.Axes
        Axes containing the scatter plot.

    Examples
    --------
    >>> ax = plot_scatter(diag, var="t", kx=120, x="obs", y="omf")
    """
    plotter = _as_plotter(diag)
    df = plotter.diag.frame_conv(var, kx)

    # get or create axes
    ax = kwargs.pop("ax", None)
    ax = plotter._ensure_ax(ax)

    # filter kwargs for scatter
    scatter_kwargs = {
        k: v for k, v in kwargs.items()
        if k not in ("title", "xlabel", "ylabel", "zero_line", "fontsize", "rotation")
    }
    ax.scatter(df[x], df[y], **scatter_kwargs)

    # apply labels and formatting
    title = kwargs.pop("title", f"Scatter: {x} vs {y} ({var}, KX={kx})")
    plotter._apply_plot_kwargs(ax, title=title, xlabel=x, ylabel=y, **kwargs)
    return ax

