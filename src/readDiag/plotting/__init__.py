"""
Plotting subpackage for readDiag.

This subpackage provides high-level plotting utilities built on top of
the stable DiagnosticAPI interface. The goal is to expose convenient
functions for the most common visualization tasks (e.g., counts of
observations, spatial maps of departures).

Users should typically import these wrappers instead of directly
instantiating internal plotting engines, unless they need fine-grained
control.

Available functions
-------------------
- plot_kx_count : Plot the distribution of observation counts by `kx`.
- plot_omf_map  : Plot spatial maps of OMF (observation minus forecast).
- plot_oma_map  : Plot spatial maps of OMA (observation minus analysis).

Notes
-----
Additional plotting functions can be added here as they become available.
By exposing them in ``__all__``, they are conveniently imported via
``from readDiag.plotting import ...``.

Examples
--------
Basic usage with conventional diagnostics:

>>> import readDiag as rd
>>> from readDiag import plotting as plt
>>> diag = rd.open_diagnostic("data/diag_conv_01.2024013018")
>>> # Plot the distribution of observation counts by kx
>>> plt.plot_kx_count(diag)

For radiance diagnostics:

>>> diag = rd.open_diagnostic("data/diag_amsua_n19_01.2024013018")
>>> # Plot OMF for variable 't' and kx=120
>>> plt.plot_omf_map(diag, var="t", kx=120)

"""

from .wrappers import (
    plot_kx_count,
    plot_omf_map,
    plot_oma_map,
    plot_histogram_omf,
    plot_histogram_oma,
    plot_scatter,
    # conv (novos)
    plot_spatial_conv_auto,
    plot_coverage_conv,
    plot_scatter_conv,
    plot_hist_conv,
    plot_box_by_kx,
    # rad (novos)
    plot_hist_channel,
    plot_scatter_channel,
    plot_abs_omf_map_channel,
    plot_qc_hist_channel,
    # new plotting functions can be added here in the future
)

__all__ = [
    "plot_kx_count",
    "plot_omf_map",
    "plot_oma_map",
    "plot_histogram_omf",
    "plot_histogram_oma",
    "plot_scatter",
    # conv
    "plot_spatial_conv_auto",
    "plot_coverage_conv",
    "plot_scatter_conv",
    "plot_hist_conv",
    "plot_box_by_kx",
    # rad
    "plot_hist_channel",
    "plot_scatter_channel",
    "plot_abs_omf_map_channel",
    "plot_qc_hist_channel",
]

