
import pathlib
import yaml

def test_table_yaml_is_loadable(pkg_path):
    yml = pkg_path / "gsidiag" / "table.yml"
    assert yml.exists(), "table.yml must exist"
    data = yaml.safe_load(yml.read_text())
    assert isinstance(data, dict) and "observations" in data and isinstance(data["observations"], list)
    # Sanity: at least one kx entry and nested details
    first = data["observations"][0]
    assert "kx" in first and "details" in first and isinstance(first["details"], list)

def test_dataSourcesInfo_parses_yaml(monkeypatch):
    import gsidiag.datasources as ds
    # Build a tiny synthetic YAML file to exercise edge cases
    tmp_yaml = """
observations:
  - kx: 999
    details:
      - var: t
        abbreviation: TESTSRC
        instrument: Test Instrument
        color: "#000000"
        symbol: "*"
        iuse: "1"
"""
    tmpdir = pathlib.Path.cwd() / "tmp_ds"
    tmpdir.mkdir(exist_ok=True)
    yml = tmpdir / "table.yml"
    yml.write_text(tmp_yaml)

    # Monkeypatch module to read from our synthetic YAML
    monkeypatch.setattr(ds.path, "join", lambda a, b: str(yml))
    monkeypatch.setattr(ds.path, "dirname", lambda _: str(tmpdir))

    info = ds.dataSourcesInfo()
    assert isinstance(info.tab, dict), "tab should be a dict"
    assert "observations" in info.tab and info.tab["observations"][0]["kx"] == 999

def test_getVarInfo_contract():
    import gsidiag.datasources as ds
    # Function should exist and accept varName/varType; returns a string
    assert hasattr(ds, "getVarInfo")
    out = ds.getVarInfo(varName="t", varType="TESTSAT")
    assert isinstance(out, str)
