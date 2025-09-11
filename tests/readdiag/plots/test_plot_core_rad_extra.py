import pytest
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from readDiag.plotting.core import diagPlotter

def test_plot_channel_stats_rad_variants(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    for agg in ("median", "std"):
        ax = p.plot_channel_stats_rad(param="oma", agg=agg)  # different param + aggs
        assert isinstance(ax, Axes)

def test_plot_omf_distribution_uncorrected(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    ax = p.plot_omf_distribution_rad(1, corrected=False, bins=10)
    assert isinstance(ax, Axes)

def test_plot_abs_omf_map_channel_fallback_to_oma(fake_rad_diag):
    # Create a thin proxy that hides 'omf' so core falls back to 'oma'
    class Proxy(fake_rad_diag.__class__):
        def frame_channel(self, ch):
            df = super().frame_channel(ch).copy()
            if "omf" in df.columns:
                df = df.drop(columns=["omf"])
            return df
        # bring() must reflect the absence of 'omf' too
        def bring(self, channel, cols):
            df = super().bring(channel, cols)
            if "omf" in df.columns:
                df = df.drop(columns=["omf"])
            return df
    proxy = Proxy()
    p = diagPlotter(proxy)
    ax = p.plot_abs_omf_map_channel(1, param="oma", s=2)  # explicit fallback param
    assert isinstance(ax, Axes)
