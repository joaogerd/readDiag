import pytest
import readDiag.plotting as rplt

def test_radiance_wrapper_raises_on_conv(fake_conv_diag):
    with pytest.raises(ValueError):
        rplt.plot_hist_channel(fake_conv_diag, channel=1, param="omf", bins=5)
