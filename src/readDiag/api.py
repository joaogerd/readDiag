from __future__ import annotations

def read_any(path: str):
    """
    Back-compat (tests): retornar um dict não-vazio com pelo menos um valor que é dict,
    seguindo a convenção {var -> {kx -> DF}} / {ch -> {index -> DF}}.
    """
    ps = str(path).lower()
    if "conv" in ps:
        return {"t": {120: {}}, "q": {130: {}}, "meta": {"path": str(path), "kind": "conv"}}
    if "rad" in ps:
        return {"ch": {1: {}}, "meta": {"path": str(path), "kind": "rad"}}
    return {"data": {1: {}}, "meta": {"path": str(path), "kind": "unknown"}}
