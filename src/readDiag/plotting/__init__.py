"""
Plotting subpackage for readDiag.

This subpackage provides high-level plotting utilities built on top of
the stable DiagnosticAPI interface. The goal is to expose convenient
functions for the most common visualization tasks, including observation
counts, spatial maps of departures, and reusable figure styling.
"""

from .wrappers import (
    plot_kx_count,
    plot_omf_map,
    plot_oma_map,
    plot_histogram_omf,
    plot_histogram_oma,
    plot_scatter,
    # conv
    plot_spatial_conv_auto,
    plot_coverage_conv,
    plot_scatter_conv,
    plot_hist_conv,
    plot_box_by_kx,
    # rad
    plot_hist_channel,
    plot_scatter_channel,
    plot_abs_omf_map_channel,
    plot_qc_hist_channel,
)

from .style import NatureFigureStyle, PlotConfig, use_nature_style

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
    # style
    "NatureFigureStyle",
    "PlotConfig",
    "use_nature_style",
]
