# 📦 readDiag

[![CI](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml/badge.svg)](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://opensource.org/licenses/LGPL-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

**readDiag** is a modern Python package for reading, analyzing, and visualizing GSI (Gridpoint Statistical Interpolation) diagnostic files, including both conventional and radiance data.  
It is designed for robust analysis of observation impact and supports scalable batch processing for multi-cycle and multi-sensor experiments.

---

## 🚀 Installation

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install -e .[dev]
````

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

diag = diagAccess("data/diag_conv_01.2020010100")
plotter = diagPlotter(diag)
plotter.plot()
```

### Multi-Cycle Impact Analysis

```python
from readDiag import ImpactAnalyzer, ExperimentComparator

# Build pairs of (OmF, OmA) files for two sensors (e.g., n18 and n19)
exp1 = [("data/diag_amsua_n18_01.2023041600", "data/diag_amsua_n18_03.2023041600"), ...]
exp2 = [("data/diag_amsua_n19_01.2023041600", "data/diag_amsua_n19_03.2023041600"), ...]

comparator = ExperimentComparator(exp1, exp2)
comparator.compare()
df = comparator.comparison_df
print(df.head())
```

**More complete batch analysis and visualization scripts can be found in the `examples/` directory.**

---

## 📝 Examples

Several ready-to-use scripts are provided in [`examples/`](examples):

* `compare_sensor_impact_multi_cycle.py`: Batch impact analysis and robust statistical comparison between two sensors over multiple cycles.
* `example_impact.py`, `run_impact_batch.py`: End-to-end pipeline for impact calculation and plotting.
* `plotting_demo.ipynb`: Interactive notebook for custom plotting styles and diagnostics.

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
