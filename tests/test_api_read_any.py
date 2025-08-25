"""
API read_any: auto-detect conventional vs radiance.
"""
from __future__ import annotations
from pathlib import Path
import pytest
from readDiag.api import read_any

@pytest.mark.usefixtures("conv01_path", "rad01_path")
def test_read_any_conv_and_rad(conv01_path: Path, rad01_path: Path):
    conv = read_any(str(conv01_path))
    assert isinstance(conv, dict) and conv, "Empty dict for conv read_any"
    # Conventional structure {var -> {kx -> DataFrame}}
    assert any(isinstance(v, dict) for v in conv.values())

    rad = read_any(str(rad01_path))
    # Radiance structure has top keys (sensor/kx/dataframes) per current reader
    assert "dataframes" in rad and isinstance(rad["dataframes"], dict)

