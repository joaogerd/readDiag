# tests/readdiag/surface/test_access_adapter_rad.py
import pandas as pd
from datetime import datetime
from readDiag.surface import AccessAdapter

def test_access_adapter_rad_tables_and_frames(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)
    assert a.kind() == "rad"
    # mapeamento 1-based e nomes estáveis de tabelas
    ch_map = a.table("diagbufchan_df")
    assert set(ch_map.keys()) == {1, 2, 3}
    assert "sfcstp" in a.table("diagbuf_df").columns
    assert "freq" in a.table("channel_df").columns 
    # frame_channel: índice público é 1-based
    df2 = a.frame_channel(2)
    assert {"emiss", "omf"} <= set(df2.columns)

def test_access_adapter_rad_table_unknown_raises(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)
    try:
        a.table("unknown")
        assert False, "deveria ter lançado KeyError"
    except KeyError:
        pass  # nome não reconhecido → KeyError (contrato)  :contentReference[oaicite:4]{index=4}

def test_access_adapter_bring_join_and_fallbacks(rad_backend_fake):
    a = AccessAdapter(rad_backend_fake)
    # Caso 1: join por chave (entre ch_df e diagbuf_df)
    out = a.bring(1, ["zasat"])
    assert "zasat" in out.columns                      # :contentReference[oaicite:5]{index=5}
    # Caso 2: coluna já existe → retorno direto (sem merge)
    out2 = a.bring(1, ["emiss"])
    assert out2.equals(a.frame_channel(1))               # :contentReference[oaicite:6]{index=6}
    # Caso 3: join posicional (alinha por comprimento quando não há chaves)
    out3 = a.bring(1, ["zasat"], on=["__nope__"])       # força fallback posicional
    assert "zasat" in out3.columns                      # :contentReference[oaicite:7]{index=7}
    # Caso 4: coluna inexistente em qualquer tabela → KeyError
    try:
        a.bring(1, "not_here")
        assert False, "deveria ter lançado KeyError"
    except KeyError:
        pass                                             # :contentReference[oaicite:8]{index=8}

