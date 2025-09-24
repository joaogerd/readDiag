import yaml
from os import path

class dataSourcesInfo:
    """
    A class to parse and store information from a YAML file containing observations data.

    Attributes:
        tab (dict): A dictionary to store the parsed observations data.
    """
    def __init__(self):
        """
        The constructor for dataSourcesInfo class. Reads from a YAML file and initializes the 'tab' attribute.
        """
        yaml_file = path.join(path.dirname(__file__), 'table.yml')

        with open(yaml_file, 'r') as file:
            self.data = yaml.safe_load(file)

        self.tab = {}
        for observation in self.data['observations']:
            kx = observation['kx']
            self.tab[kx] = {}
            for detail in observation['details']:
                var = detail['var']
                self.tab[kx][var] = detail


# dataSourcesInfo.py  (ou datasources.py)

def getVarInfo(varType, varName, what: str) -> str:
    """
    Retorna metadados amigáveis; PRIORIDADE:
    1) table.yml (se existir uma entrada)
    2) heurística (ex.: 'NOAA-19 AMSU-A' para n19/amsua)
    Nunca retorna None.
    """
    # Converte tudo para string (tratando ints ou None)
    varType = "" if varType is None else str(varType)
    varName = "" if varName is None else str(varName)
    what    = "" if what is None else str(what)

    varType = varType.strip()
    varName = varName.strip()
    what    = what.strip().lower()

    # 1) YAML (se houver):
    try:
        ds = dataSourcesInfo()  # carrega table.yml
        val = ds.tab.get(varType, {}).get(varName, {}).get(what)
        if val not in (None, ""):
            return str(val)
    except Exception:
        pass  # segue pro fallback

    # 2) Fallbacks heurísticos:
    if what == "instrument":
        sensor_map = {
            "amsua": "AMSU-A", "amsub": "AMSU-B", "airs": "AIRS", "iasi": "IASI",
            "hirs": "HIRS", "mhs": "MHS", "ssmis": "SSMIS", "atms": "ATMS",
        }
        sensor = sensor_map.get(varName.lower(), varName.upper() or "SENSOR")

        vt = varType.lower()
        if vt.startswith("n") and vt[1:].isdigit():
            platform = f"NOAA-{vt[1:]}"
        elif vt.startswith("metop"):
            platform = vt.replace("_", "-").replace("metop", "MetOp").replace("metop-", "MetOp-").title()
            platform = platform.replace("Metop", "MetOp")
        elif vt in ("gmi","ssmis-f16","ssmis-f17","ssmis-f18","ssmis-f19"):
            platform = vt.upper()
        else:
            platform = varType.upper() or "PLATFORM"

        return f"{platform} {sensor}"

    if what in ("platform", "satellite"):
        return varType.upper() or "PLATFORM"

    if what in ("sensor", "instrument_name"):
        return varName.upper() or "SENSOR"

    return ""


