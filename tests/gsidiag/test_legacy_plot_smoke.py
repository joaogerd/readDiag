
import matplotlib.pyplot as plt
from gsidiag.legacy_api.plot import geoMap, getColor

def test_geoMap_smoke():
    ax = geoMap(area=[-80, -40, -30, 10])
    assert hasattr(ax, "set_xlim") and hasattr(ax, "set_ylim")
    # Render once to ensure the figure pipeline is OK
    ax.figure.canvas.draw()

def test_getColor_single_and_array():
    # Single value RGBA
    c = getColor(0.0, 1.0, 0.5)
    assert isinstance(c, tuple) and len(c) in (3, 4)
    # Hex output
    h = getColor(0.0, 1.0, 0.5, hex=True)
    assert isinstance(h, str) and h.startswith("#")
    # Vectorized
    v = getColor(-1.0, 1.0, [0.0, 0.5, 1.0])
    assert hasattr(v, "__iter__") and len(v) == 3
