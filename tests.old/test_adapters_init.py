# tests/test_adapters_init.py
import importlib

def test_adapters_exports():
    """Ensure adapters subpackage exports only the stable API."""
    adapters = importlib.import_module("readDiag.adapters")

    # __all__ must be defined
    assert hasattr(adapters, "__all__")
    exported = set(adapters.__all__)

    # Expected symbols
    expected = {"AccessAdapter", "LegacyCompatAdapter"}
    assert exported == expected

    # They must be importable directly
    for name in expected:
        assert hasattr(adapters, name), f"{name} not found in adapters"
        obj = getattr(adapters, name)
        assert isinstance(obj, type), f"{name} is not a class"

