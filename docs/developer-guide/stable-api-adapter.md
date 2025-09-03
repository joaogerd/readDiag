# Developer Guide — Stable API Adapter

**Last updated:** 2025-08-30

This guide documents how to evolve `readDiag` safely after we introduced a stable
surface (`DiagnosticAPI`) plus adapters that decouple `plotting.py` from `reader.py`.
It’s written to be future‑proof, so that “future‑you” can quickly understand
what to touch when formats change — and what must *not* change.

---

## 1. Goals & Vocabulary

**Goal.** Provide a stable, *format‑agnostic* API that plotting and higher‑level tools
depend on. File formats and low‑level readers can change; plotting should not.

**Stable surface.** A minimal, typed interface (the `DiagnosticAPI` `Protocol`) that
returns plain Python types and pandas `DataFrame`s. It lives in `readDiag/surface.py`.

**Adapter.** A thin class that translates any backend (e.g., `reader.diagAccess`)
to the stable surface. The current adapter is `AccessAdapter` in `readDiag/adapters.py`.

**Factory.** `open_diagnostic(path, **kwargs)` builds a backend, chooses an adapter,
and returns a `DiagnosticAPI` instance.

**Legacy.** Existing public functions/classes that your tests rely on
(`readDiag/api.py`, `diagAccess`, legacy plotting entry points). We keep them working,
with deprecations planned, not breakages.

---

## 2. Stable Surface (`readDiag/surface.py`)

The stable surface is small by design. Keep it frozen unless absolutely necessary.

```python
# readDiag/surface.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, Literal, Optional
import pandas as pd

Kind = Literal["conv", "rad"]

@dataclass(frozen=True)
class Metadata:
    file_name: str
    date: datetime
    kind: Kind
    sensor: Optional[str] = None
    platform: Optional[str] = None
    n_channels: Optional[int] = None
    n_obs: Optional[int] = None

class DiagnosticAPI(Protocol):
    # generic
    def meta(self) -> Metadata: ...
    def kind(self) -> Kind: ...

    # conv
    def variables(self) -> list[str]: ...
    def kx_list(self, var: str) -> list[int]: ...
    def frame_conv(self, var: str, kx: int) -> pd.DataFrame: ...

    # rad
    def channels(self) -> list[int]: ...
    def frame_channel(self, ch_index: int) -> pd.DataFrame: ...
    def table(self, name: str) -> pd.DataFrame | dict[int, pd.DataFrame]: ...
```

**Do not** leak backend‑specific dict structures through this interface.

---

## 3. Adapter (`readDiag/adapters.py`)

`AccessAdapter` wraps the current `reader.diagAccess` and exposes the stable surface.
It also provides **legacy shims** so existing plotting/tests keep working:

- `get_data_frame()`, `get_variables()`, `get_kx_list()`, `get_channels()`,
  `get_dataframe(var, kx)`, `get_data_type()`, `get_file_info()`.

These shims are marked for deprecation in a future release.

**Key normalization rules inside the adapter:**

- Map any backend column names to the stable set (e.g., `lat`, `lon`, `omf`, `omf_nbc`).
- Convert sentinel values to `NaN`.
- Normalize types (e.g., timestamps to `datetime`, indices to `int`).

Skeleton (abridged):

```python
# readDiag/adapters.py (excerpt)
from .surface import DiagnosticAPI, Metadata, Kind
from .reader import diagAccess

class AccessAdapter(DiagnosticAPI):
    def __init__(self, backend: diagAccess) -> None:
        m = backend.get_file_info()
        self._meta = Metadata(
            file_name=m["file_name"],
            date=m["date"],
            kind=("rad" if m.get("data_type") == "rad" else "conv"),
            sensor=m.get("sensor"),
            platform=(str(m.get("platform")) if m.get("platform") is not None else None),
            n_channels=m.get("n_channels"),
            n_obs=m.get("n_obs"),
        )
        self._b = backend

    # --- API methods ---
    def meta(self): return self._meta
    def kind(self): return self._meta.kind
    # conv/rad data access ...

    # --- legacy shims (for plotting/tests) ---
    def get_data_type(self) -> int: return 2 if self.kind() == "rad" else 1
    def get_variables(self) -> list[str]: return self.variables()
    def get_kx_list(self, var: str) -> list[int]: return self.kx_list(var)
    def get_channels(self) -> list[int]: return self.channels()
    def get_dataframe(self, var: str, kx: int): return self.frame_conv(var, kx)
    def get_data_frame(self): ...
    def get_file_info(self) -> dict: ...
```

