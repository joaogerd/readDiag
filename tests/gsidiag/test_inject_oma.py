
import pandas as pd
import numpy as np

def _make_conv_stack(kx, n=4):
    # Build a stacked df with MultiIndex [kx, points]
    df = pd.DataFrame({
        "omf": np.linspace(0.0, 0.3, n),
        "oma": np.zeros(n),
    })
    stacked = pd.concat({kx: df}, names=["kx"]).rename_axis(["kx", "points"]).copy()
    return stacked

def _make_rad_stack(satid, channel_value, n=3):
    df = pd.DataFrame({
        "nchan": [channel_value]*n,
        "omf": np.linspace(1.0, 1.2, n),
        "oma": np.zeros(n),
    })
    stacked = pd.concat({satid: df}, names=["SatId"]).rename_axis(["SatId", "points"]).copy()
    return stacked

def test_inject_conv_mode():
    from gsidiag.legacy_api.read import _inject_oma_from_anl
    bg = _make_conv_stack(120, n=5)
    anl = bg.droplevel(0).copy()  # analysis omf to be copied positionally into oma
    # Change the omf values to verify copy
    anl["omf"] = np.array([9,8,7,6,5], dtype=float)
    _inject_oma_from_anl(bg, anl, lvl0=120)
    # After injection, oma column at kx=120 should match analysis omf (positionally)
    got = bg.xs(120, level=0)["oma"].to_numpy()
    assert (got == np.array([9,8,7,6,5], dtype=float)).all()

def test_inject_rad_mode():
    from gsidiag.legacy_api.read import _inject_oma_from_anl
    sat = "NOAA-15"
    ch  = 1
    bg = _make_rad_stack(sat, ch, n=4)
    anl = bg.droplevel(0).copy()
    anl["omf"] = np.array([0.5, 0.6, 0.7, 0.8], dtype=float)
    _inject_oma_from_anl(bg, anl, sat_id=sat, channel_value=ch, channel_col="nchan")
    got = bg.xs(sat, level=0)["oma"].to_numpy()
    assert (got == np.array([0.5,0.6,0.7,0.8])).all()
