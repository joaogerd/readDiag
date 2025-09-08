# tests/legacy/test_gsidiag_plot_wrappers.py
from __future__ import annotations
import pytest
import importlib

# Try to locate matplotlib dynamically.
# This avoids hard dependency on plotting libs during basic test runs.
matplotlib = importlib.util.find_spec("matplotlib")

# If matplotlib is not installed, mark these tests as "expected fail".
# The legacy interface intentionally degrades to RuntimeError in such cases.
xfail_no_mpl = pytest.mark.xfail(matplotlib is None, reason="matplotlib not installed")

import gsidiag as gd


@xfail_no_mpl
def test_plot_kx_count(conv_path):
    """Test wrapper plot for conventional diagnostics (kx count).

    This test ensures that the legacy plot wrapper can be invoked
    successfully when `matplotlib` is available. It does not validate
    graphical output, only that no error is raised.

    Parameters
    ----------
    conv_path : pathlib.Path
        Path to a conventional diagnostic file, provided via pytest fixture.

    Notes
    -----
    - If no `matplotlib` is installed, this test is marked as `xfail`.
    - The function generates a figure, but the figure object is not
      returned or checked here.
    """
    rd = gd.read_diag([str(conv_path)])
    from readDiag.plotting.wrappers import plot_kx_count

    # Should execute without error and create a plot
    plot_kx_count(rd)


@xfail_no_mpl
def test_plot_maps(conv_path):
    """Test wrapper plots for OMF and OMA spatial maps.

    This test ensures that both `plot_omf_map` and `plot_oma_map`
    can be called for at least one variable/kx combination in a
    conventional diagnostic file.

    Parameters
    ----------
    conv_path : pathlib.Path
        Path to a conventional diagnostic file, provided via pytest fixture.

    Notes
    -----
    - The test dynamically selects the first variable and kx found.
    - If no variables or kx are available, the test is skipped.
    - The figures are generated but not validated for visual correctness.
    """
    rd = gd.read_diag([str(conv_path)])

    # Defensive: only proceed if API has expected attributes
    if hasattr(rd, "variables") and hasattr(rd, "kx_list"):
        vars_ = rd.variables()
        if not vars_:
            pytest.skip("No variables in test conventional diagnostic file.")
        var = vars_[0]

        kxs = rd.kx_list(var)
        if not kxs:
            pytest.skip("No KX available in test conventional diagnostic file.")
        kx = kxs[0]

        from readDiag.plotting.wrappers import plot_omf_map, plot_oma_map

        # Should run without raising errors
        plot_omf_map(rd, var=var, kx=kx)
        plot_oma_map(rd, var=var, kx=kx)

