
import pytest
import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes

from readDiag.plotting.core import diagPlotter

def test_plot_hist_conv(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_hist_conv("t", 120, param="omf", bins=10, title="HIST")
    assert isinstance(ax, Axes)
    assert "HIST" in ax.get_title()

def test_plot_boxplot_kxs_conv(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_boxplot_kxs_conv("t", param="omf", color="0.3")
    assert isinstance(ax, Axes)
    assert ax.get_xlabel() == "KX"

def test_plot_observation_counts(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_observation_counts("t", rotation=30)
    assert isinstance(ax, Axes)
    assert ax.get_ylabel() == "Number of Observations"

def test_plot_kx_count(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_kx_count(title="Total per KX")
    assert isinstance(ax, Axes)

def test_plot_variable_count(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_variable_count(title="Total per variable")
    assert isinstance(ax, Axes)

def test_plot_kx_count_stacked(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_kx_count_stacked(vars=["t"], title="Stacked counts")
    assert isinstance(ax, Axes)

def test_deprecated_aliases_conv(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax1 = p.pcount("t")
    ax2 = p.vcount("t", kx=120, param="omf", bins=5)
    ax3 = p.plot_value_counts()
    assert isinstance(ax1, Axes) and isinstance(ax2, Axes) and isinstance(ax3, Axes)

def test_legacy_plot_conv(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot(varName="t", kx=120, param="omf", cmap="jet")
    assert isinstance(ax, Axes)
