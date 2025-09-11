import importlib.util
import pytest
import matplotlib
matplotlib.use("Agg")
from readDiag.plotting._utils import make_axes

_has_cartopy = importlib.util.find_spec("cartopy") is not None

@pytest.mark.skipif(not _has_cartopy, reason="Cartopy not installed")
def test_make_axes_with_basemap():
    ax, crs = make_axes(basemap=True)
    # When cartopy is available, crs should be non-None
    assert crs is not None
