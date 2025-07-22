
# ---------------------------------------------------------------------------
#src/readDiag/__init__.py
# ---------------------------------------------------------------------------

try:
    from .reader import diagAccess
    from .plotting import diagPlotter
    __all__ = ['diagAccess', 'diagPlotter']
except ModuleNotFoundError:
    pass  # ou log, ou warning


