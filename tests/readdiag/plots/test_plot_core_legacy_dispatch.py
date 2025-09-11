import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes
from readDiag.plotting.core import diagPlotter

def test_legacy_plot_conv_area(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot(varName="t", kx=121, param="oma", area=[-120, -80, -20, 20])
    assert isinstance(ax, Axes)

def test_legacy_plot_rad_extra_opts(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot(varName="amsua", varType="n19", param="oma", channel=2, s=3.5)
    assert isinstance(ax, Axes)
