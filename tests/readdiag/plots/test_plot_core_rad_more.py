import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes
from readDiag.plotting.core import diagPlotter

def test_plot_qc_hist_channel_with_canonical_qc(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot_qc_hist_channel(1, param="qc_flag")
    assert isinstance(ax, Axes)

def test_plot_scatter_channel_styled(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot_scatter_channel(2, x="omf", y="oma", s=6, alpha=0.5, marker=".")
    assert isinstance(ax, Axes)
