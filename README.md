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

### (Optional) Minimal Conda environment

```bash
conda create --name readDiag python=3.11 --no-default-packages
conda activate readDiag
````

### For Users (runtime)

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install .
```

### For Development

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install -e .[dev]
```

> The **dev** extras include tools for linting, testing and docs (if defined in `pyproject.toml`).

### Verify the install

```bash
python -c "import readDiag; print('✅ import ok')"
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
````

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

```
readDiag    : 2.1.0
Python      : 3.12.2
OS          : Linux 6.8.0-...
Executable  : /usr/bin/python3
NumPy       : 2.0.2
Pandas      : 2.2.3
Matplotlib  : 3.9.2
Cartopy     : not installed
GeoPandas   : 0.14.4
```

**Example output (conv):**

```
conv | date=2024-01-30 18:00:00 | file=data/diag_conv_01.2024013018
  var=t kx=[120, 220, ...]
  var=q kx=[...]
  ...
```

**Example output (rad):**

```
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

# style/lint (if configured)
ruff check .
black --check .
```

---

## 📚 Examples

See the `examples/` folder for quickstarts and scripts.
(We’re organizing examples by **basic/**, **advanced/**, and **cli/**.)

---

## 🧾 Legacy vs New (READ THIS)

* **LEGACY**: the `gsidiag/` package keeps the old `read_diag` class and methods for compatibility.
  Importing it triggers a **DeprecationWarning**.
* **NEW**: the `readDiag/` package provides the stable entrypoint:

  ```python
  import readDiag as rd
  api = rd.open_diagnostic("path/to/diag_file")  # -> DiagnosticAPI
  ```
* The low-level reader **is modern** (not legacy): `readDiag.io.reader.diagAccess`.
* For migration details and before/after mapping, see **[MIGRATION\_LEGACY.md](MIGRATION_LEGACY.md)**.

---

### ⚠️ Large Files (Git LFS)

Some diagnostic files used for testing or examples may exceed the default GitHub size limit.
To ensure these files are downloaded correctly, **install and configure Git LFS** before cloning the repository:

#### **1. Install Git LFS**

**Linux (Debian/Ubuntu):**

```bash
sudo apt-get install git-lfs
```

**macOS (Homebrew):**

```bash
brew install git-lfs
```

**Windows (Chocolatey):**

```bash
choco install git-lfs
```

### ⚠️ Large Files (Git LFS)

Some diagnostic files used for testing or examples may exceed the default GitHub size limit.
To ensure these files are downloaded correctly, **install and configure Git LFS** before cloning the repository:

#### **1. Install Git LFS**

**Linux (Debian/Ubuntu):**

```bash
sudo apt-get install git-lfs
```

**macOS (Homebrew):**

```bash
brew install git-lfs
```

**Windows (Chocolatey):**

```bash
choco install git-lfs
```

#### **2. Enable Git LFS**

After installation, enable LFS in your local Git environment:

```bash
git lfs install
```

#### **3. Clone the Repository**

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
git lfs pull
```

> **Tip**: If you already cloned the repo without LFS, just run:
>
> ```bash
> git lfs install
> git lfs pull
> ```


## 📄 License

Distributed under the [LGPL-3.0-or-later](https://opensource.org/licenses/LGPL-3.0) license.

---

## 👤 Author & Contact

João Gerd Zell de Mattos
Feel free to open issues or contribute!


