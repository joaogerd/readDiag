# tests/gsidiag/test_package_data.py
from importlib.resources import files
import yaml

def test_table_yml_packaged_and_loadable():
    yml = files("gsidiag") / "table.yml"
    assert yml.is_file(), "gsidiag/table.yml missing from installed package"
    data = yaml.safe_load(yml.read_bytes())
    assert data and "observations" in data and data["observations"]

