# Guia de Integração: ComfyUI + n8n

## 🎯 Objetivo

Automatizar workflows do ComfyUI usando n8n para criação de pipelines de geração de conteúdo (imagens, vídeos, etc.).

---

## 📋 Pré-requisitos

- ComfyUI rodando localmente (http://127.0.0.1:8188)
- n8n instalado (local ou cloud)
- Workflow do ComfyUI salvo em formato API

---

## 🔧 Configuração Básica

### 1. Workflow Simples de Geração

#### Node 1: HTTP Request - Enviar Workflow

**Configuração:**
- **Method:** POST
- **URL:** `http://127.0.0.1:8188/prompt`
- **Authentication:** None
- **Body:** JSON (Inline)

```json
{
  "prompt": {
    "3": {
      "inputs": {
        "seed": "={{$now.toInteger()}}",
        "steps": 20,
        "cfg": 8,
        "sampler_name": "euler",
        "scheduler": "normal",
        "model": ["4", 0],
        "positive": ["6", 0],
        "negative": ["7", 0],
        "latent_image": ["5", 0]
      },
      "class_type": "KSampler"
    },
    "4": {
      "inputs": {
        "ckpt_name": "v1-5-pruned-emaonly-fp16.safetensors"
      },
      "class_type": "CheckpointLoaderSimple"
    },
    "5": {
      "inputs": {
        "width": 512,
        "height": 512,
        "batch_size": 1
      },
      "class_type": "EmptyLatentImage"
    },
    "6": {
      "inputs": {
        "text": "={{$json.prompt}}",
        "clip": ["4", 1]
      },
      "class_type": "CLIPTextEncode"
    },
    "7": {
      "inputs": {
        "text": "text, watermark, blurry",
        "clip": ["4", 1]
      },
      "class_type": "CLIPTextEncode"
    },
    "8": {
      "inputs": {
        "samples": ["3", 0],
        "vae": ["4", 2]
      },
      "class_type": "VAEDecode"
    },
    "9": {
      "inputs": {
        "filename_prefix": "ComfyUI",
        "images": ["8", 0]
      },
      "class_type": "SaveImage"
    }
  },
  "client_id": "n8n_workflow"
}
```

#### Node 2: Wait - Aguardar Processamento

**Configuração:**
- **Time:** 30 segundos (ajustar conforme complexidade)

#### Node 3: HTTP Request - Obter Resultados

**Configuração:**
- **Method:** GET
- **URL:** `http://127.0.0.1:8188/history/{{$node["HTTP Request"].json["prompt_id"]}}`

#### Node 4: Code - Processar Outputs

**JavaScript:**
```javascript
// Extrair informações das imagens
const promptId = $input.item.json.prompt_id;
const outputs = $input.item.json[promptId].outputs;
const images = [];

for (const [nodeId, nodeData] of Object.entries(outputs)) {
  if (nodeData.images) {
    for (const img of nodeData.images) {
      images.push({
        filename: img.filename,
        subfolder: img.subfolder || "",
        type: img.type || "output",
        url: `http://127.0.0.1:8188/view?filename=${img.filename}&subfolder=${img.subfolder || ""}&type=${img.type || "output"}`
      });
    }
  }
}

return images.map(img => ({ json: img }));
```

#### Node 5: HTTP Request - Baixar Imagens

**Configuração:**
- **Method:** GET
- **URL:** `{{$json.url}}`
- **Response Format:** File

---

## 🚀 Workflow Avançado com Webhook

### Gatilho via Webhook

#### Node 1: Webhook - Receber Solicitação

**Configuração:**
- **Path:** comfyui-generate
- **Method:** POST
- **Response:** Respond to Webhook

**Body esperado:**
```json
{
  "prompt": "a beautiful sunset over mountains",
  "negative": "blurry, low quality",
  "steps": 20,
  "cfg": 8
}
```

#### Node 2: Set - Configurar Parâmetros

**Valores:**
```json
{
  "seed": "={{$now.toInteger()}}",
  "prompt": "={{$json.body.prompt}}",
  "negative": "={{$json.body.negative}}",
  "steps": "={{$json.body.steps || 20}}",
  "cfg": "={{$json.body.cfg || 8}}"
}
```

#### Node 3: HTTP Request - Enviar para ComfyUI

Mesma configuração do exemplo básico, mas usando variáveis:

```json
{
  "prompt": {
    "6": {
      "inputs": {
        "text": "={{$node['Set'].json.prompt}}"
      }
    },
    "7": {
      "inputs": {
        "text": "={{$node['Set'].json.negative}}"
      }
    },
    "3": {
      "inputs": {
        "seed": "={{$node['Set'].json.seed}}",
        "steps": "={{$node['Set'].json.steps}}",
        "cfg": "={{$node['Set'].json.cfg}}"
      }
    }
  }
}
```

---

## 🔄 Workflow de Batch Processing

### Node 1: Webhook - Receber Lista de Prompts

```json
{
  "prompts": [
    "a beautiful sunset",
    "a futuristic city",
    "a serene forest"
  ]
}
```

### Node 2: Split Out - Dividir Prompts

### Node 3: Loop - Processar Cada Prompt

#### Inside Loop:

**a. HTTP Request - Enviar para ComfyUI**

**b. Wait - Aguardar**

**c. HTTP Request - Obter Resultados**

**d. HTTP Request - Baixar Imagem**

**e. Google Drive/Cloud - Salvar Arquivo**

---

## 📊 Workflow com Monitoramento WebSocket

Para monitoramento em tempo real, use um Function Node com WebSocket:

### Node: Function Node - WebSocket Monitor

```javascript
const WebSocket = require('ws');

