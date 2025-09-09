# run_all_plots.py
from __future__ import annotations
import subprocess
import sys
import os
from pathlib import Path
from _common import PROJECT_ROOT , PROJECT_ROOT

"""
Executa todos os scripts de exemplo em examples/basic/plots/
(exceto 00_common.py e ele próprio se estiver nesse diretório).

Uso:
  python run_all_plots.py [diag_conv] [diag_rad]

Se não passar caminhos, usa defaults:
  diag_conv = data/diag_conv_01.2024013018
  diag_rad  = data/diag_amsua_n19_01.2024013018
"""

# Absolute project root (used to derive default data locations)
#PROJECT_ROOT: Path = discover_base()

# Environment overrides (allow local + CI customizations)
READDIAG_DATA: Path = Path(
    os.getenv("READDIAG_DATA", PROJECT_ROOT / "data")
).resolve()
READDIAG_DATA_TEST: Path = Path(
    os.getenv("READDIAG_DATA_TEST", PROJECT_ROOT / "dataTest" / "exp20")
).resolve()

def main():
    base = Path(__file__).resolve().parent
    conv_default = READDIAG_DATA / "diag_conv_01.2024013018"
    rad_default = READDIAG_DATA / "diag_amsua_n19_01.2024013018"

    diag_conv = sys.argv[1] if len(sys.argv) > 1 else conv_default
    diag_rad = sys.argv[2] if len(sys.argv) > 2 else rad_default

    # scripts ordenados pelo nome
    scripts = sorted(p for p in base.glob("*.py") if p.name not in ("_common.py", "run_all_plots.py"))

    print(f"[INFO] executando {len(scripts)} scripts de exemplo...")
    print(f"[INFO] diag_conv = {diag_conv}")
    print(f"[INFO] diag_rad  = {diag_rad}")
    print("=" * 60)

    for s in scripts:
        print(f"\n[RUN] {s.name}")
        try:
            # heurística: se o nome contém "rad" -> passa diag_rad, senão diag_conv
            args = [sys.executable, str(s), (diag_rad if "rad" in s.stem else diag_conv)]
            subprocess.run(args, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] script {s.name} retornou código {e.returncode}")
        except Exception as e:
            print(f"[ERRO] ao rodar {s.name}: {e}")

    print("\n[INFO] Finalizado.")

if __name__ == "__main__":
    main()

