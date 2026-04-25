#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utilitários para integração com ComfyUI
"""

import json
import requests
import asyncio
import websockets
from pathlib import Path
import time


COMFYUI_SERVER = "http://127.0.0.1:8188"
WS_SERVER = "ws://127.0.0.1:8188/ws"


def check_server():
    """Verifica se ComfyUI está rodando"""
    try:
        response = requests.get(f"{COMFYUI_SERVER}/system_stats", timeout=2)
        return response.status_code == 200
    except:
        return False


def load_workflow(workflow_path):
    """Carrega workflow JSON"""
    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def run_workflow(workflow, workflow_name="workflow", client_id="python_client", save_outputs=True, custom_output_dir=None):
    """Executa workflow no ComfyUI e monitora via WebSocket

    Args:
        workflow: Dicionário do workflow ComfyUI
        workflow_name: Nome do workflow para organização
        client_id: ID do cliente para ComfyUI
        save_outputs: Se True, baixa e salva os arquivos gerados
        custom_output_dir: Diretório customizado para salvar arquivos (Path ou str)
    """

    # Enviar workflow
    prompt_data = {
        "prompt": workflow,
        "client_id": client_id
    }

    response = requests.post(f"{COMFYUI_SERVER}/prompt", json=prompt_data)
    result = response.json()

    if "prompt_id" not in result:
        raise Exception(f"Erro ao enviar workflow: {result}")

    prompt_id = result["prompt_id"]
    print(f"📝 Workflow enviado: {prompt_id}")

    # Monitorar via WebSocket
    print("⏳ Aguardando processamento...")

    async with websockets.connect(WS_SERVER) as websocket:
        while True:
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=30.0)
                data = json.loads(message)

                # Verificar tipo de mensagem
                if data.get("type") == "executing":
                    if data.get("data", {}).get("node") is None:
                        print("✅ Processamento concluído!")
                        break

                # Mostrar progresso
                elif data.get("type") == "progress":
                    progress_data = data.get("data", {})
                    value = progress_data.get("value", 0)
                    max_value = progress_data.get("max", 100)
                    print(f"🔄 Progresso: {value}/{max_value}")

                # Mostrar execução de nós
                elif data.get("type") == "execution_cached":
                    print("💾 Usando cache")

                elif data.get("type") == "executing":
                    node_id = data.get("data", {}).get("node")
                    if node_id:
                        print(f"⚙️  Executando nó: {node_id}")

            except asyncio.TimeoutError:
                print("⚠️  Timeout na WebSocket, verificando status...")
                break
            except Exception as e:
                print(f"⚠️  Erro no WebSocket: {e}")
                break

    # Obter resultados
    print("📊 Buscando resultados...")
    history_response = requests.get(f"{COMFYUI_SERVER}/history/{prompt_id}")
    history = history_response.json()

    saved_files = []

    if prompt_id in history:
        outputs = history[prompt_id].get("outputs", {})

        for node_id, node_output in outputs.items():
            # Processar imagens
            if "images" in node_output:
                for image_info in node_output["images"]:
                    filename = image_info["filename"]
                    subfolder = image_info.get("subfolder", "")
                    image_type = image_info.get("type", "output")

                    # Baixar/salvar imagem
                    if save_outputs:
                        params = {
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": image_type
                        }

                        response = requests.get(f"{COMFYUI_SERVER}/view", params=params)

                        # Criar diretório de saída (customizado ou padrão)
                        if custom_output_dir:
                            output_dir = Path(custom_output_dir)
                        else:
                            output_dir = Path("outputs") / workflow_name

                        output_dir.mkdir(parents=True, exist_ok=True)

                        output_path = output_dir / filename
                        with open(output_path, 'wb') as f:
                            f.write(response.content)

                        saved_files.append(str(output_path))
                        print(f"💾 Salvo: {output_path}")
                    else:
                        saved_files.append(filename)

            # Processar áudio
            if "audio" in node_output:
                for audio_info in node_output["audio"]:
                    filename = audio_info["filename"]
                    subfolder = audio_info.get("subfolder", "")
                    audio_type = audio_info.get("type", "output")

                    # Baixar/salvar áudio
                    if save_outputs:
                        params = {
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": audio_type
                        }

                        response = requests.get(f"{COMFYUI_SERVER}/view", params=params)

                        # Criar diretório de saída (customizado ou padrão)
                        if custom_output_dir:
                            output_dir = Path(custom_output_dir)
                        else:
                            output_dir = Path("outputs") / workflow_name

                        output_dir.mkdir(parents=True, exist_ok=True)

                        output_path = output_dir / filename
                        with open(output_path, 'wb') as f:
                            f.write(response.content)

                        saved_files.append(str(output_path))
                        print(f"💾 Salvo: {output_path}")
                    else:
                        saved_files.append(filename)

    return saved_files


def get_workflow_params(workflow_path):
    """Extrai parâmetros modificáveis de um workflow"""
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    params = {}

    for node_id, node in workflow.items():
        if isinstance(node, dict) and "inputs" in node:
            for key, value in node["inputs"].items():
                # Não incluir links (listas)
                if not isinstance(value, list):
                    if node_id not in params:
                        params[node_id] = {}
                    params[node_id][key] = value

    return params
