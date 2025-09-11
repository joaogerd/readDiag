# -*- coding: utf-8 -*-
import sys
import subprocess
import pytest

def test_module_entrypoint_help_runs():
    # Executa "python -m gsidiag --help" num subprocesso para entrar no bloco __main__
    # Argparse imprime ajuda e sai com código 0; não carrega dados reais.
    proc = subprocess.run(
        [sys.executable, "-m", "gsidiag", "--help"],
        capture_output=True, text=True
    )
    # Alguns Python imprimem a ajuda em stdout, outros em stderr, então aceitamos qualquer um
    out = proc.stdout + proc.stderr
    assert proc.returncode == 0
    assert "diagnostic file(s)" in out or "usage:" in out.lower()

