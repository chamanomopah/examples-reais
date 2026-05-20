# Scripts Python

Scripts essenciais do sistema de produção automatizada de vídeos faceless.

## Local
`.alfredo/.scripts/`

## Execução

Todos executam a partir de `.scripts/`:

```bash
cd C:\Users\JOSE\.alfredo\.scripts & python <script>.py [args]
```

## Dependências

**Python:**
- `yt-dlp` — scraper e download
- `youtube-transcript-api` — transcrições
- `opencv-python` — extração de frames
- `requests` + `websockets` — integração ComfyUI
- `deepgram-sdk` — transcrição com timestamps

**Bun:**
- (nenhum script TypeScript atualmente)

API keys em `C:\Users\JOSE\.alfredo\.env`:
- `DEEPGRAM_API_KEY` — transcribe_deepgram.py
- `ELEVENLABS_API_KEY` — elevenlabs_tts.py
- `KIE_AI_API_KEY` — banana.py, veo.py

> **NOTA:** Todos os vídeos gerados são em inglês (narração voiceover). Configurações default refletem isso.

## Exemplos Práticos

### channel_videos_scraper.py
Lista top vídeos do canal por views

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python channel_videos_scraper.py "https://www.youtube.com/@canal/videos"
cd C:\Users\JOSE\.alfredo\.scripts & python channel_videos_scraper.py "https://www.youtube.com/@canal/videos" --limit 10
```

**Edge cases:**
```bash
# URL com / no final (funciona igual)
cd C:\Users\JOSE\.alfredo\.scripts & python channel_videos_scraper.py "https://www.youtube.com/@canal/videos/"

# Channel ID em vez de @
cd C:\Users\JOSE\.alfredo\.scripts & python channel_videos_scraper.py "https://www.youtube.com/channel/UCxxxxxxxxxxxxxx"

# Salvar resultado em JSON
cd C:\Users\JOSE\.alfredo\.scripts & python channel_videos_scraper.py "@canal" --output "C:\Users\JOSE\alfredo\canal1\videos\top_videos.json"
```

### video_downloader.py
Baixa vídeo do YouTube

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "https://youtu.be/VIDEO_ID"
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "https://youtu.be/VIDEO_ID" --output "C:\Users\JOSE\alfredo\canal1\videos\video1\video.mp4"
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "https://youtu.be/VIDEO_ID" --quality 1080
```

**Edge cases:**
```bash
# Qualidades disponíveis: best, 1080, 720, 480
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "VIDEO_ID" --quality 720

# Caminho com espaços (use aspas)
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "VIDEO_ID" --output "C:\Users\JOSE\alfredo\meu canal\videos\video 1.mp4"

# Apenas ID do vídeo (sem URL completa)
cd C:\Users\JOSE\.alfredo\.scripts & python video_downloader.py "dQw4w9WgXcQ"
```

### video_cutter.py
Corta vídeos por timestamp

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "C:\Users\JOSE\alfredo\canal1\videos\video1\video.mp4" --start "00:00:10" --end "00:01:30"
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "video.mp4" -s 10 -e 90 --output "clip.mp4"
```

**Edge cases:**
```bash
# Timestamp em segundos apenas
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "video.mp4" -s 30 -e 125

# Formato MM:SS (sem horas)
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "video.mp4" --start "1:20" --end "5:45"

# Caminho relativo
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "..\videos\video.mp4" -s 0 -e 60

# Do início até um ponto (end só)
cd C:\Users\JOSE\.alfredo\.scripts & python video_cutter.py "video.mp4" --end "00:02:00"
```

### frames_extractor.py
Extrai frames de vídeos

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python frames_extractor.py "https://youtu.be/VIDEO_ID"
cd C:\Users\JOSE\.alfredo\.scripts & python frames_extractor.py "C:\Videos\video.mp4" --frames 10
```

**Edge cases:**
```bash
# Vídeo local com caminho relativo
cd C:\Users\JOSE\.alfredo\.scripts & python frames_extractor.py "..\..\videos\video.mp4"

# Extrair frames com intervalo específico
cd C:\Users\JOSE\.alfredo\.scripts & python frames_extractor.py "video.mp4" --interval 5

# YouTube Shorts
cd C:\Users\JOSE\.alfredo\.scripts & python frames_extractor.py "https://www.youtube.com/shorts/VIDEO_ID"
```

### thumbnail_downloader.py
Baixa thumbnail de vídeo

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "https://youtu.be/VIDEO_ID"
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "https://youtu.be/VIDEO_ID" --quality maxres --output "thumb.jpg"
```

**Edge cases:**
```bash
# Qualidades: maxres, high, medium, default
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "VIDEO_ID" --quality high

