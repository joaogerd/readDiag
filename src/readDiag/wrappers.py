from __future__ import annotations
from typing import Any
from .core import diagPlotter


def _as_plotter(diag: Any) -> "diagPlotter":
    """Internal helper to wrap a diagnostic object in a :class:`diagPlotter`.

    Parameters
    ----------
    diag : Any
        Diagnostic object (e.g., output from ``open_diagnostic``).

    Returns
    -------
    diagPlotter
        A plotting wrapper bound to the provided diagnostic.
    """
    return diagPlotter(diag)


def plot_kx_count(diag, **kwargs):
    """Plot the count of observations by ``kx`` (observation type).

    This is a thin wrapper around :meth:`diagPlotter.plot_kx_count`,
    provided for backward compatibility with legacy code.

    Parameters
    ----------
    diag : Any
        Diagnostic object (e.g., returned by ``open_diagnostic``).
    **kwargs : dict
        Additional keyword arguments passed to
        :meth:`diagPlotter.plot_kx_count`.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.

    Examples
    --------
    >>> import readDiag as rd
    >>> d = rd.open_diagnostic("diag_conv_01.2024013018")
    >>> from readDiag.plotting.wrappers import plot_kx_count
    >>> fig = plot_kx_count(d)
    >>> fig.show()
    """
    return _as_plotter(diag).plot_kx_count(**kwargs)


def plot_omf_map(diag, var: str, kx: int, **kwargs):
    """Plot spatial map of OMF (observation minus forecast) for a variable.

    This wrapper calls :meth:`diagPlotter.plot_spatial_conv` with
    ``param="omf"``.

    Parameters
    ----------
    diag : Any
        Diagnostic object.
    var : str
        Variable name (e.g., ``"t"`` for temperature).
    kx : int
        Observation type code (``kx``).
    **kwargs : dict
        Additional keyword arguments forwarded to
        :meth:`diagPlotter.plot_spatial_conv`.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.

    Examples
    --------
    >>> d = rd.open_diagnostic("diag_conv_01.2024013018")
    >>> from readDiag.plotting.wrappers import plot_omf_map
    >>> fig = plot_omf_map(d, var="t", kx=120)
    >>> fig.show()
    """
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="omf", **kwargs)


def plot_oma_map(diag, var: str, kx: int, **kwargs):
    """Plot spatial map of OMA (observation minus analysis) for a variable.

    This wrapper calls :meth:`diagPlotter.plot_spatial_conv` with
    ``param="oma"``.

    Parameters
    ----------
    diag : Any
        Diagnostic object.
    var : str
        Variable name (e.g., ``"q"`` for humidity).
    kx : int
        Observation type code (``kx``).
    **kwargs : dict
        Additional keyword arguments forwarded to
        :meth:`diagPlotter.plot_spatial_conv`.

    Returns
    -------
    matplotlib.figure.Figure
        The generated figure.

    Examples
    --------
    >>> d = rd.open_diagnostic("diag_conv_01.2024013018")
    >>> from readDiag.plotting.wrappers import plot_oma_map
    >>> fig = plot_oma_map(d, var="q", kx=130)
    >>> fig.show()
    """
    return _as_plotter(diag).plot_spatial_conv(var, kx, param="oma", **kwargs)

