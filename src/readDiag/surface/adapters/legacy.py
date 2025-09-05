from __future__ import annotations
from typing import Any, Iterable, Optional, List, Dict
import pandas as pd
from ..api import DiagnosticAPI, Metadata

def _safe_call(obj: Any, names: Iterable[str], *args, **kwargs):
    for name in names:
        fn = getattr(obj, name, None)
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

    # -------- util ----------
    def _infer_kind(self) -> str:
        k = getattr(self._l, "kind", None)
        k = k() if callable(k) else k
        if k in ("conv", "rad"):
            return k
        # heurística: conv possui kx list
        if _safe_call(self._l, ("get_kx_list","kx_list")) is not None:
            return "conv"
        return "rad"

    def kind(self) -> str:
        m = _safe_call(self._l, ("meta",))
        k = getattr(m, "kind", None) if m is not None else None
        return k or self._infer_kind()

    def get_data_type(self) -> int:
        return 1 if self.kind() == "conv" else 2 if self.kind() == "rad" else 0

    def meta(self) -> Metadata:
        fi = _safe_call(self._l, ("get_file_info",))
        file_name = getattr(self._l, "file_name", None) \
            or getattr(fi, "file_name", None) \
            or getattr(self._l, "name", "unknown")
        date = getattr(self._l, "date", None) or getattr(fi, "date", None)
        kind = self.kind()
        return Metadata(file_name=file_name, date=date, kind=kind)

    def _ensure(self, expected: str, meth: str):
        k = self.kind()
        if k != expected:
            raise ValueError(f"{meth} only valid for {expected} diagnostics")

    # -------- conv API ----------
    def variables(self) -> List[str]:
        self._ensure("conv", "variables")
        res = _safe_call(self._l, ("get_variables","variables"))
        return list(res) if res is not None else []

    def kx_list(self, var: str) -> List[int]:
        self._ensure("conv", "kx_list")
        res = _safe_call(self._l, ("get_kx_list","kx_list"), var)
        return list(res) if res is not None else []

    def frame_conv(self, var: str, kx: Optional[int]=None) -> pd.DataFrame:
        self._ensure("conv", "frame_conv")
        # valida var/kx se possível
        vars_ = set(self.variables())
        if vars_ and var not in vars_:
            raise ValueError(f"unknown var {var}")
        kxs = set(self.kx_list(var)) if var else set()
        if kx is not None and kxs and kx not in kxs:
            raise ValueError(f"unknown kx {kx} for var {var}")
        res = _safe_call(self._l, ("get_dataframe","frame_conv","table"), var, kx)
        if isinstance(res, pd.DataFrame):
            return res
        res = _safe_call(self._l, ("get_dataframe","frame_conv","table"), var)
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    # -------- rad API ----------
    def channels(self) -> List[int]:
        self._ensure("rad", "channels")
        res = _safe_call(self._l, ("channels","get_channels","get_channel_list"))
        lst = list(res) if res is not None else []
        if lst and min(lst) == 0:
            lst = [i+1 for i in lst]
        return lst

    def frame_channel(self, ch: int) -> pd.DataFrame:
        self._ensure("rad", "frame_channel")
        # aceita 1-based na interface, tenta converter p/ 0-based se necessário
        res = _safe_call(self._l, ("frame_channel","get_channel_dataframe","get_dataframe"), ch)
        if isinstance(res, pd.DataFrame):
            return res
        res0 = _safe_call(self._l, ("frame_channel","get_channel_dataframe","get_dataframe"), ch-1)
        return res0 if isinstance(res0, pd.DataFrame) else pd.DataFrame()

    # -------- comum ----------
    def table(self, name: Optional[str]=None, *args, **kwargs):
        # caso especial legado de rad: mapa de canais
        if name == "diagbufchan_df":
            src = getattr(self._l, "diagbufchan_df", None)
            if isinstance(src, dict):
                keys = list(src.keys())
                if keys and min(keys) == 0:
                    return {k+1: src[k] for k in keys}
                return src
            if isinstance(src, (list, tuple)):
                return {i+1: src[i] for i in range(len(src))}
            if src is not None:
                return {1: src}
            # se não existir atributo, tenta um .table(name)
        res = _safe_call(self._l, ("table",), name, *args, **kwargs)
        if name == "diagbufchan_df":
            # normalize para dict sempre
            if isinstance(res, dict):
                keys = list(res.keys())
                if keys and min(keys) == 0:
                    return {k+1: res[k] for k in keys}
                return res
            if isinstance(res, (list, tuple)):
                return {i+1: res[i] for i in range(len(res))}
            if isinstance(res, pd.DataFrame):
                return {1: res}
            return {}
        return res if isinstance(res, pd.DataFrame) else (res if isinstance(res, dict) else pd.DataFrame())
