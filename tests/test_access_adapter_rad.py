# tests/test_access_adapter_rad.py
import pandas as pd
import pytest

from readDiag.adapters import AccessAdapter


def test_access_rad_meta_kind(fake_access_rad_backend):
    api = AccessAdapter(fake_access_rad_backend)
    meta = api.meta()
    assert api.kind() == "rad"
    assert meta.sensor == "amsua"
    assert meta.platform == "n15"
    assert meta.n_channels == 3
    assert meta.n_obs == 3


def test_access_rad_channels_and_frames(fake_access_rad_backend):
    api = AccessAdapter(fake_access_rad_backend)
    chs = api.channels()
    assert chs == [1, 2, 3]
    df1 = api.frame_channel(1)
    assert isinstance(df1, pd.DataFrame)
    # tabelas nomeadas
    chdf = api.table("channel_df")
    main = api.table("diagbuf_df")
    ext = api.table("diagbufex_df")
    chmap = api.table("diagbufchan_df")
    assert isinstance(chdf, pd.DataFrame)
    assert isinstance(main, pd.DataFrame)
    assert isinstance(ext, pd.DataFrame)
    assert isinstance(chmap, dict)
    assert len(chmap) == 3
    # Aceita tanto base 0 (0,1,2) quanto base 1 (1,2,3)
    keys = set(chmap.keys())
    assert keys in ({0, 1, 2}, {1, 2, 3})
    for k in sorted(chmap.keys()):
        assert isinstance(chmap[k], pd.DataFrame)


def test_access_rad_errors(fake_access_rad_backend):
    api = AccessAdapter(fake_access_rad_backend)
    with pytest.raises(ValueError):
        _ = api.frame_conv("t", 120)  # wrong kind

    with pytest.raises(KeyError):
        _ = api.table("unknown_table")


def test_access_rad_legacy_shims(fake_access_rad_backend):
    api = AccessAdapter(fake_access_rad_backend)
    assert api.get_data_type() == 2
    assert api.get_channels() == api.channels()
    # get_data_frame mantém lista para channels
    legacy = api.get_data_frame()
    assert "dataframes" in legacy
    assert isinstance(legacy["dataframes"]["diagbufchan_df"], list)
    info = api.get_file_info()
    assert info["data_type"] == "rad"

