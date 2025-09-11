
import pytest
import matplotlib
matplotlib.use("Agg")
from matplotlib.axes import Axes

import readDiag.plotting as rplt
from readDiag.plotting import wrappers as W

def test_wrappers_kx_and_hist(fake_conv_diag):
    ax1 = rplt.plot_kx_count(fake_conv_diag)
    ax2 = rplt.plot_hist_conv(fake_conv_diag, var="t", kx=120, param="omf", bins=15)
    assert isinstance(ax1, Axes) and isinstance(ax2, Axes)

def test_wrapper_scatter_conv(fake_conv_diag):
    ax = rplt.plot_scatter_conv(fake_conv_diag, var="t", kx=120, x="omf", y="oma", s=10, alpha=0.4)
    assert isinstance(ax, Axes)

def test_radiance_wrappers_hist_and_stats(fake_rad_diag):
    axh = rplt.plot_hist_channel(fake_rad_diag, channel=1, param="omf", bins=25)
    axs = rplt.plot_scatter_channel(fake_rad_diag, channel=1, x="omf", y="oma", s=8)
    assert isinstance(axh, Axes) and isinstance(axs, Axes)

def test_radiance_wrappers_qc_and_abs(fake_rad_diag):
    ax1 = rplt.plot_qc_hist_channel(fake_rad_diag, channel=1, param="idqc")
    ax2 = rplt.plot_abs_omf_map_channel(fake_rad_diag, channel=1)
    assert isinstance(ax1, Axes) and isinstance(ax2, Axes)

import importlib.util
import pytest
import readDiag.plotting as rplt

_has_cartopy = importlib.util.find_spec("cartopy") is not None

@pytest.mark.skipif(not _has_cartopy, reason="Cartopy not installed")
def test_conv_spatial_wrappers_with_cartopy(fake_conv_diag):
    # These call into core.plot_spatial_conv under the hood
    ax1 = rplt.plot_omf_map(fake_conv_diag, var="t", kx=120, value="omf")
    ax2 = rplt.plot_oma_map(fake_conv_diag, var="t", kx=120, value="oma")
    import matplotlib.axes
    assert isinstance(ax1, matplotlib.axes.Axes) and isinstance(ax2, matplotlib.axes.Axes)
