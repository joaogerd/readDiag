
import matplotlib
matplotlib.use("Agg")  # headless backend

def test_geoMap_returns_axes():
    import matplotlib.pyplot as plt
    from gsidiag.legacy_api.plot import geoMap
    ax = geoMap(area=None, ax=None)
    # Should return a Matplotlib Axes (with or without Cartopy projection)
    import matplotlib.axes
    assert isinstance(ax, matplotlib.axes.Axes)
    # Draw to ensure no errors
    ax.plot([0,1],[0,1])
    plt.close(ax.figure)
