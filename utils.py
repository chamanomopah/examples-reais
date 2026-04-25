#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utils módulo para scripts ComfyUI
Funções básicas para carregar workflows e executar no ComfyUI server
"""

import json
import requests
import websockets
import asyncio
from pathlib import Path
from typing import Optional


COMFYUI_SERVER = "http://127.0.0.1:8188"
WEBSOCKET_URL = "ws://127.0.0.1:8188/ws"
WORKFLOWS_DIR = r"C:\Users\JOSE\Downloads\confyui\ComfyUI_windows_portable\ComfyUI\user\default\workflows"


def check_server(server_url: str = COMFYUI_SERVER) -> bool:
    """Verifica se o ComfyUI server está rodando."""
    try:
        response = requests.get(f"{server_url}/system_stats", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def load_workflow(filename: str, directory: str = None) -> dict:
    """Carrega um workflow JSON do diretório especificado."""
    if directory is None:
        directory = WORKFLOWS_DIR

    workflow_path = Path(directory) / filename

    if not workflow_path.exists():
        # Tentar no diretório atual
        workflow_path = Path(filename)

    if not workflow_path.exists():
        raise FileNotFoundError(f"Workflow não encontrado: {filename}\nProcurado em: {directory}")

    with open(workflow_path, 'r', encoding='utf-8') as f:
        return json.load(f)


async def run_workflow(
    workflow: dict,
    workflow_name: str = "workflow",
    client_id: str = "python_client",
    server_url: str = COMFYUI_SERVER,
    websocket_url: str = WEBSOCKET_URL,
    save_outputs: bool = False
) -> list:
    """
    Executa um workflow no ComfyUI via WebSocket.

    Returns:
        Lista de Path objects para os arquivos salvos
    """
    import aiohttp

    saved_files = []

    # Preparar o prompt
    prompt = workflow
    print(f"  DEBUG: Enviando workflow com {len(prompt)} nós para ComfyUI...")

    # Conectar via WebSocket
    async with websockets.connect(websocket_url) as websocket:
        # Enviar prompt
        data = {
            "prompt": prompt,
            "client_id": client_id
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{server_url}/prompt", json=data) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erro ao enviar prompt: {response.status}\nDetalhes: {error_text}")

                result = await response.json()
                prompt_id = result.get("prompt_id")

                if not prompt_id:
                    raise Exception("Não recebeu prompt_id")

                # Escutar mensagens
                while True:
                    try:
                        message = await websocket.recv()

                        if isinstance(message, str):
                            msg_data = json.loads(message)
                        else:
                            continue

                        msg_type = msg_data.get("type")

                        if msg_type == "executing":
                            # Execução em andamento
                            node_id = msg_data.get("data", {}).get("node")

                            if node_id is None:
                                # Execução finalizada
                                break

                        elif msg_type == "execution_cached":
                            # Nó executado do cache
                            pass

                        elif msg_type == "progress":
                            # Progresso
                            value = msg_data.get("data", {}).get("value", 0)
                            max_value = msg_data.get("data", {}).get("max", 1)
                            if max_value > 0:
                                progress = (value / max_value) * 100
                                print(f"  Progresso: {progress:.1f}%", end="\r")

                        elif msg_type == "executed":
                            # Nó executado
                            node_id = msg_data.get("data", {}).get("node")
                            output = msg_data.get("data", {}).get("output")

                            if output and "images" in output:
                                for img in output["images"]:
                                    filename = img.get("filename")
                                    subfolder = img.get("subfolder", "")
                                    folder_type = img.get("type", "output")

                                    if filename:
                                        print(f"\n  ✓ Imagem gerada: {filename}")

                                        if save_outputs:
                                            file_path = await download_image(
                                                filename,
                                                subfolder,
                                                folder_type,
                                                server_url,
                                                session
                                            )
                                            if file_path:
                                                saved_files.append(file_path)

                    except websockets.exceptions.ConnectionClosed:
                        break

    return saved_files


async def download_image(
    filename: str,
    subfolder: str,
    folder_type: str,
    server_url: str = COMFYUI_SERVER,
    session = None
) -> Optional[Path]:
    """Faz download de uma imagem gerada pelo ComfyUI."""
    import aiohttp

    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": folder_type
    }

    if session is None:
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{server_url}/view", params=params) as response:
                if response.status == 200:
                    # Criar diretório de saída
                    output_dir = Path("outputs") / workflow_name
                    output_dir.mkdir(parents=True, exist_ok=True)

                    file_path = output_dir / filename

                    # Salvar arquivo
                    with open(file_path, 'wb') as f:
                        f.write(await response.read())

                    return file_path
    else:
        async with session.get(f"{server_url}/view", params=params) as response:
            if response.status == 200:
                # Criar diretório de saída
                output_dir = Path("outputs") / workflow_name
                output_dir.mkdir(parents=True, exist_ok=True)

                file_path = output_dir / filename

                # Salvar arquivo
                with open(file_path, 'wb') as f:
                    f.write(await response.read())

                return file_path

    return None
