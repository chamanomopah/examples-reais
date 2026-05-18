#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ElevenLabs Text-to-Speech Generator
====================================

Script para geração de áudio usando ElevenLabs API.

Uso:
    python elevenlabs_tts.py --text "Olá mundo" --voice rachel
    python elevenlabs_tts.py --input script.md --output-dir ./output
    python elevenlabs_tts.py --interactive
"""

import os
import sys
import argparse
import requests
from pathlib import Path

# Fix Windows encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# =============================================================================
# CARREGAR .ENV
# =============================================================================
def load_env():
    """Carrega variáveis de ambiente do arquivo .env"""
    env_path = Path.home() / ".alfredo" / ".env"
    if env_path.exists():
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()

load_env()

# =============================================================================
# ═════════════════════════════════════════════════════════════════════════
# CONFIGURAÇÕES DEFAULT
# ═════════════════════════════════════════════════════════════════════════
# =============================================================================

DEFAULT_CONFIG = {
    # API Key (obter em https://elevenlabs.io)
    # Lê de: 1) variável de ambiente ELEVENLABS_API_KEY
    #        2) arquivo ~/.alfredo/.env (auto-carregado)
    "api_key": os.getenv("ELEVENLABS_API_KEY", ""),

    # Modelo
    "model_id": "eleven_multilingual_v2",  # ou eleven_turbo_v2_5, eleven_turbo_v2

    # Formato de saída: codec_sample_rate_bitrate
    # mp3_44100_128, mp3_22050_32, pcm_16000, wav_44100
    "output_format": "mp3_44100_128",

    # Configurações de voz
    "voice_settings": {
        "stability": 0.5,        # 0 a 1 - maior = mais estável, menos expressivo
        "similarity_boost": 0.75, # 0 a 1 - maior = mais similar à voz original
        "style": 0.0,            # 0 a 1 - estilo exagerado (só multilingual v2)
        "use_speaker_boost": True # melhorar clareza de consonantes
    },

    # Idioma (ISO 639-1)
    # NOTA: Todos os vídeos do canal são em inglês (narração voiceover)
    "language_code": "en",  # pt, en, es, etc

    # Normalização de texto
    "apply_text_normalization": "auto",  # auto, on, off
}

# =============================================================================
# VOICES - Coleção de Voice IDs do ElevenLabs
# =============================================================================
# IDs obtidos de: https://elevenlabs.io/app/voice-library
# =============================================================================

VOICES = {
    # === PREMIUM VOICES ===
    "rachel": "21m00Tcm4TlvDq8ikWAM",      # Feminino, americano, suave
    "drew": "29vD33N1CtxCmqQRPOHJ",        # Masculino, americano, profundo
    "clyde": "2EiwWnXFnvU5JbP1N6B7",        # Masculino, americano, narrativa
    "mimi": "pFZP5JQG7iQjIQuC4Bku",         # Feminino, americano, expressivo
    "fin": "JBFqnCBsd6RMkjVDRZzb",          # Masculino, irlandês/escocês
    "declan": "kqVT88a5QfII1HNAEPTJ",       # Masculino, grave

    # === CLONED / CUSTOM VOICES ===
    # Adicione seus próprios voice IDs aqui
    "custom1": "YOUR_CUSTOM_VOICE_ID_1",
    "custom2": "YOUR_CUSTOM_VOICE_ID_2",

    # === PORTUGUESE / LATAM ===
    # Busque na Voice Library por "portuguese" ou "brazil"
    "pt_custom": "SEARCH_IN_VOICE_LIBRARY",
}

# Voice IDs alternativos comuns (documentação/community)
ALTERNATIVE_VOICES = {
    "adam": "AZnzlk1XvdvUeBnXmlld",         # Masculino, jovem
    "josh": "TxGEqnHWrfWFTfGW9XjX",         # Masculino, americano
    "arnold": "VR6AewLTigWG4xSOukaG",       # Masculino, maduro
    "sam": "yoZ06aMxZSU28sdfwRgq",          # Masculino, americano
    "patrick": "ODq5zmih8GrVes37Dizj",      # Masculino, irlandês
    "thomas": "GBv7InTcMAy67cIxQZqP",       # Masculino, britânico
    "charlie": "IKne3meq5aSn9XLyUdCD",      # Masculino, britânico
    "emily": "EXAVITQu4vr4xnSDxMaL",        # Feminino, americano
    "katie": "MF3mGyEYCl7XYWbV9V6O",        # Feminino, americano
    "grace": "Ow45ixWBpJC9bdxgVC7w",        # Feminino, americano
    "matthew": "Yko7PKHZNXosIqXrv0sj",      # Masculino, americano
    "jose": "V/fRB8u7FGLe7jpXhZ3b",         # Masculino, português (exemplo)
    "luiz": "YOUR_PORTUGUESE_VOICE_ID",     # Adicionar ID real
}

# Merge todos os voices
ALL_VOICES = {**VOICES, **ALTERNATIVE_VOICES}

# =============================================================================
# MODELOS DISPONÍVEIS
# =============================================================================
MODELS = {
    "eleven_multilingual_v2": "Melhor qualidade, multilingual (recomendado)",
    "eleven_turbo_v2_5": "Baixa latência, bom custo-benefício",
    "eleven_turbo_v2": "Versão turbo anterior",
    "eleven_monolingual_v1": "Apenas inglês, muito rápido",
}

# =============================================================================
# FORMATOS DE SAÍDA
# =============================================================================
OUTPUT_FORMATS = {
    "mp3_44100_128": "MP3 44.1kHz 128kbps (padrão)",
    "mp3_44100_192": "MP3 44.1kHz 192kbps (alta qualidade, requer Creator+)",
    "mp3_22050_32": "MP3 22.05kHz 32kbps (baixo bitrate)",
    "pcm_16000": "PCM 16kHz",
    "pcm_22050": "PCM 22.05kHz",
    "pcm_44100": "PCM 44.1kHz (requer Pro+)",
    "wav_44100": "WAV 44.1kHz (requer Pro+)",
}


# =============================================================================
# ═════════════════════════════════════════════════════════════════════════
# FUNÇÕES PRINCIPAIS
# ═════════════════════════════════════════════════════════════════════════
# =============================================================================

def validate_api_key(api_key: str) -> bool:
    """Valida se a API key está configurada."""
    if not api_key or api_key == "YOUR_API_KEY_HERE":
        print("❌ Erro: API Key não configurada!")
        print("   Defina a variável de ambiente ELEVENLABS_API_KEY")
        print("   Ou altere DEFAULT_CONFIG['api_key'] no script")
        return False
    return True


def list_voices():
    """Lista todas as vozes disponíveis."""
    print("\n🎙️  VOZES DISPONÍVEIS:\n")
    print("   NOME      | VOICE ID")
    print("   " + "-" * 60)
    for name, voice_id in sorted(ALL_VOICES.items()):
        if not voice_id.startswith("YOUR_") and voice_id != "SEARCH_IN_VOICE_LIBRARY":
            print(f"   {name:12} | {voice_id}")


def list_models():
    """Lista todos os modelos disponíveis."""
    print("\n🤖 MODELOS DISPONÍVEIS:\n")
    for model_id, description in MODELS.items():
        print(f"   {model_id:25} - {description}")


def list_formats():
    """Lista todos os formatos de saída."""
    print("\n📁 FORMATOS DE SAÍDA:\n")
    for format_id, description in OUTPUT_FORMATS.items():
        print(f"   {format_id:20} - {description}")


def generate_speech(
    text: str,
    voice_id: str,
    api_key: str,
    model_id: str = None,
    output_format: str = None,
    stability: float = None,
    similarity_boost: float = None,
    style: float = None,
    use_speaker_boost: bool = None,
    language_code: str = None,
    seed: int = None,
    apply_text_normalization: str = None,
) -> bytes:
    """
    Gera áudio usando ElevenLabs API.

    Args:
        text: Texto para converter em áudio
        voice_id: ID da voz a ser usada
        api_key: ElevenLabs API key
        model_id: ID do modelo (default: eleven_multilingual_v2)
        output_format: Formato de saída (default: mp3_44100_128)
        stability: Estabilidade da voz (0-1)
        similarity_boost: Similaridade com voz original (0-1)
        style: Exagero de estilo (0-1, só multilingual v2)
        use_speaker_boost: Boost de clareza
        language_code: Código ISO do idioma
        seed: Seed para geração determinística
        apply_text_normalization: Normalização de texto (auto/on/off)

    Returns:
        bytes: Conteúdo do áudio gerado
    """
    # Aplica defaults
    model_id = model_id or DEFAULT_CONFIG["model_id"]
    output_format = output_format or DEFAULT_CONFIG["output_format"]
    language_code = language_code or DEFAULT_CONFIG["language_code"]
    apply_text_normalization = apply_text_normalization or DEFAULT_CONFIG["apply_text_normalization"]

    # Configurações de voz
    settings = DEFAULT_CONFIG["voice_settings"].copy()
    if stability is not None:
        settings["stability"] = stability
    if similarity_boost is not None:
        settings["similarity_boost"] = similarity_boost
    if style is not None:
        settings["style"] = style
    if use_speaker_boost is not None:
        settings["use_speaker_boost"] = use_speaker_boost

    # URL da API
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    # Headers
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    # Body
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": settings,
        "output_format": output_format,
    }

    # Opcionais
    if language_code:
        payload["language_code"] = language_code
    if seed is not None:
        payload["seed"] = seed
    if apply_text_normalization:
        payload["apply_text_normalization"] = apply_text_normalization

    # Request
    response = requests.post(url, json=payload, headers=headers)

    if response.status_code == 200:
        return response.content
    else:
        raise Exception(f"API Error {response.status_code}: {response.text}")


def save_audio(content: bytes, output_path: str):
    """Salva o conteúdo de áudio em um arquivo."""
    with open(output_path, "wb") as f:
        f.write(content)
    return os.path.getsize(output_path)


def read_text_file(input_path: str) -> str:
    """Lê texto de um arquivo."""
    with open(input_path, "r", encoding="utf-8") as f:
        return f.read()


def interactive_mode():
    """Modo interativo para geração de áudio."""
    print("\n" + "="*60)
    print("  ELEVENLABS TTS - MODO INTERATIVO")
    print("="*60 + "\n")

    # API Key
    api_key = input("API Key (ou ENTER para usar variável de ambiente): ").strip()
    if not api_key:
        api_key = DEFAULT_CONFIG["api_key"]

    if not validate_api_key(api_key):
        return

    # Texto
    print("\nOpções de entrada:")
    print("  1. Digitar texto")
    print("  2. Ler de arquivo")
    choice = input("Escolha (1/2): ").strip()

    if choice == "2":
        input_file = input("Caminho do arquivo: ").strip()
        try:
            text = read_text_file(input_file)
            print(f"✓ Lido {len(text)} caracteres de {input_file}")
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            return
    else:
        print("\nDigite o texto (Ctrl+D ou Ctrl+Z para finalizar):")
        text = sys.stdin.read()

    if not text.strip():
        print("❌ Texto vazio!")
        return

    # Voz
    print("\nVozes populares: rachel, drew, clyde, mimi, fin, emily, katie")
    print("Use --list-voices para ver todas")
    voice_name = input("Nome da voz (default: rachel): ").strip() or "rachel"

    if voice_name in ALL_VOICES:
        voice_id = ALL_VOICES[voice_name]
    else:
        print(f"⚠️  Voz '{voice_name}' não encontrada, usando como ID direto")
        voice_id = voice_name

    # Modelo
    model_id = input(f"Modelo (default: {DEFAULT_CONFIG['model_id']}): ").strip() or DEFAULT_CONFIG["model_id"]

    # Saída
    output_file = input("Arquivo de saída (default: output.mp3): ").strip() or "output.mp3"

    # Gerar
    try:
        print(f"\n🎙️  Gerando áudio...")
        audio = generate_speech(text, voice_id, api_key, model_id=model_id)
        size = save_audio(audio, output_file)
        print(f"✓ Áudio salvo: {output_file} ({size:,} bytes)")
    except Exception as e:
        print(f"❌ Erro: {e}")


# =============================================================================
# ═════════════════════════════════════════════════════════════════════════
# MAIN / CLI
# ═════════════════════════════════════════════════════════════════════════
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="ElevenLabs Text-to-Speech Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --text "Olá mundo" --voice rachel
  %(prog)s --input script.md --output audio.mp3
  %(prog)s --input script.md --output-dir ./output
  %(prog)s --text "Hello" --voice emily --model eleven_turbo_v2_5
  %(prog)s --list-voices
  %(prog)s --interactive

Vozes: rachel, drew, clyde, mimi, fin, emily, katie, josh, adam, ...

SSML suportado: <break time="1s" />, <emphasis>, etc.
        """
    )

    # Argumentos principais
    parser.add_argument("--text", "-t", help="Texto para converter em áudio")
    parser.add_argument("--input", "-i", help="Arquivo com texto de entrada (.txt, .md, etc)")
    parser.add_argument("--output", "-o", default="output.mp3", help="Arquivo de saída (default: output.mp3)")
    parser.add_argument("--output-dir", "-d", help="Diretório de saída (nome do arquivo será derivado do input)")
    parser.add_argument("--voice", "-v", default="rachel", help="Nome da voz ou voice ID (default: rachel)")

    # Configurações
    parser.add_argument("--model", "-m", help="Modelo (default: eleven_multilingual_v2)")
    parser.add_argument("--format", "-f", help="Formato de saída (default: mp3_44100_128)")
    parser.add_argument("--language", "-l", help="Código do idioma (default: pt)")

    # Voice settings
    parser.add_argument("--stability", type=float, help="Estabilidade 0-1 (default: 0.5)")
    parser.add_argument("--similarity", type=float, help="Similaridade 0-1 (default: 0.75)")
    parser.add_argument("--style", type=float, help="Estilo 0-1 (default: 0.0)")
    parser.add_argument("--no-boost", action="store_true", help="Desabilitar speaker boost")

    # Outros
    parser.add_argument("--seed", type=int, help="Seed para geração determinística")
    parser.add_argument("--normalization", choices=["auto", "on", "off"], help="Normalização de texto")

    # Info
    parser.add_argument("--list-voices", action="store_true", help="Listar vozes disponíveis")
    parser.add_argument("--list-models", action="store_true", help="Listar modelos disponíveis")
    parser.add_argument("--list-formats", action="store_true", help="Listar formatos de saída")
    parser.add_argument("--interactive", action="store_true", help="Modo interativo")

    # API Key
    parser.add_argument("--api-key", help="ElevenLabs API Key (sobrescreve variável de ambiente)")

    args = parser.parse_args()

    # Listagens
    if args.list_voices:
        list_voices()
        return
    if args.list_models:
        list_models()
        return
    if args.list_formats:
        list_formats()
        return

    # Modo interativo
    if args.interactive:
        interactive_mode()
        return

    # Validação de entrada
    if not args.text and not args.input:
        parser.error("Especifique --text ou --input (ou use --interactive)")

    # API Key
    api_key = args.api_key or DEFAULT_CONFIG["api_key"]
    if not validate_api_key(api_key):
        sys.exit(1)

    # Texto
    if args.input:
        try:
            text = read_text_file(args.input)
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
            sys.exit(1)
    else:
        text = args.text

    # Voice ID
    voice_id = ALL_VOICES.get(args.voice, args.voice)

    # Output path
    output_path = args.output
    if args.output_dir:
        # Criar diretório se não existir
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)
        # Derivar nome do arquivo de input
        if args.input:
            input_name = Path(args.input).stem
            output_path = str(Path(args.output_dir) / f"{input_name}.mp3")
        else:
            output_path = str(Path(args.output_dir) / "output.mp3")

    # Gerar
    try:
        print(f"🎙️  Gerando áudio com voz '{args.voice}'...")
        audio = generate_speech(
            text=text,
            voice_id=voice_id,
            api_key=api_key,
            model_id=args.model,
            output_format=args.format,
            stability=args.stability,
            similarity_boost=args.similarity,
            style=args.style,
            use_speaker_boost=not args.no_boost,
            language_code=args.language,
            seed=args.seed,
            apply_text_normalization=args.normalization,
        )
        size = save_audio(audio, output_path)
        print(f"✓ Salvo: {output_path} ({size:,} bytes)")
    except Exception as e:
        print(f"❌ Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
