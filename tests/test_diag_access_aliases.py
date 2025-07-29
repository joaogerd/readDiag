import os
import pytest
from readDiag import diagAccess
from datetime import datetime
import warnings
import pandas as pd

TEST_FILE = os.path.join(os.path.dirname(__file__), "../data/diag_conv_01.2020010100")

def test_get_overview_and_alias():
    diag = diagAccess(TEST_FILE)

    # Teste do método novo
    overview_text = diag.get_overview()
    assert isinstance(overview_text, str)
    assert "File" in overview_text
    assert "Conventional" in overview_text

    # Teste do método antigo com aviso
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        overview_old = diag.overview()
        assert len(w) > 0
        assert "deprecated" in str(w[0].message)
        assert overview_old == overview_text

def test_get_file_info_and_alias():
    diag = diagAccess(TEST_FILE)

    info = diag.get_file_info()
    assert isinstance(info, dict)
    assert info["data_type"] == "conv"
    assert info["file_name"] == TEST_FILE
    assert isinstance(info["date"], datetime)

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        legacy = diag.pfileinfo()
        assert legacy == info
        assert len(w) > 0
        assert "deprecated" in str(w[0].message)

def test_export_to_csv_and_alias(tmp_path):
    diag = diagAccess(TEST_FILE)
    var = next(iter(diag.get_variables()))
    kx = diag.get_kx_list(var)[0]

    new_file = tmp_path / "export_new.csv"
    legacy_file = tmp_path / "export_old.csv"

    # novo
    diag.export_to_csv(new_file, var=var, kx=kx)
    assert new_file.exists()
    df_new = pd.read_csv(new_file)
    assert not df_new.empty

    # antigo
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        diag.tocsv(legacy_file, var=var, kx=kx)
        assert len(w) > 0
        assert "deprecated" in str(w[0].message)
        df_old = pd.read_csv(legacy_file)
        assert df_old.equals(df_new)
