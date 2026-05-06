import sys
import re
import os
from pathlib import Path

def split_script(input_path, output_path="script_cutted.md", chunk_lines=None):
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

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
    input_dir = Path(input_path).parent
    output_full_path = input_dir / output_path
    with open(output_full_path, "w", encoding="utf-8") as f:
        for line in unique_final:
            f.write(line + "\n")

    print(f"Salvo: {output_full_path}")
    print(f"Total de linhas: {len(unique_final)}")

    # Se chunk_lines for especificado, cria os chunks
    if chunk_lines:
        storyboard_dir = input_dir / "storyboard"
        storyboard_dir.mkdir(exist_ok=True)

        # Divide em chunks
        total_lines = len(unique_final)
        num_chunks = (total_lines + chunk_lines - 1) // chunk_lines

        for i in range(num_chunks):
            start_idx = i * chunk_lines
            end_idx = min((i + 1) * chunk_lines, total_lines)
            chunk = unique_final[start_idx:end_idx]

            chunk_filename = f"script_chuck{i + 1}.md"
            chunk_path = storyboard_dir / chunk_filename

            with open(chunk_path, "w", encoding="utf-8") as f:
                for line in chunk:
                    f.write(line + "\n")

            print(f"Chunk {i + 1}: {chunk_path} ({len(chunk)} linhas)")

        print(f"Total de chunks: {num_chunks}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python split_script.py <caminho_do_script> [-n <linhas_por_chunk>]")
        sys.exit(1)

    input_path = sys.argv[1]
    chunk_lines = None

    # Parse flag -n
    if "-n" in sys.argv:
        idx = sys.argv.index("-n")
        if idx + 1 < len(sys.argv):
            try:
                chunk_lines = int(sys.argv[idx + 1])
            except ValueError:
                print("Erro: -n requer um número inteiro")
                sys.exit(1)

    split_script(input_path, chunk_lines=chunk_lines)
