<p align="center">
  <img src="docs/images/readDiag_logo.png" alt="readDiag Logo" width="300">
</p>

[![CI](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml/badge.svg)](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://opensource.org/licenses/LGPL-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

# readDiag

**readDiag** is a modern Python toolkit for reading, analyzing, and visualizing **GSI (Gridpoint Statistical Interpolation)** diagnostics — both **conventional** and **radiance**.  
It focuses on a **stable high-level API** (the `DiagnosticAPI`) and clear separation between **legacy** interfaces and the **new** supported surface.

> 🔁 Migrating from older scripts? See **[MIGRATION_LEGACY.md](MIGRATION_LEGACY.md)**.  
> TL;DR: `gsidiag` = legacy (kept for compatibility, deprecated); `readDiag` = new.

---

## 🚀 Installation

### Install the latest release candidate directly from GitHub

The current release candidate is:

```text
v2.0.0-rc5
```

For a clean installation in a new Conda environment:

```bash
conda create -n readdiag python=3.12 -y
conda activate readdiag

python -m pip install --upgrade pip
python -m pip install --force-reinstall \
  "readDiag @ git+https://github.com/joaogerd/readDiag.git@v2.0.0-rc5"

readDiag --version
```

Expected output:

```text
readDiag 2.0.0rc5
```

### Install on systems without Git LFS preconfigured, such as HPC/JACI

The repository uses Git LFS for large diagnostic test files. On systems where
`git-lfs` is not available by default, installation from Git may fail during
checkout with an error similar to:

```text
git-lfs filter-process: git-lfs: command not found
```

In that case, install `git-lfs` in the Conda environment and skip downloading
large LFS files during package installation:

```bash
conda create -n readdiag python=3.12 -y
conda activate readdiag

conda install -c conda-forge git-lfs -y
git lfs install --skip-smudge

python -m pip install --upgrade pip

GIT_LFS_SKIP_SMUDGE=1 python -m pip install --force-reinstall \
  "readDiag @ git+https://github.com/joaogerd/readDiag.git@v2.0.0-rc5"

readDiag --version
```

Expected output:

```text
readDiag 2.0.0rc5
```

Quick import test:

```bash
python - <<'PY'
from readDiag import ImpactAnalyzer
from readDiag.analysis.impact_plots import plot_impact_ranked_bar
print("readDiag import OK")
print("ImpactAnalyzer OK:", ImpactAnalyzer)
PY
```

### Install from a local clone

If you need the full repository, including LFS-managed test/example files:

```bash
git lfs install
git clone https://github.com/joaogerd/readDiag
cd readDiag
git lfs pull
python -m pip install .
```

### For development

```bash
git lfs install
git clone https://github.com/joaogerd/readDiag
cd readDiag
git lfs pull
python -m pip install -e .[dev]
```

The **dev** extras include tools for linting, testing and documentation.

### Verify the install

```bash
python -c "import readDiag; print('✅ import ok')"
readDiag --version
```

---

## ⚡ Quick Start (New API)

Open any diagnostic file and work with a **stable** surface (`DiagnosticAPI`).

```python
import readDiag as rd

api = rd.open_diagnostic("data/diag_conv_01.2024013018")  # -> DiagnosticAPI
print(api.kind())  # "conv" or "rad"

if api.kind() == "conv":
    for v in api.variables():
        for kx in api.kx_list(v):
            df = api.frame_conv(v, kx)      # pandas.DataFrame
            # ... analysis/plots ...
else:
    for ch in api.channels():
        df = api.frame_channel(ch)          # pandas.DataFrame for channel `ch`
```

### Observation-impact analysis

```python
from readDiag import ImpactAnalyzer

analyzer = ImpactAnalyzer.from_pair(
    "dataout/2025100100/diag_conv_01.2025100100",
    "dataout/2025100100/diag_conv_03.2025100100",
)

metrics = analyzer.compute_all_metrics()
print(metrics.head())
```

Nature-style / academic-modern impact plots:

```python
from readDiag.analysis.impact_plots import (
    plot_impact_ranked_bar,
    save_impact_figure,
)

ax = plot_impact_ranked_bar(metrics, metric="FI", top_k=15)
save_impact_figure(ax, "impact_fi_top15.pdf", validate=False)
save_impact_figure(ax, "impact_fi_top15.png", validate=False)
```

### Plotting helpers (wrappers)

```python
from readDiag.plotting.wrappers import plot_kx_count, plot_omf_map, plot_oma_map

api = rd.open_diagnostic("data/diag_conv_01.2024013018")
plot_kx_count(api)
plot_omf_map(api, var="t", kx=120)
plot_oma_map(api, var="t", kx=120)
```

---

## 📟 CLI Usage

Once installed, **readDiag** provides a lightweight command-line interface (CLI) for quick environment checks and debugging.

### Run via Python module

```bash
# Show package version
python -m readDiag --version

# Show full environment (Python, OS, NumPy, Pandas, Matplotlib, Cartopy)
python -m readDiag --show-versions

# JSON output (machine-readable)
python -m readDiag --show-versions --json

# Include extra packages in the report (scipy, xarray, netCDF4, shapely, pyproj, cfgrib, eccodes)
python -m readDiag --show-versions --extra
```

### Run via console script (if installed with entrypoint)

```bash
# Show package version
readDiag --version

# Show environment versions (table)
readDiag --show-versions

# JSON output
readDiag --show-versions --json

# Include extra packages
readDiag --show-versions --extra
```

### Quick file inspection

```bash
# Inspect a single diagnostic file (conv or rad)
python -m readDiag data/diag_conv_01.2024013018

# or
readDiag data/diag_conv_01.2024013018
```

**Example output (show-versions):**

```text
readDiag    : 2.0.0rc5
Python      : 3.12.13
OS          : Linux 6.8.0-...
Executable  : /path/to/python
NumPy       : 2.x
Pandas      : 2.x
Matplotlib  : 3.x
Cartopy     : installed/not installed
GeoPandas   : installed/not installed
```

**Example output (conv):**

```text
conv | date=2024-01-30 18:00:00 | file=data/diag_conv_01.2024013018
  var=t kx=[120, 220, ...]
  var=q kx=[...]
  ...
```

**Example output (rad):**

```text
rad | date=2024-01-30 18:00:00 | file=data/diag_amsua_n19_01.2024013018
  channels=[1, 2, 3, ...]
```

### Legacy CLI (compat only)

```bash
# legacy interface (deprecated, still available)
gsidiag data/diag_conv_01.2024013018 --var t --kx 120
```

---

## 🧪 Tests & Dev

```bash
# run tests
pytest -q

# style/lint, if configured
ruff check .
black --check .
```

---

## 📚 Examples

See the `examples/` folder for quickstarts and scripts.
We are organizing examples by **basic/**, **advanced/**, and **cli/**.

---

## 🧾 Legacy vs New

* **LEGACY**: the `gsidiag/` package keeps the old `read_diag` class and methods for compatibility.
  Importing it triggers a **DeprecationWarning**.
* **NEW**: the `readDiag/` package provides the stable entrypoint:

  ```python
  import readDiag as rd
  api = rd.open_diagnostic("path/to/diag_file")  # -> DiagnosticAPI
  ```
* The low-level reader **is modern** (not legacy): `readDiag.io.reader.diagAccess`.
* For migration details and before/after mapping, see **[MIGRATION_LEGACY.md](MIGRATION_LEGACY.md)**.

---

## ⚠️ Large Files (Git LFS)

Some diagnostic files used for testing or examples may exceed the default
GitHub size limit and are managed with Git LFS.

Install Git LFS before cloning the full repository:

```bash
git lfs install
git clone https://github.com/joaogerd/readDiag
cd readDiag
git lfs pull
```

If you only want to install the package and do not need large test/example
files, use:

```bash
GIT_LFS_SKIP_SMUDGE=1 python -m pip install --force-reinstall \
  "readDiag @ git+https://github.com/joaogerd/readDiag.git@v2.0.0-rc5"
```

---

## 📄 License

Distributed under the [LGPL-3.0-or-later](https://opensource.org/licenses/LGPL-3.0) license.

---

## 👤 Author & Contact

João Gerd Zell de Mattos  
Feel free to open issues or contribute!
