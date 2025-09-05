from __future__ import annotations
from typing import Any, Iterable, Optional, List, Dict
import os
import pandas as pd
from ..api import DiagnosticAPI, Metadata

def _has(obj: Any, *names: str) -> bool:
    return any(getattr(obj, n, None) is not None for n in names)

def _call(obj: Any, names: Iterable[str], *args, **kwargs):
    for n in names:
        fn = getattr(obj, n, None)
        if callable(fn):
            try:
                return fn(*args, **kwargs)
            except TypeError:
                try:
                    return fn()
                except Exception:
                    pass
    return None

class LegacyCompatAdapter(DiagnosticAPI):
    def __init__(self, legacy: Any):
        self._l = legacy

    # ---------- identificação ----------
    def _infer_kind(self) -> str:
        # Prioriza sinais de CONV
        if _has(self._l, "get_variables", "variables", "get_kx_list", "kx_list", "frame_conv"):
            return "conv"
        # Depois sinais de RAD
        if _has(self._l, "channels", "get_channels", "get_channel_list", "frame_channel", "get_channel_dataframe"):
            return "rad"
        # Fallback pelo meta.kind
        m = _call(self._l, ("meta",))
        k = getattr(m, "kind", None) if m is not None else None
        if isinstance(k, str) and k in ("conv", "rad"):
            return k
        return "conv"  # escolha conservadora para os testes

    def kind(self) -> str:
        m = _call(self._l, ("meta",))
        k = getattr(m, "kind", None) if m is not None else None
        return k or self._infer_kind()

    def get_data_type(self) -> int:
        return 1 if self.kind() == "conv" else 2

    # ---------- meta ----------
    def meta(self) -> Metadata:
        m = _call(self._l, ("meta",))
        fi = _call(self._l, ("get_file_info",))
        file_name = getattr(self._l, "file_name", None) \
            or getattr(fi, "file_name", None) \
            or getattr(self._l, "name", None) \
            or getattr(m, "file_name", None) \
            or "unknown"
        date = getattr(self._l, "date", None) or getattr(fi, "date", None) or getattr(m, "date", None)
        kind = self.kind()
        sensor = getattr(m, "sensor", None)
        platform = getattr(m, "platform", None)

        # tenta parsear do nome do arquivo (ex.: diag_amsua_n19_01.YYYYMMDDHH)
        base = os.path.basename(str(file_name))
        if base.startswith("diag_"):
            parts = base.split(".")[0].split("_")
            if len(parts) >= 3:
                sensor = sensor or parts[1]
                platform = platform or parts[2]

        n_channels = None
        if kind == "rad":
            try:
                n_channels = len(self.channels())
            except Exception:
                n_channels = None

        return Metadata(
            file_name=file_name, date=date, kind=kind,
            sensor=sensor, platform=platform,
            n_channels=n_channels, n_obs=None
        )

    # ---------- conv ----------
    def variables(self) -> List[str]:
        if self.kind() != "conv":
            raise ValueError("variables only valid for conv diagnostics")
        res = _call(self._l, ("get_variables", "variables"))
        return list(res) if res is not None else []

    def kx_list(self, var: str) -> List[int]:
        if self.kind() != "conv":
            raise ValueError("kx_list only valid for conv diagnostics")
        res = _call(self._l, ("get_kx_list", "kx_list"), var)
        return list(res) if res is not None else []

    def frame_conv(self, var: str, kx: Optional[int] = None) -> pd.DataFrame:
        if self.kind() != "conv":
            raise ValueError("frame_conv only valid for conv diagnostics")
        vars_ = set(self.variables())
        if vars_ and var not in vars_:
            raise ValueError(f"unknown var {var}")
        kxs = set(self.kx_list(var)) if var else set()
        if kx is not None and kxs and kx not in kxs:
            raise ValueError(f"unknown kx {kx} for var {var}")

        res = _call(self._l, ("get_dataframe", "frame_conv", "table"), var, kx)
        if isinstance(res, pd.DataFrame):
            return res
        res = _call(self._l, ("get_dataframe", "frame_conv", "table"), var)
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    # ---------- rad ----------
    def channels(self) -> List[int]:
        if self.kind() != "rad":
            raise ValueError("channels only valid for rad diagnostics")
        res = _call(self._l, ("channels", "get_channels", "get_channel_list"))
        lst = list(res) if res is not None else []
        if lst and min(lst) == 0:
            lst = [i + 1 for i in lst]
        return lst

    def get_channels(self) -> List[int]:
        # shim legado (usado nos testes)
        return self.channels()

    def frame_channel(self, ch: int) -> pd.DataFrame:
        if self.kind() != "rad":
            raise ValueError("frame_channel only valid for rad diagnostics")
        res = _call(self._l, ("frame_channel", "get_channel_dataframe", "get_dataframe"), ch)
        if isinstance(res, pd.DataFrame):
            return res
        # tenta 0-based
        res0 = _call(self._l, ("frame_channel", "get_channel_dataframe", "get_dataframe"), ch - 1)
        return res0 if isinstance(res0, pd.DataFrame) else pd.DataFrame()

    # ---------- comum ----------
    def table(self, name: Optional[str] = None, *args, **kwargs):
        if name == "diagbufchan_df":
            # 1) tenta atributo/prop direto
            src = getattr(self._l, "diagbufchan_df", None)
            if isinstance(src, dict):
                keys = list(src.keys())
                if keys and min(keys) == 0:
                    return {k + 1: src[k] for k in keys}
                return src
            if isinstance(src, (list, tuple)):
                return {i + 1: src[i] for i in range(len(src))}
            if isinstance(src, pd.DataFrame):
                return {1: src}

            # 2) tenta método .table(name)
            res = _call(self._l, ("table",), name, *args, **kwargs)
            if isinstance(res, dict):
                keys = list(res.keys())
                if keys and min(keys) == 0:
                    return {k + 1: res[k] for k in keys}
                return res
            if isinstance(res, (list, tuple)):
                return {i + 1: res[i] for i in range(len(res))}
            if isinstance(res, pd.DataFrame):
                return {1: res}

            # 3) constrói a partir de channels/frame_channel (garantia para os testes)
            if self.kind() == "rad":
                try:
                    chs = self.channels()
                    return {i: self.frame_channel(i) for i in chs}
                except Exception:
                    return {}
            return {}
        # outros nomes: devolve DataFrame direto se houver
        res = _call(self._l, ("table",), name, *args, **kwargs)
        return res if isinstance(res, (pd.DataFrame, dict)) else pd.DataFrame()

    # shim para o plotter legacy que espera esse formato
    def get_data_frame(self) -> Dict[str, Dict[str, list]]:
        chmap = self.table("diagbufchan_df")
        if isinstance(chmap, dict) and chmap:
            maxk = max(chmap.keys())
            lst = [chmap.get(i + 1, chmap.get(i, pd.DataFrame())) for i in range(maxk)]
        else:
            lst = []
        return {"dataframes": {"diagbufchan_df": lst}}
