
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from readDiag.plotting.style import PlotConfig

def test_plotconfig_apply_to_axes():
    cfg = PlotConfig()
    fig, ax = plt.subplots()
    ax.plot([0,1],[0,1])
    cfg.apply_to_axes(ax)
    assert hasattr(ax, "grid")
    assert ax.get_facecolor() is not None