# Apenas ID
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "dQw4w9WgXcQ"

# Salvar em pasta específica
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "VIDEO_ID" --output "C:\Users\JOSE\alfredo\canal1\thumbs\video1.jpg"

# Auto-fallback (se maxres não existir, tenta high)
cd C:\Users\JOSE\.alfredo\.scripts & python thumbnail_downloader.py "VIDEO_ID" --quality maxres
```

### transcript_downloader.py
Baixa transcrição de vídeo

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python transcript_downloader.py "https://youtu.be/VIDEO_ID"
```

**Edge cases:**
```bash
# Vídeo sem transcrição (retorna erro)
cd C:\Users\JOSE\.alfredo\.scripts & python transcript_downloader.py "VIDEO_ID_SEM_LEGENDA"

# URL completa do YouTube
cd C:\Users\JOSE\.alfredo\.scripts & python transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Shorts
cd C:\Users\JOSE\.alfredo\.scripts & python transcript_downloader.py "https://www.youtube.com/shorts/VIDEO_ID"
```

### transcribe_deepgram.py
Transcreve áudio/vídeo com timestamps (cache automático)

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "C:\Users\JOSE\alfredo\canal1\videos\video1\audio.wav"
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.wav" -l pt -f srt -o "legendas.srt"
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.mp3" --no-cache
```

**Edge cases:**
```bash
# Idiomas disponíveis: pt, pt-br, pt-pt, en, es, fr, de, it, ja, nl, hi, ru, multi
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.wav" -l es

# Formatos: text, srt, json
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.wav" -f json -o "transcricao.json"

# Arquivo já transcrito (usa cache - mais rápido)
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.wav"

# Forçar nova transcrição (ignora cache)
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "audio.wav" --no-cache

# Vídeo (extrais áudio automaticamente)
cd C:\Users\JOSE\.alfredo\.scripts & python transcribe_deepgram.py "video.mp4" -l pt
```

### split_script.py
Divide roteiro em chunks (50 linhas por chunk, padrão) ou único arquivo de sentenças

**Básico (chunks):**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "C:\Users\JOSE\alfredo\canal1\videos\video1\script.md"
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "script.md" --output "C:\Users\JOSE\alfredo\canal1\videos\video1\chunks"
```

**Dividir por sentenças (arquivo único):**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "script.md" --sentences
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "script.md" -s -o "chunks"
```

**Edge cases:**
```bash
# Script com formatação complexa (remove ##, *, -, ** automaticamente)
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "script_sujo.md"

# Caminho relativo
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "..\..\canal1\videos\video1\script.md"

# Script com abreviações (Dr, Mr, etc) - não divide no meio
cd C:\Users\JOSE\.alfredo\.scripts & python split_script.py "script_medico.md" --sentences
```

### join_files.py
Junta arquivos de uma pasta em um único arquivo (ordem crescente natural)

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "C:\Users\JOSE\alfredo\canal3\videos\video1\img_prompt_chuncks" --output "image_prompt.md"
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/" --output "script_unido.md"
```

**Edge cases:**
```bash
# Salvar em outra pasta
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/" --output "result.md" --output-dir "C:\Users\JOSE\alfredo\output"

# Padrão de arquivo customizado
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/" --pattern "*.txt"

# Sem separador entre arquivos
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/" --separator ""

# Separador customizado
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/" --separator "---"

# Ordem natural: chunk_1.md, chunk_2.md, chunk_10.md (não chunk_1, chunk_10, chunk_2)
cd C:\Users\JOSE\.alfredo\.scripts & python join_files.py "chunks/"
```

### run_workflow.py
Executor de workflows ComfyUI (auto-incremento ativo)

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py --list
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py kokoro --output-dir "C:\Users\JOSE\alfredo\canal1\videos\video1\audio"
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo --name "minha_imagem"
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py kokoro kokorogenerator.text="Texto para falar"
```

**Edge cases:**
```bash
# Auto-incremento (cria image_1, image_2, image_3... automaticamente)
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo
# Resultado: z-image-turbo_1.png, z-image-turbo_2.png, z-image-turbo_3.png

# Múltiplos parâmetros
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo cliptextencode.text="gato astronauta" emptysd3latentimage.width=1024 emptysd3latentimage.height=1024

# Output dir com espaços
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py kokoro --output-dir "C:\Users\JOSE\alfredo\meu canal\audio"

# Sem auto-update de config
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo --no-update

