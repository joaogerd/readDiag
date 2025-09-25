from __future__ import annotations

from importlib.resources import files
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

import yaml

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def _normalize_vartype(vt: Optional[Union[str, int]]) -> str:
    """
    Normalize an observation type identifier (varType) into a canonical string.

    This function ensures that both satellite/platform identifiers (strings)
    and conventional observation codes (integers, i.e., *kx* values) are
    represented in a consistent, lowercase, hyphenated string form.

    Parameters
    ----------
    vt : str or int or None
        Observation type identifier.
        - If ``int`` (e.g., 120), it is returned as a string (``"120"``).
        - If ``str``, it is normalized: stripped, lowercased, and with
          underscores converted to hyphens.
        - If ``None``, returns an empty string.

    Returns
    -------
    str
        Normalized observation type identifier. Always a string.

    Examples
    --------
    >>> _normalize_vartype(120)
    '120'
    >>> _normalize_vartype("MetOp_B")
    'metop-b'
    >>> _normalize_vartype(None)
    ''
    """
    if vt is None:
        return ""
    if isinstance(vt, int):
        return str(vt)  # KX codes as plain strings, e.g. "120"
    return str(vt).strip().lower().replace("_", "-")


def _normalize_varname(vn: Optional[str]) -> str:
    """
    Normalize a variable or channel family name into a canonical string.

    This function standardizes variable names (e.g., "amsua", "uv", "t")
    to a consistent, lowercase, hyphenated format.

    Parameters
    ----------
    vn : str or None
        Variable or channel family name.
        - If ``str``, it is normalized: stripped, lowercased, and with
          underscores converted to hyphens.
        - If ``None``, returns an empty string.

    Returns
    -------
    str
        Normalized variable name. Always a string.

    Examples
    --------
    >>> _normalize_varname("Amsua")
    'amsua'
    >>> _normalize_varname("uv_wind")
    'uv-wind'
    >>> _normalize_varname(None)
    ''
    """
    if vn is None:
        return ""
    return str(vn).strip().lower().replace("_", "-")


