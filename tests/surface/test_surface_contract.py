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
            
def assert_surface_api(obj):
     assert hasattr(obj, "meta")

def test_access_adapter_smoke(handle_conv):
    d = handle_conv
    assert_surface_api(d)
    # chamadas leves do contrato
    d.kind(); d.variables(); d.kx_list()
