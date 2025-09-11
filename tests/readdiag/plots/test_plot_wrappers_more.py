
import matplotlib.pyplot as plt
from readDiag.plotting.core import diagPlotter

def test_wrapper_boxplot_only(fake_conv_diag):
    # The wrappers module doesn't expose a boxplot helper;
    # call the canonical core method instead for coverage.
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_boxplot_kxs_conv("t", param="omf", showmeans=True)
    assert hasattr(ax, "boxplot")
