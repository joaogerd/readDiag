
import sys
import types
import pytest

@pytest.fixture(scope="session", autouse=True)
def mock_readDiag_dependency():
    """Ensure `gsidiag` can be imported by providing a minimal fake `readDiag` tree.
    This avoids requiring the real `readDiag` package in the test environment."""
    # Create a minimal fake module hierarchy: readDiag.reader.diagAccess, readDiag.schema.naming.resolve_col_in_df
    fake_readDiag = types.ModuleType("readDiag")
    fake_reader = types.ModuleType("readDiag.reader")
    fake_schema = types.ModuleType("readDiag.schema")
    fake_naming = types.ModuleType("readDiag.schema.naming")

    def diagAccess(*args, **kwargs):  # pragma: no cover - simple stub
        return {"opened": True, "args": args, "kwargs": kwargs}

    def resolve_col_in_df(df, *candidates):  # pragma: no cover - simple stub
        for name in candidates:
            if name in getattr(df, "columns", []):
                return name
        return candidates[0] if candidates else None

    fake_reader.diagAccess = diagAccess
    fake_naming.resolve_col_in_df = resolve_col_in_df
    fake_schema.naming = fake_naming
    fake_readDiag.reader = fake_reader
    fake_readDiag.schema = fake_schema

    sys.modules.setdefault("readDiag", fake_readDiag)
    sys.modules.setdefault("readDiag.reader", fake_reader)
    sys.modules.setdefault("readDiag.schema", fake_schema)
    sys.modules.setdefault("readDiag.schema.naming", fake_naming)

    yield

@pytest.fixture(scope="session")
def pkg_path():
    import pathlib
    return pathlib.Path(__file__).resolve().parents[1]

@pytest.fixture(scope="session", autouse=True)
def add_pkg_to_path(pkg_path):
    sys.path.insert(0, str(pkg_path))
    yield
    if str(pkg_path) in sys.path:
        sys.path.remove(str(pkg_path))
