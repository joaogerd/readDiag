import os
from readDiag.plotting.core import diagPlotter

def test_plot_hist_conv_savepath(tmp_path, fake_conv_diag):
    p = diagPlotter(fake_conv_diag)
    outfile = tmp_path / "hist.png"
    ax = p.plot_hist_conv("t", 120, param="omf", bins=5, savepath=str(outfile))
    assert outfile.exists() and outfile.stat().st_size > 0
