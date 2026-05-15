#!/usr/bin/env python3
"""
Renderiza vídeo com FFmpeg a partir de masterfile.json.

Entrada: masterfile.json
Saída: vídeo montado com imagens + áudio sincronizados
"""

import argparse
import json
import subprocess
from pathlib import Path


def parse_duration(d: str) -> float:
    """Converte duração para segundos (suporta 1.5, 00:01:500, etc)"""
    if ":" in d:
        parts = d.split(":")
        if len(parts) == 2:
            return float(parts[0]) * 60 + float(parts[1])
        return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
    return float(d)


def build_complex_filter(scenes: list, width: int, height: int) -> str:
    """Constrói filtro complexo FFmpeg para sobrepor imagens com timing"""
    filters = []
    inputs = []

    for i, scene in enumerate(scenes):
        duration = scene["duration"]
        # Escala + loop pela duração
        filters.append(f"[{i}:v]scale={width}:{height},loop=loop=-1:size=1[start{i}]")

    # Concatena todos
    concat_inputs = "".join([f"[start{i}]" for i in range(len(scenes))])
    filters.append(f"{concat_inputs}concat=n={len(scenes)}:v=1:a=0[outv]")

    return ";".join(filters)


def build_concat_file(scenes: list, base_dir: Path, output_txt: Path, image_subdir: str = "image") -> Path:
    """Cria arquivo concat para FFmpeg estendendo cenas para preencher gaps"""
    image_dir = base_dir / image_subdir

    with open(output_txt, "w") as f:
        for i, scene in enumerate(scenes):
            img_path = image_dir / scene["image"]

            # Duração estendida: do start desta cena até o start da próxima
            if i < len(scenes) - 1:
                # Estende até o início da próxima cena
                extended_duration = scenes[i + 1]["start"] - scene["start"]
            else:
                # Última cena: usa duração original
                extended_duration = scene["duration"]

            f.write(f"file '{img_path.absolute()}'\n")
            f.write(f"duration {extended_duration:.3f}\n")

    return output_txt


def get_pad_filter(position: str, width: int, height: int) -> str:
    """Retorna filtro pad para posicionar imagem no canvas"""
    # x,y para cada posição
    positions = {
        "center": f"(ow-iw)/2:(oh-ih)/2",
        "top-left": "0:0",
        "top-right": f"ow-iw:0",
        "bottom-left": f"0:oh-ih",
        "bottom-right": f"ow-iw:oh-ih",
    }
    return f"pad={width}:{height}:{positions.get(position, positions['center'])}:black"


def render_with_concat(
    masterfile: Path,
    output: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30,
    position: str = "center"
) -> None:
    """Renderiza usando método concat demuxer (simples, eficiente)"""

    with open(masterfile, "r", encoding="utf-8") as f:
        data = json.load(f)

    base_dir = masterfile.parent
    audio_path = base_dir / data["audio"]

    # Tenta encontrar áudio se o caminho exato não exister
    if not audio_path.exists():
        # Busca variações comuns: audio1.flac -> audio_1.flac, etc
        for pattern in [audio_path.name.replace("audio", "audio_"),
                        f"audio_{data['audio'].replace('audio', '')}",
                        data["audio"]]:
            test_path = base_dir / pattern
            if test_path.exists():
                audio_path = test_path
                break

    scenes = data["scenes"]

    # Cria arquivo concat (imagens em subdiretório images/)
    concat_file = base_dir / "_concat.txt"
    build_concat_file(scenes, base_dir, concat_file, image_subdir="images")

    # Filtro de vídeo: scale + posicionar
    vf = f"scale={width}:{height}"
    if position != "stretch":
        vf += f",{get_pad_filter(position, width, height)}"

    # Comando FFmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_file),
        "-i", str(audio_path),
        "-vf", vf,
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        str(output)
    ]

    print(f"Renderizando: {output}")
    print(f"  Cenas: {len(scenes)}")
    print(f"  Resolução: {width}x{height}")
    print(f"  Posição: {position}")
    print(f"  Áudio: {audio_path.name}")

    subprocess.run(cmd, check=True)
    concat_file.unlink()

    print(f"Vídeo salvo: {output}")


def render_with_complex_filter(
    masterfile: Path,
    output: Path,
    width: int = 1920,
    height: int = 1080,
    fps: int = 30
) -> None:
    """Renderiza usando filtro complex (mais controle)"""

    with open(masterfile, "r", encoding="utf-8") as f:
        data = json.load(f)

    base_dir = masterfile.parent
    audio_path = base_dir / data["audio"]

    # Tenta encontrar áudio se o caminho exato não exister
    if not audio_path.exists():
        for pattern in [audio_path.name.replace("audio", "audio_"),
                        f"audio_{data['audio'].replace('audio', '')}",
                        data["audio"]]:
            test_path = base_dir / pattern
            if test_path.exists():
                audio_path = test_path
                break

    scenes = data["scenes"]

    # Inputs
    inputs = []
    for scene in scenes:
        inputs.extend(["-loop", "1", "-i", str(base_dir / "images" / scene["image"])])
    inputs.extend(["-i", str(audio_path)])

    # Filtro
    filter_str = build_complex_filter(scenes, width, height)

    # Trim por duração total
    total_duration = data["duration"]

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "[outv]",
        "-map", f"{len(scenes)}:a",
        "-t", str(total_duration),
        "-r", str(fps),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        str(output)
    ]

    print(f"Renderizando: {output}")
    print(f"  Cenas: {len(scenes)}")
    print(f"  Resolução: {width}x{height}")

    subprocess.run(cmd, check=True)
    print(f"Vídeo salvo: {output}")


def main():
    parser = argparse.ArgumentParser(description="Renderiza vídeo a partir de masterfile.json")
    parser.add_argument("--masterfile", required=True, help="Caminho do masterfile.json")
    parser.add_argument("--output", default="output.mp4", help="Arquivo de saída (default: output.mp4)")
    parser.add_argument("--width", type=int, default=1920, help="Largura (default: 1920)")
    parser.add_argument("--height", type=int, default=1080, help="Altura (default: 1080)")
    parser.add_argument("--fps", type=int, default=30, help="FPS (default: 30)")
    parser.add_argument("--position", choices=["center", "top-left", "top-right", "bottom-left", "bottom-right", "stretch"],
                        default="stretch", help="Posição da imagem (default: stretch)")
    parser.add_argument("--method", choices=["concat", "complex"], default="concat",
                        help="Método de renderização (default: concat)")

    args = parser.parse_args()

    if args.method == "concat":
        render_with_concat(
            masterfile=Path(args.masterfile),
            output=Path(args.output),
            width=args.width,
            height=args.height,
            fps=args.fps,
            position=args.position
        )
    else:
        render_with_complex_filter(
            masterfile=Path(args.masterfile),
            output=Path(args.output),
            width=args.width,
            height=args.height,
            fps=args.fps
        )


if __name__ == "__main__":
    main()
