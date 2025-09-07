# tests/test_legacy_adapter_conv.py
import pandas as pd
import pytest

from readDiag.adapters import LegacyCompatAdapter


def test_legacy_conv_meta_kind(legacy_conv_fake):
    api = LegacyCompatAdapter(legacy_conv_fake)
    meta = api.meta()
    assert api.kind() == "conv"
    assert meta.file_name.endswith("2025010100")
    # best-effort fields
    assert meta.sensor is None
    assert meta.n_channels is None


def test_legacy_conv_api(legacy_conv_fake):
    api = LegacyCompatAdapter(legacy_conv_fake)
    assert api.variables() == ["t", "q"]
    assert api.kx_list("t") == [120, 130]
    df = api.frame_conv("q", 120)
    assert isinstance(df, pd.DataFrame)
    with pytest.raises(ValueError):
        _ = api.frame_channel(1)  # wrong kind
    with pytest.raises((ValueError, KeyError)):
        _ = api.table("diagbuf_df")  # wrong kind


def test_legacy_conv_legacy_shims(legacy_conv_fake):
    api = LegacyCompatAdapter(legacy_conv_fake)
    assert api.get_data_type() == 1
    assert api.get_variables() == ["t", "q"]
    assert api.get_kx_list("t") == [120, 130]
    df = api.get_dataframe("t", 120)
    assert isinstance(df, pd.DataFrame)
    legacy = api.get_data_frame()
    assert "t" in legacy and 120 in legacy["t"]
    info = api.get_file_info()
    assert info["data_type"] == "conv"

