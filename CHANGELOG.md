# 📑 Changelog

All notable changes to this project will be documented in this file.  
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

---
## [2.0.0-rc.2] - 2025-09-04 (Pre-release)

### 🚨 Breaking changes
- Test suite reorganized into subpackages:
  - `tests/adapters/`, `tests/surface/`, `tests/legacy/`, `tests/utils/`.
- Removed `src/readDiag/requirements.txt` (dependencies are now managed exclusively via `pyproject.toml`).
- `AccessAdapter` and `LegacyCompatAdapter` APIs slightly adjusted for surface contract compliance.

### ✨ Improvements
- Added new test modules:
  - `tests/test_access_adapter_file_name.py`
  - Dedicated `conftest.py` files per test subpackage.
- Added documentation page `docs/user-guide/file_structure.md` describing GSI file structure.
- Figures in `docs/assets/figs/` updated for consistency with new plotting API.
- Example script `01_quickstart_conv.py` revised to reflect stable surface API.

### 🔧 Internal
- Updated `.gitignore` to exclude `site/` and generated artifacts.
- Cleaned up legacy adapters and utils for clarity.
- Adjusted `mkdocs.yml`, `pytest.ini`, and `pyproject.toml` to reflect new layout.


## [2.0.0-rc.1] - 2025-09-02 (Pre-release)

### Added
- Stable Surface API + Adapters (access/legacy).
- mkdocstrings API reference.

### Changed
- Packaging migrated to PEP 621; dependencies split.
- Logging defaults to console; file logging opt‑in via env.

### Removed
- setup.py and egg‑info from repo.


### 🚨 Breaking changes
- Introduced the new **stable API layer** with adapters:
  - `AccessAdapter` for modern, stable access.
  - `LegacyCompatAdapter` for legacy-like backends.
- Removed `diagAccess_legacy.py` (now replaced by adapters).
- Major refactor of `plotting.*` and `utils.*`:
  - Plotting methods now use decorators (`check_kind`) instead of manual `if kind != ...`.
  - Endianness helpers updated to be idempotent and NumPy 2.0+ compatible.
- Changes in test suite structure to cover adapters and plotting compatibility.

### ✨ Improvements
- Added `check_kind` decorator with support for `.kind()` callables.
- Enhanced **legacy compatibility**:
  - Fakes and test backends now supported via `LegacyCompatAdapter`.
  - Metadata inference (date, sensor, platform, n_channels, n_obs) more robust.
- Extended plotting API:
  - More consistent kwargs (`title`, `xlabel`, `ylabel`, `color`, `alpha`).
  - Publication-ready defaults.
- Improved logging and error handling across `utils.py`.

### 🧪 Testing
- Added dedicated test modules:
  - `test_access_adapter_conv.py` and `test_access_adapter_rad.py`
  - `test_legacy_adapter_conv.py` and `test_legacy_adapter_rad.py`
  - Compatibility tests for plotting (`test_plotting.py`, `test_plotting_aliases.py`)
- Expanded coverage of decorators, metadata inference, and DataFrame outputs.

---

## [1.x] - Previous Series

Earlier versions of `readDiag` provided basic diagnostic reading and plotting.  
This pre-release marks the beginning of the **2.x stable API**, with adapters and improved plotting.  

---

[2.0.0-rc.1]: https://github.com/joaogerd/readDiag/releases/tag/v2.0.0-rc.1

