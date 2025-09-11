import pytest
from readDiag.plotting.core import diagPlotter

def test_plot_channel_stats_rad_invalid_agg(fake_rad_diag):
    p = diagPlotter(fake_rad_diag)
    with pytest.raises(ValueError):
        p.plot_channel_stats_rad(param="omf", agg="not_a_stat")

def test_plot_abs_omf_map_channel_missing_metrics(fake_rad_diag):
    class Proxy(fake_rad_diag.__class__):
        def frame_channel(self, ch):
            df = super().frame_channel(ch).copy()
            for col in ["omf", "oma", "omf_nbc"]:
                if col in df.columns:
                    df = df.drop(columns=[col])
            return df
        def bring(self, channel, cols):
            df = super().bring(channel, cols)
            for col in ["omf", "oma", "omf_nbc"]:
                if col in df.columns:
                    df = df.drop(columns=[col])
            return df
    p = diagPlotter(Proxy())
    with pytest.raises(KeyError):
        p.plot_abs_omf_map_channel(1, s=2)
