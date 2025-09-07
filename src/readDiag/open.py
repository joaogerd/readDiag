from __future__ import annotations
from .io.reader import diagAccess
from .surface.access_adapter import AccessAdapter
from .surface.api import DiagnosticAPI


def open_diagnostic(path: str) -> DiagnosticAPI:
    """
    High-level entry point for opening a GSI diagnostic file.

    This function provides a stable, user-friendly interface to the
    `readDiag` package. It internally calls the low-level diagnostic reader
    (`diagAccess`) and wraps the result into an `AccessAdapter`, ensuring
    compliance with the stable `DiagnosticAPI` interface. This makes the
    function safe for downstream use in analysis and plotting tools.

    Parameters
    ----------
    path : str
        Path to the diagnostic file. Both conventional ("conv") and radiance ("rad")
        diagnostic files are supported. The path may be absolute or relative.

    Returns
    -------
    DiagnosticAPI
        An instance of `DiagnosticAPI` that exposes high-level, format-stable
        methods for querying metadata, variables, kx lists, channels, and
        observation tables.

    Notes
    -----
    - This is the recommended way to open diagnostic files in the modern API.
    - Legacy usage via `gsidiag.read_diag` is still supported but deprecated.
    - The returned object automatically distinguishes between conventional and
      radiance files.

    Examples
    --------
    Open a conventional diagnostic file:

    >>> from readDiag import open_diagnostic
    >>> conv = open_diagnostic("data/diag_conv_01.2024013018")
    >>> meta = conv.meta()
    >>> meta.kind
    'conv'
    >>> conv.variables()
    ['t', 'q', 'u', 'v']

    Open a radiance diagnostic file:

    >>> rad = open_diagnostic("data/diag_amsua_n19_01.2024013018")
    >>> meta = rad.meta()
    >>> meta.kind
    'rad'
    >>> rad.channels()[:3]
    [1, 2, 3]

    Inspect metadata:

    >>> meta.file_name
    'data/diag_conv_01.2024013018'
    >>> meta.date
    datetime.datetime(2024, 1, 30, 18, 0)
    """
    # Call the low-level diagnostic reader (NOT legacy).
    raw = diagAccess(path)

    # Wrap the raw backend in a stable high-level interface.
    return AccessAdapter(raw)

