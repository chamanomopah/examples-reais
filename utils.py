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


async def run_workflow(workflow, workflow_name="workflow", client_id="python_client", save_outputs=True, custom_output_dir=None, filename_prefix=None):
    """Executa workflow no ComfyUI e monitora via polling

    Args:
        workflow: Dicionário do workflow ComfyUI
        workflow_name: Nome do workflow para organização
        client_id: ID do cliente para ComfyUI
        save_outputs: Se True, baixa e salva os arquivos gerados
        custom_output_dir: Diretório customizado para salvar arquivos (Path ou str)
        filename_prefix: Prefixo do arquivo para detectar sobrescrita
    """

    # Enviar workflow
    prompt_data = {
        "prompt": workflow,
        "client_id": client_id
    }
    response = requests.post(f"{COMFYUI_SERVER}/prompt", json=prompt_data, timeout=10)
    result = response.json()

    if "prompt_id" not in result:
        raise Exception(f"Erro ao enviar workflow: {result}")

    prompt_id = result["prompt_id"]
    print(f"📝 {prompt_id[:8]}...")

    # Polling até completar
    print("⏳ ")
    poll_count = 0
    max_attempts = 120  # 2 minutos

    while poll_count < max_attempts:
        await asyncio.sleep(0.5)
        poll_count += 1

        try:
            r = requests.get(f"{COMFYUI_SERVER}/history/{prompt_id}", timeout=2)
            if r.status_code == 200:
                data = r.json()
                if prompt_id in data:
                    outputs = data[prompt_id].get("outputs", {})
                    if outputs:
                        print()  # Nova linha
                        break
        except:
            pass

        # Progresso visual
        if poll_count % 10 == 0:
            print(".", end="", flush=True)

    else:
        raise Exception("Timeout: workflow não completou")

    # Buscar resultados
    saved_files = []

    if custom_output_dir:
        output_dir = Path(custom_output_dir)
    else:
        output_dir = Path("outputs") / workflow_name
    output_dir.mkdir(parents=True, exist_ok=True)

    r = requests.get(f"{COMFYUI_SERVER}/history/{prompt_id}", timeout=10)
    data = r.json()

    if prompt_id not in data:
        raise Exception("Workflow não encontrado no histórico")

    outputs = data[prompt_id].get("outputs", {})

    for node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                f = await download_output(
                    filename=img["filename"],
                    subfolder=img.get("subfolder", ""),
                    file_type=img.get("type", "output"),
                    output_dir=output_dir,
                    filename_prefix=filename_prefix
                )
                if f:
                    saved_files.append(f)

        if "audio" in node_output:
            for aud in node_output["audio"]:
                f = await download_output(
                    filename=aud["filename"],
                    subfolder=aud.get("subfolder", ""),
                    file_type=aud.get("type", "output"),
                    output_dir=output_dir,
                    filename_prefix=filename_prefix
                )
                if f:
                    saved_files.append(f)

        if "videos" in node_output:
            for vid in node_output["videos"]:
                f = await download_output(
                    filename=vid["filename"],
                    subfolder=vid.get("subfolder", ""),
                    file_type=vid.get("type", "output"),
                    output_dir=output_dir,
                    filename_prefix=filename_prefix
                )
                if f:
                    saved_files.append(f)

    return saved_files


async def download_output(filename, subfolder, file_type, output_dir, filename_prefix=None, max_retries=3):
    """Baixa arquivo do ComfyUI com retry e evita sobrescrita"""
    params = {
        "filename": filename,
        "subfolder": subfolder,
        "type": file_type
    }

    # Se filename tem nome temporário e temos prefixo, usar prefixo como nome base
    if filename_prefix and ("ComfyUI_temp" in filename or "temp_" in filename):
        extension = Path(filename).suffix
        filename = f"{filename_prefix}{extension}"

    for attempt in range(max_retries):
        try:
            response = requests.get(f"{COMFYUI_SERVER}/view", params=params, timeout=30)
            response.raise_for_status()

            # Verificar sobrescrita
            output_path = output_dir / filename
            if output_path.exists():
                if filename_prefix:
                    # Gerar novo nome
                    stem = output_path.stem.split('_')[0]  # Pega prefixo original
                    suffix = output_path.suffix
                    counter = 1
                    while output_path.exists():
                        new_name = f"{stem}_{counter}{suffix}"
                        output_path = output_dir / new_name
                        counter += 1
                else:
                    # Adicionar timestamp
                    stem = output_path.stem
                    suffix = output_path.suffix
                    import time
                    output_path = output_dir / f"{stem}_{int(time.time())}{suffix}"

            with open(output_path, 'wb') as f:
                f.write(response.content)

            print(f"💾 Salvo: {output_path}")
            return str(output_path)

        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Erro baixando {filename}: {e}")
                return None
            await asyncio.sleep(0.5)

    return None


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
