#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Executor universal de workflows ComfyUI
Auto-detecta workflows novos e atualiza config
"""

import asyncio
import sys
import io
import json
import subprocess
from pathlib import Path
import argparse

# UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, str(Path(__file__).parent))

from utils import check_server, run_workflow

WORKFLOWS_DIR = Path("workflows_api_converted")
CONFIG_FILE = Path("workflow_config.json")


def check_sync():
    """Verifica se config está sincronizado com pasta de workflows"""
    if not CONFIG_FILE.exists():
        return False

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Contar workflows na pasta
    workflow_files = list(WORKFLOWS_DIR.glob("*.json"))
    return len(config) == len(workflow_files)


def auto_update_config():
    """Atualiza config automaticamente"""
    print("🔄 Config desatualizado, atualizando...")
    print()
    result = subprocess.run(
        [sys.executable, "update_workflow_config.py"],
        capture_output=True,
        text=True
    )
    print(result.stdout)
    return result.returncode == 0


def modify_workflow_params(workflow, config, params):
    """Modifica workflow baseado no config e parâmetros fornecidos"""
    modified = False

    for full_param_name, param_value in params.items():
        # Parse dot notation (ex: "kokorogenerator.text" -> group="kokorogenerator", param="text")
        if "." in full_param_name:
            group_name, param_name = full_param_name.split(".", 1)
        else:
            # Tentar encontrar automaticamente
            group_name = None
            param_name = full_param_name

        # Buscar em todos os grupos de parâmetros
        found = False

        for config_group_name, group_config in config["params"].items():
            # Se group_name especificado, verificar match
            if group_name and config_group_name != group_name:
                continue

            if param_name in group_config:
                # Encontrou o parâmetro
                param_config = group_config[param_name]
                node_id = group_config["node_id"]
                field = param_config["field"]

                if node_id not in workflow:
                    print(f"⚠️  Nó não encontrado: {node_id}")
                    continue

                # Navegar até o campo (ex: "inputs.text")
                parts = field.split(".")
                obj = workflow[node_id]
                for part in parts[:-1]:
                    obj = obj[part]

                # Modificar valor
                obj[parts[-1]] = param_value
                print(f"  ✓ {config_group_name}.{param_name} = {param_value}")
                found = True
                modified = True
                break

        if not found:
            print(f"⚠️  Parâmetro desconhecido: {full_param_name}")
            print(f"   Parâmetros disponíveis:")
            for group_name, group_config in config["params"].items():
                for param_key in group_config.keys():
                    if param_key != "node_type" and param_key != "node_id" and param_key != "field":
                        print(f"     - {group_name}.{param_key}")

    return workflow


def list_workflows():
    """Lista workflows disponíveis"""
    if not CONFIG_FILE.exists():
        print("❌ Config não encontrado. Execute o script pela 1ª vez para criar.")
        return

    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    print("📋 Workflows disponíveis:")
    print()
    for key, workflow_config in config.items():
        print(f"  🎨 {key}")
        print(f"     Arquivo: {workflow_config['file']}")
        if workflow_config['params']:
            print(f"     Parâmetros: {', '.join(workflow_config['params'].keys())}")
        print()


def parse_args():
    """Parse argumentos"""
    parser = argparse.ArgumentParser(
        description='Executor universal de workflows ComfyUI',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument(
        'workflow',
        nargs='?',
        help='Nome do workflow (ex: z_image_turbo)'
    )

    parser.add_argument(
        '--list',
        action='store_true',
        help='Listar workflows disponíveis'
    )

    parser.add_argument(
        '--no-update',
        action='store_true',
        help='Não auto-atualizar config'
    )

    # Parâmetros dinâmicos (todos os outros argumentos)
    parser.add_argument(
        'params',
        nargs=argparse.REMAINDER,
        help='Parâmetros do workflow (ex: prompt="texto" width=1024)'
    )

    return parser.parse_args()


def parse_params(params_list):
    """Converte lista de parâmetros para dict"""
    params = {}
    for param in params_list:
        if '=' in param:
            key, value = param.split('=', 1)
            # Tentar converter para tipo apropriado
            if value.isdigit():
                value = int(value)
            elif value.replace('.', '').isdigit():
                value = float(value)
            params[key] = value
    return params


async def main():
    args = parse_args()

    # List mode
    if args.list:
        list_workflows()
        return

    # Verificar workflow fornecido
    if not args.workflow:
        print("❌ Especifique um workflow ou use --list")
        print()
        print("Exemplo: python run_workflow.py z_image_turbo prompt=\"gato\" width=1024")
        return

    # Auto-atualizar config se necessário
    if not args.no_update and not check_sync():
        if not auto_update_config():
            print("❌ Falha ao atualizar config")
            return
        print()

    # Carregar config
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Encontrar workflow
    workflow_key = args.workflow.lower()
    if workflow_key not in config:
        print(f"❌ Workflow não encontrado: {workflow_key}")
        print()
        print("Use --list para ver workflows disponíveis")
        return

    workflow_config = config[workflow_key]

    # Verificar ComfyUI
    print("1. Verificando ComfyUI...")
    if not check_server():
        print("❌ ComfyUI não está rodando")
        return
    print("✓ ComfyUI OK")
    print()

    # Carregar workflow
    print(f"2. Carregando workflow: {workflow_config['file']}")
    workflow_path = WORKFLOWS_DIR / workflow_config['file']

    from utils import load_workflow
    workflow = load_workflow(str(workflow_path))
    print(f"✓ Workflow carregado ({len(workflow)} nós)")
    print()

    # Parse parâmetros
    params = parse_params(args.params)

    if params:
        print("3. Aplicando parâmetros:")
        workflow = modify_workflow_params(workflow, workflow_config, params)
        print()
    else:
        print("3. Usando parâmetros padrão")
        print()

    # Executar
    print("4. Executando workflow...")
    print("-" * 50)

    try:
        saved_files = await run_workflow(
            workflow=workflow,
            workflow_name=workflow_key,
            client_id=f"python_{workflow_key}",
            save_outputs=True
        )

        print("-" * 50)
        print()

        if saved_files:
            print("✅ SUCESSO!")
            for file_path in saved_files:
                print(f"  📁 {file_path}")
        else:
            print("⚠️  Executou mas não salvou arquivos")

    except Exception as e:
        print(f"❌ Erro: {e}")
        return


if __name__ == "__main__":
    asyncio.run(main())
