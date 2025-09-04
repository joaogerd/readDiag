

"""
Plotting aliases and modern methods:
- Ensure deprecated aliases still work and warn.
- Ensure modern methods accept kwargs for titles/labels/colors.
"""
from __future__ import annotations
import pytest


import warnings
import matplotlib.pyplot as plt
from readDiag import diagAccess, diagPlotter

@pytest.mark.usefixtures("conv01_path", "conv_var_kx")
def test_plotting_conv(conv01_path, conv_var_kx):
    d = diagAccess(str(conv01_path))
    plotter = diagPlotter(d)
    var, kx = conv_var_kx

    # Modern
    ax1 = plotter.plot_observation_counts(var, title="Counts")
    assert isinstance(ax1, plt.Axes)
    plt.close(ax1.figure)

    ax2 = plotter.plot_boxplot_kxs_conv(var, col="omf", title="Box")
    assert isinstance(ax2, plt.Axes)
    plt.close(ax2.figure)

    # Deprecated aliases (warn but succeed)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ax3 = plotter.pcount(var)
        assert isinstance(ax3, plt.Axes)
        assert any("deprecated" in str(x.message).lower() for x in w)
        plt.close(ax3.figure)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        ax4 = plotter.kxcount()
        assert isinstance(ax4, plt.Axes)
        assert any("deprecated" in str(x.message).lower() for x in w)
        plt.close(ax4.figure)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        # vcount legacy → hist
        ax5 = plotter.vcount(var=var, kx=kx, column="omf", bins=30)
        assert isinstance(ax5, plt.Axes)
        assert any("deprecated" in str(x.message).lower() for x in w)
        plt.close(ax5.figure)

