# 📦 readDiag

<p align="center">
  <img src="images/readDiag_logo.png" alt="readDiag Logo" width="240">
</p>

**readDiag** is a modern Python toolkit for **reading, analyzing, and visualizing GSI diagnostic files**.  
It provides a clean and extensible API for both **conventional** and **radiance** diagnostics, with built-in support for **impact metrics (TI, FI, FBI)** and **publication-ready plots**.

---

## ✨ Key Features

- 📊 **Easy plotting** — ready-to-use functions for counts, histograms, channel stats, swaths, and more.  
- 🔎 **Flexible analysis** — explore data directly as Pandas DataFrames.  
- ⚡ **Impact metrics** — compute TI, FI, and FBI from paired OMF/OMA files.  
- 🛠 **Modern API + legacy support** — use `diagAccess` / `diagPlotter` for new workflows, or `read_diag(...)` for compatibility.  
- 🌍 **Maps support** — optional Cartopy integration for geospatial visualization.  
- 🔬 **Developer-friendly** — modular design, type hints, NumPy-style docstrings, auto-generated API docs.

---

## 🚀 Get Started

- [Getting Started Guide](getting-started.md) — install instructions, quickstart scripts, and first plots.  
- [User Guide](user-guide/config.md) — learn how to configure and filter diagnostics, and explore usage flags.  
- [API Reference](api-reference/reader.md) — detailed documentation of all public classes and functions.  

---

## 📚 Example Workflows

- Quickstart with **conventional** diagnostics → [01_quickstart_conv.py](https://github.com/joaogerd/readDiag/tree/master/examples)  
- Quickstart with **radiance** diagnostics → [02_quickstart_rad.py](https://github.com/joaogerd/readDiag/tree/master/examples)  
- Basic **impact analysis (TI/FI/FBI)** → [05_impact_basic.py](https://github.com/joaogerd/readDiag/tree/master/examples)  
- End-to-end demo → [kitchen_sink.py](https://github.com/joaogerd/readDiag/tree/master/examples)  

---

## 👩‍💻 Contributing

We welcome contributions!  
- Open issues or feature requests on [GitHub](https://github.com/joaogerd/readDiag/issues).  
- Submit pull requests with new features, bug fixes, or improved documentation.  
- Check the [Developer Guide](developer-guide/stable-api-adapter.md) to learn about internal design.

---

## 📄 License

**readDiag** is released under the [LGPL v3](https://www.gnu.org/licenses/lgpl-3.0.html).  
You are free to use, modify, and distribute it under the terms of this license.

---

<p align="center">
  <em>Built for atmospheric data assimilation research — and beyond.</em>
</p>

