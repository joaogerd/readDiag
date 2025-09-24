
import importlib

def test_legacy_read_module_imports():
    mod = importlib.import_module("gsidiag.legacy_api.read")
    assert hasattr(mod, "__name__")

def test_legacy_plot_module_imports():
    mod = importlib.import_module("gsidiag.legacy_api.plot")
    assert hasattr(mod, "__name__")
