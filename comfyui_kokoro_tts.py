"""
ComfyUI - Kokoro TTS Automation
Script para gerar áudio usando o modelo Kokoro TTS
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Adicionar diretório parent ao path para importar utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_workflow, run_workflow, check_server,
    get_output_dir
)


def prepare_kokoro_workflow(
    text: str,
    speaker: str = "am_onyx",
    speed: float = 1.0,
    lang: str = "English"
) -> dict:
    """
    Prepara o workflow Kokoro TTS com os parâmetros fornecidos.
    
    Args:
        text: Texto para converter em áudio
        speaker: Nome do speaker (ex: 'am_onyx', 'am_michael', etc)
        speed: Velocidade da fala (1.0 = normal)
        lang: Idioma ('English', 'Portuguese', etc)
        
    Returns:
        Dicionário do workflow pronto para enviar
    """
    # Carregar workflow base
    workflow = load_workflow("WORKFLOW - KOKORO.json")
    
    # Atualizar parâmetros do nó KokoroGenerator (id 11)
    if "11" in workflow and "inputs" in workflow["11"]:
        workflow["11"]["inputs"]["text"] = text
        workflow["11"]["inputs"]["speed"] = speed
        workflow["11"]["inputs"]["lang"] = lang
    
    # Atualizar speaker no nó KokoroSpeaker (id 10)
    if "10" in workflow and "inputs" in workflow["10"]:
        workflow["10"]["inputs"]["speaker_name"] = speaker
    
    return workflow


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Gera áudio usando Kokoro TTS no ComfyUI"
    )
    parser.add_argument(
        "--text", "-t",
        type=str,
        required=True,
        help="Texto para converter em áudio"
    )
    parser.add_argument(
        "--speaker", "-s",
        type=str,
        default="am_onyx",
        help="Nome do speaker (padrão: am_onyx)"
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=1.0,
        help="Velocidade da fala (padrão: 1.0)"
    )
    parser.add_argument(
        "--lang", "-l",
        type=str,
        default="Portuguese",
        help="Idioma (padrão: Portuguese)"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="kokoro_tts_client",
        help="ID do cliente para ComfyUI"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Não salvar o arquivo de áudio"
    )
    
    args = parser.parse_args()
    
    # Verificar servidor
    print("Verificando servidor ComfyUI...")
    if not check_server():
        print("ERRO: Servidor ComfyUI não está rodando em http://127.0.0.1:8188")
        print("Inicie o ComfyUI e tente novamente.")
        sys.exit(1)
    print("Servidor OK!")
    
    # Preparar workflow
    print(f"\nPreparando workflow Kokoro TTS:")
    print(f"  Texto: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
    print(f"  Speaker: {args.speaker}")
    print(f"  Velocidade: {args.speed}")
    print(f"  Idioma: {args.lang}")
    
    workflow = prepare_kokoro_workflow(
        text=args.text,
        speaker=args.speaker,
        speed=args.speed,
        lang=args.lang
    )
    
    # Executar workflow
    try:
        output_files = await run_workflow(
            workflow=workflow,
            workflow_name="kokoro_tts",
            client_id=args.client_id,
            save_outputs=not args.no_save
        )
        
        if output_files:
            print(f"\n✓ Sucesso! {len(output_files)} arquivo(s) gerado(s):")
            for f in output_files:
                print(f"  - {f}")
        else:
            print("\n✓ Workflow executado (sem outputs salvos)")
    
    except Exception as e:
        print(f"\n✗ Erro: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
