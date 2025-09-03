# tests/test_data_integrity.py
"""
Test suite for verifying the integrity of diagnostic fixture files.

This module computes and compares the SHA256 hash of reference files
(e.g., GSI diagnostics for conventional and radiance data). It ensures
that test fixtures are not corrupted or accidentally modified.

Functions
---------
sha256(p : Path) -> str
    Compute the SHA256 hash of a given file.

Tests
-----
test_fixtures_hash()
    Verify that all required test fixture files exist and match their
    expected SHA256 hash.

Examples
--------
>>> from pathlib import Path
>>> sha256(Path("data/diag_conv_01.2024013018"))
'3d7f1c...9a2'  # Example SHA256 hash
"""

from pathlib import Path
import hashlib

# -------------------------------------------------------------------------
# Reference hashes for fixture files
# Replace "SHA256_AQUI" with the actual computed hash for each file.
# This guarantees data consistency across test environments.
# -------------------------------------------------------------------------
FILES = {
    "data/diag_conv_01.2024013018": "3c166a36aa48a23c4b783eb64510b51d2428a1cf46d2f038ee861e8c7455b67e",
    "data/diag_amsua_n15_01.2024013018": "3f0f6e186b64337cb0bb2a93d13ccc31a56f6df74e3b6fcfdbbdd20ca5af7683",
}


def sha256(p: Path) -> str:
    """Compute the SHA256 hash of a file.

    This function reads the file in chunks (1 MiB each) to handle large
    binary files efficiently without loading the entire file into memory.

    Parameters
    ----------
    p : Path
        Path to the file.

    Returns
    -------
    str
        The SHA256 hexadecimal digest of the file.

    Examples
    --------
    >>> from pathlib import Path
    >>> path = Path("data/diag_conv_01.2024013018")
    >>> hash_val = sha256(path)
    >>> isinstance(hash_val, str)
    True
    """
    h = hashlib.sha256()
    # Read file in 1 MiB chunks
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_fixtures_hash():
    """Check integrity of fixture files via SHA256.

    This test ensures that:
    1. All fixture files exist.
    2. Their SHA256 hashes match the expected reference values.

    Raises
    ------
    AssertionError
        If any fixture is missing or its hash does not match.

    Notes
    -----
    - Update the `FILES` dictionary with correct SHA256 values
      after preparing new test fixtures.
    """
    for rel, expected in FILES.items():
        p = Path(rel)
        # Assert that the fixture exists
        assert p.exists(), f"Missing fixture: {p}"
        # Assert that the hash matches the expected value
        assert sha256(p) == expected, f"Corrupted fixture: {p}"

