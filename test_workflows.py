#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Teste abrangente de workflows com diversos parâmetros
Valida automaticamente os resultados
"""

import asyncio
import sys
import io
import subprocess
from pathlib import Path

# UTF-8
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


async def run_test(test_name, workflow, params, expected_success=True):
    """Executa um teste e valida o resultado"""
    print(f"\n{'='*60}")
    print(f"🧪 TESTE: {test_name}")
    print(f"{'='*60}")

    # Construir comando
    cmd = ["python", "run_workflow.py", workflow]
    for key, value in params.items():
        cmd.append(f"{key}={value}")

    print(f"📋 Comando: {' '.join(cmd)}")
    print()

    # Executar
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    # Mostrar output
    print(result.stdout)

    if result.stderr:
        print("⚠️  STDERR:")
        print(result.stderr)

    # Verificar sucesso
    success = "✅ SUCESSO!" in result.stdout

    if success == expected_success:
        print(f"✅ Teste '{test_name}' PASSOU")
        return True
    else:
        print(f"❌ Teste '{test_name}' FALHOU")
        return False


async def main():
    print("🚀 Iniciando testes abrangentes de workflows")
    print()

    tests = [
        # Testes KOKORO TTS
        {
            "name": "KOKORO - Inglês básico",
            "workflow": "kokoro",
            "params": {
                "kokorogenerator.text": "Hello world, this is a test",
                "kokorogenerator.lang": "English",
                "kokorogenerator.speed": 1.0
            },
            "expected_success": False  # PreviewAudio não salva arquivos
        },

        {
            "name": "KOKORO - Português acelerado",
            "workflow": "kokoro",
            "params": {
                "kokorogenerator.text": "Olá mundo, teste de voz",
                "kokorogenerator.lang": "Portuguese",
                "kokorogenerator.speed": 1.5
            },
            "expected_success": False
        },

        {
            "name": "KOKORO - Espanhol lento",
            "workflow": "kokoro",
            "params": {
                "kokorogenerator.text": "Hola mundo, prueba de voz",
                "kokorogenerator.lang": "Spanish",
                "kokorogenerator.speed": 0.8
            },
            "expected_success": False
        },

        # Testes Z-IMAGE-TURBO
        {
            "name": "Z-IMAGE - Resolução 512x512",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "a red sports car",
                "emptysd3latentimage.width": 512,
                "emptysd3latentimage.height": 512,
                "ksampler.steps": 4,
                "saveimage.filename_prefix": "car_512"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Resolução 768x768",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "a magical forest with glowing trees",
                "emptysd3latentimage.width": 768,
                "emptysd3latentimage.height": 768,
                "ksampler.steps": 6,
                "saveimage.filename_prefix": "forest_768"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Resolução 1024x1024",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "an astronaut riding a horse on Mars",
                "emptysd3latentimage.width": 1024,
                "emptysd3latentimage.height": 1024,
                "ksampler.steps": 8,
                "saveimage.filename_prefix": "astronaut_1024"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Diferentes samplers",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "a beautiful sunset over the ocean",
                "emptysd3latentimage.width": 640,
                "emptysd3latentimage.height": 640,
                "ksampler.steps": 5,
                "ksampler.sampler_name": "euler",
                "ksampler.scheduler": "normal",
                "saveimage.filename_prefix": "sunset_euler"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Diferentes CFG",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "a cute cartoon dragon",
                "emptysd3latentimage.width": 512,
                "emptysd3latentimage.height": 512,
                "ksampler.steps": 4,
                "ksampler.cfg": 2.0,
                "saveimage.filename_prefix": "dragon_cfg2"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Seed específico",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "a steampunk airship",
                "emptysd3latentimage.width": 768,
                "emptysd3latentimage.height": 768,
                "ksampler.steps": 6,
                "ksampler.seed": 42,
                "saveimage.filename_prefix": "airship_seed42"
            },
            "expected_success": True
        },

        {
            "name": "Z-IMAGE - Variação de denoise",
            "workflow": "z_image_turbo",
            "params": {
                "cliptextencode.text": "abstract colorful art",
                "emptysd3latentimage.width": 512,
                "emptysd3latentimage.height": 512,
                "ksampler.steps": 4,
                "ksampler.denoise": 0.8,
                "saveimage.filename_prefix": "abstract_denoise"
            },
            "expected_success": True
        }
    ]

    # Executar testes
    passed = 0
    failed = 0

    for test in tests:
        try:
            result = await run_test(
                test["name"],
                test["workflow"],
                test["params"],
                test["expected_success"]
            )

            if result:
                passed += 1
            else:
                failed += 1

        except Exception as e:
            print(f"❌ Erro no teste '{test['name']}': {e}")
            failed += 1

    # Resumo
    print(f"\n{'='*60}")
    print("📊 RESUMO DOS TESTES")
    print(f"{'='*60}")
    print(f"✅ Passou: {passed}/{len(tests)}")
    print(f"❌ Falhou: {failed}/{len(tests)}")
    print(f"📈 Taxa de sucesso: {passed/len(tests)*100:.1f}%")
    print()

    # Verificar arquivos gerados
    print("📁 Arquivos gerados:")
    for workflow_dir in Path("outputs").glob("*"):
        if workflow_dir.is_dir():
            files = list(workflow_dir.glob("*.png")) + list(workflow_dir.glob("*.jpg"))
            print(f"  📂 {workflow_dir.name}: {len(files)} arquivos")

    print()
    print("🎉 Testes concluídos!")


if __name__ == "__main__":
    asyncio.run(main())
