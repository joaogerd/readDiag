# setup.py
from pathlib import Path
from setuptools import setup, find_packages

README = Path(__file__).with_name("README.md")
long_description = README.read_text(encoding="utf-8") if README.exists() else ""

setup(
    name="readDiag",
    version="2.0.0rc1",
    description="Reader and Plotter for GSI Diagnostic Files",
    author="João Gerd Zell de Mattos",
    license="LGPL-3.0-or-later",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.9",
    install_requires=[
        # Runtime core
        "numpy>=2.0,<3.0",
        "pandas>=2.2,<3.0",
        "matplotlib>=3.8,<4.0",
        "scipy>=1.12,<2.0",
        # Runtime extras usados pela lib
        "statsmodels>=0.14,<0.15",
        "scikit-learn>=1.4,<2.0",
        "cartopy>=0.22,<0.26",
        "geopandas>=1.0,<1.3",
    ],
    extras_require={
        # Documentação
        "docs": [
            "mkdocs-material",
            "mkdocstrings[python]",
        ],
        # Ferramentas de desenvolvimento
        "dev": [
            "pytest>=8.2,<9.0",
            "pytest-cov",
            "black",
            "ruff",
            "mypy",
        ],
    },
)
