from __future__ import annotations
import argparse
from .legacy_api import read_diag


def cli() -> int:
    """Legacy command-line interface for ``gsidiag``.

    This entrypoint wraps the legacy :func:`read_diag` API, allowing
    users to quickly inspect GSI diagnostic files (conventional or radiance).

    Parameters
    ----------
    None
        Command-line arguments are parsed internally via ``argparse``.

    Returns
    -------
    int
        Exit status code (``0`` for success).

    Notes
    -----
    - This CLI is **legacy** and relies on :func:`read_diag` from
      :mod:`gsidiag.legacy_api`.
    - The interface prints basic file metadata and optionally summarizes
      a given variable/kx combination (for conventional files).
    - Radiance files currently only print metadata via ``pfileinfo()``.

    Examples
    --------
    Run on a conventional diagnostics file:

    .. code-block:: bash

       $ python -m gsidiag data/diag_conv_01.2024013018 --var t --kx 120

    Example output (truncated):

    .. code-block:: text

       File: data/diag_conv_01.2024013018
       Date: 2024-01-30 18:00:00
       Kind: conv
       ...
       Summary for variable 't', kx=120:
       count     1532
       mean       -0.12
       std         0.45
       ...

    Run on a radiance diagnostics file:

    .. code-block:: bash

       $ python -m gsidiag data/diag_amsua_n15_03.2024013018

    Output:

    .. code-block:: text

       File: data/diag_amsua_n15_03.2024013018
       Date: 2024-01-30 18:00:00
       Kind: rad
       Sensor: amsua
       Platform: n15
       Channels: 15
       Observations: 145823
    """
    # Argument parser definition
    p = argparse.ArgumentParser(prog="gsidiag (legacy)")
    p.add_argument("file", nargs="+", help="diagnostic file(s) (conv or rad)")
    p.add_argument("--var", help="variable (conv only)")
    p.add_argument("--kx", type=int, help="kx (conv only)")
    args = p.parse_args()

    # Load diagnostic(s) using legacy API
    rd = read_diag(args.file)

    # Print metadata
    rd.pfileinfo()

    # If variable provided, print summary for var/kx
    if args.var:
        print(rd.summarize(varName=args.var, kx=args.kx))

    return 0


if __name__ == "__main__":
    # Standard CLI pattern: exit with return code from cli()
    raise SystemExit(cli())

