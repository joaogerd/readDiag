"""
Canonical naming and alias resolution for readDiag.

This module defines *canonical* column names for **conventional** and
**radiance** diagnostic files and provides helpers to translate legacy field
names to the canonical schema. It also offers guardrails to gradually migrate
downstream code: optional deprecation warnings for legacy names and an opt-in
"strict mode" that rejects unknown/non-canonical columns.

Design goals
------------
- Minimal surface area (a couple of dicts + small helpers)
- Zero runtime dependencies
- Backward compatibility (aliases keep older scripts running)
- Easy extension (drop new aliases or canonical names into the tables)

Quick start
-----------
Basic resolution for a single name:

>>> resolve_name("kx", domain="conv")
'obs_type_code'

Resolve a list of names:

>>> resolve_names(["lat", "lon", "omf_nbc"], domain="rad")
['lat', 'lon', 'omf_nobc']

Enable strict validation and deprecation warnings:

>>> with set_canonical_policy(strict=True, deprecations=True):
...     resolve_name("kx", "conv")       # ok (warns; maps to 'obs_type_code')
...     resolve_name("unknown", "conv")  # doctest: +IGNORE_EXCEPTION_DETAIL
Traceback (most recent call last):
    ...
KeyError: "Column 'unknown'→'unknown' is not recognized canonical name."

Notes
-----
- Columns starting with ``pred`` or ``extra`` are *always* accepted even in
  strict mode, to allow user-augmented features (predictions, extra metadata).
- This module intentionally does **not** import pandas or any plotting libs.

"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterable, List, Mapping, Sequence
import warnings as _w

# ---------------------------------------------------------------------------
# User-tunable policy flags (module globals)
# ---------------------------------------------------------------------------

#: If ``True``, reject any non-canonical names in :func:`resolve_name`
#: (except those starting with ``pred`` or ``extra``). Default: ``False``.
STRICT_CANON_NAMES: bool = False

#: If ``True``, emit ``DeprecationWarning`` when a legacy name is translated
#: to its canonical counterpart. Default: ``True``.
DEPRECATION_WARNINGS: bool = True


# ---------------------------------------------------------------------------
# Aliases (legacy → canonical)
# ---------------------------------------------------------------------------
# The tables below translate legacy/old field names, commonly found in
# historical GSI diagnostics or older wrappers, into the canonical schema.
# Keys are legacy; values are canonical.

ALIASES_CONV: Mapping[str, str] = {
    # Identification / location
    "kx": "obs_type_code",
    "ksub": "obs_subtype",
    "sid": "obs_id",
    "lat": "lat",
    "lon": "lon",
    "elev": "elev",
    "prs": "pressure",
    "hgt": "model_height",
    "time": "time_hours",

    # Quality / use
    "iqc": "qc_flag",
    "qc_setup": "qc_setup_flag",
    "iuse": "use_flag",
    "analysis_use": "analysis_use_flag",
    "rwgt": "spread",  # legacy synonym found in some dumps

    # Errors
    "errinv_inp": "errinv_input",
    "errinv_adj": "errinv_adjusted",
    "errinv_fin": "errinv",
    "end_err": "err_value",

    # Obs and increments
    "obs": "obs_value",
    "omf": "omf",
    "omf_wob": "omf_nobc",
    "spread": "spread",
    "factw": "spread",

    # Vector winds
    "obs_u": "obs_value_u",
    "omf_u": "omf_u",
    "omf_wob_u": "omf_nobc_u",
    "obs_v": "obs_value_v",
    "omf_v": "omf_v",
    "omf_wob_v": "omf_nobc_v",
}

ALIASES_RAD: Mapping[str, str] = {
    # Common fields
    "lat": "lat",
    "lon": "lon",
    "elev": "elev",
    "time": "time_hours",

    # Geometry
    "iscanp": "scan_position",
    "zasat": "sat_zenith",
    "ilazi": "sat_azimuth",
    "pangs": "sol_zenith",
    "isazi": "sol_azimuth",
    "sgagl": "sun_glint_angle",

    # Surface / environment
    "sfcst": "sfc_temp",
    "sfcstp": "sfc_temp_prev",
    "sfcws": "sfc_wind",
    "sfcwt": "sfc_water_frac",
    "sfclt": "sfc_land_frac",
    "sfcic": "sfc_ice_frac",
    "sfcsd": "sfc_snow_depth",
    "sfclc": "sfc_snow_frac",
    "sfcsmc": "sfc_soil_moist",
    "sfcltp": "sfc_soil_temp",
    "sfcvf": "sfc_veg_frac",
    "sfcsc": "sfc_class",
    "clsORclw": "clw",
    "cldpORtpwc": "tpwc",

    # Per-channel values
    "tb_obs": "obs_value",
    "omf": "omf",
    "omf_nbc": "omf_nobc",
    "oma": "oma",
    "errinv": "errinv",
    "end_err": "err_value",
    "idqc": "qc_flag",
    "emiss": "emissivity",
    "tlach": "tlap",  # historical misspelling → canonical 'tlap'
    "ts": "skin_temp",
    "spread": "spread",
    "ich": "channel",
    "freq": "freq",
    "pol": "pol",
    "wave": "wave",
    "varch": "varch",
    "tlap": "tlap",
}

# Canonical universe for validation (all mapped canonical values)
CANON_CORE = set(ALIASES_CONV.values()) | set(ALIASES_RAD.values())

__all__ = [
    # policy
    "STRICT_CANON_NAMES",
    "DEPRECATION_WARNINGS",
    # maps / sets
    "ALIASES_CONV",
    "ALIASES_RAD",
    "CANON_CORE",
    # API
    "resolve_name",
    "resolve_names",
    "resolve_col_in_df",
    "is_canonical",
    "set_canonical_policy",
]

# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _maybe_warn_deprecated(old: str, new: str) -> None:
    """Emit a deprecation warning if a legacy name was translated.

    Parameters
    ----------
    old : str
        The user-provided (possibly legacy) name.
    new : str
        The resolved canonical name.
    """
    if DEPRECATION_WARNINGS and old != new:
        # stacklevel=3: point at the *caller of resolve_name* for nicer UX.
        _w.warn(
            f"Column name '{old}' is deprecated; use '{new}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# These are expected to exist in your module:
# - ALIASES_CONV: dict[str, str]  # legacy → canonical (conventional)
# - ALIASES_RAD:  dict[str, str]  # legacy → canonical (radiance)
# - CANON_CORE:   set[str]        # known canonical names
# - STRICT_CANON_NAMES: bool
# - DEPRECATION_WARNINGS: bool
# - _maybe_warn_deprecated(old: str, new: str) -> None

def resolve_name(
    name: str,
    domain: str,
    *,
    flag: Optional[str] = None,
    columns: Optional[Iterable[str]] = None,
) -> str:
    """
    Resolve a user-supplied column *name* to either a **canonical** or **legacy**
    representation, optionally considering the *columns* available in a DataFrame.

    The function supports three modes controlled by ``flag``:

    - ``flag=None`` (default): **canonical-first** resolution (backward compatible
      with previous behavior). If ``columns`` is provided, the function attempts,
      in order: exact match in ``columns`` → canonical of ``name`` if present in
      ``columns`` → a legacy alias that maps to the same canonical and *is* in
      ``columns`` → otherwise, returns the canonical.
    - ``flag='legacy'``: **legacy-preferred** resolution. Returns a legacy alias
      that maps to the canonical of ``name``. If multiple aliases exist, a stable
      choice is made (in iteration order); when ``columns`` is provided, the
      returned alias is preferentially one that appears in ``columns``. If none
      are found, falls back to the canonical.
    - Any other value for ``flag`` raises ``ValueError``.

    Parameters
    ----------
    name : str
        User-provided column name (canonical or legacy).
    domain : {'conv', 'rad'}
        Diagnostic domain. Selects the alias table to use.
    flag : {None, 'legacy'}, optional
        Resolution strategy (see description). Default is ``None``.
    columns : iterable of str, optional
        A collection of column names (e.g., ``df.columns``) used to disambiguate
        and prefer names that actually exist in the data.

    Returns
    -------
    str
        The resolved column name to use when accessing data.

    Raises
    ------
    ValueError
        If ``domain`` is not one of ``'conv'`` or ``'rad'``; or if ``flag`` is
        invalid (not ``None`` or ``'legacy'``).
    KeyError
        When ``STRICT_CANON_NAMES`` is ``True`` and the resolved canonical name
        is not recognized (i.e., not in ``CANON_CORE`` and not prefixed by
        allowed dynamic patterns such as ``'pred'`` or ``'extra'``).

    Notes
    -----
    - Deprecation warnings for legacy → canonical transitions are emitted through
      ``_maybe_warn_deprecated`` when ``DEPRECATION_WARNINGS`` is enabled.
    - Dynamic fields commonly produced by diagnostic pipelines (e.g., predictors
      ``pred1..predN`` or extra columns ``extra_*``) are allowed even when
      ``STRICT_CANON_NAMES`` is ``True``.
    - The function is deliberately conservative: if nothing matches in
      ``columns`` (when provided), it still returns the canonical target so that
      a subsequent access can fail loudly and early, helping discovery.

    Examples
    --------
    Canonical-first resolution (no ``columns`` provided):

    >>> resolve_name("kx", domain="conv")
    'obs_type_code'

    Prefer the name that already exists in the DataFrame:

    >>> cols = ["lat", "lon", "obs_type_code"]  # canonical already present
    >>> resolve_name("kx", domain="conv", columns=cols)
    'obs_type_code'

    Prefer a legacy alias that exists in the DataFrame:

    >>> cols = ["lat", "lon", "kx"]  # legacy present, canonical absent
    >>> resolve_name("obs_type_code", domain="conv", columns=cols)
    'kx'

    Force a legacy-form name (stable choice; prefers what's in ``columns``):

    >>> cols = ["idqc", "omf"]  # typical radiance legacy
    >>> resolve_name("qc_flag", domain="rad", flag="legacy", columns=cols)
    'idqc'
    """
    # --- Select alias table by domain -----------------------------------------
    if domain == "conv":
        aliases = ALIASES_CONV
    elif domain == "rad":
        aliases = ALIASES_RAD
    else:
        raise ValueError("domain must be 'conv' or 'rad'")

    # Normalize provided columns to a fast lookup set of strings (or None)
    cols = set(map(str, columns)) if columns is not None else None

    # --- Helpers ---------------------------------------------------------------
    def _to_canonical(n: str) -> str:
        """
        Map a possibly-legacy name to its canonical target, honoring
        deprecation warnings and STRICT_CANON_NAMES.
        """
        new = aliases.get(n, n)  # legacy→canonical; canonical stays canonical
        if new != n:
            _maybe_warn_deprecated(n, new)

        # Guardrail: optionally enforce canonical catalog
        if (
            STRICT_CANON_NAMES
            and new not in CANON_CORE
            and not new.startswith(("pred", "extra"))
        ):
            raise KeyError(f"Column '{n}'→'{new}' is not a recognized canonical name.")
        return new

    def _find_legacy_for(canon: str) -> str | None:
        """
        Given a canonical name, return a legacy alias that maps to it.
        Prefer one present in `cols`, otherwise return the first stable alias.
        """
        if cols is not None:
            for legacy, target in aliases.items():
                if target == canon and legacy in cols:
                    return legacy
        for legacy, target in aliases.items():  # stable fall-back
            if target == canon:
                return legacy
        return None

    # --- Strategy: LEGACY mode ------------------------------------------------
    if flag is not None and flag.lower() != "legacy":
        raise ValueError("flag must be None or 'legacy'")

    if (flag or "").lower() == "legacy":
        canon = _to_canonical(name)
        # If `name` itself is a legacy present in columns, keep it as-is.
        if cols is not None and name in cols:
            return name
        legacy = _find_legacy_for(canon)
        return legacy or canon  # fall back to canonical if no alias exists

    # --- Strategy: AUTO (canonical-first), optionally guided by columns --------
    if flag is None and cols is not None:
        # 1) Exact name already present: use it (don't “correct” user input).
        if name in cols:
            return name
        # 2) Canonical of `name` is present: use it directly.
        canon = _to_canonical(name)
        if canon in cols:
            return canon
        # 3) A legacy that maps to the same canonical is present: prefer it.
        legacy = _find_legacy_for(canon)
        if legacy is not None:
            return legacy
        # 4) Nothing matched: return canonical and let callers decide.
        return canon

    # --- Default: canonical-only behavior (backward compatible) ---------------
    return _to_canonical(name)


def resolve_names(
    names: Iterable[str],
    domain: str,
    *,
    flag: Optional[str] = None,
    columns: Optional[Iterable[str]] = None,
) -> list[str]:
    """
    Vectorized convenience wrapper over :func:`resolve_name`.

    It resolves each input name (canonical or legacy) into a concrete string to
    be used when accessing data, optionally guided by a set of available
    *columns* (e.g., a DataFrame's columns).

    Parameters
    ----------
    names : iterable of str
        Names to resolve. Items may be canonical (e.g., ``'qc_flag'``) or
        legacy (e.g., ``'idqc'``).
    domain : {'conv', 'rad'}
        Diagnostic domain. Selects the alias table used by :func:`resolve_name`.
    flag : {None, 'legacy'}, optional
        Resolution strategy forwarded to :func:`resolve_name`:
        - ``None`` (default): canonical-first with column-awareness if
          ``columns`` is provided.
        - ``'legacy'``: return a legacy alias that maps to the canonical
          semantics, preferring one present in ``columns`` if available.
    columns : iterable of str, optional
        Column names present in your data. When provided, resolution prefers a
        spelling that actually exists in this set.

    Returns
    -------
    list of str
        A list with the resolved names in the same order as *names*.

    Raises
    ------
    ValueError
        If *domain* or *flag* is invalid (see :func:`resolve_name`).
    KeyError
        If strict canonical checks are enabled in :func:`resolve_name` and an
        unrecognized canonical name is requested.

    See Also
    --------
    resolve_name : Scalar resolution with full control.
    resolve_col_in_df : Resolve a single name to the *actual* column present.

    Notes
    -----
    - This function does **not** verify that the returned names exist in
      *columns* unless ``columns`` is provided; it delegates all logic to
      :func:`resolve_name`.

    Examples
    --------
    Canonical-first resolution (no columns provided):

    >>> resolve_names(["kx", "lat", "lon"], domain="conv")
    ['obs_type_code', 'lat', 'lon']

    Prefer what already exists in the DataFrame columns:

    >>> cols = ["kx", "lat", "lon"]               # only legacy for kx is present
    >>> resolve_names(["obs_type_code", "lat"], "conv", columns=cols)
    ['kx', 'lat']

    Force legacy spellings (stable choice; prefer what's present in columns):

    >>> cols = ["idqc", "omf"]
    >>> resolve_names(["qc_flag", "omf"], "rad", flag="legacy", columns=cols)
    ['idqc', 'omf']

    Mixed inputs are ok; each element is resolved independently:

    >>> resolve_names(["qc_flag", "idqc"], "rad")
    ['qc_flag', 'idqc']
    """
    return [
        resolve_name(n, domain, flag=flag, columns=columns)
        for n in names
    ]


def resolve_col_in_df(
    df_columns: Iterable[str],
    name: str,
    domain: str,
    *,
    prefer: Optional[str] = None,
) -> str:
    """
    Resolve ``name`` to the **actual** column present in a DataFrame.

    This helper answers the practical question:
    “I want the field with *these* semantics; which concrete column name should
    I use in *this* DataFrame?”

    The function tries, in order:
    1. Use the exact spelling *name* if it already exists in ``df_columns``.
    2. Use the canonical form (via :func:`resolve_name`) if present.
    3. Use a legacy alias that maps to the same canonical target, if present.
    4. Otherwise, raise ``KeyError``.

    Parameters
    ----------
    df_columns : iterable of str
        Column names of the target DataFrame (e.g., ``df.columns``).
    name : str
        Desired field (canonical or legacy), e.g., ``'qc_flag'`` or ``'idqc'``.
    domain : {'conv', 'rad'}
        Diagnostic domain that selects the alias table.
    prefer : {None, 'canonical', 'legacy'}, optional
        Tie-break policy **only when both** canonical and legacy forms exist in
        ``df_columns``. Defaults to ``None``, which prefers:
        - the exact user spelling *name* if present,
        - otherwise canonical,
        - otherwise legacy.
        If set to ``'canonical'`` or ``'legacy'``, that form is preferred when
        both are available.

    Returns
    -------
    str
        The column name **as it appears** in the DataFrame.

    Raises
    ------
    KeyError
        If neither canonical nor legacy forms are present in ``df_columns``.
    ValueError
        If *domain* or *flag* (internally in :func:`resolve_name`) is invalid.

    See Also
    --------
    resolve_name : Canonical/legacy resolution without checking DataFrame columns.
    resolve_names : Vectorized resolution for multiple names.

    Notes
    -----
    - This function never **renames** your DataFrame; it only selects which
      spelling you should use for access.
    - When strict canonical checking is enabled in :func:`resolve_name`, that
      validation applies when computing the canonical target.

    Examples
    --------
    Basic “pick what exists” for radiance diagnostics:

    >>> import pandas as pd
    >>> df = pd.DataFrame(columns=["idqc", "omf"])  # legacy qc + canonical omf
    >>> resolve_col_in_df(df.columns, "qc_flag", "rad")
    'idqc'
    >>> resolve_col_in_df(df.columns, "omf", "rad")
    'omf'

    Honor the user spelling if it already exists:

    >>> df = pd.DataFrame(columns=["qc_flag", "idqc"])
    >>> resolve_col_in_df(df.columns, "qc_flag", "rad")
    'qc_flag'  # exact spelling wins

    Tie-breaking when both forms exist:

    >>> df = pd.DataFrame(columns=["qc_flag", "idqc"])
    >>> resolve_col_in_df(df.columns, "idqc", "rad", prefer="canonical")
    'qc_flag'
    >>> resolve_col_in_df(df.columns, "qc_flag", "rad", prefer="legacy")
    'idqc'

    Conventional example (kx / obs_type_code):

    >>> df = pd.DataFrame(columns=["kx", "lat", "lon"])
    >>> resolve_col_in_df(df.columns, "obs_type_code", "conv")
    'kx'

    Failure example with helpful message (shortened):

    >>> df = pd.DataFrame(columns=["lat", "lon"])
    >>> resolve_col_in_df(df.columns, "qc_flag", "rad")  # doctest: +ELLIPSIS
    Traceback (most recent call last):
        ...
    KeyError: "Column 'qc_flag' not found (canonical='qc_flag', legacy='idqc') in DataFrame columns: ['lat', 'lon']"
    """
    cols = set(map(str, df_columns))

    # 1) Exact user spelling wins.
    if name in cols:
        return name

    # 2) Compute canonical and legacy targets (without forcing column awareness).
    canon = resolve_name(name, domain, flag=None, columns=None)
    legacy = resolve_name(name, domain, flag="legacy", columns=None)

    # 3) If both exist, apply explicit preference.
    if prefer == "legacy" and legacy in cols and canon in cols:
        return legacy
    if prefer == "canonical" and legacy in cols and canon in cols:
        return canon

    # 4) Default preference: canonical, then legacy.
    if canon in cols:
        return canon
    if legacy in cols:
        return legacy

    # 5) Nothing matched; fail loud with context.
    raise KeyError(
        f"Column '{name}' not found (canonical='{canon}', legacy='{legacy}') "
        f"in DataFrame columns: {sorted(cols)}"
    )


def is_canonical(name: str) -> bool:
    """
    Check whether a given name is canonical.

    Parameters
    ----------
    name : str
        Name to check.

    Returns
    -------
    bool
        ``True`` if the name is in :data:`CANON_CORE`, ``False`` otherwise.

    Notes
    -----
    This function does not consider the ``pred*``/``extra*`` escape hatch.
    """
    return name in CANON_CORE


@contextmanager
def set_canonical_policy(*, strict: bool | None = None, deprecations: bool | None = None):
    """
    Temporarily set canonical enforcement and deprecation warning policies.

    Handy for tests or short blocks that require different policies without
    permanently changing module-level flags.

    Parameters
    ----------
    strict : bool, optional
        If provided, temporarily sets :data:`STRICT_CANON_NAMES`.
    deprecations : bool, optional
        If provided, temporarily sets :data:`DEPRECATION_WARNINGS`.

    Yields
    ------
    None
        Context manager with side effects on module-level flags.

    Examples
    --------
    >>> with set_canonical_policy(strict=True, deprecations=True):
    ...     resolve_name("kx", "conv")  # maps to 'obs_type_code' (warns)
    ...     # any unknown would raise KeyError here
    """
    old_strict = STRICT_CANON_NAMES
    old_depr = DEPRECATION_WARNINGS
    try:
        if strict is not None:
            globals()["STRICT_CANON_NAMES"] = strict
        if deprecations is not None:
            globals()["DEPRECATION_WARNINGS"] = deprecations
        yield
    finally:
        globals()["STRICT_CANON_NAMES"] = old_strict
        globals()["DEPRECATION_WARNINGS"] = old_depr


# ---------------------------------------------------------------------------
# Usage tips (non-executable comments)
# ---------------------------------------------------------------------------
# • When consuming arbitrary user input, prefer `resolve_col_in_df(df.columns, ...)`
#   to locate the *actual* DataFrame label you can select, then use that label
#   consistently in subsequent operations (plotting, coloring, filtering, etc.).
#
# • Keep alias tables small and intentional. If you need a new canonical field,
#   add it to the appropriate ALIASES_* value set (as a value) by wiring at least
#   one legacy key that maps to it—or directly use the same string on both sides.
#
# • To help users migrate, consider temporarily enabling:
#       with set_canonical_policy(strict=False, deprecations=True):
#           ...
#   to surface warnings without breaking old notebooks/scripts.

