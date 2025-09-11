import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from readDiag.plotting._utils import ensure_axes_gpd

def test_ensure_axes_gpd_with_existing_ax_and_no_area():
    fig, ax = plt.subplots()
    out = ensure_axes_gpd(ax=ax, area=None)
    assert out is ax
