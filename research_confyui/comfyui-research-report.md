# ComfyUI - Relatório Completo de Pesquisa

**Data da Pesquisa:** 20 de Abril de 2026  
**Status:** ✅ Pesquisa Completa

---

## 📋 Índice

1. [O que é ComfyUI](#o-que-é-comfyui)
2. [Principais Funcionalidades](#principais-funcionalidades)
3. [API REST - Documentação Completa](#api-rest---documentação-completa)
4. [WebSocket API](#websocket-api)
5. [Exemplos de Requisições HTTP/cURL](#exemplos-de-requisiçõeshttpcurl)
6. [Uso em Automações](#uso-em-automações)
7. [Bibliotecas de Cliente](#bibliotecas-de-cliente)
8. [Exemplos de Código](#exemplos-de-código)
9. [Referências e Fontes](#referências-e-fontes)

---

## 1. O que é ComfyUI

**ComfyUI** é uma interface baseada em nós e um mecanismo de inferência para IA generativa. Ele permite aos usuários combinar vários modelos de IA e operações através de nós para alcançar geração de conteúdo altamente personalizável e controlável.

### Características Principais:

- ✅ **Código Aberto:** Completamente open source e pode ser executado localmente
- ✅ **Interface Baseada em Nós:** Workflow visual para conectar diferentes operações de IA
- ✅ **Suporte a Múltiplos Modelos:** Stable Diffusion, SDXL, modelos personalizados, LoRA, etc.
- ✅ **API REST e WebSocket:** Integração completa com aplicações externas
- ✅ **Extensível:** Suporte a custom nodes e workflows personalizados
- ✅ **Multi-plataforma:** Windows, macOS e Linux

### Casos de Uso:

- Geração de imagens com Stable Diffusion
- Image-to-image transformations
- Text-to-video generation
- Controle com ControlNet
- Workflows complexos de IA generativa
- Automação de geração de conteúdo

---

## 2. Principais Funcionalidades

### Interface Visual
- **Node-based workflow:** Conecte diferentes operações visualmente
- **Workflow Templates:** Salve e reutilize workflows
- **Subgraphs:** Organize workflows complexos em módulos
- **Partial Execution:** Execute partes específicas do workflow
- **Mask Editor:** Editor de máscaras integrado

### Extensibilidade
- **Custom Nodes:** Crie e publique nós personalizados
- **Comfy Hub:** Descubra workflows e criadores
- **Plugin System:** Extensões via custom nodes

---

## 3. API REST - Documentação Completa

### Visão Geral dos Endpoints

| Método | Endpoint | Propósito |
|--------|----------|-----------|
| POST | /prompt | Enviar workflow para fila |
| GET | /history | Recuperar histórico completo |
| GET | /history/{prompt_id} | Recuperar histórico específico |
| POST | /history | Limpar histórico |
| GET | /queue | Ver status da fila |
| POST | /queue | Limpar fila |
| GET | /object_info | Obter informações de todos os nós |
| GET | /object_info/{node} | Obter informações de nó específico |
| GET | /view | Baixar imagem gerada |
| POST | /upload/image | Fazer upload de imagem |
| POST | /upload/mask | Fazer upload de máscara |
| GET | /system_stats | Estatísticas do sistema |
| POST | /interrupt | Interromper execução |
| POST | /free | Liberar memória |
| WS | /ws | WebSocket para monitoramento |

### Detalhes dos Endpoints

#### POST /prompt

**Propósito:** Enviar um workflow para fila de execução

**Request:**
```bash
curl -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {WORKFLOW_JSON},
    "client_id": "optional-client-id"
  }'
```

**Response (Sucesso):**
```json
{
  "prompt_id": "26bc628d-7ab2-43e6-8a67-d6a793e7fbcc",
  "number": 1,
  "node_errors": {}
}
```

**Response (Erro):**
```json
{
  "error": "error message",
  "node_errors": {
    "3": ["error details"],
    "5": ["error details"]
  }
}
```

#### GET /history/{prompt_id}

**Propósito:** Recuperar resultados e metadados

**Response:**
```json
{
  "prompt_id": {
    "prompt": [...],
    "outputs": {
      "9": {
        "images": [
          {
            "filename": "ComfyUI_00002_.png",
            "subfolder": "",
            "type": "output"
          }
        ]
      }
    },
    "status": {
      "status_str": "success",
      "completed": true
    }
  }
}
```

#### GET /object_info

**Propósito:** Obter definições de todos os nós

**Response:**
```json
{
  "KSampler": {
    "input": {
      "required": {
        "seed": ["INT", {"default": 0, "min": 0, "max": 18446744073709552000}],
        "steps": ["INT", {"default": 20, "min": 1, "max": 1000}],
        "cfg": ["FLOAT", {"default": 8, "min": 0, "max": 100}]
      }
    }
  }
}
```

#### POST /upload/image

**Propósito:** Fazer upload de imagem

```bash
curl -X POST http://127.0.0.1:8188/upload/image \
  -F "image=@path/to/image.png" \
  -F "type=input"
```

---

## 4. WebSocket API

### Endpoint: /ws

**URL:** `ws://127.0.0.1:8188/ws?clientId={client_id}`

### Tipos de Mensagens

| Tipo | Descrição |
|------|-----------|
| execution_start | Execução iniciada |
| execution_cached | Nó em cache |
| executing | Nó sendo executado (null quando completo) |
| progress | Progresso do sampling (value/max) |
| executed | Nó completado com output |
| execution_error | Erro na execução |

**Exemplo de Mensagem:**
```json
{
  "type": "progress",
  "data": {
    "value": 10,
    "max": 20
  }
}
```

---

## 5. Exemplos de Requisições HTTP/cURL

### Workflow Text-to-Image Completo

```bash
# 1. Enviar workflow
curl -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": {
      "3": {
        "inputs": {"seed": 1044669037100678, "steps": 20, "cfg": 8},
        "class_type": "KSampler"
      },
      "4": {
        "inputs": {"ckpt_name": "model.safetensors"},
        "class_type": "CheckpointLoaderSimple"
      }
    },
    "client_id": "my_client"
  }'

# 2. Obter histórico
curl http://127.0.0.1:8188/history/{prompt_id}

# 3. Baixar imagem
curl "http://127.0.0.1:8188/view?filename=image.png&type=output" -o output.png
```

### Upload de Imagem

```bash
curl -X POST http://127.0.0.1:8188/upload/image \
  -F "image=@input.png" \
  -F "type=input"
```

---

## 6. Uso em Automações

### Fluxo Básico de Automação

1. **Preparar Workflow:** Salvar workflow em formato API
2. **Modificar Parâmetros:** Alterar prompts, seeds, dimensões
3. **Enviar Prompt:** POST /prompt
4. **Monitorar:** WebSocket /ws para progresso
5. **Coletar Resultados:** GET /history/{prompt_id}
6. **Baixar Imagens:** GET /view

### Integração com Ferramentas

- **n8n:** Use HTTP Request nodes
- **Python:** requests + websockets
- **Node.js:** node-fetch + ws
- **Bash:** curl com scripts

---

## 7. Bibliotecas de Cliente

### Python - comfyui-cli

**Repositório:** https://github.com/tokimwc/comfyui-cli

```bash
pip install git+https://github.com/tokimwc/comfyui-cli.git
```

**Comandos:**
```bash
comfyui run workflow.json --seed 42
comfyui run workflow.json --batch 10
comfyui convert gui_workflow.json
comfyui status gpu
```

### Python - comfyui-api-client

**Repositório:** https://github.com/sugarkwork/Comfyui_api_client

```python
from Comfyui_api_client import ComfyUIClient

client = ComfyUIClient("localhost:8188", "workflow.json")
client.connect()
client.set_data(key='KSampler', seed=12345)
results = client.generate(["Result Image"])
```

### JavaScript - @stable-canvas/comfyui-client

```bash
npm install @stable-canvas/comfyui-client
```

```javascript
const { ComfyClient } = require('@stable-canvas/comfyui-client');
const client = new ComfyClient('http://127.0.0.1:8188');
await client.connect();
```

---

## 8. Exemplos de Código

### Python - Cliente Básico

```python
import requests
import json
import time

SERVER = "http://127.0.0.1:8188"

# Carregar workflow
with open("workflow_api.json") as f:
    workflow = json.load(f)

# Modificar
workflow["6"]["inputs"]["text"] = "beautiful sunset"
workflow["3"]["inputs"]["seed"] = 12345

# Enviar
response = requests.post(f"{SERVER}/prompt", json={
    "prompt": workflow,
    "client_id": "python_client"
})

prompt_id = response.json()["prompt_id"]
print(f"Queued: {prompt_id}")

# Aguardar
time.sleep(30)

# Obter resultado
history = requests.get(f"{SERVER}/history/{prompt_id}").json()
outputs = history[prompt_id]["outputs"]
prin
