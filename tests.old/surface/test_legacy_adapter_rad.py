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

    # canais normalizados
    assert api.channels() == [1, 2, 3]

    df1 = api.frame_channel(1)
    assert isinstance(df1, pd.DataFrame)

    # diagbufchan_df -> mapeamento {canal: DF}
    chmap = api.table("diagbufchan_df")
    assert isinstance(chmap, dict)
    keys = set(chmap.keys())
    assert keys in ({1, 2, 3}, {0, 1, 2})
    any_key = sorted(keys)[0]
    assert isinstance(chmap[any_key], pd.DataFrame)

    # demais tabelas
    chdf = api.table("channel_df")
    main = api.table("diagbuf_df")
    ext = api.table("diagbufex_df")
    assert isinstance(chdf, pd.DataFrame)
    assert isinstance(main, pd.DataFrame)
    assert isinstance(ext, pd.DataFrame)

    # erros: AGORA chamando algo dentro do bloco
    with pytest.raises(KeyError):
        api.table("desconhecida")

    with pytest.raises(KeyError):
        api.table("")  # nome vazio

    with pytest.raises(KeyError):
        api.table(None)  # type: ignore[arg-type]


def test_legacy_rad_legacy_shims(legacy_rad_fake):
    api = LegacyCompatAdapter(legacy_rad_fake)
    assert api.get_data_type() == 2
    assert api.get_channels() == [1, 2, 3]
    legacy = api.get_data_frame()
    # get_data_frame (legado) deve manter lista para diagbufchan_df
    assert isinstance(legacy["dataframes"]["diagbufchan_df"], list)
    info = api.get_file_info()
    assert info["data_type"] == "rad"

