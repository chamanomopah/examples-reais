"""
ComfyUI - Qwen TTS Voice Clone Automation
Script para clonar voz usando o modelo Qwen TTS
"""

import asyncio
import sys
import argparse
from pathlib import Path

# Adicionar diretório parent ao path para importar utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_workflow, run_workflow, check_server,
    upload_audio
)


def prepare_qwen_clone_workflow(
    ref_audio_path: str,
    ref_audio_name: str,
    target_text: str,
    ref_text: str = "",
    model_choice: str = "1.7B",
    language: str = "Portuguese",
    device: str = "auto",
    precision: str = "bf16",
    seed: int = 0,
    max_new_tokens: int = 2048,
    top_p: float = 0.8,
    top_k: int = 20,
    temperature: float = 1.0,
    repetition_penalty: float = 1.05
) -> dict:
    """
    Prepara o workflow Qwen TTS para clonagem de voz.
    
    Args:
        ref_audio_path: Caminho do áudio de referência
        ref_audio_name: Nome do arquivo após upload
        target_text: Texto para falar com a voz clonada
        ref_text: Texto correspondente ao áudio de referência
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
    
    # Configurar nó de LoadAudio (id 24)
    if "24" in workflow and "inputs" in workflow["24"]:
        workflow["24"]["inputs"]["audio"] = ref_audio_name
        workflow["24"]["mode"] = 0  # Ativar este nó
    
    # Ativar nó FB_Qwen3TTSVoiceClone (id 40) e desativar outros
    if "40" in workflow:
        workflow["40"]["mode"] = 0
        workflow["40"]["inputs"] = {
            "ref_audio": ref_audio_name,
            "voice_clone_prompt": "",
            "target_text": target_text,
            "model_choice": model_choice,
            "device": device,
            "precision": precision,
            "language": language,
            "ref_text": ref_text,
            "seed": seed,
            "max_new_tokens": max_new_tokens,
            "top_p": top_p,
            "top_k": top_k,
            "temperature": temperature,
            "repetition_penalty": repetition_penalty,
            "x_vector_only": True,
            "attention": "auto",
            "unload_model_after_generate": False,
            "custom_model_path": ""
        }
    
    # Desativar outros nós de TTS
    if "39" in workflow:
        workflow["39"]["mode"] = 4  # Bypass
    if "38" in workflow:
        workflow["38"]["mode"] = 4  # Bypass
    
    # Ativar nó SaveAudio (id 42)
    if "42" in workflow:
        workflow["42"]["mode"] = 0
    
    return workflow


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Clona voz usando Qwen TTS no ComfyUI"
    )
    parser.add_argument(
        "--ref-audio", "-r",
        type=str,
        required=True,
        help="Caminho do áudio de referência para clonagem"
    )
    parser.add_argument(
        "--target-text", "-t",
        type=str,
        required=True,
        help="Texto para falar com a voz clonada"
    )
    parser.add_argument(
        "--ref-text",
        type=str,
        default="",
        help="Texto correspondente ao áudio de referência"
    )
    parser.add_argument(
        "--model",
        type=str,
        default="1.7B",
        choices=["1.7B", "0.6B"],
        help="Tamanho do modelo (padrão: 1.7B)"
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
        default=1.0,
        help="Temperatura (padrão: 1.0)"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="qwen_tts_clone_client",
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
    
    # Upload do áudio de referência
    print(f"\nFazendo upload do áudio de referência: {args.ref_audio}")
    try:
        upload_result = upload_audio(args.ref_audio)
        ref_audio_name = upload_result.get("name", Path(args.ref_audio).name)
        print(f"Áudio carregado como: {ref_audio_name}")
    except Exception as e:
        print(f"ERRO ao fazer upload: {e}")
        sys.exit(1)
    
    # Preparar workflow
    print(f"\nPreparando workflow Qwen TTS Clone:")
    print(f"  Texto alvo: {args.target_text[:100]}{'...' if len(args.target_text) > 100 else ''}")
    print(f"  Modelo: {args.model}")
    print(f"  Idioma: {args.language}")
    
    workflow = prepare_qwen_clone_workflow(
        ref_audio_path=args.ref_audio,
        ref_audio_name=ref_audio_name,
        target_text=args.target_text,
        ref_text=args.ref_text,
        model_choice=args.model,
        language=args.language,
        seed=args.seed,
        temperature=args.temperature
    )
    
    # Executar workflow
    try:
        output_files = await run_workflow(
            workflow=workflow,
            workflow_name="qwen_tts_clone",
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
