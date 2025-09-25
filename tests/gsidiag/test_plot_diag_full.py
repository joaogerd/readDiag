# tests/gsidiag/test_plot_diag_full.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
import pytest

@pytest.fixture
def plotter(conv_data_map, rad_dataframes):
    from gsidiag.legacy_api.plot import plot_diag
    import numpy as np
    import pandas as pd

    # -------- conv ('ps') --------
    conv_map = conv_data_map.get("ps") or next(iter(conv_data_map.values()))
    cleaned = []
    for df in conv_map.values():
        c = df.copy()
        if "kx" in c.columns:
            c = c.drop(columns=["kx"])
        # campos usados nas rotinas
        for col in ("obs", "omf", "oma", "iuse", "imp"):
            if col not in c.columns:
                if col == "iuse":
                    c[col] = 1
                elif col == "imp":
                    rng = np.random.default_rng(42)
                    c[col] = rng.normal(0, 0.1, len(c))  # inclui negativos
                else:
                    c[col] = 0.0
        if "prs" not in c.columns:
            c["prs"] = 1000  # nível default para as agregações por nível
        if "time" not in c.columns:
            c["time"] = np.repeat(["2024020100", "2024020112"], len(c) // 2 + 1)[: len(c)]
        cleaned.append(c)
    conv_df = pd.concat(cleaned, keys=list(conv_map.keys()), names=["kx", "points"])

    # -------- rad ('amsua') --------
    dfs = rad_dataframes
    dgeom = dfs["diagbuf_df"].reset_index(drop=True)
    dlist = dfs["diagbufchan_df"]
    long = []
    for ich, dfc in enumerate(dlist, start=1):
        d = dfc.reset_index(drop=True).copy()
        d["nchan"] = ich
        n = min(len(d), len(dgeom))
        for col in ("lat", "lon", "time"):
            if col in dgeom.columns:
                d.loc[: n - 1, col] = dgeom.loc[: n - 1, col].to_numpy()
        for col in ("obs", "omf", "oma", "iuse", "imp"):
            if col not in d.columns:
                if col == "iuse":
                    d[col] = 1
                elif col == "imp":
                    rng = np.random.default_rng(7)
                    d[col] = rng.normal(0, 0.1, len(d))
                else:
                    d[col] = 0.0
        long.append(d)
    rad_long = pd.concat(long, ignore_index=True) if long else pd.DataFrame()
    # manter nomes exigidos por impRad/ibfRad
    rad_df = pd.concat({"n15": rad_long}, names=["SatId", "points"])

    # -------- instancia plot_diag --------
    gd = plot_diag()
    gd.obsInfo = {"ps": conv_df, "amsua": rad_df}

    # self.obs: padroniza níveis p/ kxcount, sem alterar obsInfo['amsua']
    obs_concat = pd.concat(gd.obsInfo, sort=False)
    obs_concat.index = obs_concat.index.set_names(["varName", "kx", "points"])
    gd.obs = obs_concat

    # 🔧 níveis padrão para time_series (se o método usar self.zlevs)
    gd.zlevs = [1000, 925, 850, 700, 600, 500, 400, 300, 250, 200, 150, 100, 70, 50, 30]

    return gd

def test_vcount(plotter):
    plotter.vcount()  # smoke


def test_kxcount(plotter):
    # exige que self.obs tenha nível 'kx' nomeado (fixture já garante)
    plotter.kxcount()  # smoke


def test_pcount(plotter):
    plotter.pcount("ps")  # smoke


def test_impConv(plotter):
    pytest.importorskip("seaborn")
    plotter.impConv("ps")  # smoke


def test_ibfConv(plotter):
    pytest.importorskip("seaborn")
    plotter.ibfConv("ps")  # smoke


def test_impRad(plotter):
    pytest.importorskip("seaborn")
    plotter.impRad("amsua")  # smoke


def test_ibfRad(plotter):
    pytest.importorskip("seaborn")
    plotter.ibfRad("amsua")  # smoke


def test_plot_points(tmp_path, plotter):
    """
    Exercita .plot em dados convencionais; não impomos geopandas aqui.
    Se o método exigir GeoDataFrame, o seu outro teste de mapas já cobre.
    """
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ax = plotter.plot("ps", 120, "obs", mask="iuse>=0", area=[-180, 180, -90, 90])
        assert ax is not None
    finally:
        os.chdir(cwd)


def test_ptmap(tmp_path, plotter):
    gpd = pytest.importorskip("geopandas")
    try:
        import shapely  # noqa: F401
    except Exception:
        pytest.skip("shapely ausente")

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ax = plotter.ptmap("ps", [120, 130], mask="iuse>=0", area=[-180, 180, -90, 90])
        assert ax is not None
    finally:
        os.chdir(cwd)


def test_pvmap(tmp_path, plotter):
    gpd = pytest.importorskip("geopandas")
    try:
        import shapely  # noqa: F401
    except Exception:
        pytest.skip("shapely ausente")

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        ax = plotter.pvmap(varName=["ps"], mask="iuse>=0", area=[-180, 180, -90, 90])
        assert ax is not None
    finally:
        os.chdir(cwd)


def test_statcount_smoke(plotter):
    """statcount para radiância; não exige geopandas."""
    plotter.statcount(
        varName="amsua",
        varType="n15",
        noiqc=False,
        dateIni=2024020100,
        dateFin=2024020118,
        nHour="06",
        channel=None,
        figTS=False,
        figMap=False,
    )


def test_time_series_conv_and_radi(tmp_path, plotter):
    """
    Exercita a variante LEGACY de plot_diag.time_series: o método espera que 'self'
    seja uma SEQUÊNCIA de objetos com .zlevs e .obsInfo[varName].loc[varType]
    (mesma ideia do read_diag.tocsv).
    """
    from gsidiag.legacy_api.plot import plot_diag as PlotClass

    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)

        # ---------- prepara sequência dummy de "ciclos" ----------
        conv_df = plotter.obsInfo["ps"]  # MultiIndex ['kx','points'] com colunas prs/omf/oma/iuse/imp/time

        class _Cycle:
            def __init__(self, df, zlevs):
                # time_series acessa obj.obsInfo[varName].loc[varType]
                self.obsInfo = {"ps": df}
                self.zlevs = zlevs

        # 2 ciclos para casar com dateIni..dateFin de 12h
        seq = [
            _Cycle(conv_df, plotter.zlevs),
            _Cycle(conv_df, plotter.zlevs),
        ]

        # --- Conv: chama como função "não vinculada", passando a sequência como 'self'
        PlotClass.time_series(
            seq,
            varName="ps",
            varType=120,
            mask="iuse>=0",
            dateIni=2024020100,
            dateFin=2024020112,
            nHour="12",
            Clean=True,
        )

        # --- Radiance: segue normal (essa rotina é método real do plotter)
        plotter.time_series_radi(
            varName="amsua",
            varType="n15",
            mask="iuse>=0",
            dateIni=2024020100,
            dateFin=2024020118,
            nHour="06",
            channel=[1, 2],
            Clean=True,
        )

        # Verifica que imagens foram geradas
        pngs = list(Path(".").glob("*.png"))
        assert pngs, "nenhum PNG gerado por time_series/time_series_radi"
    finally:
        os.chdir(cwd)

