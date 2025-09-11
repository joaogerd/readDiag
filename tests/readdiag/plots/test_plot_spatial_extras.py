import importlib.util
import pytest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from readDiag.plotting.core import diagPlotter

_has_cartopy = importlib.util.find_spec("cartopy") is not None

@pytest.mark.skipif(not _has_cartopy, reason="Cartopy not installed")
def test_plot_spatial_conv_area_wrap(fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    ax = p.plot_spatial_conv("t", 120, param="omf", area=[-90,-60,-30,15], lon_wrap="pm180")
    assert isinstance(ax, Axes)
