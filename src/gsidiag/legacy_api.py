from __future__ import annotations
from typing import Optional, Tuple, Dict, List
import pandas as pd
import geopandas as gpd

# Motor NOVO (não é legacy)
from readDiag.io.reader import diagAccess
from readDiag.surface.access_adapter import AccessAdapter
from readDiag.surface.api import DiagnosticAPI

def _to_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    # normaliza lon para [-180,180] e cria geometria
    lon = (df["lon"] + 180) % 360 - 180
    lat = df["lat"]
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(lon, lat))

class read_diag:
    """
    Legacy class preserved for backwards compatibility.
    Internamente utiliza o novo motor (diagAccess + AccessAdapter),
    mas mantém métodos com a mesma “cara” do legado.
    """

    # ------------------------ abertura ------------------------
    def __init__(
        self,
        diag_file: str,
        diag_file_anl: Optional[str] = None,
        isis_list: Optional[List[str]] = None,
        zlevs: Optional[List[float]] = None,
    ) -> None:
        self._diag_file = diag_file
        self._diag_file_anl = diag_file_anl
        self._isis_list = isis_list if isis_list is not None else ["None"]
        self._zlevs = zlevs if zlevs is not None else [
            1000.0, 900.0, 800.0, 700.0, 600.0, 500.0, 400.0, 300.0,
            250.0, 200.0, 150.0, 100.0, 50.0, 0.0
        ]

        # usa o motor baixo-nível novo
        raw = diagAccess(self._diag_file)
        self._file_type = raw.get_data_type()   # 1=conv, 2=rad
        self._idate = raw.get_date()
        # adapta para a superfície estável
        self._api: DiagnosticAPI = AccessAdapter(raw)

        # materializa DataFrames “no estilo legado”
        self._build_obsinfo()

    # ------------------------ materialização ------------------------
    def _build_obsinfo(self) -> None:
        if self._file_type == 1:  # CONV
            frames = []
            for v in self._api.variables():
                for kx in self._api.kx_list(v):
                    df = self._api.frame_conv(v, kx).copy()
                    df["var"] = v
                    df["kx"] = kx
                    frames.append(df)
            if frames:
                obs = pd.concat(frames, ignore_index=True)
                obs["idate"] = self._idate
                obs = obs.set_index(["idate", "var", "kx"])
                self.obsInfo = _to_gdf(obs.reset_index()).set_index(["idate", "var", "kx"])
            else:
                self.obsInfo = pd.DataFrame()
            self.varNames = self._api.variables()
            self._variablesList: Dict[str, List[int]] = {
                v: self._api.kx_list(v) for v in self.varNames
            }
            self._nVars = len(self.varNames)

        elif self._file_type == 2:  # RAD
            # Mantemos convenções próximas ao legado
            frames = []
            for ch in self._api.channels():
                df = self._api.frame_channel(ch).copy()
                df["channel"] = ch
                frames.append(df)
            self.obsInfo = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
            self.varNames = ["radiance"]
            self._variablesList = {"radiance": self._api.channels()}
            self._nVars = 1

        else:
            self.obsInfo = pd.DataFrame()
            self.varNames = []
            self._variablesList = {}
            self._nVars = 0

    # ------------------------ helpers “legado” ------------------------
    def _overview(self) -> None:
        # já populado em _build_obsinfo(); mantemos método p/ compat
        return

    def pfileinfo(self) -> None:
        for name in self._variablesList.keys():
            print("Variable Name :", name)
            print("              └── kx => ", end="", flush=True)
            for kx in self._variablesList[name]:
                print(kx, " ", end="", flush=True)
            print("\n")

    @staticmethod
    def filter_multiindex(df: pd.DataFrame, level_values: List[Tuple[str, object]]) -> pd.DataFrame:
        mask = None
        for level, value in level_values:
            current_mask = df.index.get_level_values(level) == value
            mask = current_mask if mask is None else (mask & current_mask)
        return df[mask] if mask is not None else df

    def summarize(self, varName: Optional[str] = None, kx: Optional[int] = None, idate=None) -> pd.DataFrame:
        if self._file_type != 1 or self.obsInfo.empty:
            return pd.DataFrame()
        data = self.obsInfo
        crit: List[Tuple[str, object]] = []
        def add(level: str, value) -> None:
            if value is not None:
                if value not in data.index.get_level_values(level).unique():
                    raise KeyError(f"{level.title()} '{value}' not found in the data.")
                crit.append((level, value))
        add("var", varName); add("kx", kx); add("idate", idate)
        filtered = self.filter_multiindex(data, crit)
        return filtered.describe() if not filtered.empty else pd.DataFrame()

    def tmsummarize(self, varName: str, kx: int) -> Dict[object, pd.DataFrame]:
        if self._file_type != 1 or self.obsInfo.empty:
            return {}
        if varName not in self.obsInfo.index.get_level_values("var").unique():
            raise KeyError(f"Variable {varName} not found in the data.")
        if kx not in self.obsInfo.index.get_level_values("kx").unique():
            raise KeyError(f"Cannot filter by kx {kx}.")
        out: Dict[object, pd.DataFrame] = {}
        for dt in self.obsInfo.index.get_level_values("idate").unique():
            df = self.filter_multiindex(self.obsInfo, [("var", varName), ("kx", kx), ("idate", dt)])
            out[dt] = df.describe()
        return out

    # atalhos úteis preservados
    def get_unique_dates(self) -> List[object]:
        return [] if self.obsInfo.empty else self.obsInfo.index.get_level_values("idate").unique().tolist()

    def get_unique_kx(self, date=None) -> List[int]:
        if self.obsInfo.empty:
            return []
        data = self.obsInfo.loc[date] if date is not None else self.obsInfo
        return data.index.get_level_values("kx").unique().tolist() if "kx" in data.index.names else []

    def get_unique_vars(self, date=None) -> List[str]:
        if self.obsInfo.empty:
            return []
        data = self.obsInfo.loc[date] if date is not None else self.obsInfo
        return data.index.get_level_values("var").unique().tolist() if "var" in data.index.names else []

