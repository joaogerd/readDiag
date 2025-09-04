<p align="center">
  <img src="docs/images/readDiag_logo.png" alt="readDiag Logo" width="300">
</p>

[![CI](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml/badge.svg)](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://opensource.org/licenses/LGPL-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**readDiag** is a modern Python package for reading, analyzing, and visualizing GSI (Gridpoint Statistical Interpolation) diagnostic files, including both conventional and radiance data.  
It is designed for robust analysis of observation impact and supports scalable batch processing for multi-cycle and multi-sensor experiments.

---

## 🚀 Installation

### Minimal Conda environment (optional, but recommended)

```bash
conda create --name readDiag python=3.11 --no-default-packages
conda activate readDiag
````

### For Users (runtime only)

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install -r requirements.txt
````

This will install only the dependencies needed to run **readDiag** (data reading, analysis, and plotting).

### For Development

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install -e .[dev]
```
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

---
### Verify package import and version

```bash
python -c "import readDiag; print('✅ import ok, version =', readDiag.__version__)"
````
### Or via CLI

```bash
python -m readDiag --show-versions
``` 
This installs additional dependencies for testing, linting, and documentation.

---

## 📟 CLI Usage

Once installed, **readDiag** provides a lightweight command-line interface (CLI) for quick environment checks and debugging.

### Run via Python module

```bash
# Show package version
python -m readDiag --version

# Show full environment (Python, OS, NumPy, Pandas, Matplotlib, Cartopy)
python -m readDiag --show-versions
```

### Run via console script (if installed with entrypoint)

If `setup.py` / `pyproject.toml` defines a `console_scripts` entrypoint, you can also call it directly:

```bash
# Show package version
readDiag --version

# Show environment versions
readDiag --show-versions
```

### Example output

```text
readDiag    : 2.1.0
Python      : 3.12.2
OS          : Linux 6.8.0-...
NumPy       : 2.0.2
Pandas      : 2.2.3
Matplotlib  : 3.9.2
Cartopy     : not installed
```

---

## ⚡ Features

* Fast and flexible reading of GSI diagnostics (conventional & radiance).
* Detailed **observation impact analysis**: Total Impact (TI), Fractional Impact (FI), Fractional Background Impact (FBI).
* Robust statistical comparison of experiments (mean, median, CI, significance tests, effect size, trends, and more).
* Highly customizable plotting and publication-ready visualizations.
* Example scripts for batch impact analysis, comparison between sensors, and visualization.

---

## 📚 Usage Example

### Basic Access & Plot

```python
from readDiag import diagAccess, diagPlotter

diag = diagAccess("data/diag_conv_01.2024013018")
plotter = diagPlotter(diag)
plotter.plot()
```

### Multi-Cycle Impact Analysis

```python
from readDiag import ImpactAnalyzer, ExperimentComparator

# Build pairs of (OmF, OmA) files for two sensors (e.g., n18 and n19)
exp1 = [("data/diag_amsua_n18_01.2024013018", "data/diag_amsua_n18_03.2024013018"), ...]
exp2 = [("data/diag_amsua_n18_01.2024013018", "data/diag_amsua_n19_03.2024013018"), ...]

comparator = ExperimentComparator(exp1, exp2)
comparator.compare()
df = comparator.comparison_df
print(df.head())
```

**More complete batch analysis and visualization scripts can be found in the `examples/` directory.**

---

## 📝 Examples

Several ready-to-use scripts are provided in [`examples/`](examples):

* `01_quickstart_conv.py`, `02_quickstart_rad.py`: Basic usage for conventional and radiance diagnostics.
* `05_impact_basic.py`, `06_impact_series.py`: Impact analysis and multi-cycle comparisons.
* `07_legacy_compat.py`: Using the **LegacyCompatAdapter** with older code.
* `08_plot_amsua_swath.py`: AMSU-A swath visualization.
* `09_show_conv_dataframe.py`: Inspecting DataFrames directly.

---

## 🧪 Tests

Run the full test suite:

```bash
make test
```

Run benchmarks:

```bash
make benchmark
```

Check code style with linter:

```bash
make lint
```

---

## 📄 License

Distributed under the [LGPL-3.0-or-later](https://opensource.org/licenses/LGPL-3.0) license.

---

## 👤 Author & Contact

João Gerd Zell de Mattos
Feel free to open issues or contribute!

---
