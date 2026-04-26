# Scripts - Quick Reference

## 1. channel_videos_scraper.py
Lista top vídeos do canal por views (decrescente).

```bash
py channel_videos_scraper.py "URL"
py channel_videos_scraper.py "URL" -l 5
py channel_videos_scraper.py "URL" -od "C:\output" -o videos.json
```

| Flag | Descrição |
|------|-----------|
| `-l` | Número de vídeos (default: 3) |
| `-od` | Diretório de saída |
| `-o` | Nome do arquivo JSON |

---

## 2. frames_extractor.py
Extrai frames de vídeos (URL ou local).

```bash
py frames_extractor.py "URL"
py frames_extractor.py "C:\video.mp4"
py frames_extractor.py "URL" --frames 10
py frames_extractor.py "URL" -od "C:\output"
```

| Flag | Descrição |
|------|-----------|
| `--frames` | N frames distribuídos |
| `-fps` | Frames por segundo (default: 1) |
| `-od` | Diretório de saída |

---

## 3. thumbnail_downloader.py
Baixa thumbnail de vídeo YouTube.

```bash
py thumbnail_downloader.py "URL"
py thumbnail_downloader.py "URL" -q maxres
py thumbnail_downloader.py "URL" -od "C:\output" -o thumb.jpg
```

| Flag | Descrição |
|------|-----------|
| `-q` | Qualidade: maxres/high/medium/default |
| `-od` | Diretório de saída |
| `-o` | Nome do arquivo |

---

## 4. transcript_downloader.py
Baixa transcrição de vídeo YouTube.

```bash
py transcript_downloader.py "URL"
py transcript_downloader.py "URL" -l pt
py transcript_downloader.py "URL" -od "C:\output"
```

| Flag | Descrição |
|------|-----------|
| `-l` | Idioma (pt, en, auto) |
| `-od` | Diretório de saída |
| `-o` | Nome do arquivo (default: transcript.txt) |
| `--no-display` | Só salva, não mostra |

---

## 5. run_workflow.py
Executor de workflows ComfyUI.

```bash
py run_workflow.py --list
py run_workflow.py z_image_turbo prompt="gato"
py run_workflow.py workflow -o "C:\output" -n nome
```

| Flag | Descrição |
|------|-----------|
| `--list` | Lista workflows disponíveis |
| `-od/-o` | Diretório de saída |
| `-n` | Nome base do arquivo |
| `--no-update` | Não auto-atualiza config |
