"""
Legacy shim: `gsidiag.plotting`
Bridges old imports to modern `readDiag.plotting`.
"""
from readDiag.plotting.core import diagPlotter  # noqa: F401
try:
    from readDiag.plotting.wrappers import (
        plot_kx_count, plot_omf_map, plot_oma_map,
        plot_histogram_omf, plot_histogram_oma, plot_scatter,
    )  # noqa: F401
    __all__ = [
        "diagPlotter",
        "plot_kx_count","plot_omf_map","plot_oma_map",
        "plot_histogram_omf","plot_histogram_oma","plot_scatter",
    ]
except Exception:
    __all__ = ["diagPlotter"]