# Nome customizado (não usa auto-incremento)
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py z_image_turbo --name "thumbnail_final"
# Resultado: thumbnail_final_00001.png (ComfyUI adiciona sufixo)

# Parâmetro com espaços (sem aspas no valor)
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py kokoro kokorogenerator.text=Texto longo para falar

# Workflows disponíveis: z_image_turbo, kokoro
cd C:\Users\JOSE\.alfredo\.scripts & python run_workflow.py --list
```

### update_workflow_config.py
Auto-gera workflow_config.json

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python update_workflow_config.py
```

**Edge cases:**
```bash
# Executa após adicionar novo workflow em workflows_api_converted/
cd C:\Users\JOSE\.alfredo\.scripts & python update_workflow_config.py

# Recria config do zero (se workflow_config.json foi corrompido)
cd C:\Users\JOSE\.alfredo\.scripts & python update_workflow_config.py
```

### build_masterfile.py
Gera masterfile.json sincronizando imagens, áudio e timestamps

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python build_masterfile.py --script "script.md" --transcript "transcript.txt" --image-dir "image/" --audio "audio.mp3"
cd C:\Users\JOSE\.alfredo\.scripts & python build_masterfile.py --script "script.md" --transcript "transcript.txt" --image-dir "image/" --audio "audio.mp3" --output "masterfile.json"
```

**Edge cases:**
```bash
# Transcript em formato WebVTT (padrão Deepgram/ComfyUI)
cd C:\Users\JOSE\.alfredo\.scripts & python build_masterfile.py --script "C:\Videos\script.md" --transcript "C:\Videos\transcript.txt" --image-dir "C:\Videos\images" --audio "C:\Videos\narracao.mp3"

# Masterfile em outra pasta
cd C:\Users\JOSE\.alfredo\.scripts & python build_masterfile.py --script "script.md" --transcript "transcript.txt" --image-dir "image/" --audio "audio.mp3" --output "../canal1/videos/video1/masterfile.json"
```

### render_from_masterfile.py
Renderiza vídeo com FFmpeg a partir de masterfile.json

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python render_from_masterfile.py --masterfile "masterfile.json"
cd C:\Users\JOSE\.alfredo\.scripts & python render_from_masterfile.py --masterfile "masterfile.json" --output "video_final.mp4"
```

**Edge cases:**
```bash
# Resolução customizada
cd C:\Users\JOSE\.alfredo\.scripts & python render_from_masterfile.py --masterfile "masterfile.json" --width 1920 --height 1080

# FPS diferente
cd C:\Users\JOSE\.alfredo\.scripts & python render_from_masterfile.py --masterfile "masterfile.json" --fps 60

# Método de renderização complex (mais controle sobre timing)
cd C:\Users\JOSE\.alfredo\.scripts & python render_from_masterfile.py --masterfile "masterfile.json" --method complex
```

### storyboard_to_timeline.py
Converte storyboard markdown em timeline HTML horizontal com 3 camadas

**Formato do storyboard (3 sub-camadas por Scene):**
```markdown
Scene 01
Time: 00:00:00.000 - 00:00:15.000
Narration: ...

Layer 1 - A-Roll:
  Type: ai_video
  Visual: ...
  Camera: ...
  Assets: ...

Layer 2 - B-Roll GFX:
  (vazio se não houver)

Layer 3 - Overlay:
  Type: lower_third
  Visual: ...
  TimeIn: 00:00:06.800
  TimeOut: 00:00:10.500
```

**Regras de camadas:**
| Combinação | Válido? |
|------------|---------|
| A-Roll alone | ✅ |
| A-Roll + Overlay | ✅ |
| B-Roll alone | ✅ |
| B-Roll + Overlay | ❌ Overlay depende de A-Roll |
| Todas as 3 juntas | ❌ |

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_timeline.py "storyboard.md"
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_timeline.py "storyboard.md" --output "timeline.html"
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_timeline.py "storyboard.md" --title "Meu Vídeo"
```

**Validação:**
O script valida combinações de camadas e lança erro se:
- Layer 3 (Overlay) existe sem Layer 1 (A-Roll)
- Layer 2 (B-Roll) tem Overlay
- Todas as 3 camadas juntas

**Edge cases:**
```bash
# Output em outra pasta
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_timeline.py "storyboard.md" --output "C:\Users\JOSE\alfredo\canal1\timeline.html"

