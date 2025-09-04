

"""
Legacy compatibility: read_diag wrapper + plotting aliases.

These tests ensure 100% drop-in behavior for legacy names:
- read_diag(...).diag1/.diag2
- pcount, vcount (hist), kxcount
- impact(var=...) for pair of conv files
"""
from __future__ import annotations
import pytest


import warnings
from pathlib import Path
import matplotlib.pyplot as plt

from readDiag.legacy import read_diag

@pytest.mark.usefixtures("conv01_path", "conv03_path", "conv_var_kx")
def test_legacy_single_file_conv(conv01_path: Path, conv_var_kx):
    warnings.simplefilter("default", DeprecationWarning)
    r = read_diag(str(conv01_path))

    # attributes
    assert r.diag1 is not None
    assert r.diag2 is None

    var, kx = conv_var_kx

    # data access shims
    vars_ = r.get_variables()
    assert var in vars_
    assert kx in r.get_kx_list(var)

    df = r.to_dataframe(var, kx)
    assert not df.empty

    # plots (should emit deprecations, but succeed)
    ax = r.plot(var, title="counts")
    assert isinstance(ax, plt.Axes)
    plt.close(ax.figure)

    ax = r.pcount(var, title="pcount")
    assert isinstance(ax, plt.Axes)
    plt.close(ax.figure)

    ax = r.vcount(var, kx=kx, column="omf", bins=20, title="vcount hist")
    assert isinstance(ax, plt.Axes)
    plt.close(ax.figure)

    ax = r.kxcount(var, title="kxcount")
    assert isinstance(ax, plt.Axes)
    plt.close(ax.figure)

@pytest.mark.usefixtures("conv01_path", "conv03_path")
def test_legacy_impact_pair(conv01_path: Path, conv03_path: Path):
    warnings.simplefilter("default", DeprecationWarning)
    r = read_diag([str(conv01_path), str(conv03_path)])
    assert r.diag2 is not None

    ia = r.impact(var="t")
    table = ia.compute_all_metrics()
    assert not table.empty

    ax = ia.plot_impact_bar(metric="TI", top_k=10)
    assert isinstance(ax, plt.Axes)
    plt.close(ax.figure)