---

## 4. Factory (`readDiag/open.py`) & Routing

`open_diagnostic(path, **kwargs)` returns a `DiagnosticAPI`:

```python
# readDiag/open.py
from .surface import DiagnosticAPI
from .adapters import AccessAdapter
from .reader import diagAccess

def open_diagnostic(path: str, **kwargs) -> DiagnosticAPI:
    backend = diagAccess(path, **kwargs)
    # If/when versions arrive, route by header:
    # info = backend.get_file_info()
    # return AccessAdapterV2(backend) if info.get("version") == 2 else AccessAdapter(backend)
    return AccessAdapter(backend)
```

---

## 5. Plotting (`readDiag/plotting.py`) – How It Uses the Surface

- The plotter accepts both an API instance *or* a legacy `diagAccess`.
- It only wraps the **real** `diagAccess` (not test fakes), using a strict guard.
- Prefer using `variables()/kx_list()/frame_conv()` (conv) and
  `channels()/frame_channel()/table()` (rad). Legacy dict walking is deprecated.

`__init__` (core logic):

```python
if hasattr(diag, "kind") and hasattr(diag, "meta"):
    self.diag = diag                    # DiagnosticAPI
elif isinstance(diag, _DiagAccess) and hasattr(diag, "get_file_info") and hasattr(diag, "file_name"):
    try:
        self.diag = AccessAdapter(diag) # wrap real backend
    except Exception:
        self.diag = diag                # fallback for odd cases
else:
    self.diag = diag                    # keep legacy/fake

self.kind = (self.diag.kind() if hasattr(self.diag, "kind")
             else ("rad" if getattr(self.diag, "get_data_type", lambda: 1)() == 2 else "conv"))
```

---

## 6. Legacy Compatibility Strategy

- Leave legacy APIs in place (module `readDiag/api.py`, `diagAccess`, etc.).
- Provide shims in the adapter so old plotting/tests keep passing.
- Mark shims with `DeprecationWarning` after one stable release.
- Publish deprecation plan in `CHANGELOG.md` (see template below).

---

## 7. Contract Tests (Recommended)

Add tests that validate any `DiagnosticAPI` implementation.
This prevents accidental coupling to a specific backend.

```python
# tests/test_surface_contract.py (sketch)
from readDiag.surface import DiagnosticAPI

def check_api(d: DiagnosticAPI):
    m = d.meta()
    assert m.file_name and m.date and d.kind() in ('conv', 'rad')
    if d.kind() == "conv":
        for var in d.variables():
            for kx in d.kx_list(var):
                df = d.frame_conv(var, kx)
                assert ('lat', 'lon') <= set(df.columns)
    else:
        _ = d.table("diagbuf_df")
        for i in d.channels():
            df = d.frame_channel(i)
            assert "omf" in df.columns

def test_access_adapter_conv_smoke(conv_file_path):
    from readDiag.open import open_diagnostic
    d = open_diagnostic(conv_file_path)
    check_api(d)
```

---

## 8. Adding a New Format/Version – Checklist

1. Identify schema diffs (columns, types, sentinels).  
2. Create `AccessAdapterV2` implementing `DiagnosticAPI`.  
3. Normalize columns (`lat/lon/omf/...`), types, and NaNs in the adapter.  
4. Route in `open_diagnostic` by header/version.  
5. Add/extend contract tests for the new adapter.  
6. Keep legacy shims for one release; emit `DeprecationWarning`.  
7. Run CI: `pytest`, `mypy`, `ruff`, `black`.  
8. Update docs and `CHANGELOG.md`.

---

## 9. Normalization Rules (Strongly Recommended)

- **Columns (conv):** must include `lat`, `lon`, and measurement columns (`omf`, `oma`, etc.).  
- **Columns (rad):** per‑channel frames include `omf` (and optionally `omf_nbc`, `tb_obs`).  
- **Sentinels:** convert any `-9999`, `1e20`, etc. to `NaN` **in the adapter**.  
- **Timestamps:** return Python `datetime`.  
- **Indices:** use Python `int` for `kx`, channel index (`0`‑based) inside the adapter;
  external/legacy 1‑based channel numbering remains a presentation concern.  

