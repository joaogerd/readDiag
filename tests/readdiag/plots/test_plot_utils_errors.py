import matplotlib
matplotlib.use("Agg")
from readDiag.plotting._utils import cmap_hex

def test_cmap_hex_out_of_range_behaves():
    c = cmap_hex(5, total=3, cmap_name="tab10")
    assert isinstance(c, str) and c.startswith("#")