class DataSourcesInfo:
    """Parser and accessor for observation metadata defined in ``table.yml``.

    The YAML is expected to have the following structure:

    ```yaml
    observations:
      - kx: <platform_or_kx>        # e.g., "n19", "metop-b", "120"
        details:
          - var: <variable>         # e.g., "amsua", "uv", "t"
            abbreviation: <str>     # short label for legends
            instrument: <str>       # human-friendly instrument/platform description
            color: <hex>            # e.g., "#1f77b4"
            symbol: <str>           # plotting symbol, e.g., "x", "s", "*"
            iuse: "<-1|0|1|2>"      # keep as string for compatibility with existing code
    ```
    """

    def __init__(self, yaml_file: Optional[str | Path] = None) -> None:
        """Load observation metadata from the packaged YAML table.
    
        Parameters
        ----------
        yaml_file : str | Path | None
            Optional custom path to a YAML file. When `None`, the loader tries:
            (1) `importlib.resources.files("gsidiag") / "table.yml"` (works in wheels),
            then (2) a sibling `table.yml` next to this module as a fallback.
        """
        data: Dict[str, Any] = {}
        source_desc = ""

        if yaml_file is not None:
            yml_path = Path(yaml_file)
            logger.debug("Attempting to load table.yml from explicit path: %s", yml_path)
            text = yml_path.read_text(encoding="utf-8")
            data = yaml.safe_load(text) or {}
            source_desc = str(yml_path)
        else:
            # Try packaged resource (wheel-safe)
            try:
                res = files("gsidiag") / "table.yml"
                logger.debug("Attempting to load packaged table.yml: %s", res)
                text = res.read_text(encoding="utf-8")
                data = yaml.safe_load(text) or {}
                source_desc = "pkg://gsidiag/table.yml"
            except (FileNotFoundError, ModuleNotFoundError, AttributeError) as e:
                # Fallback to sibling file (editable install)
                logger.debug(
                    "Packaged resource not available (%s). Falling back to sibling table.yml",
                    e,
                )
                sibling = Path(__file__).with_name("table.yml")
                if not sibling.is_file():
                    logger.error(
                        "Missing 'table.yml' alongside %s and not packaged.",
                        __file__,
                    )
                    raise FileNotFoundError(
                        "Missing 'table.yml' inside installed package 'gsidiag'. "
                        "Make sure build config includes this data file."
                    ) from e
                logger.debug("Loading sibling table.yml: %s", sibling)
                text = sibling.read_text(encoding="utf-8")
                data = yaml.safe_load(text) or {}
                source_desc = str(sibling)

        logger.info(
            "Loaded %d observation groups from %s",
            len(data.get("observations", []) or []),
            source_desc or "<unknown>",
        )

        # Build lookups (nova API) e `tab` (legado)
        self.lookup: Dict[str, Dict[str, Dict[str, Any]]] = {}

        for obs in data.get("observations", []) or []:
            raw_kx = obs.get("kx", "")
            kx = str(raw_kx).strip()
            if not kx:
                logger.warning("Skipping observation without 'kx': %r", obs)
                continue

            bucket = self.lookup.setdefault(kx, {})
            details_list = obs.get("details", []) or []
            if not details_list:
                logger.debug("kx=%s has no 'details' entries", kx)

            count = 0
            for detail in details_list:
                var = str(detail.get("var", "")).strip()
                if not var:
                    logger.warning("Skipping detail without 'var' in kx=%s: %r", kx, detail)
                    continue
                bucket[var] = detail
                count += 1

            logger.debug("Registered kx=%s with %d detail entries", kx, count)

        total_pairs = sum(len(v) for v in self.lookup.values())
        logger.info(
            "Built lookup with %d platforms (kx) and %d (kx,var) pairs",
            len(self.lookup),
            total_pairs,
        )

        # Compat: legacy `tab` uses int keys quando possível
        self.tab: Dict[int | str, Dict[str, Dict[str, Any]]] = {}
        for kx_str, mapping in self.lookup.items():
            try:
                kx_key: int | str = int(kx_str)
            except (ValueError, TypeError):
                kx_key = kx_str
            self.tab[kx_key] = mapping

    def get(self, var_type: str, var_name: str, key: str) -> str:
        """Retrieve a metadata field from the lookup.

        Args:
            var_type: Observation type (e.g., "n19", "metop-a", "120").
            var_name: Variable name (e.g., "amsua", "uv", "t").
            key: Field to retrieve (e.g., "instrument", "abbreviation", "color").

        Returns:
            The field value as a string, or an empty string if not found.
        """
        val = self.lookup.get(var_type, {}).get(var_name, {}).get(key, "")
        return "" if val in (None, "") else str(val)

    def platforms(self) -> list[str]:
        """List all platforms/keys (``kx``) available in the table."""
        return sorted(self.lookup.keys())

    def variables_for(self, var_type: str) -> list[str]:
        """List variables available for a given ``var_type`` (``kx``)."""
        return sorted(self.lookup.get(var_type, {}).keys())

    def detail(self, var_type: str, var_name: str) -> Dict[str, Any]:
        """Return the complete detail dict for a (``var_type``, ``var_name``) pair."""
        return dict(self.lookup.get(var_type, {}).get(var_name, {}))


# Module-level singleton for fast reads
_DS_INFO = DataSourcesInfo()


