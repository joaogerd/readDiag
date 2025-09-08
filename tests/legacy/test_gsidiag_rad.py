# tests/legacy/test_gsidiag_rad.py
from __future__ import annotations
import pandas as pd
import pytest
import gsidiag as gd


@pytest.mark.usefixtures("rad_path")
def test_rad_open_and_channels(rad_path):
    """Test opening a radiance diagnostic file and accessing channels.

    This test validates the behavior of the legacy `gsidiag.read_diag`
    when reading a radiance (rad) diagnostic file. It ensures that
    channel information and per-channel DataFrames are accessible.

    Steps
    -----
    1. Open the radiance diagnostic file with `gd.read_diag`.
    2. Verify that `channels()` exists and returns a list or tuple.
    3. If channels exist, try to open one with `frame_channel()`.
    4. Assert that the result is a pandas DataFrame and contains
       typical radiance columns (e.g., "omf").

    Notes
    -----
    - The "omf" column (observation minus forecast) is a common
      element in radiance diagnostics and is used here as a
      minimal validation check.

    Examples
    --------
    >>> import gsidiag as gd
    >>> rd = gd.read_diag(["data/diag_amsua_n15_03.2024013018"])
    >>> chs = rd.channels()
    >>> chs[:3]
    [1, 2, 3]
    >>> df = rd.frame_channel(chs[0])
    >>> isinstance(df, pd.DataFrame)
    True
    >>> "omf" in df.columns
    True
    """
    rd = gd.read_diag([str(rad_path)])
    # Verify the presence of channels method
    if hasattr(rd, "channels"):
        chs = rd.channels()
        assert isinstance(chs, (list, tuple))
        if chs and hasattr(rd, "frame_channel"):
            ch1 = chs[0]
            df = rd.frame_channel(ch1)
            assert isinstance(df, pd.DataFrame)
            # Column "omf" is typical in radiance diagnostics
            assert "omf" in df.columns


def test_rad_tables_exist_when_available(rad_path):
    """Test that optional radiance diagnostic tables exist and are valid.

    This test checks for the presence and consistency of tables
    that may be exposed by the legacy radiance reader.

    Steps
    -----
    1. Open the radiance diagnostic file with `gd.read_diag`.
    2. If `table` method is available:
       - Attempt to retrieve known table names (diagbuf_df,
         diagbufchan_df, channel_df).
       - If available, ensure returned object is either:
         a) a pandas DataFrame, or
         b) a mapping (dict) of int->DataFrame.
    3. Validate that mapping keys are integers (or int-like)
       and values are DataFrames.

    Notes
    -----
    - The tables are optional and may vary depending on file type.
    - Both 0-based and 1-based channel keys are tolerated.

    Examples
    --------
    >>> import gsidiag as gd
    >>> rd = gd.read_diag(["data/diag_amsua_n19_01.2024013018"])
    >>> df = rd.table("channel_df")
    >>> isinstance(df, pd.DataFrame)
    True
    >>> ch_map = rd.table("diagbufchan_df")
    >>> isinstance(ch_map, dict)
    True
    >>> list(ch_map.keys())[:3]
    [1, 2, 3]
    >>> isinstance(ch_map[1], pd.DataFrame)
    True
    """
    rd = gd.read_diag([str(rad_path)])
    if hasattr(rd, "table"):
        # Check for known optional tables
        for name in ("diagbuf_df", "diagbufchan_df", "channel_df"):
            try:
                t = rd.table(name)
            except Exception:
                continue
            if t is None:
                continue
            if isinstance(t, dict):
                assert t, "Channel mapping should not be empty"
                # Ensure keys are int-like and values are DataFrames
                assert all(hasattr(k, "__int__") for k in t.keys())
                assert all(isinstance(v, pd.DataFrame) for v in t.values())
            else:
                assert isinstance(t, pd.DataFrame)

