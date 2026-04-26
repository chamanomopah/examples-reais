import sys
import re

def split_script(input_path, output_path="script_cutted.md"):
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

    # Divide em sentenças (preservando aspas inteiras)
    sentences = []
    current = ""
    quote_depth = 0

    for i, char in enumerate(text):
        if char == '"':
            quote_depth += 1

        current += char

        # Divide apenas fora de aspas
        if quote_depth % 2 == 0 and char in '.!?' and i + 1 < len(text):
            next_char = text[i + 1]
            if next_char in ' "\'\n':
                # Evita abreviações comuns
                if len(current) > 4 and not (current[-3] == '.' and current[-2:].isupper()):
                    sentence = current.strip()
                    if sentence:
                        sentences.append(sentence)
                    current = ""

    if current.strip():
        sentences.append(current.strip())

    # Pós-processa: separa aspas do texto ao redor
    result = []
    for sent in sentences:
        # Se tem aspas, divide: antes, aspas, depois
        if '"' in sent:
            # Encontra todas as aspas
            parts = re.split(r'("[^"]+")', sent)
            for p in parts:
                p = p.strip()
                if p and p != '"':
                    result.append(p)
        else:
            result.append(sent)

    # Remove vazias e duplicatas
    final = []
    for r in result:
        r = r.strip()
        if r and r not in final:
            final.append(r)

    # Escreve o output
    output_full_path = str(input_path).rsplit("\\", 1)[0] + "\\" + output_path
    with open(output_full_path, "w", encoding="utf-8") as f:
        for line in final:
            f.write(line + "\n")

    print(f"Salvo: {output_full_path}")
    print(f"Total de linhas: {len(final)}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python split_script.py <caminho_do_script>")
        sys.exit(1)

    split_script(sys.argv[1])
