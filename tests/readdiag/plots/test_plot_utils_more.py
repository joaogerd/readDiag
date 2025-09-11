import matplotlib
matplotlib.use("Agg")
import pytest
from readDiag.plotting._utils import wrap_label, cmap_hex

def test_wrap_label_edge_cases():
    s = "abc def ghi"
    with pytest.raises(ValueError):
        wrap_label(s, width=0)
    assert wrap_label("", width=5) == ""
    assert wrap_label(None, width=5) == ""

def test_cmap_hex_large_index_and_single_total():
    assert isinstance(cmap_hex(99, total=1), str)
