def test_access_adapter_file_name_property(monkeypatch):
    from readDiag.adapters.access import AccessAdapter
    class Fake:
        def get_file_info(self):
            return {"file_name": "X", "date": "2024010100", "data_type": "conv"}
    a = AccessAdapter(Fake())
    assert a.file_name == "X"
    # escrever no property deve falhar
    import pytest
    with pytest.raises(AttributeError):
        setattr(a, "file_name", "Y")

