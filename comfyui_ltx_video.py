"""
ComfyUI - LTX Video (Image-to-Video) Automation
Script para gerar vídeos a partir de imagens usando o modelo LTX-2.3
"""

import asyncio
import sys
import argparse
from pathlib import Path
import random

# Adicionar diretório parent ao path para importar utils
sys.path.insert(0, str(Path(__file__).parent))
from utils import (
    load_workflow, run_workflow, check_server,
    upload_image
)


def prepare_ltx_video_workflow(
    prompt: str,
    negative_prompt: str = "pc game, console game, video game, cartoon, childish, ugly",
    image_path: str = None,
    image_name: str = None,
    width: int = 1280,
    height: int = 720,
    length: int = 121,
    frame_rate: int = 25,
    switch_to_text_to_video: bool = False,
    cfg: float = 1.0,
    ckpt_name: str = "ltx-2.3-22b-dev-fp8.safetensors",
    lora_name: str = "ltx-2.3-22b-distilled-lora-384.safetensors",
    text_encoder: str = "gemma_3_12B_it_fp4_mixed.safetensors",
    lora_text: str = "gemma-3-12b-it-abliterated_lora_rank64_bf16.safetensors"
) -> dict:
    """
    Prepara o workflow LTX Video com os parâmetros fornecidos.
    
    Args:
        prompt: Descrição do movimento/cena desejada
        negative_prompt: Coisas a evitar no vídeo
        image_path: Caminho da imagem de entrada (opcional para text-to-video)
        image_name: Nome da imagem após upload
        width: Largura do vídeo
        height: Altura do vídeo
        length: Duração em frames
        frame_rate: FPS do vídeo
        switch_to_text_to_video: Se True, gera vídeo apenas do texto
        cfg: CFG scale
        ckpt_name: Nome do checkpoint
        lora_name: Nome do LoRA
        text_encoder: Nome do text encoder
        lora_text: Nome do LoRA de texto
        
    Returns:
        Dicionário do workflow pronto para enviar
    """
    # Carregar workflow base
    workflow = load_workflow("WORKFLOW - video_ltx2_3_i2v.json")
    
    # Encontrar e atualizar os nós principais
    for node_id, node_data in workflow.items():
        if isinstance(node_data, dict):
            class_type = node_data.get("class_type", "")
            inputs = node_data.get("inputs", {})
            title = node_data.get("title", "")
            
            # Prompt (PrimitiveStringMultiline)
            if title == "Prompt" and "STRING" in str(inputs.get("value", "")):
                node_data["inputs"]["value"] = prompt
            
            # Negative prompt (CLIPTextEncode)
            elif class_type == "CLIPTextEncode" and "pc game" in str(inputs.get("text", "")):
                node_data["inputs"]["text"] = negative_prompt
            
            # Switch (PrimitiveBoolean)
            elif title == "Switch to Text to Video?":
                node_data["inputs"]["value"] = switch_to_text_to_video
            
            # Width (PrimitiveInt)
            elif title == "Width":
                node_data["inputs"]["value"] = width
            
            # Height (PrimitiveInt)
            elif title == "Height":
                node_data["inputs"]["value"] = height
            
            # Length (PrimitiveInt)
            elif title == "Length":
                node_data["inputs"]["value"] = length
            
            # Frame Rate (PrimitiveInt)
            elif title == "Frame Rate":
                node_data["inputs"]["value"] = frame_rate
            
            # CheckpointLoaderSimple
            elif class_type == "CheckpointLoaderSimple":
                node_data["inputs"]["ckpt_name"] = ckpt_name
            
            # LoraLoaderModelOnly
            elif class_type == "LoraLoaderModelOnly":
                node_data["inputs"]["lora_name"] = lora_name
                node_data["inputs"]["strength_model"] = 0.5
            
            # LTXAVTextEncoderLoader
            elif class_type == "LTXAVTextEncoderLoader":
                node_data["inputs"]["ckpt_name"] = ckpt_name
                node_data["inputs"]["text_encoder"] = text_encoder
            
            # LoraLoader (para texto)
            elif class_type == "LoraLoader":
                node_data["inputs"]["lora_name"] = lora_text
                node_data["inputs"]["strength_model"] = 1.0
                node_data["inputs"]["strength_clip"] = 1.0
            
            # CFGGuider
            elif class_type == "CFGGuider":
                node_data["inputs"]["cfg"] = cfg
            
            # ResizeImageMaskNode (se imagem fornecida)
            elif class_type == "ResizeImageMaskNode" and image_name:
                # Este nó precisa da imagem como input
                # O link será criado automaticamente pelo ComfyUI
                pass
    
    # Se imagem fornecida e não for text-to-video
    if image_path and not switch_to_text_to_video:
        # Upload da imagem será feito antes de enviar o workflow
        # O nome da imagem será passado como image_name
        pass
    
    return workflow, image_name


