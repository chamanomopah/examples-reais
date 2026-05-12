# Scripts Python

Scripts essenciais do sistema de produção automatizada de vídeos faceless.

## Local
`.alfredo/.scripts/`

## Execução

Todos executam a partir de `.scripts/`:

```bash
py <script>.py [args]
```

## Dependências

- `yt-dlp` — scraper e download
- `youtube-transcript-api` — transcrições
- `opencv-python` — extração de frames
- `requests` + `websockets` — integração ComfyUI
- `deepgram-sdk` — transcrição com timestamps

API keys em `C:\Users\JOSE\.alfredo\.env`:
- `DEEPGRAM_API_KEY` — transcribe_deepgram.py

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
| `run_workflow.py` | Executor de workflows ComfyUI |
| `update_workflow_config.py` | Auto-gera workflow_config.json |
| `utils.py` | Utilitários ComfyUI (server, websocket, IO) |
| `advanced_keyword_researcher.py` | Análise de nicho YouTube (wrapper CLI) | |

## Subdiretórios

- `workflows_api_converted/` — JSONs de workflows ComfyUI (Z-IMAGE-TURBO, KOKORO)
- `advanced_keyword_researcher/` — módulo de pesquisa de keywords (collector, scorer, analyzer, cache)

## Referência rápida

Ver `z_scripts.md` para exemplos de uso com flags.
