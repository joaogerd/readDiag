import pytest
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from readDiag.plotting._utils import wrap_lon, cmap_hex, wrap_label, make_axes, ensure_axes_gpd

def test_wrap_lon_basic():
    a = np.array([0, 90, 270.0])
    out = wrap_lon(a, mode="pm180")
    assert np.allclose(out, [0, 90, -90])

def test_wrap_lon_auto():
    a = np.array([350.0, 10.0])
    out = wrap_lon(a, mode="auto")
    # 350 -> -10
    assert np.isclose(out[0], -10.0)

def test_cmap_hex_and_errors():
    c0 = cmap_hex(0, total=3, cmap_name="tab10")
    c2 = cmap_hex(2, total=3, cmap_name="tab10")
    assert c0.startswith("#") and c2.startswith("#") and c0 != c2
    with pytest.raises(ValueError):
        cmap_hex(0, total=0)

def test_wrap_label_width_and_empty():
    assert wrap_label("", 10) == ""
    assert "\n" in wrap_label("ABCDEFGHIJ", width=4)

def test_make_axes_non_geo_and_gpd_fallback():
    ax, crs = make_axes(basemap=False)
    assert crs is None
    assert hasattr(ax, "plot")
    # ensure_axes_gpd should return a valid Axes without requiring geopandas
    ax2 = ensure_axes_gpd(ax=None, area=[-90, -60, -30, 15])
    assert hasattr(ax2, "scatter")
