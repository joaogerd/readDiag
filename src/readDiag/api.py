from __future__ import annotations

def read_any(path: str) -> dict:
    """
    Lightweight back-compatibility reader for diagnostic files (mock/test use).

    This function provides a **minimal heuristic interface** to mimic the
    output structure of legacy diagnostic readers. It is intended only
    for tests or back-compatibility, not for production use.

    The behavior depends on the file name:
    
    - If the path contains `"conv"`, it assumes a **conventional (CONV)**
      diagnostic file and returns a dictionary mapping variables
      to nested dictionaries of KX indices.
      Structure: ``{var -> {kx -> DF}, "meta": {...}}``
    
    - If the path contains `"diag_"` or `"amsua"`, it assumes a **radiance (RAD)**
      diagnostic file and returns a dictionary with a `"dataframes"` key
      containing sub-dataframes, following the expected radiance convention.
      Structure: ``{"dataframes": {...}, "meta": {...}}``
    
    - Otherwise, it returns a generic "unknown" structure for unsupported files.

    Parameters
    ----------
    path : str
        File path (or name) to inspect. The function uses simple substring
        heuristics (`"conv"`, `"diag_"`, `"amsua"`) to decide the type.

    Returns
    -------
    dict
        A non-empty dictionary with at least one nested dictionary value.
        Keys depend on the detected type:
        
        * Conventional: ``{"t": {120: {}}, "q": {130: {}}, "meta": {...}}``
        * Radiance: ``{"dataframes": {"diagbufchan_df": {}}, "meta": {...}}``
        * Unknown: ``{"data": {1: {}}, "meta": {...}}``

    Notes
    -----
    - This function is **not** a real parser; it is a stub for tests and
      back-compatibility.
    - The nested dictionaries are left empty (`{}`) for tests to fill.

    Examples
    --------
    Detect a conventional diagnostic file:

    >>> read_any("diag_conv_01.2024013018")
    {'t': {120: {}}, 'q': {130: {}},
     'meta': {'path': 'diag_conv_01.2024013018', 'kind': 'conv'}}

    Detect a radiance diagnostic file:

    >>> read_any("diag_amsua_n15_01.2024013018")
    {'dataframes': {'diagbufchan_df': {}},
     'meta': {'path': 'diag_amsua_n15_01.2024013018', 'kind': 'rad'}}

    Unknown file type:

    >>> read_any("random_file.txt")
    {'data': {1: {}}, 'meta': {'path': 'random_file.txt', 'kind': 'unknown'}}
    """
    ps = str(path).lower()

    # Conventional case: return mock variables and KX indices
    if "conv" in ps:
        return {
            "t": {120: {}},  # variable "t" with KX=120
            "q": {130: {}},  # variable "q" with KX=130
            "meta": {"path": str(path), "kind": "conv"},
        }

    # Radiance case: return placeholder for channel dataframe
    if "diag_" in ps or "amsua" in ps:
        return {
            "dataframes": {"diagbufchan_df": {}},
            "meta": {"path": str(path), "kind": "rad"},
        }

    # Fallback: unknown type
    return {
        "data": {1: {}},  # at least one nested dict
        "meta": {"path": str(path), "kind": "unknown"},
    }

