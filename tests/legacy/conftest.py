from __future__ import annotations
import os
from pathlib import Path
import pytest

# Typical candidate file names used in the repository/logs.
# Adjust this list if your dataset files have different names.
CONV_CANDIDATES = [
    "diag_conv_01.2024013018",
    "diag_conv_01.2024013000",
]
RAD_CANDIDATES = [
    "diag_amsua_n19_01.2024013018",
    "diag_amsua_n19_03.2024013018",
    "diag_amsua_n15_03.2024013018",
]


def _candidate_paths(candidates: list[str]) -> list[Path]:
    """
    Search for candidate diagnostic files across known roots.

    The function looks for files under:
    1. The local default `./data` directory (relative to repo root).
    2. A directory defined in the `READDIAG_DATA` environment variable.

    Parameters
    ----------
    candidates : list of str
        List of possible file names to search for (e.g. CONV or RAD candidates).

    Returns
    -------
    list of pathlib.Path
        List of valid existing paths matching the candidates.

    Notes
    -----
    - This is a utility function to be used by pytest fixtures.
    - It is not meant to raise errors: missing files are silently ignored.

    Examples
    --------
    >>> files = _candidate_paths(["diag_conv_01.2024013018"])
    >>> isinstance(files, list)
    True
    >>> all(isinstance(f, Path) for f in files)
    True
    """
    roots = []
    # 1) Local default `./data` directory inside repository root
    roots.append(Path(__file__).resolve().parents[2] / "data")
    # 2) Environment variable allows datasets outside repo
    env = os.environ.get("READDIAG_DATA")
    if env:
        roots.append(Path(env))

    out = []
    for root in roots:
        for name in candidates:
            p = root / name
            if p.exists():
                out.append(p)
    return out


@pytest.fixture(scope="session")
def conv_path() -> Path:
    """
    Provide path to a conventional (CONV) diagnostic file.

    The fixture checks local candidates and the directory defined
    by `READDIAG_DATA`. If no file is found, the test is skipped.

    Returns
    -------
    pathlib.Path
        Path to the first available CONV diagnostic file.

    Raises
    ------
    pytest.skip
        If no conventional file is found.

    Examples
    --------
    Use this fixture in tests:

    >>> def test_conv_file(conv_path):
    ...     assert conv_path.exists()
    """
    paths = _candidate_paths(CONV_CANDIDATES)
    if not paths:
        pytest.skip(
            "CONV file not found (set READDIAG_DATA or add files under ./data)."
        )
    return paths[0]


@pytest.fixture(scope="session")
def rad_path() -> Path:
    """
    Provide path to a radiance (RAD) diagnostic file.

    The fixture checks local candidates and the directory defined
    by `READDIAG_DATA`. If no file is found, the test is skipped.

    Returns
    -------
    pathlib.Path
        Path to the first available RAD diagnostic file.

    Raises
    ------
    pytest.skip
        If no radiance file is found.

    Examples
    --------
    Use this fixture in tests:

    >>> def test_rad_file(rad_path):
    ...     assert rad_path.exists()
    """
    paths = _candidate_paths(RAD_CANDIDATES)
    if not paths:
        pytest.skip(
            "RAD file not found (set READDIAG_DATA or add files under ./data)."
        )
    return paths[0]

