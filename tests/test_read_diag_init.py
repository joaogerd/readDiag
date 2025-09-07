from __future__ import annotations
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd
import pytest


def _write_fakepkg(tmp_path: Path, src_path: Path) -> str:
    """Cria um pacote temporário 'fakepkg' contendo o __main__.py fornecido
    e stubs mínimos para plot_utils e diagAccess, e injeta um stub de geopandas."""
    pkg = tmp_path / "fakepkg"
    pkg.mkdir()

    # __init__.py
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    # __main__.py (cópia 1:1 do arquivo do usuário)
    (pkg / "__main__.py").write_text(Path(src_path).read_text(encoding="utf-8"), encoding="utf-8")

    # plot_utils.py – stub básico usado pelo __main__.py
    (pkg / "plot_utils.py").write_text(
        """
class plot_diag:
    def __init__(self, owner): self.owner = owner
    def plot(self, *a, **k): return ("plot", a, k)
    def ptmap(self, *a, **k): return ("ptmap", a, k)
    def pvmap(self, *a, **k): return ("pvmap", a, k)
    def pcount(self, *a, **k): return ("pcount", a, k)
    def vcount(self, *a, **k): return ("vcount", a, k)
    def kxcount(self, *a, **k): return ("kxcount", a, k)
    def plot_time_series_mean(self, *a, **k): return ("ts_mean", a, k)
    def plot_time_series_mean_std(self, *a, **k): return ("ts_mean_std", a, k)
        """,
        encoding="utf-8",
    )

    # diagAccess.py – stub que devolve um dicionário no formato esperado por _process_conventional_data
    (pkg / "diagAccess.py").write_text(
        """
from datetime import datetime
import pandas as pd

class diagAccess:
    def __init__(self, path):
        self._path = path

    def get_data_type(self):
        # 1 = convencional (como o __main__.py espera no método _process_conventional_data)
        return 1

    def get_date(self):
        return datetime(2024, 1, 30, 18, 0, 0)

    def get_data_frame(self):
        # Estrutura: dict[var][kx] = DataFrame com 'lat' e 'lon'
        df_t_120 = pd.DataFrame(
            {
                "lat": [-23.5, -22.9],
                "lon": [315.1, 320.2],  # será convertido para [-180, 180) no método
                "robs": [1.0, 2.0],
                "omf": [0.1, -0.2],
                "oma": [0.05, -0.1],
                "err": [0.5, 0.5],
            }
        )
        df_q_100 = pd.DataFrame(
            {
                "lat": [-10.0, -10.5, -11.0],
                "lon": [350.0, 10.0, 180.0],
                "robs": [0.3, 0.4, 0.5],
                "omf": [0.0, 0.0, 0.0],
                "oma": [0.0, 0.0, 0.0],
                "err": [1.0, 1.0, 1.0],
            }
        )
        return {"t": {120: df_t_120}, "q": {100: df_q_100}}
        """,
        encoding="utf-8",
    )

    # Injeta um stub de geopandas no sys.modules (evita dependência real de GeoPandas/Shapely)
    class _FakeGeoPandasModule:
        GeoDataFrame = pd.DataFrame

        @staticmethod
        def points_from_xy(lon, lat):
            # Retorna uma "série de geometria" fake; o código só precisa da coluna existir.
            return pd.Series([None] * len(lon))

    sys.modules.setdefault("geopandas", _FakeGeoPandasModule())

    # Deixa o pacote importável
    sys.path.insert(0, str(tmp_path))
    return "fakepkg"


@pytest.fixture(scope="module")
def fakepkg(tmp_path_factory) -> str:
    tmp = tmp_path_factory.mktemp("pkgspace")
    # Caminho do __main__.py fornecido pelo usuário (gravado pelo runner no sandbox)
    src = Path("/mnt/data/__main__.py")
    return _write_fakepkg(tmp, src)


def test_init_accepts_str(fakepkg):
    mod = __import__(f"{fakepkg}.__main__", fromlist=["*"])
    # Não deve explodir; _process_files roda e popula obsInfo com dados fake
    rd = mod.read_diag(diag_file="data/diag_conv_01.2024013018")
    assert isinstance(rd._diag_file, list) and rd._diag_file == ["data/diag_conv_01.2024013018"]


def test_init_accepts_list(fakepkg):
    mod = __import__(f"{fakepkg}.__main__", fromlist=["*"])
    rd = mod.read_diag(diag_file=["a", "b"], diag_file_anl=None)
    assert rd._diag_file == ["a", "b"]
    assert rd._diag_file_anl == [None, None]


def test_init_diag_file_anl_mismatch_raises(fakepkg):
    mod = __import__(f"{fakepkg}.__main__", fromlist=["*"])
    with pytest.raises(ValueError):
        mod.read_diag(diag_file=["a", "b"], diag_file_anl=["only-one"])

