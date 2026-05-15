import sys
import re
import os
import argparse
from pathlib import Path


def natural_sort_key(text):
    """Ordenação natural: chunk_1.md, chunk_2.md, chunk_10.md (não chunk_1, chunk_10, chunk_2)"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


def join_files(input_dir, output_name="joined.txt", output_dir=None, pattern="*.md", separator="\n"):
    input_path = Path(input_dir)

    if not input_path.exists():
        print(f"Erro: pasta não existe: {input_path}")
        return

    # Lista todos os arquivos que combinam com o padrão
    files = sorted(input_path.glob(pattern), key=lambda x: natural_sort_key(x.name))

    if not files:
        print(f"Nenhum arquivo encontrado em {input_path} com padrão '{pattern}'")
        return

    # Output padrão: na mesma pasta dos arquivos
    if output_dir:
        output = Path(output_dir) / output_name
    else:
        output = input_path / output_name

    # Junta o conteúdo
    content = []
    for file in files:
        with open(file, "r", encoding="utf-8") as f:
            file_content = f.read()
            content.append(file_content)

    # Escreve o arquivo unido
    joined_content = separator.join(content)
    with open(output, "w", encoding="utf-8") as f:
        f.write(joined_content)

    print(f"Salvo: {output}")
    print(f"Arquivos unidos: {len(files)}")
    print(f"Total de caracteres: {len(joined_content)}")
    print(f"Total de linhas: {len(joined_content.split(chr(10)))}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Junta arquivos de uma pasta em um único arquivo")
    parser.add_argument("input_dir", help="Pasta com os arquivos para juntar")
    parser.add_argument("--output", "-o", default="joined.txt", help="Nome do arquivo de saída (default: joined.txt)")
    parser.add_argument("--output-dir", "-d", help="Pasta onde salvar o arquivo (default: mesma pasta dos arquivos)")
    parser.add_argument("--pattern", "-p", default="*.md", help="Padrão dos arquivos (default: *.md)")
    parser.add_argument("--separator", "-s", default="\n", help="Separador entre arquivos (default: \\n)")

    args = parser.parse_args()

    join_files(args.input_dir, output_name=args.output, output_dir=args.output_dir, pattern=args.pattern, separator=args.separator)
