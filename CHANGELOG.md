# 📑 Changelog

All notable changes to this project will be documented in this file.  
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),  
and this project adheres to [Semantic Versioning](https://semver.org/).

---
## [2.0.0-rc.3] - 2025-09-10 (Pre-release)

### ✨ Features
- **CLI**: Added `--version` and `--show-versions` options (with `--json`/`--extra`); preserved quick file inspection mode; updated README usage examples. (d0c7537)
- **Surface/Adapters**: Consolidated exports and introduced **modern + compatibility adapters** to simplify migration and usage of the new stable API layer. (dedb9ad)

### 🐛 Fixes
- **Legacy compatibility**: multiple shims added (`gsidiag.utils`, `gsidiag.plotting`, `readDiag.adapters.access`, `readDiag.reader`, import bridges), fixed relative imports and exports (`diagAccess`, `__version__`, `show_versions`), and restored aliases such as `top_k`/`n` for impact metrics. (d12480f, bb7c7f6, ea0e271, af64b72, 9236a45, e5e2420, 92044fa, c0594bc, 7106b6d, f3b8b2d, 4d009ca, 0596c99)
- **Plotting/Core**: adjusted imports to `_utils`, added fallback for `get_cycle`, centralized utils, and ensured wrappers now properly delegate to the correct core modules. (880a6c4, af90869, f4ff36d, 5585495, 3db086c, 3877a78)
- **Generic I/O**: consolidated `api.read_any` to return **dict-of-dict** outputs and fixed shape mismatches for `rad/conv` datasets. (92044fa, c0594bc, 4d009ca, 0596c99)

### 🔧 Refactors
- **Boundary cleanup (legacy)**: removed outdated scripts and reorganized the entire test suite, migrating relevant components into `gsidiag/`. (7ec31d8, 9930481)
- **Unified plotting wrappers**: wrappers now delegate directly to the **core** and **Surface API**; improved naming consistency and unified method signatures. (51abba4, 6ce6f8d)
- **Architecture**: clear separation between **LEGACY** under `gsidiag` (with a `read_diag` class and deprecation warnings) and **NEW** under `readDiag` (`open_diagnostic` + `DiagnosticAPI`); continued the split of **io/plot/analysis** layers. (3ce38b1, 24a051a)
- **I/O improvements**: added docstrings, input validations, and consistent APIs for `conv/rad/reader`. (3df5470)
- **Examples**: removed outdated examples and introduced a new structured suite under `examples/basic/plots`. (e2f5a7e)

### 📝 Documentation
- Added **NumPy-style docstrings** for the `Metadata` dataclass with practical usage examples. (6e75c45)
- Overhauled **plotting documentation** with updated examples, safer helper functions, and clarified usage of legacy wrappers. (15c2162)

### 🗑️ Removed / Cleanup
- Removed unnecessary files and obsolete scripts tied to the legacy workflow; updated Makefile and related references accordingly. (3d58d7d, 7ec31d8)

> **Migration Note**  
> Projects relying on legacy modules should now reference `gsidiag.*` temporarily.  
> Migration to the **Surface API** under `readDiag.*` is recommended moving forward.

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