# Caminho relativo
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_timeline.py "..\canal1\videos\test\storyboard.md"
```

### storyboard_to_remotion.py
Converte storyboard markdown em projeto Remotion completo (React + TypeScript)

**Formato do storyboard:**
```markdown
Scene 01
Time: 00:00:00.000 - 00:00:05.000
Type: ai_video | gfx_persistent | gfx_insert
Layer: 1 | 2
Narration: Texto da narração
Visual: Descrição visual
Camera: Ângulo da câmera
Assets: Lista de assets
```

**Básico:**
```bash
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_remotion.py "storyboard.md"
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_remotion.py "storyboard.md" --output "meu_projeto"
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_remotion.py "storyboard.md" --fps 60
```

**Estrutura gerada:**
```
meu_projeto/
├── src/
│   ├── index.ts                    # Ponto de entrada
│   ├── Root.tsx                    # Registro de composições
│   ├── types/storyboard.d.ts       # Tipos TypeScript
│   ├── compositions/Storyboard.tsx # Componente visual
│   └── data/storyboard.json        # Dados das cenas
├── out/                            # Output de renders
├── package.json
├── tsconfig.json
└── remotion.config.ts
```

**Usar o projeto gerado:**
```bash
cd meu_projeto
bun install
bun start     # Abre Remotion Studio (http://localhost:3000)
bun run build # Renderiza vídeo
```

**Layers:**
- `Layer: 1` ou `Type: ai_video/gfx_persistent` → A-roll (base)
- `Layer: 2` ou `Type: gfx_insert` → B-roll (overlay)

**Edge cases:**
```bash
# FPS customizado (default: 30)
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_remotion.py "storyboard.md" --fps 60

# Output em caminho absoluto
cd C:\Users\JOSE\.alfredo\.scripts & python storyboard_to_remotion.py "storyboard.md" --output "C:\Users\JOSE\alfredo\canal1\videos\test\remotion"
```

### banana.py
Geração de imagens com Nano Banana 2 (Gemini 3.1 Flash Image).

**Requisitos:** Python 3.10+, API key em `KIE_AI_API_KEY` do `.env`.

```bash
# Saldo de créditos
python banana.py credits

# Gerar imagem
python banana.py image "a cat in space" --ratio 16:9 --res 2K

# Gerar e esperar resultado
python banana.py image "a cat in space" --wait --output image.png
```

**Flags:**
| Flag | Opções |
|------|--------|
| `--ratio` | auto, 1:1, 3:2, 2:3, 16:9, 9:16 |
| `--res` | 1K, 2K, 4K |
| `--fmt` | png, jpg, webp |
| `--wait` | Aguarda conclusão |
| `--output` | Salvar imagem em caminho específico |

### veo.py
Geração de vídeos com Veo 3.1 (Fast/Quality).

**Requisitos:** Python 3.10+, API key em `KIE_AI_API_KEY` do `.env`.

```bash
# Saldo de créditos
python veo.py credits

# Gerar vídeo do texto (Veo 3.1 Fast)
python veo.py video "a dog playing in a park" --fast

# Imagem para vídeo
python veo.py video "make the person wave" --image https://example.com/img.jpg

# First/Last frames (transição)
python veo.py video "transition" --first frame1.jpg --last frame2.jpg

# Ingredients/Materiais (1-3 referências)
python veo.py video "character in this style" --ingredients char.jpg style.jpg bg.jpg

# Status da tarefa
python veo.py status abc123

# Link de download
python veo.py download "https://storage.kie.ai/..."
```

**Flags de vídeo:**
| Flag | Descrição |
|------|-----------|
| `--fast` | Usa modelo veo3_fast (rápido, barato) |
| `--quality` | Usa modelo veo3 (alta qualidade) |
| `--ratio` | 16:9, 9:16, Auto |
| `--image URL` | Imagem única (image-to-video) |
| `--first URL --last URL` | Primeiro e último frame (transição) |
| `--ingredients URL...` | 1-3 imagens de referência (estilo/personagem) |
| `--seeds N` | Seed 10000-99999 (reprodutibilidade) |
| `--wait` | Aguarda conclusão da tarefa |
| `--1080p` | Upgrade para 1080p após conclusão |
| `--4k` | Upgrade para 4K após conclusão |
| `--no-translate` | Desabilita tradução automática |

**Modos de geração de vídeo:**
| Modo | Imagens | Descrição |
|------|--------|-----------|
| `TEXT_2_VIDEO` | 0 | Prompt texto apenas |
| `FIRST_AND_LAST_FRAMES_2_VIDEO` | 1-2 | 1 imagem = animar imagem; 2 imagens = transição entre frames |
| `REFERENCE_2_VIDEO` | 1-3 | Ingredients/materiais para estilo e personagem (veo3_fast only) |

### Imagens Base
Imagens low-poly 3D para consistência de estilo em `~/.alfredo/.templates/images_base/`:

| Arquivo | Categoria |
|---------|-----------|
| `humans_base.png` | Humanos |
| `objects_base.png` | Objetos |
| `vehicles_base.png` | Veículos |
| `environments_base.png` | Cenários |

### elevenlabs_tts.py
Gera áudio Text-to-Speech usando ElevenLabs API. Lê API key de `~/.alfredo/.env`.

**Básico:**
```bash
# Texto direto
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --text "Olá mundo" --voice rachel

