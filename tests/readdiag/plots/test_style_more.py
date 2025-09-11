import matplotlib
matplotlib.use("Agg")
from readDiag.plotting.style import PlotConfig

def test_plotconfig_with_defaults():
    cfg = PlotConfig()
    assert isinstance(cfg, PlotConfig)
