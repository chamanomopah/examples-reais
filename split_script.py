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

    # Divide em sentenças completas
    result = []
    current = ""
    quote_depth = 0  # rastreia se estamos dentro de aspas

    i = 0
    while i < len(text):
        char = text[i]

        # Rastreia aspas
        if char == '"':
            quote_depth += 1
            current += char
            i += 1
            continue

        # Adiciona caractere
        current += char

        # Divide apenas quando fora de aspas e temos pontuação final
        if quote_depth % 2 == 0 and char in '.!?' and i + 1 < len(text):
            next_char = text[i + 1]
            # Próximo é espaço ou aspas de fechamento ou fim
            if next_char in ' "\'\n':
                # Verifica se não é abreviação (Dr., Mr., etc.)
                if len(current) > 3 and not current[-3:].isupper():
                    sentence = current.strip()
                    if sentence:
                        result.append(sentence)
                    current = ""

        i += 1

    # Adiciona o restante
    if current.strip():
        remaining = current.strip()

        # Divide o resto em pedaços razoáveis
        # Se contém aspas, divide por dentro das aspas
        if '"' in remaining:
            parts = re.split(r'("\w[^"]*\.")', remaining)
            for p in parts:
                p = p.strip()
                if p and p not in ('"', '" '):
                    result.append(p)
        else:
            result.append(remaining)

    # Remove duplicatas e vazias
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
