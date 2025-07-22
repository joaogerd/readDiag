# 📦 readDiag

[![CI](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml/badge.svg)](https://github.com/joaogerd/readDiag/actions/workflows/ci.yml)
[![License: LGPL v3](https://img.shields.io/badge/License-LGPL%20v3-blue.svg)](https://opensource.org/licenses/LGPL-3.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)


**readDiag** é um pacote Python para leitura, análise e visualização de arquivos diagnósticos do GSI (Gridpoint Statistical Interpolation), tanto de dados convencionais quanto radiância.

## 🚀 Instalação

```bash
git clone https://github.com/joaogerd/readDiag
cd readDiag
pip install -e .[dev]
```

## 📚 Exemplo de uso

```python
from readDiag import diagAccess, diagPlotter

diag = diagAccess("data/diag_conv_01.2020010100")
plotter = diagPlotter(diag)
plotter.plot()
```

## 🧪 Testes

Execute os testes com:

```bash
make test
```

Rode os benchmarks:

```bash
make benchmark
```

Verifique estilo com lint:

```bash
make lint
```

## 📄 Licença

Distribuído sob a licença [LGPL-3.0-or-later](https://opensource.org/licenses/LGPL-3.0).
