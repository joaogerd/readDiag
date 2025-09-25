from pathlib import Path

import pytest


def test_datasources_load_and_lookup(monkeypatch, minimal_yaml: Path):
    # Import the module and rebind the singleton to point to our temporary YAML
    import importlib
    ds_module = importlib.import_module("gsidiag.datasources")  # adjust if your package path differs

    # Rebuild the singleton using temporary YAML
    ds_module._DS_INFO = ds_module.DataSourcesInfo(yaml_file=minimal_yaml)

    ds = ds_module.DataSourcesInfo(yaml_file=minimal_yaml)

    # Platforms
    plats = ds.platforms()
    assert "120" in plats and "n19" in plats

    # Variables per kx
    assert ds.variables_for("120") == ["ps", "t"]
    assert ds.variables_for("n19") == ["amsua"]

    # Detail returns a copy of dict with expected keys
    d = ds.detail("120", "ps")
    assert d["abbreviation"] == "ADPUPA"
    assert d["instrument"] == "Radiosonde"
    assert d["color"] == "#1f77b4"
    assert d["symbol"] == "s"
    assert d["iuse"] == "1"

    # ds.get basic fields
    assert ds.get("120", "ps", "instrument") == "Radiosonde"
    assert ds.get("120", "ps", "color") == "#1f77b4"
    assert ds.get("120", "ps", "nonexistent_key") == ""


def test_getVarInfo_yaml_priority_and_fallbacks(monkeypatch, minimal_yaml: Path):
    import importlib
    ds_module = importlib.import_module("gsidiag.datasources")

    # Inject a singleton tied to our minimal YAML
    ds_module._DS_INFO = ds_module.DataSourcesInfo(yaml_file=minimal_yaml)

    # YAML-priority: instrument present for (120, ps)
    assert ds_module.getVarInfo("120", "ps", "instrument") == "Radiosonde"

    # Fallback for (n19, amsua): instrument was empty in YAML → heuristic
    inst = ds_module.getVarInfo("n19", "amsua", "instrument")
    # Heuristic should be "NOAA-19 AMSU-A"
    assert inst == "NOAA-19 AMSU-A"

    # Platform field uses canonical_platform
    assert ds_module.getVarInfo("n19", "amsua", "platform") == "NOAA-19"
    assert ds_module.getVarInfo("metop-a", "iasi", "platform") == "MetOp-A"
    assert ds_module.getVarInfo("npp", "atms", "platform") == "Suomi-NPP"

    # Sensor field fallback
    assert ds_module.getVarInfo("n19", "amsua", "sensor") == "AMSUA"
    assert ds_module.getVarInfo("foo", "bar", "sensor") == "BAR".upper()

    # Unknown field returns empty string (not None)
    assert ds_module.getVarInfo("n19", "amsua", "unknown_field") == ""


def test_canonical_platform_standalone():
    from gsidiag.datasources import canonical_platform

    assert canonical_platform("n19") == "NOAA-19"
    assert canonical_platform("N20") == "NOAA-20"
    assert canonical_platform("n21") == "NOAA-21"
    assert canonical_platform("npp") == "Suomi-NPP"
    assert canonical_platform("metop-a") == "MetOp-A"
    assert canonical_platform("metop_b") == "MetOp-B"
    assert canonical_platform("120") == "Conventional (kx=120)"
    assert canonical_platform("") == "PLATFORM"
    assert canonical_platform(None) == "PLATFORM"  # type: ignore[arg-type]

