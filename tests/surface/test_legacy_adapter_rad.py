# tests/test_legacy_adapter_rad.py
import pandas as pd
import pytest

from readDiag.adapters import LegacyCompatAdapter


def test_legacy_rad_meta_kind(legacy_rad_fake):
    api = LegacyCompatAdapter(legacy_rad_fake)
    meta = api.meta()
    assert api.kind() == "rad"
    assert meta.sensor == "amsua"
    assert meta.platform == "n15"
    assert meta.n_channels == 3
    assert meta.n_obs == 3  # inferido de diagbuf_df


def test_legacy_rad_channels_and_frames(legacy_rad_fake):
    api = LegacyCompatAdapter(legacy_rad_fake)
    # LegacyCompatAdapter normaliza channels para 1-based mesmo se inferir
    assert api.channels() == [1, 2, 3]

    df1 = api.frame_channel(1)
    assert isinstance(df1, pd.DataFrame)

    # table(): "diagbufchan_df" deve ser mapeamento {index: DF}
    # Para o LegacyCompatAdapter, normalizamos para 1-based — mas toleramos 0-based
    chmap = api.table("diagbufchan_df")
    assert isinstance(chmap, dict)
    keys = set(chmap.keys())
    assert keys in ({1, 2, 3}, {0, 1, 2})
    # escolhe uma chave válida e testa
    any_key = sorted(keys)[0]
    assert isinstance(chmap[any_key], pd.DataFrame)

    # demais tabelas
    chdf = api.table("channel_df")
    main = api.table("diagbuf_df")
    ext = api.table("diagbufex_df")
    assert isinstance(chdf, pd.DataFrame)
    assert isinstance(main, pd.DataFrame)
    assert isinstance(ext, pd.DataFrame)

    # erros
    with pytest.raises(KeyError):
        _ = api.frame_channel(99)
    with pytest.raises(KeyError):
        _ = api.table("unknown_table")


def test_legacy_rad_legacy_shims(legacy_rad_fake):
    api = LegacyCompatAdapter(legacy_rad_fake)
    assert api.get_data_type() == 2
    assert api.get_channels() == [1, 2, 3]
    legacy = api.get_data_frame()
    # get_data_frame (legado) deve manter lista para diagbufchan_df
    assert isinstance(legacy["dataframes"]["diagbufchan_df"], list)
    info = api.get_file_info()
    assert info["data_type"] == "rad"

