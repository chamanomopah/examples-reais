# ComfyUI - Resumo Executivo

## 🎯 O que é ComfyUI?

**ComfyUI** é uma interface visual baseada em nós para IA generativa, focada principalmente em geração de imagens com Stable Diffusion. É open source, roda localmente e possui API completa para automação.

### Características Chave:
- ✅ Interface visual drag-and-drop
- ✅ Suporte a Stable Diffusion, SDXL, LoRA, ControlNet
- ✅ API REST + WebSocket
- ✅ Totalmente extensível via custom nodes
- ✅ Multi-plataforma (Windows, macOS, Linux)

---

## 🚀 API REST - Principais Endpoints

| Endpoint | Método | Propósito |
|----------|--------|-----------|
| `/prompt` | POST | Enviar workflow para execução |
| `/history/{id}` | GET | Obter resultados |
| `/queue` | GET | Ver fila de execução |
| `/object_info` | GET | Listar nós disponíveis |
| `/view` | GET | Baixar imagem gerada |
| `/upload/image` | POST | Fazer upload de imagem |
| `/ws` | WebSocket | Monitoramento em tempo real |

**Servidor padrão:** `http://127.0.0.1:8188`

---

## 📝 Fluxo Básico de Automação

```bash
# 1. Enviar workflow
curl -X POST http://127.0.0.1:8188/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": {...}, "client_id": "my_app"}'

# 2. Obter prompt_id da resposta
# 3. Monitorar via WebSocket ws://127.0.0.1:8188/ws
# 4. Quando completo, obter resultados
curl http://127.0.0.1:8188/history/{prompt_id}

# 5. Baixar imagens
curl "http://127.0.0.1:8188/view?filename=image.png&type=output" -o output.png
```

---

## 🐍 Python - Exemplo Rápido

```python
import requests
import json

# Carregar workflow
with open("workflow_api.json") as f:
    workflow = json.load(f)

# Enviar
response = requests.post("http://127.0.0.1:8188/prompt", json={
    "prompt": workflow,
    "client_id": "python_script"
})

prompt_id = response.json()["prompt_id"]
print(f"Queued: {prompt_id}")
```

---

## 🔌 Integração com n8n

Para usar ComfyUI no n8n:

1. **HTTP Request Node (POST):**
   - URL: `http://127.0.0.1:8188/prompt`
   - Method: POST
   - Body: JSON com workflow

2. **Wait Node:** Aguardar processamento

3. **HTTP Request Node (GET):**
   - URL: `http://127.0.0.1:8188/history/{{prompt_id}}`

4. **Loop sobre outputs:** Baixar cada imagem

---

## 📚 Recursos

- **Documentação Oficial:** https://docs.comfy.org
- **GitHub:** https://github.com/comfyanonymous/ComfyUI
- **Python CLI:** https://github.com/tokimwc/comfyui-cli
- **Python Client:** https://github.com/sugarkwork/Comfyui_api_client

---

## ⚡ Uso Recomendado para Automação

1. **Desenvolva workflow visualmente** no ComfyUI
2. **Salve em "API Format"** (Save → Save (API Format))
3. **Automatize** usando:
   - Python com `requests` + `websockets`
   - Node.js com `node-fetch` + `ws`
   - n8n com HTTP Request nodes
   - Scripts bash com `curl`

---

## ✅ Próximos Passos

1. Instalar ComfyUI localmente
2. Criar workflow simples (text-to-image)
3. Salvar em formato API
4. Testar com scripts de exemplo
5. Integrar ao seu pipeline de automação

**Relatório completo:** `comfyui-research-report.md`