# De arquivo .md com SSML
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --input script.md --output audio.mp3

# Output automático em diretório
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --input script.md --output-dir "./output"

# Modo interativo
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --interactive
```

**SSML suportado (pausas, ênfase):**
```markdown
Texto com pause.<break time="1s" />
Outro texto.<break time="0.5s" />
```

**Flags principais:**
| Flag | Descrição | Default |
|------|-----------|---------|
| `--text`, `-t` | Texto para converter | - |
| `--input`, `-i` | Arquivo de entrada (.txt, .md) | - |
| `--output`, `-o` | Arquivo de saída | output.mp3 |
| `--output-dir`, `-d` | Diretório de saída (nome derivado do input) | - |
| `--voice`, `-v` | Nome da voz ou ID | rachel |
| `--model`, `-m` | Modelo | eleven_multilingual_v2 |

**Voice settings:**
| Flag | Descrição | Default |
|------|-----------|---------|
| `--stability` | Estabilidade 0-1 | 0.5 |
| `--similarity` | Similaridade 0-1 | 0.75 |
| `--style` | Estilo 0-1 | 0.0 |
| `--no-boost` | Desabilitar speaker boost | False |
| `--seed` | Seed determinística | - |

**Listagens:**
```bash
# Vozes disponíveis
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --list-voices

# Modelos disponíveis
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --list-models

# Formatos de saída
cd C:\Users\JOSE\.alfredo\.scripts & python elevenlabs_tts.py --list-formats
```

**Vozes populares:**
| Nome | Descrição |
|------|-----------|
| rachel | Feminino, americano, suave |
| drew | Masculino, americano, profundo |
| mimi | Feminino, expressivo |
| emily | Feminino, americano |
| katie | Feminino, americano |
| josh | Masculino, americano |
| adam | Masculino, jovem |

## Lista de Scripts

| Script | Função |
|--------|--------|
| `channel_videos_scraper.py` | Lista top vídeos do canal por views |
| `video_downloader.py` | Baixa vídeo do YouTube (URL ou ID) |
| `video_cutter.py` | Corta vídeos por timestamp (início/fim) |
| `frames_extractor.py` | Extrai frames de vídeos (URL ou local) |
| `thumbnail_downloader.py` | Baixa thumbnail de vídeo YouTube |
| `transcript_downloader.py` | Baixa transcrição de vídeo YouTube |
| `transcribe_deepgram.py` | Transcreve áudio/vídeo (Deepgram). Cache automático por hash do arquivo. Flags: `-l` idioma, `-f` formato, `-o` saída, `--no-cache` |
| `split_script.py` | Divide roteiro em sentenças/chunks |
| `join_files.py` | Junta arquivos de uma pasta em um único arquivo |
| `run_workflow.py` | Executor de workflows ComfyUI |
| `update_workflow_config.py` | Auto-gera workflow_config.json |
| `build_masterfile.py` | Gera masterfile.json (sync imagens + áudio + timestamps) |
| `render_from_masterfile.py` | Renderiza vídeo com FFmpeg via masterfile.json |
| `storyboard_to_timeline.py` | Converte storyboard markdown em timeline HTML horizontal |
| `storyboard_to_remotion.py` | Converte storyboard markdown em projeto Remotion completo |
| `utils.py` | Utilitários ComfyUI (server, websocket, IO) |
| `advanced_keyword_researcher.py` | Análise de nicho YouTube (wrapper CLI) |
| `elevenlabs_tts.py` | Gera áudio TTS via ElevenLabs API |
| `banana.py` | Geração de imagens (Nano Banana 2) |
| `veo.py` | Geração de vídeos (Veo 3.1 Fast/Quality) |

## Subdiretórios

- `workflows_api_converted/` — JSONs de workflows ComfyUI (Z-IMAGE-TURBO, KOKORO)
- `advanced_keyword_researcher/` — módulo de pesquisa de keywords (collector, scorer, analyzer, cache)
