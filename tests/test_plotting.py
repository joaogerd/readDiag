# tests/test_plotting.py
import os
import matplotlib
matplotlib.use("Agg")  # garante backend não-interativo

import pytest
from readDiag import diagAccess, diagPlotter

ROOT = os.path.dirname(os.path.dirname(__file__))

CONV_FILE = os.path.join(ROOT, "data", "diag_conv_01.2020010100")
RAD_FILE = os.path.join(ROOT, "data", "diag_amsua_n15_01.2020010100")


def test_plot_conv_hist_and_box(tmp_path):
    """Smoke test: histogram e boxplot para dados convencionais."""
    da = diagAccess(CONV_FILE)
    # escolher primeira variável e primeiro canal disponível
    df_dict = da.get_data_frame()
    assert df_dict
    var = next(iter(df_dict.keys()))
    chan = next(iter(df_dict[var].keys()))

    plotter = diagPlotter(da)
    ax1 = plotter.plot_hist_conv(var, chan, col="omf", savepath=tmp_path / "hist.png")
    ax2 = plotter.plot_boxplot_channels_conv(var, col="omf", savepath=tmp_path / "box.png")
    # arquivos foram criados
    assert (tmp_path / "hist.png").exists()
    assert (tmp_path / "box.png").exists()
    # eixos retornados
    assert ax1 is not None and ax2 is not None


def test_plot_rad_metrics(tmp_path):
    """Smoke test: estatística de canais e distribuição O-F para radiância."""
    da = diagAccess(RAD_FILE)
    plotter = diagPlotter(da)

    ax1 = plotter.plot_channel_stats_rad(metric="omf", agg="mean",
                                         savepath=tmp_path / "stats.png")
    ax2 = plotter.plot_omf_distribution_rad(0, corrected=False,
                                            savepath=tmp_path / "omf_hist.png")
    assert (tmp_path / "stats.png").exists()
    assert (tmp_path / "omf_hist.png").exists()
    assert ax1 is not None and ax2 is not None

