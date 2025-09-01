# tests/test_access_adapter_conv.py
import pandas as pd
import pytest

from readDiag.adapters import AccessAdapter


def test_access_conv_meta_kind(fake_access_conv_backend):
    api = AccessAdapter(fake_access_conv_backend)
    meta = api.meta()
    assert api.kind() == "conv"
    assert meta.file_name.endswith("2025010100")
    assert meta.sensor is None
    assert meta.n_channels is None
    assert meta.n_obs == 3


def test_access_conv_variables_kx(fake_access_conv_backend):
    api = AccessAdapter(fake_access_conv_backend)
    vars_ = api.variables()
    assert vars_ == ["t", "q"]
    assert api.kx_list("t") == [120, 130]
    assert api.kx_list("q") == [120]


def test_access_conv_frame(fake_access_conv_backend):
    api = AccessAdapter(fake_access_conv_backend)
    df = api.frame_conv("t", 120)
    assert isinstance(df, pd.DataFrame)
    assert df.iloc[0]["var"] == "t"
    assert df.iloc[0]["kx"] == 120


def test_access_conv_errors(fake_access_conv_backend):
    api = AccessAdapter(fake_access_conv_backend)
    with pytest.raises(ValueError):
        _ = api.frame_channel(1)  # wrong kind
    with pytest.raises(ValueError):
        _ = api.table("diagbuf_df")  # wrong kind


def test_access_conv_legacy_shims(fake_access_conv_backend):
    api = AccessAdapter(fake_access_conv_backend)
    assert api.get_data_type() == 1
    assert api.get_variables() == api.variables()
    assert api.get_kx_list("t") == api.kx_list("t")
    df = api.get_dataframe("t", 120)
    assert isinstance(df, pd.DataFrame)
    legacy = api.get_data_frame()
    assert "t" in legacy and 120 in legacy["t"]
    info = api.get_file_info()
    assert info["data_type"] == "conv"

