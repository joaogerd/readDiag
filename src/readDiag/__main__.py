"""
CLI entrypoint for the `readDiag` package.

This module allows quick inspection of GSI diagnostic files directly
from the command line:

>>> python -m readDiag <diag_file>

It provides a minimal summary of the file metadata (file name, date,
and kind) and a quick listing of variables (for conventional files)
or channels (for radiance files).
"""

import sys
import argparse
from . import read_diag


def main(argv=None):
    """
    Command-line interface for `readDiag`.

    Parameters
    ----------
    argv : list of str, optional
        Command-line arguments. If None (default), `sys.argv[1:]` is used.

    Returns
    -------
    int
        Exit status code (0 = success).

    Notes
    -----
    - When invoked without arguments, prints the help message.
    - If a diagnostic file is provided, prints metadata and either the
      variables (for conventional files) or the channels (for radiance files).
    - The output is truncated at 200 characters to avoid overly long listings.

    Examples
    --------
    From the shell:

    >>> # Show metadata for a conventional file
    >>> # $ python -m readDiag data/diag_conv_01.2024013018
    File: diag_conv_01.2024013018
    Date: 2024-01-30 18:00:00
    Kind: conv
    Variables: t, q, ps, ...

    >>> # Show metadata for a radiance file
    >>> # $ python -m readDiag data/diag_amsua_n15_01.2024013018
    File: diag_amsua_n15_01.2024013018
    Date: 2024-01-30 18:00:00
    Kind: rad
    Channels: 1, 2, 3, ...
    """
    # Use system arguments if none provided (makes testing easier)
    argv = sys.argv[1:] if argv is None else argv

    # Create parser with program name for nicer help message
    parser = argparse.ArgumentParser(prog="python -m readDiag", add_help=True)

    # Positional argument for the diagnostic file
    parser.add_argument(
        "diag_file",
        nargs="?",
        help="Path to GSI diagnostic file (conventional or radiance).",
    )

    # Parse arguments
    args = parser.parse_args(argv)

    # If no file is given, print help and exit cleanly
    if not args.diag_file:
        parser.print_help()
        return 0

    # Read file using public API
    d = read_diag(args.diag_file)
    m = d.meta()

    # Print basic metadata
    print(f"File: {getattr(m, 'file_name', '?')}")
    print(f"Date: {getattr(m, 'date', '?')}")
    print(f"Kind: {getattr(m, 'kind', '?')}")

    # Try to show either variables (conv) or channels (rad)
    try:
        if getattr(m, "kind", None) == "conv":
            print("Variables:", ", ".join(d.variables())[:200])
        else:
            print("Channels:", ", ".join(map(str, d.channels()))[:200])
    except Exception:
        # Fail silently if adapter lacks expected methods
        pass

    return 0


if __name__ == "__main__":
    # Proper exit code propagation
    raise SystemExit(main())

