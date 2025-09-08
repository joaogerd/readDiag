#!/usr/bin/env python3
import os
import re
import argparse
from pathlib import Path

HEADER_PATTERN = re.compile(
    r"""^#\s*📄\s*`([^`]+)`\s*```(?:[A-Za-z0-9_+-]+)?\s*\n(.*?)\n```""",
    re.MULTILINE | re.DOTALL,
)

def sanitize_filename(name: str) -> str:
    """
    Mantém o nome (com extensão) mas remove caracteres ilegais para arquivo
    e evita diretórios acidentais. Não altera a extensão existente.
    """
    # troca separadores de diretório por sublinhado (evita path traversal)
    name = name.replace("/", "_").replace("\\", "_")
    # remove caracteres problemáticos em Windows/macOS
    name = re.sub(r'[<>:"|?*\x00-\x1F]', "_", name).strip()
    # evita nomes vazios
    return name or "sem_nome.txt"

def extrair_scripts(entrada: Path, saida: Path, overwrite: bool = False) -> int:
    saida.mkdir(parents=True, exist_ok=True)
    text = entrada.read_text(encoding="utf-8")

    matches = list(HEADER_PATTERN.finditer(text))
    if not matches:
        print("Nenhum bloco encontrado no formato esperado.")
        return 0

    count = 0
    for m in matches:
        raw_name, code = m.group(1), m.group(2)
        fname = sanitize_filename(raw_name)
        out_path = saida / fname

        if out_path.exists() and not overwrite:
            print(f"[SKIP] Já existe: {out_path} (use --overwrite para substituir)")
            continue

        # normaliza quebra de linha e tira espaços extras nas bordas
        code = code.rstrip() + "\n"
        out_path.write_text(code, encoding="utf-8")
        print(f"[OK] Criado: {out_path}")
        count += 1

    print(f"\n✅ {count} arquivo(s) extraído(s) para: {saida}")
    return count

def main():
    ap = argparse.ArgumentParser(
        description="Separa múltiplos blocos de código em arquivos individuais mantendo a extensão do título."
    )
    ap.add_argument("input", help="Arquivo .txt com os blocos")
    ap.add_argument("-o", "--outdir", default="scripts", help="Pasta de saída (default: scripts)")
    ap.add_argument("--overwrite", action="store_true", help="Sobrescrever arquivos existentes")
    args = ap.parse_args()

    entrada = Path(args.input)
    saida = Path(args.outdir)

    if not entrada.exists():
        ap.error(f"Arquivo de entrada não encontrado: {entrada}")

    extrair_scripts(entrada, saida, overwrite=args.overwrite)

if __name__ == "__main__":
    main()

