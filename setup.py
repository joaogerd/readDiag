# =============================
# setup.py (opcional)
# =============================
from setuptools import setup, find_packages

setup(
    name="readDiag",
    version="2.0.0",
    description="Reader and Plotter for GSI Diagnostic Files",
    author="João Gerd Zell de Mattos",
    license="LGPL-3.0-or-later",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "numpy",
        "pandas",
        "matplotlib",
    ],
    python_requires=">=3.9",
)
