import sys
import re
import os
import argparse
from pathlib import Path

def split_script(input_path, output_dir=None, sentences=False):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    input_dir = Path(input_path).parent

    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = input_dir / "chunks"

    output_path.mkdir(exist_ok=True, parents=True)

    if sentences:
        split_by_sentences(content, output_path)
    else:
        split_by_chunks(content, output_path)

def split_by_sentences(content, output_path):
    # Remove tudo depois de ## descrição (ou similar)
    content = re.split(r"^##\s+(descrição|description|Descrição)", content, flags=re.MULTILINE | re.IGNORECASE)[0]

    # Remove linhas que começam com #, *, -
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "*", "-", "---")):
            continue
        if stripped.startswith("**") and stripped.endswith("**:"):
            continue
        cleaned.append(stripped)

    # Junta tudo
    text = " ".join(cleaned)

    # Abreviações comuns que não devem terminar sentença
    abbreviations = ['Dr', 'Mr', 'Ms', 'Mrs', 'Prof', 'St', 'etc', 'vs', 'e.g', 'i.e']

    def should_split_after(current_text, dot_pos, full_text):
        """Decide se deve dividir após este ponto."""
        if dot_pos + 1 >= len(full_text):
            return True

        # Encontra o próximo caractere não-espaço
        next_non_space = dot_pos + 1
        while next_non_space < len(full_text) and full_text[next_non_space] == ' ':
            next_non_space += 1

        if next_non_space >= len(full_text):
            return True

        next_char = full_text[next_non_space]
        trimmed = current_text.rstrip()

        # Se o próximo caractere é letra minúscula, NÃO divide (continuação)
        if next_char.islower():
            return False

        # Verifica se o ponto é parte de número decimal
        if re.search(r'\d+\.$', trimmed):
            # Se depois vem dígito, é decimal
            if next_char.isdigit():
                return False

        # Verifica abreviações padrão
        for ab in abbreviations:
            if trimmed.endswith(ab + '.'):
                return False

        # Padrão: Dr. [Nome] [Inicial]. - verifica se é esse padrão
        # Ex: Dr. Lisa M. seguido de nome
        if re.search(r'\bDr\.\s+[A-Z][a-z]*\s+[A-Z]\.$', trimmed):
            # Olha mais adiante para ver se vem sobrenome
            look_ahead = next_non_space + 1
            while look_ahead < len(full_text) and full_text[look_ahead] == ' ':
                look_ahead += 1
            if look_ahead < len(full_text) and full_text[look_ahead].isupper():
                return False

        return len(trimmed) > 4

    # Divide em sentenças
    sentences = []
    current = ""
    in_quote = False

    for i, char in enumerate(text):
        if char == '"':
            in_quote = not in_quote

        current += char

        if not in_quote and char in '.!?':
            if should_split_after(current, i, text):
                sentence = current.strip()
                if sentence:
                    sentences.append(sentence)
                current = ""

    if current.strip():
        sentences.append(current.strip())

    # Pós-processamento: junta aspas sem pontuação final e fragmentos
    result = []
    i = 0
    while i < len(sentences):
        sent = sentences[i]
        merged = False

        # Se sentença termina com aspas SEM pontuação final
        if sent.endswith('"') and not re.search(r'[.!?]["\']$', sent.rstrip()):
            if i + 1 < len(sentences):
                combined = sent + ' ' + sentences[i + 1]
                sentences[i + 1] = combined
                i += 1
                continue

        # Verifica se termina com Dr. + inicial (backup)
        if re.search(r'\bDr\.\s+[A-Z][a-z]*\s+[A-Z]\.\s*$', sent.rstrip()):
            if i + 1 < len(sentences):
                combined = sent + ' ' + sentences[i + 1]
                sentences[i + 1] = combined
                i += 1
                continue

        result.append(sent)
        i += 1

    # Separa aspas longas do contexto
    final = []
    for r in result:
        r = r.strip()
        if not r:
            continue

        # Verifica se contém aspas longas (> 10 palavras)
        quote_matches = re.findall(r'"[^"]{30,}"', r)

        if quote_matches:
            # Divide a sentença mantendo aspas longas separadas
            parts = re.split(r'("[^"]{30,}")', r)
            for p in parts:
                p = p.strip()
                if p and p not in ('"', '" '):
                    final.append(p)
        else:
            final.append(r)

    # Remove fragmentos muito curtos
    cleaned = []
    for r in final:
        r = r.strip()
        if not r:
            continue

        word_count = len(r.split())

        # Fragmentos muito curtos (< 4 palavras) - junta com anterior
        if word_count < 4 and cleaned:
            cleaned[-1] = cleaned[-1] + ' ' + r
        else:
            cleaned.append(r)

    # Remove duplicatas
    seen = set()
    unique_final = []
    for f in cleaned:
        if f not in seen:
            seen.add(f)
            unique_final.append(f)

    # Escreve o output
    output_file = output_path / "script_split.md"
    with open(output_file, "w", encoding="utf-8") as f:
        for line in unique_final:
            f.write(line + "\n")

    print(f"Salvo: {output_file}")
    print(f"Total de linhas: {len(unique_final)}")

def split_by_chunks(content, output_path, chunk_lines=50):
    # Remove tudo depois de ## descrição (ou similar)
    content = re.split(r"^##\s+(descrição|description|Descrição)", content, flags=re.MULTILINE | re.IGNORECASE)[0]

    # Remove linhas que começam com #, *, -
    lines = content.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "*", "-", "---")):
            continue
        if stripped.startswith("**") and stripped.endswith("**:"):
            continue
        cleaned.append(stripped)

    # Divide em chunks de ~50 linhas
    chunks = []
    current_chunk = []

    for line in cleaned:
        current_chunk.append(line)
        if len(current_chunk) >= chunk_lines:
            chunks.append(current_chunk)
            current_chunk = []

    if current_chunk:
        chunks.append(current_chunk)

    # Salva os chunks
    for i, chunk in enumerate(chunks):
        chunk_filename = f"chunk_{i + 1}.md"
        chunk_path = output_path / chunk_filename

        with open(chunk_path, "w", encoding="utf-8") as f:
            for j, line in enumerate(chunk):
                if j == len(chunk) - 1:
                    f.write(line)  # última linha sem \n
                else:
                    f.write(line + "\n")

        total_words = sum(len(s.split()) for s in chunk)
        print(f"Chunk {i + 1}: {chunk_path} ({len(chunk)} linhas, {total_words} palavras)")

    print(f"Total de chunks: {len(chunks)}")
    print(f"Total de linhas: {sum(len(c) for c in chunks)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Divide roteiro em chunks ou sentenças")
    parser.add_argument("input_path", help="Caminho do script de entrada")
    parser.add_argument("--output", "-o", help="Pasta de saída (default: ./chunks)")
    parser.add_argument("--sentences", "-s", action="store_true", help="Dividir por sentenças (comportamento anterior)")

    args = parser.parse_args()

    split_script(args.input_path, output_dir=args.output, sentences=args.sentences)