---

## 10. Deprecation Policy Template

- **vX.Y (current):** shims exist; no breakage.  
- **vX.Y+1:** emit `DeprecationWarning` on shim usage (plotting/tests can silence).  
- **vX.Y+2:** remove shim and legacy dict walking from `plotting.py` (only `DiagnosticAPI`).  

Document this plan in `CHANGELOG.md` and the docs site.

---

## 11. Performance Notes

- Consider lazy loading per `(var, kx)` and per‑channel.  
- Avoid concatenating large frames in the adapter; return iterables where it helps.  
- If backend supports memory mapping, normalize on access, not upfront.

---

## 12. Troubleshooting / FAQ

**Q:** Tests with `FakeDiagConv/FakeDiagRad` fail with `file_name` error.  
**A:** The plotter only wraps the *real* `diagAccess`. Ensure the guard in `__init__`
checks `isinstance(diag, _DiagAccess)` *and* required attributes before wrapping.
Fakes remain unwrapped.

**Q:** Plotting still calls `get_data_frame()`.  
**A:** Keep the shim in `AccessAdapter` until you migrate those call sites to
`DiagnosticAPI` methods.

**Q:** How do I map 1‑based channel numbers from masks/labels?  
**A:** Keep UI as 1‑based, convert to 0‑based index in the adapter before `frame_channel`.

---

## 13. File Layout (Suggested)

```
readDiag/
  __init__.py
  surface.py          # stable contract (Protocol + Metadata)
  adapters.py         # AccessAdapter (+ future V2, V3...)
  open.py             # factory + adapter routing
  reader.py           # low-level backend (conv/rad parsing)
  plotting.py         # only consumes DiagnosticAPI (or legacy temporarily)
  utils*.py, style.py, impact/*.py, legacy.py, api.py (legacy funcs)
docs/
  stable_api_adapter_guide.md
```

---

## 14. CHANGELOG Template

```
## [Unreleased]
### Added
- Stable `DiagnosticAPI` (surface.py) and `AccessAdapter` (adapters.py).
- Factory `open_diagnostic()`.

### Changed
- plotting.py now prefers the stable surface; legacy still supported.

### Deprecated
- Legacy shims in AccessAdapter: get_data_frame(), get_variables(), ...

### Removed
- (none)

### Fixed
- Reduced coupling between plotting and reader internals.
```

---

## 15. Quick Reference (Cheat Sheet)

- **Open**: `from readDiag import open_diagnostic; d = open_diagnostic(path)`  
- **Kind**: `d.kind() -> "conv"|"rad"`  
- **Conv**: `d.variables() -> list[str]`, `d.kx_list(var) -> list[int]`, `d.frame_conv(var,kx) -> DataFrame`  
- **Rad**: `d.channels() -> list[int]`, `d.frame_channel(i) -> DataFrame`, `d.table("diagbuf_df") -> DataFrame`  
- **Plotter**: `diagPlotter(d_or_diagAccess)` — wraps real backend automatically, ignores fakes.

---

## Appendix A — Adapter V2 Skeleton

```python
# readDiag/adapters_v2.py (example skeleton)
from .surface import DiagnosticAPI, Metadata, Kind

class AccessAdapterV2(DiagnosticAPI):
    def __init__(self, backend) -> None:
        info = backend.get_file_info()
        self._meta = Metadata(
            file_name=info["file_name"],
            date=info["date"],
            kind=("rad" if info.get("data_type") == "rad" else "conv"),
            sensor=info.get("sensor"),
            platform=(str(info.get("platform")) if info.get("platform") is not None else None),
            n_channels=info.get("n_channels"),
            n_obs=info.get("n_obs"),
        )
        self._b = backend

    # Implement the same DiagnosticAPI methods here, normalizing names/types/sentinels...
```

## Appendix B — MkDocs Navigation (example)

Add to your `mkdocs.yml`:

```yaml
nav:
  - Home: index.md
  - Developer Guide:
      - Stable API & Adapter: docs/stable_api_adapter_guide.md
```