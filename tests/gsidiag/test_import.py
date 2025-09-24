
import warnings
import importlib

def test_import_emits_deprecation_warning():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        import gsidiag  # noqa: F401
        assert any(issubclass(ww.category, DeprecationWarning) for ww in w), "Expected DeprecationWarning"

def test_init_exports_symbols():
    import gsidiag
    # The legacy facade typically exposes a `read_diag` entry point if present
    assert hasattr(gsidiag, "read_diag") or hasattr(gsidiag, "plot_diag")