def getVarInfo(varType: Optional[Union[str, int]], varName: Optional[str], what: Optional[str]) -> str:
    """Return user-friendly metadata with YAML-first priority and robust fallbacks.

    Priority:
      1) ``table.yml`` (if an entry exists)
      2) Heuristics (e.g., "NOAA-19 AMSU-A" for ``n19``/``amsua``)

    This function never returns ``None``; it returns an empty string if nothing matches.

    Args:
        varType: Observation type identifier (e.g., "n19", "metop-b", "120").
        varName: Variable or channel family (e.g., "amsua", "uv", "t").
        what: Field to retrieve (case-insensitive), e.g., "instrument", "abbreviation",
            "platform", "sensor", "color", "symbol", "iuse".

    Returns:
        A string with the requested information, or an empty string if unknown.
    """
    vt_norm = _normalize_vartype(varType)
    vn_norm = _normalize_varname(varName)
    key = (what or "").strip().lower()

    # 1) YAML (preferred)
    try:
        val = _DS_INFO.get(vt_norm, vn_norm, key)
        if val:
            logger.debug("getVarInfo YAML hit: (%s,%s).%s -> %r", vt_norm, vn_norm, key, val)
            return str(val)
    except Exception as e:
        logger.debug("YAML lookup failed for (%s,%s).%s: %s", vt_norm, vn_norm, key, e)

    # 2) Heuristic fallbacks
    if key == "instrument":
        sensor_map = {
            "amsua": "AMSU-A",
            "amsub": "AMSU-B",
            "airs": "AIRS",
            "iasi": "IASI",
            "hirs": "HIRS",
            "mhs": "MHS",
            "ssmis": "SSMIS",
            "atms": "ATMS",
            "cris": "CrIS",
            "cris-fsr": "CrIS FSR",
            "gome": "GOME",
            "mls30": "MLS",
            "omi": "OMI",
            "sndrd1": "GOES Sounder D1",
            "sndrd2": "GOES Sounder D2",
            "sndrd3": "GOES Sounder D3",
            "sndrd4": "GOES Sounder D4",
            "uv": "Atmospheric Motion Vectors (AMVs)",
            "gps_bnd": "GNSS-RO Bending Angle",
            "gps": "GNSS-RO",
        }
        sensor = sensor_map.get(vn_norm, (varName or "").upper() or "SENSOR")
        out = f"{canonical_platform(varType)} {sensor}"
        logger.debug("getVarInfo fallback 'instrument' for (%s,%s): %s", vt_norm, vn_norm, out)
        return out

    if key in {"platform", "satellite"}:
        out = canonical_platform(varType)
        logger.debug("getVarInfo fallback '%s' for (%s,%s): %s", key, vt_norm, vn_norm, out)
        return out

    if key in {"sensor", "instrument_name"}:
        out = (varName or "").upper() or "SENSOR"
        logger.debug("getVarInfo fallback '%s' for (%s,%s): %s", key, vt_norm, vn_norm, out)
        return out

    # fields like color, symbol, iuse → no reasonable heuristic by default
    logger.debug("getVarInfo unknown field '%s' for (%s,%s): ''", key, vt_norm, vn_norm)
    return ""


def canonical_platform(vt: Optional[Union[str, int]]) -> str:
    """Return a human-friendly platform name given a varType/kx.

    Examples
    --------
    "n19"     -> "NOAA-19"
    "n20"     -> "NOAA-20"
    "n21"     -> "NOAA-21"
    "npp"     -> "Suomi-NPP"
    "metop-a" -> "MetOp-A"
    "metop_b" -> "MetOp-B"
    120       -> "Conventional (kx=120)"
    "120"     -> "Conventional (kx=120)"
    None      -> "PLATFORM"
    """
    if vt is None:
        logger.debug("canonical_platform: vt=None -> 'PLATFORM'")
        return "PLATFORM"

    v_raw = str(vt).strip()
    v = v_raw.lower().replace("_", "-")

    # Conventional obs (integer kx codes)
    if isinstance(vt, int) or v.isdigit():
        out = f"Conventional (kx={v_raw})"
        logger.debug("canonical_platform: conventional %r -> %s", vt, out)
        return out

    # NOAA identifiers like n19, n20, n21
    if v.startswith("n") and v[1:].isdigit():
        out = f"NOAA-{v[1:]}"
        logger.debug("canonical_platform: NOAA-like %r -> %s", vt, out)
        return out

    mapping = {
        "npp": "Suomi-NPP",
        "n20": "NOAA-20",
        "n21": "NOAA-21",
    }
    if v in mapping:
        out = mapping[v]
        logger.debug("canonical_platform: mapped %r -> %s", vt, out)
        return out

    # MetOp
    if v.startswith("metop"):
        out = v.title().replace("Metop", "MetOp")
        logger.debug("canonical_platform: MetOp-like %r -> %s", vt, out)
        return out

    out = v_raw.upper() or "PLATFORM"
    logger.debug("canonical_platform: default %r -> %s", vt, out)
    return out

