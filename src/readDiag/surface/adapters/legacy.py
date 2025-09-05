"""
Compat adapter para instâncias "legadas" (FakeDiagConv/Rad, etc).
Converte um objeto legado para o contrato DiagnosticAPI, com duck-typing.
"""
from __future__ import annotations
from typing import Any, Iterable, Optional, List
import pandas as pd

from ..api import DiagnosticAPI, Metadata

def _safe_call(obj: Any, names: Iterable[str], *args, **kwargs):
    for name in names:
        fn = getattr(obj, name, None)
        if callable(fn):
            try:
                return fn(*args, **kwargs)
            except TypeError:
                # tenta sem args se a assinatura variar
                try:
                    return fn()
                except Exception:
                    pass
    return None

class LegacyCompatAdapter(DiagnosticAPI):
    def __init__(self, legacy: Any):
        self._l = legacy

    # --- metadados/identificação ---
    def meta(self) -> Metadata:
        fi = _safe_call(self._l, ("get_file_info",))
        file_name = getattr(self._l, "file_name", None) or getattr(fi, "file_name", None) or getattr(self._l, "name", "unknown")
        date = getattr(self._l, "date", None) or getattr(fi, "date", None)
        # Heurística do tipo
        kind = getattr(self._l, "kind", None) or getattr(fi, "kind", None)
        if not kind:
            kind = "conv" if _safe_call(self._l, ("get_kx_list","kx_list")) is not None else "rad"
        return Metadata(file_name=file_name, date=date, kind=kind)

    # --- conv API ---
    def variables(self) -> List[str]:
        res = _safe_call(self._l, ("get_variables","variables"))
        return list(res) if res is not None else []

    def kx_list(self, var: str) -> List[int]:
        res = _safe_call(self._l, ("get_kx_list","kx_list"), var)
        return list(res) if res is not None else []

    def frame_conv(self, var: str, kx: Optional[int]=None) -> pd.DataFrame:
        # tenta get_dataframe(var, kx) → get_dataframe(var) → frame_conv(var,kx)
        res = _safe_call(self._l, ("get_dataframe","frame_conv","table"), var, kx)
        if isinstance(res, pd.DataFrame):
            return res
        res = _safe_call(self._l, ("get_dataframe","frame_conv","table"), var)
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    # --- rad API ---
    def channels(self) -> List[int]:
        res = _safe_call(self._l, ("channels","get_channels","get_channel_list"))
        return list(res) if res is not None else []

    def frame_channel(self, ch: int) -> pd.DataFrame:
        res = _safe_call(self._l, ("frame_channel","get_channel_dataframe","get_dataframe"), ch)
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()

    # --- comum ---
    def table(self, *args, **kwargs) -> pd.DataFrame:
        res = _safe_call(self._l, ("table",), *args, **kwargs)
        return res if isinstance(res, pd.DataFrame) else pd.DataFrame()