const promptId = $input.item.json.prompt_id;
const server = '127.0.0.1:8188';
const clientId = 'n8n_monitor';

return new Promise((resolve, reject) => {
  const ws = new WebSocket(`ws://${server}/ws?clientId=${clientId}`);
  let completed = false;
  
  ws.on('open', () => {
    console.log('WebSocket connected');
  });
  
  ws.on('message', (data) => {
    const msg = JSON.parse(data);
    
    if (msg.type === 'executing' && msg.data.node === null) {
      completed = true;
      ws.close();
    }
    
    if (msg.type === 'progress') {
      console.log(`Progress: ${msg.data.value}/${msg.data.max}`);
    }
  });
  
  ws.on('close', () => {
    if (completed) {
      resolve({ json: { status: 'completed', promptId } });
    } else {
      reject(new Error('WebSocket closed unexpectedly'));
    }
  });
  
  ws.on('error', (error) => {
    reject(error);
  });
  
  // Timeout após 5 minutos
  setTimeout(() => {
    if (!completed) {
      ws.close();
      reject(new Error('Timeout'));
    }
  }, 300000);
});
```

---

## 🎨 Workflow: Image-to-Image

### Node 1: HTTP Request - Upload Imagem

**Method:** POST
**URL:** `http://127.0.0.1:8188/upload/image`
**Body Type:** Form-Data

**Fields:**
- **image:** (Binary from previous node)
- **type:** `input`

### Node 2: Set - Nome da Imagem

```json
{
  "image_name": "={{$node['HTTP Request'].json.name}}"
}
```

### Node 3: HTTP Request - Processar

Usar workflow com nó LoadImage:

```json
{
  "prompt": {
    "10": {
      "inputs": {
        "image": "={{$node['Set'].json.image_name}}"
      },
      "class_type": "LoadImage"
    }
  }
}
```

---

## 📁 Workflow: Salvar no Google Drive

### Node: HTTP Request - Baixar Imagem

Conecte ao nó de processamento de outputs.

### Node: Google Drive - Upload File

**Operation:** Upload File

**Configuration:**
- **File ID:** (from HTTP Request)
- **Name:** `comfyui_{{$now.toISO()}}.png`
- **Folder ID:** (sua pasta de destino)

---

## 🔐 Workflow: Autenticação com API Key

Se usar ComfyUI Cloud ou serviço com autenticação:

### HTTP Request Headers:

```
X-API-Key: {{$env.COMFYUI_API_KEY}}
```

### Variáveis de Ambiente no n8n:

1. Abra configurações do n8n
2. Adicione variável: `COMFYUI_API_KEY`
3. Valor: sua chave API

---

## ⚠️ Tratamento de Erros

### Node: If - Verificar Erros

```javascript
{{$node["HTTP Request"].json.error !== undefined}}
```

### Branch True: Error Handler

**Enviar notificação** (Email, Slack, etc)

### Branch False: Continuar

**Processar normalmente**

---

## 📈 Workflow: Métricas e Logging

### Node: PostgresDB - Salvar Execução

**Operation:** Insert

**Table:** comfyui_executions

**Columns:**
- prompt_id (UUID)
- prompt (TEXT)
- timestamp (TIMESTAMP)
- status (VARCHAR)
- processing_time (INTEGER)
- output_files (JSONB)

---

## 🎯 Exemplo Completo: API de Geração de Imagens

### Fluxo:

```
Webhook (POST /generate)
  ↓
Validar Input
  ↓
Preparar Workflow
  ↓
HTTP Request → ComfyUI /prompt
  ↓
WebSocket Monitor
  ↓
HTTP Request → /history/{id}
  ↓
Baixar Imagens
  ↓
Upload para S3/Google Drive
  ↓
Responder Webhook com URLs
```

### Resposta do Webhook:

```json
{
  "status": "success",
  "prompt_id": "abc-123",
  "images": [
    {
      "filename": "ComfyUI_00001.png",
