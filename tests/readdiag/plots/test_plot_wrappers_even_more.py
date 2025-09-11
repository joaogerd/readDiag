
import matplotlib.pyplot as plt
import pytest
import readDiag.plotting as rplt
from readDiag.plotting.core import diagPlotter

def test_more_wrappers_calls(fake_conv_diag, fake_rad_diag):
    # keep an existing wrapper call that is supported
    a = rplt.plot_kx_count(fake_conv_diag, title="kx")
    assert hasattr(a, "plot")

    # replace nonexistent wrapper with the supported histogram wrapper
    ax = rplt.plot_hist_channel(fake_rad_diag, channel=2, param="omf", bins=15)
    assert hasattr(ax, "hist")
