# 🎯 SISTEMA COMFYUI - Resumo de Funcionalidades

## 📋 O que faz

Sistema automático para executar **workflows ComfyUI** com parâmetros customizáveis via linha de comando.

---

## 🚀 Funcionalidades Principais

### **1. Execução de Workflows**
```bash
python run_workflow.py <nome_workflow> [parâmetros...]
```

### **2. Auto-Detecção de Parâmetros**
- Escaneia automaticamente workflows JSON
- Detecta parâmetros modificáveis
- Cria arquivo de configuração automaticamente

### **3. Diretório de Saída Customizado**
```bash
-o "C:/projeto/imagens"     # Flag curta
--output-dir "C:/projeto"   # Flag longa
```

### **4. Nome de Arquivo Customizado**
```bash
-n "cena1"         # Flag curta
--name "cena1"     # Flag longa
```

### **5. Parâmetros Dinâmicos**
```bash
cliptextencode.text="prompt"
emptysd3latentimage.width=1920
ksampler.steps=8
```

---

## 🎨 Workflows Disponíveis

### **Z-IMAGE-TURBO** (Imagens)
- Geração de imagens com IA
- Resoluções: 512×512 até 1920×1080
- Controle de qualidade, seed, sampler

### **KOKORO** (Áudio/TTS)
- Text-to-speech em múltiplos idiomas
- Velocidade ajustável (0.5 - 2.0)
- Idiomas: Inglês, Português, Espanhol, Francês

---

## 📝 Exemplos Rápidos

```bash
# Listar workflows
python run_workflow.py --list

# Gerar imagem básica
python run_workflow.py z_image_turbo cliptextencode.text="um gato"

# Gerar imagem customizada
python run_workflow.py z_image_turbo \
  -o "C:/projeto/imagens" \
  -n "cena1" \
  cliptextencode.text="cidade futurista" \
  emptysd3latentimage.width=1920

# Gerar áudio
python run_workflow.py kokoro \
  -o "C:/projeto/audio" \
  -n "narração1" \
  kokorogenerator.text="Bem-vindo" \
  kokorogenerator.lang="Brazilian Portuguese"
```

---

## 📋 Parâmetros Principais

### **Z-IMAGE-TURBO**
| Parâmetro | Descrição | Exemplo |
|-----------|-----------|---------|
| `cliptextencode.text` | Prompt da imagem | "um carro vermelho" |
| `emptysd3latentimage.width` | Largura | 512, 768, 1920 |
| `emptysd3latentimage.height` | Altura | 512, 768, 1080 |
| `ksampler.steps` | Qualidade | 4-8 |
| `ksampler.seed` | Repetibilidade | 42, 123 |
| `-o` / `--output-dir` | Diretório de saída | "C:/projects/images" |
| `-n` / `--name` | Nome do arquivo | "scene1", "intro" |

### **KOKORO**
| Parâmetro | Descrição | Valores |
|-----------|-----------|---------|
| `kokorogenerator.text` | Texto para falar | Qualquer texto |
| `kokorogenerator.lang` | Idioma | "English", "Brazilian Portuguese", "Spanish", "French" |
| `kokorogenerator.speed` | Velocidade | 0.5 (lento) a 2.0 (rápido) |
| `-o` / `--output-dir` | Diretório de saída | "C:/projects/audio" |
| `-n` / `--name` | Nome do arquivo | "narration1", "voiceover" |

---

## 📁 Estrutura do Sistema

```
exemplos_reais/
├── run_workflow.py              ← Script principal (USE ESTE)
├── update_workflow_config.py    ← Automático (NÃO rode direto)
├── utils.py                     ← Funções auxiliares
├── workflows_api_converted/     ← Seus workflows JSON
├── workflow_config.json         ← Configuração auto-gerada
└── outputs/                     ← Resultados padrão
```

---

## 🔄 Como Adicionar Novo Workflow

1. **Coloque o arquivo JSON** em `workflows_api_converted/`
2. **Rode qualquer comando** - o sistema auto-detecta
3. **Use normalmente** com parâmetros

```bash
# O sistema cria config automaticamente na primeira execução
python run_workflow.py novo_workflow --list
```

---

## ✅ O que o sistema faz automaticamente

- 🔍 **Detecta novos workflows** na pasta
- 📝 **Cria/atualiza configurações** de parâmetros
- ✅ **Valida parâmetros** antes da execução
- 💾 **Salva arquivos** nos diretórios corretos
- ⚠️ **Avisa erros** de parâmetros desconhecidos
- 📊 **Mostra progresso** da execução
- 🏗️ **Cria diretórios** automaticamente

---

## 🎯 Workflow Típico de Produção

```bash
# 1. Gerar cena intro
python run_workflow.py z_image_turbo \
  -o "C:/alfredo/canal1/videos/video1/images" \
  -n "intro_scene" \
  cliptextencode.text="epic cinematic intro" \
  emptysd3latentimage.width=1920 \
  emptysd3latentimage.height=1080

# 2. Gerar narração
python run_workflow.py kokoro \
  -o "C:/alfredo/canal1/videos/video1/audio" \
  -n "intro_voiceover" \
  kokorogenerator.text="Bem-vindo ao nosso episódio especial" \
  kokorogenerator.lang="Brazilian Portuguese"

# 3. Gerar cenas do conteúdo
python run_workflow.py z_image_turbo \
  -o "C:/alfredo/canal1/videos/video1/images" \
  -n "scene1" \
  cliptextencode.text="tutorial content showing interface" \
  emptysd3latentimage.width=1920 \
  emptysd3latentimage.height=1080
```

---

## 🚀 Comandos Úteis

```bash
# Ver workflows disponíveis
python run_workflow.py --list

# Ver ajuda completa
python run_workflow.py --help

# Não auto-atualizar config (uso avançado)
python run_workflow.py workflow --no-update [parâmetros...]
```

---

## 📊 Resultados Validados

**✅ Testes Completados:**
- 10+ imagens geradas com resoluções variadas
- Múltiplos arquivos de áudio em diferentes idiomas
- Diretórios customizados funcionando perfeitamente
- Nomes de arquivos customizados validados
- Flags curtas (-o, -n) e longas funcionando

**🎯 Sistema 100% operacional e validado!**

---

**Pronto para uso em produção! 🎉**
