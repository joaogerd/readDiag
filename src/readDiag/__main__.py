from __future__ import annotations
import argparse
from .open import open_diagnostic


def cli() -> int:
    """
    Command-line interface for the ``readDiag`` package.

    This function parses command-line arguments, opens a GSI diagnostic file
    (conventional or radiance), and prints basic metadata and content overview.

    Workflow
    --------
    1. Parse the filename from CLI arguments.
    2. Open the diagnostic file using :func:`open_diagnostic`.
    3. Retrieve metadata via :meth:`DiagnosticAPI.meta`.
    4. Display metadata and file-specific information:
       - For conventional diagnostics: list variables and their KX codes.
       - For radiance diagnostics: list available channels.

    Returns
    -------
    int
        Exit code, ``0`` on success. Returned via ``SystemExit``.

    Notes
    -----
    - This CLI is intentionally minimal. For more advanced analysis
      (statistics, plotting), use the Python API directly.
    - The metadata returned includes kind, date, file name, and optionally
      sensor/platform information for radiance files.

    Examples
    --------
    Run from the command line with a conventional diagnostic file:

    >>> # In shell
    >>> readDiag data/diag_conv_01.2024013018
    conv | date=2024-01-30 18:00:00 | file=data/diag_conv_01.2024013018
      var=t kx=[120, 130, 131]
      var=q kx=[120, 130]

    Run with a radiance diagnostic file:

    >>> readDiag data/diag_amsua_n15_03.2024013018
    rad | date=2024-01-30 18:00:00 | file=data/diag_amsua_n15_03.2024013018
      channels=[1, 2, 3, 4, 5, 6, 7]

    """
    # Create argument parser with program name "readDiag"
    p = argparse.ArgumentParser(prog="readDiag")

    # Positional argument: diagnostic file (conventional or radiance)
    p.add_argument("file", help="diagnostic file (conv or rad)")
    args = p.parse_args()

    # Open diagnostic file through high-level API
    api = open_diagnostic(args.file)

    # Extract metadata (kind, date, file name, etc.)
    m = api.meta()
    print(f"{m.kind} | date={m.date} | file={m.file_name}")

    # Depending on the kind, print variables (conv) or channels (rad)
    if m.kind == "conv":
        for v in api.variables():
            kx = api.kx_list(v)
            print(f"  var={v} kx={kx}")
    else:
        print(f"  channels={api.channels()}")

    # Return success exit code
    return 0


if __name__ == "__main__":
    raise SystemExit(cli())

