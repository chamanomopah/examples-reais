#!/usr/bin/env python3
"""
Gera masterfile.json sincronizando imagens, áudio e timestamps.

Cada linha do script = 1 imagem = N palavras no transcript
Agrupa timestamps por linha do script.
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict


def parse_transcript(transcript_path: Path) -> List[Dict[str, any]]:
    """Parse WebVTT transcript para lista de {word, start, end}"""
    entries = []
    # Aceita HH:MM:SS.mmm ou MM:SS.mmm
    pattern = re.compile(r"\[(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\+)\] (.+)")

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("WEBVTT"):
                continue
            match = pattern.match(line)
            if match:
                start_str, end_str, word = match.groups()
                start = parse_timestamp(start_str)
                end = parse_timestamp(end_str)
                entries.append({"word": word, "start": start, "end": end})

    return entries


def parse_timestamp(ts: str) -> float:
    """Converte timestamp MM:SS.mmm ou HH:MM:SS.mmm para segundos"""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return float(ts)


def read_script_lines(script_path: Path) -> List[str]:
    """Lê script.md retornando linhas limpas"""
    lines = []
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def get_image_files(image_dir: Path) -> List[Path]:
    """Retorna imagens ordenadas por nome"""
    extensions = {".png", ".jpg", ".jpeg"}
    images = [p for p in image_dir.iterdir() if p.suffix.lower() in extensions]
    return sorted(images, key=lambda x: x.name)


def group_words_by_lines(transcript_entries: List[Dict], script_lines: List[str]) -> List[Dict]:
    """Agrupa palavras do transcript por linha do script"""
    result = []

    # Prepara script: cada linha vira lista de palavras normalizadas
    script_normalized = []
    for line in script_lines:
        words = line.lower().replace(".", "").replace(",", "").replace("!", "").replace("?", "").split()
        script_normalized.append(words)

    # Percorre transcript sequencialmente, distribuindo palavras nas linhas
    word_idx = 0
    line_idx = 0
    line_word_idx = 0

    current_start = None
    current_end = None

    while word_idx < len(transcript_entries) and line_idx < len(script_normalized):
        entry = transcript_entries[word_idx]
        transcript_word = entry["word"].lower().replace(".", "").replace(",", "").replace("!", "").replace("?", "")

        if line_word_idx < len(script_normalized[line_idx]):
            expected_word = script_normalized[line_idx][line_word_idx]

            if transcript_word == expected_word:
                if current_start is None:
                    current_start = entry["start"]
                current_end = entry["end"]
                line_word_idx += 1
                word_idx += 1
            else:
                # Skip palavras que não batem (pausas, respiração)
                word_idx += 1
        else:
            # Completou linha, salva cena
            if current_start is not None:
                result.append({
                    "line": line_idx + 1,
                    "text": script_lines[line_idx],
                    "start": round(current_start, 3),
                    "end": round(current_end, 3),
                    "duration": round(current_end - current_start, 3)
                })
            # Próxima linha
            line_idx += 1
            line_word_idx = 0
            current_start = None
            current_end = None

    # Última linha
    if current_start is not None and line_idx < len(script_lines):
        result.append({
            "line": line_idx + 1,
            "text": script_lines[line_idx],
            "start": round(current_start, 3),
            "end": round(current_end, 3),
            "duration": round(current_end - current_start, 3)
        })

    return result


def build_masterfile(
    script_path: Path,
    transcript_path: Path,
    image_dir: Path,
    audio_path: Path,
    output_path: Path
) -> None:
    """Constroi masterfile.json"""

    script_lines = read_script_lines(script_path)
    transcript_entries = parse_transcript(transcript_path)
    images = get_image_files(image_dir)

    if len(images) < len(script_lines):
        raise ValueError(f"Imagens insuficientes: {len(images)} para {len(script_lines)} linhas")

    scenes = group_words_by_lines(transcript_entries, script_lines)

    # Combina cenas com imagens
    masterfile = {
        "audio": str(audio_path.name),
        "duration": round(scenes[-1]["end"] if scenes else 0, 3),
        "scenes": []
    }

    for i, scene in enumerate(scenes):
        masterfile["scenes"].append({
            "line": scene["line"],
            "text": scene["text"],
            "image": str(images[i].name),
            "start": scene["start"],
            "end": scene["end"],
            "duration": scene["duration"]
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(masterfile, f, indent=2, ensure_ascii=False)

    print(f"Masterfile criado: {output_path}")
    print(f"  Áudio: {masterfile['audio']}")
    print(f"  Duração: {masterfile['duration']}s")
    print(f"  Cenas: {len(scenes)}")


def main():
    parser = argparse.ArgumentParser(description="Gera masterfile.json para montagem de vídeo")
    parser.add_argument("--script", required=True, help="Caminho do script.md")
    parser.add_argument("--transcript", required=True, help="Caminho do transcript.txt (WebVTT)")
    parser.add_argument("--image-dir", required=True, help="Pasta com imagens")
    parser.add_argument("--audio", required=True, help="Arquivo de áudio")
    parser.add_argument("--output", default="masterfile.json", help="Arquivo de saída (default: masterfile.json)")

    args = parser.parse_args()

    build_masterfile(
        script_path=Path(args.script),
        transcript_path=Path(args.transcript),
        image_dir=Path(args.image_dir),
        audio_path=Path(args.audio),
        output_path=Path(args.output)
    )


if __name__ == "__main__":
    main()