async def main():
    """Função principal."""
    parser = argparse.ArgumentParser(
        description="Gera vídeos usando LTX-2.3 no ComfyUI"
    )
    parser.add_argument(
        "--prompt", "-p",
        type=str,
        required=True,
        help="Descrição do movimento/cena desejada"
    )
    parser.add_argument(
        "--image", "-i",
        type=str,
        default=None,
        help="Caminho da imagem de entrada (opcional)"
    )
    parser.add_argument(
        "--negative", "-n",
        type=str,
        default="pc game, console game, video game, cartoon, childish, ugly",
        help="Negative prompt (coisas a evitar)"
    )
    parser.add_argument(
        "--width", "-W",
        type=int,
        default=1280,
        help="Largura do vídeo (padrão: 1280)"
    )
    parser.add_argument(
        "--height", "-H",
        type=int,
        default=720,
        help="Altura do vídeo (padrão: 720)"
    )
    parser.add_argument(
        "--length",
        type=int,
        default=121,
        help="Duração em frames (padrão: 121)"
    )
    parser.add_argument(
        "--fps",
        type=int,
        default=25,
        help="Frame rate (padrão: 25)"
    )
    parser.add_argument(
        "--text-to-video",
        action="store_true",
        help="Gerar vídeo apenas do texto (sem imagem de entrada)"
    )
    parser.add_argument(
        "--cfg",
        type=float,
        default=1.0,
        help="CFG scale (padrão: 1.0)"
    )
    parser.add_argument(
        "--client-id",
        type=str,
        default="ltx_video_client",
        help="ID do cliente para ComfyUI"
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Não salvar o vídeo"
    )
    
    args = parser.parse_args()
    
    # Verificar servidor
    print("Verificando servidor ComfyUI...")
    if not check_server():
        print("ERRO: Servidor ComfyUI não está rodando em http://127.0.0.1:8188")
        print("Inicie o ComfyUI e tente novamente.")
        sys.exit(1)
    print("Servidor OK!")
    
    # Upload da imagem se fornecida
    image_name = None
    if args.image and not args.text_to_video:
        print(f"\nFazendo upload da imagem: {args.image}")
        try:
            upload_result = upload_image(args.image)
            image_name = upload_result.get("name", Path(args.image).name)
            print(f"Imagem carregada como: {image_name}")
        except Exception as e:
            print(f"ERRO ao fazer upload: {e}")
            sys.exit(1)
    
    # Preparar workflow
    print(f"\nPreparando workflow LTX Video:")
    print(f"  Prompt: {args.prompt[:150]}{'...' if len(args.prompt) > 150 else ''}")
    print(f"  Dimensões: {args.width}x{args.height}")
    print(f"  Duração: {args.length} frames ({args.length/args.fps:.1f}s @ {args.fps}fps)")
    print(f"  CFG: {args.cfg}")
    if args.text_to_video:
        print(f"  Modo: Text-to-Video")
    elif image_name:
        print(f"  Imagem: {image_name}")
    
    try:
        workflow, _ = prepare_ltx_video_workflow(
            prompt=args.prompt,
            negative_prompt=args.negative,
            image_path=args.image,
            image_name=image_name,
            width=args.width,
            height=args.height,
            length=args.length,
            frame_rate=args.fps,
            switch_to_text_to_video=args.text_to_video,
            cfg=args.cfg
        )
    except Exception as e:
        print(f"\n✗ Erro ao preparar workflow: {e}")
        sys.exit(1)
    
    # Executar workflow
    try:
        print("\nATENÇÃO: Geração de vídeo pode levar vários minutos...")
        print("Seja paciente e monitore o progresso no ComfyUI.\n")
        
        output_files = await run_workflow(
            workflow=workflow,
            workflow_name="ltx_video",
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
