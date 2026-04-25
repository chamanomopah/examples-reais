#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
EXEMPLO 1 - KOKORO TTS: Texto Simples em Português

Descrição: Gera um áudio a partir de um texto simples em português usando 
          WebSocket para monitoramento em tempo real e download automático.

Requisitos:
    - ComfyUI rodando em http://127.0.0.1:8188
    - ComfyUI-Kokoro instalado
    - Python 3.8+ com bibliotecas: requests, websockets

Uso:
    python exemplo1_python_simple.py

Saída: Áudio salvo em ComfyUI/user/outputs/YYYY-MM-DD/kokoro_tts/exemplo1_simples/
"""

import asyncio
import sys
import io
from pathlib import Path

# Configurar stdout para UTF-8 (necessário no Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Adicionar diretório scripts/comfyui ao path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts" / "comfyui"))

from utils import (
    load_workflow,
    run_workflow,
    check_server,
    get_output_dir
)


def modify_workflow_for_text(workflow: dict, text: str, speaker: str = "am_onyx", 
                            speed: float = 1.0, lang: str = "Portuguese") -> dict:
    """
    Modifica o workflow KOKORO para usar um texto específico.
    
    Args:
        workflow: Workflow JSON carregado
        text: Texto para converter em áudio
        speaker: Nome do speaker (ex: 'am_onyx', 'am_michael', etc)
        speed: Velocidade de fala (1.0 = normal)
        lang: Idioma do texto
        
    Returns:
        Workflow modificado
    """
    # Modificar node 11 - KokoroGenerator
    if "11" in workflow and "inputs" in workflow["11"]:
        workflow["11"]["inputs"]["text"] = text
        workflow["11"]["inputs"]["speed"] = speed
        workflow["11"]["inputs"]["lang"] = lang
    
    # Modificar node 10 - KokoroSpeaker
    if "10" in workflow and "inputs" in workflow["10"]:
        workflow["10"]["inputs"]["speaker_name"] = speaker
    
    return workflow


async def main():
    """Função principal do exemplo."""
    
    print("=" * 60)
    print("KOKORO TTS - Exemplo 1: Texto Simples em Português")
    print("=" * 60)
    print()
    
    # 1. Verificar se ComfyUI está rodando
    print("1. Verificando conexão com ComfyUI...")
    if not check_server():
        print("✗ Erro: ComfyUI não está rodando em http://127.0.0.1:8188")
        print("  Inicie o ComfyUI antes de executar este script.")
        return
    
    print("✓ ComfyUI conectado com sucesso!")
    print()
    
    # 2. Carregar workflow base
    print("2. Carregando workflow KOKORO...")
    try:
        workflow = load_workflow("WORKFLOW - KOKORO.json")
        print("✓ Workflow carregado!")
    except FileNotFoundError as e:
        print(f"✗ Erro: {e}")
        return
    
    print()
    
    # 3. Configurar parâmetros
    print("3. Configurando parâmetros...")
    
    # Texto em português
    texto = "Olá, mundo! Este é um teste de automação do Kokoro TTS."
    
    # Speaker (voz)
    speaker = "am_onyx"  # Opções: am_onyx, am_michael, am_adam, am_sam, etc
    
    # Velocidade (1.0 = normal, 0.5 = mais lento, 2.0 = mais rápido)
    speed = 1.0
    
    # Idioma
    lang = "Portuguese"  # Opções: English, Portuguese, Spanish, etc
    
    print(f"  Texto: {texto}")
    print(f"  Speaker: {speaker}")
    print(f"  Velocidade: {speed}")
    print(f"  Idioma: {lang}")
    print()
    
    # 4. Modificar workflow
    print("4. Modificando workflow...")
    workflow = modify_workflow_for_text(workflow, texto, speaker, speed, lang)
    print("✓ Workflow modificado!")
    print()
    
    # 5. Executar workflow
    print("5. Executando workflow...")
    print("-" * 60)
    
    try:
        saved_files = await run_workflow(
            workflow=workflow,
            workflow_name="kokoro_tts/exemplo1_simples",
            client_id="python_kokoro_exemplo1",
            save_outputs=True
        )
        
        print("-" * 60)
        print()
        
        # 6. Resultados
        if saved_files:
            print("6. RESULTADO FINAL:")
            print()
            print("✓ Sucesso! Áudio gerado:")
            for file_path in saved_files:
                size_mb = file_path.stat().st_size / (1024 * 1024)
                print(f"  📄 {file_path.name}")
                print(f"     Caminho: {file_path}")
                print(f"     Tamanho: {size_mb:.2f} MB")
        else:
            print("⚠ Nenhum arquivo foi salvo.")
            print("  Verifique o ComfyUI para mais detalhes.")
        
    except Exception as e:
        print()
        print(f"✗ Erro durante execução: {e}")
        print("  Verifique se todos os nós do workflow estão corretos.")
        return
    
    print()
    print("=" * 60)
    print("Fim do Exemplo 1")
    print("=" * 60)


if __name__ == "__main__":
    # Executar função assíncrona
    asyncio.run(main())
