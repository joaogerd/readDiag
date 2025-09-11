def test_import_gsidiag():
    import importlib
    m = importlib.import_module("gsidiag")
    assert hasattr(m, "__version__") or m is not None
