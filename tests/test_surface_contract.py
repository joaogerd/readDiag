# tests/test_surface_contract.py
from readDiag.surface import DiagnosticAPI

def check_api(d: DiagnosticAPI):
    meta = d.meta()
    assert meta.file_name and meta.date and d.kind() in {"conv", "rad"}
    if d.kind() == "conv":
        for var in d.variables():
            for kx in d.kx_list(var):
                df = d.frame_conv(var, kx)
                assert {"lat","lon"} <= set(df.columns)
    else:
        chs = d.channels()
        _ = d.table("diagbuf_df")
        for i in chs:
            df = d.frame_channel(i)
            assert "omf" in df.columns

def test_access_adapter_smoke():
    from readDiag.open import open_diagnostic
    d = open_diagnostic("dataTest/exp20/diag_conv_01.2024013018")
    check_api(d)

