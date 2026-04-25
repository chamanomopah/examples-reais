"""
ComfyUI - Qwen TTS Custom Voice Automation
Script para usar vozes salvas do Qwen TTS
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Adicionar diretório parent ao path para importar utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_workflow, run_workflow, check_server
)


def prepare_qwen_custom_workflow(
    text: str,
    speaker: str = "Serena",
    instruct: str = "",
    model_choice: str = "0.6B",
    language: str = "English",
    device: str = "auto",
    precision: str = "bf16",
    seed: int = 0,
    max_new_tokens: int = 2048,
    top_p: float = 0.8,
    top_k: int = 20,
    temperature: float = 1.2,
    repetition_penalty: float = 1.05
) -> dict:
    """
    Prepara o workflow Qwen TTS para vozes salvas.
    
    Args:
        text: Texto para converter
        speaker: Nome do speaker predefinido
        instruct: Instruções de estilo da voz
        model_choice: Tamanho do modelo ('1.7B' ou '0.6B')
        language: Idioma
        device: Dispositivo ('auto', 'cuda', 'cpu')
        precision: Precisão ('bf16', 'fp16', 'fp32')
        seed: Semente (0 para random)
        max_new_tokens: Máximo de tokens
        top_p: Top-p para sampling
        top_k: Top-k para sampling
        temperature: Temperatura para sampling
        repetition_penalty: Penalidade de repetição
        
    Returns:
        Dicionário do workflow pronto para enviar
    """
    # Carregar workflow base
    workflow = load_workflow("WORKFLOW - QWEN TTS.json")
    
    # Ativar nó FB_Qwen3TTSCustomVoice (id 39)
    if "39" in workflow:
        workflow["39"]["mode"] = 0
        workflow["39"]["inputs"] = {
            "text": text,
            "speaker": speaker,
            "model_choice": model_choice,
            "device": device,
            "precision": precision,
            "language": language,
            "seed": seed,
            "instruct": instruct,
            "max_new_tokens": max_new_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "temperature": temperature,
            "repetition_penalty": repetition_penalty,
            "attention": "auto",
            "unload_model_after_generate": False,
            "custom_model_path": "",
            "custom_speaker_name": ""
        }
    
    # Desativar outros nós
    if "40" in workflow:
        workflow["40"]["mode"] = 4  # Bypass
    if "38" in workflow:
        workflow["38"]["mode"] = 4  # Bypass
    if "24" in workflow:
        workflow["24"]["mode"] = 4  # Bypass
    
    # Ativar nó SaveAudio (id 42)
    if "42" in workflow:
        workflow["42"]["mode"] = 0
    
    return workflow


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Gera áudio usando vozes salvas do Qwen TTS"
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
        default="Serena",
        help="Nome do speaker predefinido (padrão: Serena)"
    )
    parser.add_argument(
        "--instruct",
        type=str,
        default="",
        help="Instruções de estilo da voz"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="0.6B",
        choices=["1.7B", "0.6B"],
        help="Tamanho do modelo (padrão: 0.6B)"
    )
    parser.add_argument(
        "--language", "-l",
        type=str,
        default="Portuguese",
        help="Idioma (padrão: Portuguese)"
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Semente (0 para random, padrão: 0)"
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.2,
        help="Temperatura (padrão: 1.2)"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="qwen_tts_custom_client",
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
    print(f"\nPreparando workflow Qwen TTS Custom:")
    print(f"  Texto: {args.text[:100]}{'...' if len(args.text) > 100 else ''}")
    print(f"  Speaker: {args.speaker}")
    print(f"  Modelo: {args.model}")
    print(f"  Idioma: {args.language}")
    if args.instruct:
        print(f"  Instruções: {args.instruct[:100]}{'...' if len(args.instruct) > 100 else ''}")
    
    workflow = prepare_qwen_custom_workflow(
        text=args.text,
        speaker=args.speaker,
        instruct=args.instruct,
        model_choice=args.model,
        language=args.language,
        seed=args.seed,
        temperature=args.temperature
    )
    
    # Executar workflow
    try:
        output_files = await run_workflow(
            workflow=workflow,
            workflow_name="qwen_tts_custom",
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
