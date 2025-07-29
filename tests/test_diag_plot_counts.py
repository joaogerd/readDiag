import os
import pytest
import matplotlib
matplotlib.use("Agg")  # Backend não interativo para testes
import matplotlib.pyplot as plt

from readDiag import diagAccess, diagPlotter

TEST_FILE = os.path.join(os.path.dirname(__file__), "../data/diag_conv_01.2020010100")

@pytest.fixture
def plotter():
    diag = diagAccess(TEST_FILE)
    return diagPlotter(diag)

def test_plot_observation_counts(plotter):
    var = plotter.diag.get_variables()[0]
    ax = plotter.plot_observation_counts(var)
    assert isinstance(ax, plt.Axes)

def test_plot_kx_count(plotter):
    ax = plotter.plot_kx_count()
    assert isinstance(ax, plt.Axes)

def test_plot_variable_count(plotter):
    ax = plotter.plot_variable_count()
    assert isinstance(ax, plt.Axes)

def test_deprecated_aliases(plotter):
    var = plotter.diag.get_variables()[0]
    with pytest.warns(DeprecationWarning, match="pcount"):
        plotter.pcount(var)
    with pytest.warns(DeprecationWarning, match="kxcount"):
        plotter.kxcount()
    with pytest.warns(DeprecationWarning, match="vcount"):
        plotter.vcount()
