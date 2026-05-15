import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from argparse import ArgumentParser
from dotenv import load_dotenv
from deepgram import DeepgramClient

load_dotenv(r"C:\Users\JOSE\.alfredo\.env")

DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_FILE = CACHE_DIR / "transcribe_cache.json"

LANGUAGE_CODES = {
    "pt": "pt-BR",
    "pt-br": "pt-BR",
    "pt-pt": "pt-PT",
    "en": "en",
    "es": "es",
    "fr": "fr",
    "de": "de",
    "it": "it",
    "ja": "ja",
    "nl": "nl",
    "hi": "hi",
    "ru": "ru",
    "multi": "multi",
}


def get_file_hash(file_path: str) -> str:
    with open(file_path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except:
            return {}
    return {}


def save_cache(cache: dict):
    CACHE_DIR.mkdir(exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")


def format_time(seconds: float) -> str:
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def format_timestamps(words):
    result = []
    for word in words:
        start = format_time(word.start)
        end = format_time(word.end)
        result.append(f"[{start} --> {end}] {word.word}")
    return "\n".join(result)


def transcribe(file_path: str, language: str = "en", use_cache: bool = True):
    if not DEEPGRAM_API_KEY:
        raise ValueError("DEEPGRAM_API_KEY não encontrada no .env")

    if not Path(file_path).exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    client = DeepgramClient(api_key=DEEPGRAM_API_KEY)
    lang = LANGUAGE_CODES.get(language.lower(), language)
    file_hash = get_file_hash(file_path)
    cache_key = f"{file_hash}_{lang}"

    cache = load_cache()

    if use_cache and cache_key in cache:
        print(f"[cache] Usando transcrição em cache")
        return cache[cache_key]

    print(f"[deepgram] Transcrevendo...")
    with open(file_path, "rb") as audio:
        buffer_data = audio.read()

    response = client.listen.v1.media.transcribe_file(
        request=buffer_data,
        model="nova-2",
        language=lang,
        smart_format=True,
        utterances=False,
        paragraphs=False,
    )

    result = response.results.channels[0]

    full_text = result.alternatives[0].transcript
    words = result.alternatives[0].words
    timestamps = format_timestamps(words)

    transcription = {
        "text": full_text,
        "timestamps": timestamps,
        "language": lang,
        "date": datetime.now().isoformat(),
        "file_name": Path(file_path).name,
    }

    cache[cache_key] = transcription
    save_cache(cache)

    return transcription


def main():
    parser = ArgumentParser()
    parser.add_argument("file", help="Caminho do áudio ou vídeo")
    parser.add_argument("-l", "--local", default="en", help="Código do idioma (default: en)")
    parser.add_argument("-o", "--output", help="Caminho do arquivo de saída (default: mesmo local do vídeo com _transcript.txt)")
    parser.add_argument("-f", "--format", default="timestamps", choices=["transcricao", "timestamps"], help="Formato de saída (default: timestamps)")
    parser.add_argument("--no-cache", action="store_true", help="Ignorar cache e forçar nova transcrição")
    args = parser.parse_args()

    try:
        result = transcribe(args.file, args.local, use_cache=not args.no_cache)

        if args.output:
            output_path = Path(args.output)
        else:
            video_path = Path(args.file)
            output_path = video_path.parent / f"{video_path.stem}_transcript.txt"

        if args.format == "transcricao":
            content = result['text']
        else:
            content = result['timestamps']

        output_path.write_text(content, encoding="utf-8")
        print(f"Salvo: {output_path}")

    except Exception as e:
        print(f"Erro: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
