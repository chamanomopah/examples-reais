#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera/Autaliza workflow_config.json automaticamente
Escaneia workflows_api_converted/ e detecta parâmetros
"""

import json
import sys
import io
from pathlib import Path

# UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

WORKFLOWS_DIR = Path("workflows_api_converted")
CONFIG_FILE = Path("workflow_config.json")


def detect_node_params(node):
    """Detecta parâmetros modificáveis em um nó"""
    params = {}

    if "inputs" in node:
        for key, value in node["inputs"].items():
            # Ignorar links (que são listas)
            if not isinstance(value, list):
                # Parametros simples (string, int, float)
                params[key] = {"field": f"inputs.{key}"}

    return params


def analyze_workflow(workflow_path):
    """Analisa workflow e extrai configuração"""
    with open(workflow_path, 'r', encoding='utf-8') as f:
        workflow = json.load(f)

    config = {
        "file": workflow_path.name,
        "params": {}
    }

    # Detectar parâmetros em todos os nós
    for node_id, node in workflow.items():
        if isinstance(node, dict) and "class_type" in node:
            node_type = node["class_type"]

            # Nós comumente parametrizáveis
            if node_type in [
                "CLIPTextEncode",
                "KSampler",
                "EmptySD3LatentImage",
                "KokoroTextToSpeech",
                "KokoroGenerator",
                "KokoroSpeaker",
                "SaveImage",
                "VAEDecode",
                "PreviewAudio"
            ]:
                params = detect_node_params(node)
                if params:
                    # Criar nome amigável
                    param_name = node_type.lower().replace("(", "").replace(")", "")
                    config["params"][param_name] = {
                        "node_type": node_type,
                        "node_id": node_id,
                        **params
                    }

    return config


def scan_and_update_config():
    """Escaneia pasta e atualiza config"""

    if not WORKFLOWS_DIR.exists():
        print(f"✗ Pasta não encontrada: {WORKFLOWS_DIR}")
        return False

    # Carregar config existente
    existing_config = {}
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            existing_config = json.load(f)

    # Escanear workflows
    workflow_files = list(WORKFLOWS_DIR.glob("*.json"))
    print(f"📂 Escaneando: {len(workflow_files)} workflows")

    new_config = {}
    added = 0
    updated = 0

    for wf_file in workflow_files:
        # Criar key amigável (remover WORKFLOW - e .json)
        key = wf_file.stem.replace("WORKFLOW - ", "").lower().replace(" ", "_").replace("-", "_")

        print(f"  📄 {wf_file.name} → {key}")

        # Analisar workflow
        workflow_config = analyze_workflow(wf_file)

        # Verificar se é novo ou atualização
        if key not in existing_config:
            added += 1
            print(f"    ✨ NOVO: {len(workflow_config['params'])} parâmetros")
        else:
            updated += 1
            print(f"    🔄 EXISTENTE: {len(workflow_config['params'])} parâmetros")

        new_config[key] = workflow_config

    # Salvar config
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=2, ensure_ascii=False)

    print()
    print(f"✅ Config salvo: {CONFIG_FILE}")
    print(f"   📊 Total: {len(new_config)} workflows")
    print(f"   ✨ Novos: {added}")
    print(f"   🔄 Atualizados: {updated}")

    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Atualizador de workflow_config.json")
    print("=" * 60)
    print()

    scan_and_update_config()
