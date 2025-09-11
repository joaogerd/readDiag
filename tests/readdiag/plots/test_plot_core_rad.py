
import pytest
import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes

from readDiag.plotting.core import diagPlotter

def test_plot_channel_stats_rad(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot_channel_stats_rad(param="omf", agg="mean", marker="o")
    assert isinstance(ax, Axes)
    assert "Radiance channel" in ax.get_title()

def test_plot_omf_distribution_rad(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot_omf_distribution_rad(0, corrected=True, bins=20)
    assert isinstance(ax, Axes)
    assert ax.get_xlabel() in ("omf_nbc", "omf")

def test_legacy_plot_rad(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot(varName="amsua", varType="n19", param="omf", channel=1, cmap="jet", s=4.0)
    assert isinstance(ax, Axes)
