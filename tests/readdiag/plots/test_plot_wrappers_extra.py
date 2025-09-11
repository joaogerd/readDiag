import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
import readDiag.plotting as rplt

def test_wrappers_with_existing_axes_conv(fake_conv_diag):
    fig, ax = plt.subplots()
    ax2 = rplt.plot_hist_conv(fake_conv_diag, var="t", kx=120, param="omf", bins=12, ax=ax)
    assert isinstance(ax2, Axes) and ax2 is ax

def test_wrappers_hist_channel_simple(fake_rad_diag):
    # no explicit ax: API for radiance histogram doesn't accept 'ax'
    out = rplt.plot_hist_channel(fake_rad_diag, channel=2, param="oma", bins=12)
    assert isinstance(out, Axes)
