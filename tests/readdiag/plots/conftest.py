
import os
import sys
import math
import types
import pytest
import numpy as np
import pandas as pd

# Use non-interactive backend for Matplotlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

class _Meta:
    def __init__(self, date="2024013018"):
        self.date = date

@pytest.fixture
def fake_conv_diag():
    rng = np.random.default_rng(0)
    def make_df(n):
        lat = rng.uniform(-60, 15, n)
        lon = rng.uniform(-90, -30, n)
        omf = rng.normal(0, 1, n)
        oma = omf + rng.normal(0, 0.5, n)
        qc  = rng.integers(0, 2, n)  # 0/1
        return pd.DataFrame({"lat": lat, "lon": lon, "omf": omf, "oma": oma, "qc_flag": qc, "idqc": qc})
    frames = {120: make_df(50), 121: make_df(40)}
    class ConvDiag:
        def meta(self): return _Meta()
        def kind(self): return "conv"
        def variables(self): return ["t"]
        def kx_list(self, var): return sorted(frames.keys()) if var == "t" else []
        def frame_conv(self, var, kx): 
            if var != "t": raise KeyError(var)
            return frames[int(kx)]
        def get_dataframe(self, var, kx):
            # Alias used by spatial plotting path
            return self.frame_conv(var, kx)
        def channels(self): return []
        def frame_channel(self, ch): raise IndexError("no channels in conv")
        def table(self, name): return None
        def get_data_type(self): return 1
        def get_data_frame(self): return {"t": frames}
        def get_variables(self): return ["t"]
        def get_kx_list(self, var): return self.kx_list(var)
    return ConvDiag()

@pytest.fixture
def fake_rad_diag():
    rng = np.random.default_rng(1)
    npts = 80
    lat = rng.uniform(-60, 15, npts)
    lon = rng.uniform(-90, -30, npts)
    df_geo = pd.DataFrame({"lat": lat, "lon": lon})
    def make_ch(mu):
        omf = rng.normal(mu, 1.0, npts)
        oma = omf + rng.normal(0, 0.5, npts)
        omf_nbc = omf * 0.9
        qc = rng.integers(0, 2, npts)
        return pd.DataFrame({"omf": omf, "oma": oma, "omf_nbc": omf_nbc, "qc_flag": qc, "idqc": qc})
    ch_list = [make_ch(0.0), make_ch(0.5)]
    class RadDiag:
        def meta(self): return _Meta()
        def kind(self): return "rad"
        def variables(self): return []
        def kx_list(self, var): return []
        def frame_conv(self, var, kx): raise KeyError("not conv")
        def channels(self): return [1, 2]
        def frame_channel(self, ch): return ch_list[int(ch)-1]
        def table(self, name):
            if name == "channel_df":
                import pandas as pd
                return pd.DataFrame({"channel": [1, 2], "center_freq": [23.8, 31.4]}).set_index("channel")
            return None
        def get_data_type(self): return 2
        def get_data_frame(self):
            return {"dataframes": {"diagbuf_df": df_geo, "diagbufchan_df": ch_list}}
        def bring(self, channel, cols):
            chdf = self.frame_channel(channel).reset_index(drop=True)
            base = df_geo.reset_index(drop=True)
            df = pd.concat([base, chdf], axis=1)
            core_metrics = ["omf", "oma", "omf_nbc", "qc_flag", "idqc"]
            want = list(dict.fromkeys(list(cols or []) + core_metrics + ["lat", "lon"]))
            existing = [c for c in want if c in df.columns]
            return df[existing] if existing else df
    return RadDiag()

@pytest.fixture(autouse=True)
def close_figures():
    yield
    plt.close("all")
