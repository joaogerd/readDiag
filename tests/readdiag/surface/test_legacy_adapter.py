# tests/readdiag/surface/test_legacy_adapter.py
import pandas as pd
from readDiag.surface.adapters import LegacyCompatAdapter

class LegacyRadProvider:
    # forma 1: atributo direto com “buracos” (1 e 3) — adapter deve normalizar
    diagbufchan_df = {1: pd.DataFrame({"x":[1]}), 3: pd.DataFrame({"x":[3]})}
    def channels(self):  # ajuda a sintetizar se necessário
        return [1, 3]
    def get_data_type(self):  # 2 => rad
        return 2

class LegacyConvProvider:
    def get_data_type(self):  # 1 => conv
        return 1
    def get_variables(self):  # usado por variables()
        return ["t"]
    def get_kx_list(self, var):
        return [120]
    def frame_conv(self, var, kx):
        # sem 'omf' — shim deve criar/renomear automaticamente
        return pd.DataFrame({"value":[0.1, -0.2]})

def test_legacy_table_strict_and_chan_mapping_and_get_data_frame():
    a = LegacyCompatAdapter(LegacyRadProvider())
    # nome inválido → KeyError (shim estrito exigido pelos testes)
    try:
        a.table("whatever")
        assert False
    except KeyError:
        pass  # :contentReference[oaicite:12]{index=12}
    # mapeamento 1-based e “get_data_frame” com lista ordenada e preenchimento
    ch_map = a.table("diagbufchan_df")                    # normaliza entradas 1..N  :contentReference[oaicite:13]{index=13}
    assert set(ch_map.keys()) == {1, 3}
    legacy = a.get_data_frame()
    lst = legacy["dataframes"]["diagbufchan_df"]          # mantém lista no ramo rad  :contentReference[oaicite:14]{index=14}
    assert isinstance(lst, list) and len(lst) == 3 and not lst[1].empty  # canal 2 preenchido

def test_legacy_conv_omf_shim_and_api():
    b = LegacyCompatAdapter(LegacyConvProvider())
    assert b.kind() == "conv"                              # inferência 1/2 → conv/rad  :contentReference[oaicite:15]{index=15}
    df = b.frame_conv("t", 120)
    assert "omf" in df.columns                             # shim garante 'omf'  :contentReference[oaicite:16]{index=16}

