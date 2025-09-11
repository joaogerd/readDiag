import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from readDiag.plotting.core import diagPlotter

def test_plot_hist_conv_with_bins(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_hist_conv("t", 120, param="omf", bins=8)
    assert isinstance(ax, Axes)

def test_plot_boxplot_kxs_conv_existing_ax(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    fig, ax = plt.subplots()
    ax2 = p.plot_boxplot_kxs_conv("t", param="omf", showmeans=True, ax=ax)
    assert ax2 is ax
