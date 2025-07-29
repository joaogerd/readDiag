# tests/test_plotting.py
import os
import matplotlib
matplotlib.use("Agg")  # garante backend não-interativo

import pytest
import numpy as np
import pandas as pd
from readDiag import diagAccess, diagPlotter
import matplotlib.pyplot as plt
import matplotlib.colors
import matplotlib.colors as mcolors

ROOT = os.path.dirname(os.path.dirname(__file__))

CONV_FILE = os.path.join(ROOT, "data", "diag_conv_01.2020010100")
RAD_FILE = os.path.join(ROOT, "data", "diag_amsua_n15_01.2020010100")


def test_plot_conv_hist_and_box(tmp_path):
    """Smoke test: histogram e boxplot para dados convencionais."""
    da = diagAccess(CONV_FILE)
    df_dict = da.get_data_frame()
    assert df_dict
    var = next(iter(df_dict.keys()))
    kx = next(iter(df_dict[var].keys()))

    plotter = diagPlotter(da)
    ax1 = plotter.plot_hist_conv(var, kx, col="omf", savepath=tmp_path / "hist.png")
    ax2 = plotter.plot_boxplot_kxs_conv(var, col="omf", savepath=tmp_path / "box.png")
    assert (tmp_path / "hist.png").exists()
    assert (tmp_path / "box.png").exists()
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


# ------------------------------------------------------------------
# Novos testes para customização via kwargs e decorador
# ------------------------------------------------------------------
class FakeDiagConv(diagAccess):
    def __init__(self):
        pass
    def get_data_type(self):
        return 1
    def get_data_frame(self):
        df = pd.DataFrame({'omf': np.array([1.0, 2.0, 3.0])})
        return {'temp': {1: df}}

class FakeDiagRad(diagAccess):
    def __init__(self):
        pass
    def get_data_type(self):
        return 2
    def get_data_frame(self):
        df1 = pd.DataFrame({'omf': np.array([0.5, 0.6]), 'omf_nbc': np.array([0.4, 0.7])})
        df2 = pd.DataFrame({'omf': np.array([1.5, 1.6]), 'omf_nbc': np.array([1.4, 1.7])})
        return {'dataframes': {'diagbufchan_df': [df1, df2]}}

@pytest.fixture(autouse=True)
def no_warnings(monkeypatch):
    monkeypatch.setenv('PYTHONWARNINGS', 'ignore')


def test_plot_hist_conv_custom_kwargs(monkeypatch):
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagConv)
    diag = FakeDiagConv()
    plotter = diagPlotter(diag)

    ax = plotter.plot_hist_conv(
        'temp', 1, bins=3, color='red', alpha=0.5,
        title='Custom Hist', xlabel='Value', ylabel='Count'
    )

    assert isinstance(ax, plt.Axes)
    assert ax.get_title() == 'Custom Hist'
    assert ax.get_xlabel() == 'Value'
    assert ax.get_ylabel() == 'Count'

    exp_hex = mcolors.to_hex(mcolors.to_rgba('red', 0.5), keep_alpha=True)
    for p in ax.patches:
        assert mcolors.to_hex(p.get_facecolor(), keep_alpha=True) == exp_hex
        
@pytest.mark.parametrize("method,args", [
    ('plot_boxplot_kxs_conv', ('temp',)),
    ('plot_observation_counts', ('temp',)),
    ('plot_kx_count', ()),
    ('plot_variable_count', ()),
])
def test_conv_methods_no_error(monkeypatch, method, args):
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagConv)
    diag = FakeDiagConv()
    plotter = diagPlotter(diag)
    func = getattr(plotter, method)
    ax = func(*args, color='green', title='Test', xlabel='X', ylabel='Y')
    assert isinstance(ax, plt.Axes)
    assert ax.get_title() == 'Test'


def test_plot_channel_stats_rad(monkeypatch):
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagRad)
    diag = FakeDiagRad()
    plotter = diagPlotter(diag)
    ax = plotter.plot_channel_stats_rad(
        metric='omf', agg='mean', marker='x', color='blue',
        title='Rad Mean', xlabel='Ch', ylabel='Mean'
    )
    assert isinstance(ax, plt.Axes)
    lines = ax.get_lines()
    assert len(lines) == 1


def test_plot_omf_distribution_rad(monkeypatch):
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagRad)
    diag = FakeDiagRad()
    plotter = diagPlotter(diag)
    ax = plotter.plot_omf_distribution_rad(
        1, corrected=True, bins=2, color='purple', alpha=0.7,
        title='Rad Hist', xlabel='O-F', ylabel='Freq'
    )
    assert isinstance(ax, plt.Axes)
    assert ax.get_title() == 'Rad Hist'
    assert ax.get_xlabel() == 'O-F'
    assert ax.get_ylabel() == 'Freq'
    assert len(ax.patches) > 0


def test_check_kind_decorator(monkeypatch):
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagConv)
    diag = FakeDiagConv()
    plotter = diagPlotter(diag)
    with pytest.raises(ValueError):
        plotter.plot_channel_stats_rad()
    monkeypatch.setattr('readDiag.diagAccess', FakeDiagRad)
    diag2 = FakeDiagRad()
    plotter2 = diagPlotter(diag2)
    with pytest.raises(ValueError):
        plotter2.plot_hist_conv('temp', 1)

