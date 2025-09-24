
import types
import pandas as pd
import numpy as np
import importlib
import sys

def _make_rad_stub():
    class RD:
        def get_data_type(self):
            return 2  # radiance
        def get_dataframe(self, *args, **kwargs):
            # Return a bundle with required dataframes
            # diagbuf_df is a placeholder (geo/scan meta); not used deeply in our check
            diagbuf_df = pd.DataFrame({"dummy":[1]})
            # Create per-channel frames
            d1 = pd.DataFrame({
                "lat":[0.0, 1.0], "lon":[0.0, 1.0],
                "nchan":[1,1], "idqc":[0,0], "iuse":[1,1],
                "obs":[200.0, 201.0], "omf":[-0.1, 0.2], "oma":[0.0,0.0]
            })
            d2 = pd.DataFrame({
                "lat":[-1.0, 2.0], "lon":[-2.0, 3.0],
                "nchan":[2,2], "idqc":[0,0], "iuse":[1,1],
                "obs":[220.0, 221.0], "omf":[0.0, 0.3], "oma":[0.0,0.0]
            })
            return {"dataframes":{"diagbuf_df":diagbuf_df, "diagbufchan_df":[d1, d2]}, "meta":{"sensor":"amsua_n15"}}
    return RD()

def test_read_rad_builds_obsinfo(monkeypatch):
    import gsidiag.legacy_api.read as legacy_read
    def fake_diag_access(*a, **k):
        return _make_rad_stub()
    sys.modules["readDiag.reader"].diagAccess = fake_diag_access

    g = legacy_read.read_diag("diag_rad_bg", None)
    # sensor name from meta or default; we accept presence of any key
    assert isinstance(g.obsInfo, dict) and len(g.obsInfo) >= 1
    sensor_key = next(iter(g.obsInfo.keys()))
    df = g.obsInfo[sensor_key]
    assert not df.empty
    assert {"lat","lon","omf","oma"} <= set(df.columns)
    assert any(df["nchan"].unique())
    assert g.close() == 0
