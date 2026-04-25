# 🔍 Pesquisa ComfyUI - Índice Principal

Pesquisa completa sobre **ComfyUI** (não "ConfyUI") realizada em 20 de Abril de 2026.

---

## 📚 Documentos Disponíveis

### 1. 📖 Relatório Completo
**Arquivo:** `comfyui-research-report.md`

Contém:
- O que é ComfyUI e para que serve
- Documentação completa da API REST
- WebSocket API e tipos de mensagens
- Exemplos de requisições HTTP/cURL
- Bibliotecas de cliente (Python, JavaScript)
- Exemplos de código práticos

**Quando usar:** Consulta técnica completa e referência de API

---

### 2. ⚡ Resumo Executivo
**Arquivo:** `comfyui-executive-summary.md`

Contém:
- Visão geral em 2 minutos
- Tabela de endpoints principais
- Exemplo rápido em Python
- Guia de integração com n8n

**Quando usar:** Começar rapidamente ou apresentar a equipe

---

### 3. 🔌 Guia de Integração n8n
**Arquivo:** `comfyui-n8n-integration-guide.md`

Contém:
- Workflows completos para n8n
- Configuração de HTTP Request nodes
- Monitoramento via WebSocket
- Tratamento de erros
- Exemplos avançados (batch, webhooks, salvamento em cloud)

**Quando usar:** Implementar automação com n8n

---

### 4. 💻 Exemplos de Código
**Diretório:** `comfyui-examples/`

Contém scripts práticos em:
- Python (cliente básico, WebSocket, batch)
- JavaScript (Node.js)
- Bash
- n8n workflow JSON

**Quando usar:** Copiar e adaptar para seu projeto

---

## 🎯 Por Onde Começar

### Quer apenas entender o que é?
→ Leia o **Resumo Executivo** (5 minutos)

### Precisa implementar uma automação?
→ Leia o **Guia de Integração n8n** e use os **Exemplos de Código**

### Precisa de referência técnica completa?
→ Leia o **Relatório Completo**

---

## 🔗 Links Rápidos

### Documentação Oficial
- Site: https://docs.comfy.org
- GitHub: https://github.com/comfyanonymous/ComfyUI
- API Reference: https://docs.comfy.org/development/comfyui-server/comms_routes

### Ferramentas
- comfyui-cli: https://github.com/tokimwc/comfyui-cli
- comfyui-api-client: https://github.com/sugarkwork/Comfyui_api_client

### Comunidade
- Discord: https://discord.com/invite/comfyui
- Reddit: r/comfyui

---

## 📋 Principais Descobertas

### ✅ ComfyUI (não "ConfyUI")
- Interface visual baseada em nós para IA generativa
- API REST completa na porta 8188
- WebSocket para monitoramento em tempo real
- Totalmente open source e extensível

### 🎯 Principais Endpoints
- `POST /prompt` - Enviar workflow
- `GET /history/{id}` - Obter resultados
- `GET /object_info` - Listar nós
- `GET /view` - Baixar imagens
- `WS /ws` - Monitoramento

### 🔧 Integração com n8n
- HTTP Request nodes funcionam perfeitamente
- WebSocket requer Function Node customizado
- Ideal para pipelines de geração de conteúdo

---

## 🚀 Próximos Passos Sugeridos

1. **Instalar ComfyUI** localmente
2. **Criar workflow** simples (text-to-image)
3. **Salvar em API Format**
4. **Testar com curl** ou Python
5. **Integrar ao n8n** seguindo o guia

---

## 📝 Notas da Pesquisa

- **Data:** 20 de Abril de 2026
- **Fontes:** Documentação oficial, GitHub, blogs técnicos
- **Validação:** Informações cruzadas de múltiplas fontes
- **Status:** ✅ Pesquisa completa e validada

---

**Pesquisa realizada com Tavily API e fontes oficiais.**
