import importlib
import pytest
from readDiag.plotting.core import diagPlotter
import readDiag.plotting.core as core_mod

def test_plot_spatial_conv_cartopy_gate_raises(fake_conv_diag, monkeypatch):
    # Force the internal _HAS_CARTOPY flag to False to hit the guard
    monkeypatch.setattr(core_mod, "_HAS_CARTOPY", False, raising=False)
    p = diagPlotter(fake_conv_diag)
    with pytest.raises(RuntimeError):
        p.plot_spatial_conv("t", 120, param="omf")
