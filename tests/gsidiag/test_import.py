
import importlib
import warnings

def test_import_emits_deprecation_warning(monkeypatch):
    # Reload the package to capture warning consistently
    if "gsidiag" in list(importlib.sys.modules):
        del importlib.sys.modules["gsidiag"]
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        mod = importlib.import_module("gsidiag")
    assert any(w.category is DeprecationWarning for w in rec), "No DeprecationWarning on import"
    assert hasattr(mod, "__all__") or hasattr(mod, "__doc__")
