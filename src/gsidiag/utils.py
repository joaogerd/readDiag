"""
Legacy shim: `gsidiag.utils`
Bridges to modern `readDiag._utils`.
"""
try:
    from readDiag._utils import deprecated, check_kind  # type: ignore
except Exception:
    import warnings as _w
    def deprecated(msg: str):
        _w.warn(msg, DeprecationWarning, stacklevel=2)
    def check_kind(*_a, **_k):
        return True

__all__ = ["deprecated", "check_kind"]
