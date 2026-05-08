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
- `youtube-transcript-api` — transcrições

API keys em `C:\Users\JOSE\.alfredo\.env` (apenas para advanced_keyword_researcher).

## Lista de Scripts

| Script | Função |
|--------|--------|
| `channel_videos_scraper.py` | Lista top vídeos do canal por views |
| `frames_extractor.py` | Extrai frames de vídeos (URL ou local) |
| `thumbnail_downloader.py` | Baixa thumbnail de vídeo YouTube |
| `transcript_downloader.py` | Baixa transcrição de vídeo YouTube |
| `split_script.py` | Divide roteiro em sentenças/chunks |
| `run_workflow.py` | Executor de workflows ComfyUI |
| `update_workflow_config.py` | Auto-gera workflow_config.json |
| `utils.py` | Utilitários ComfyUI (server, websocket, IO) |
| `advanced_keyword_researcher.py` | Análise de nicho YouTube (wrapper CLI) |

## Subdiretórios

- `workflows_api_converted/` — JSONs de workflows ComfyUI (Z-IMAGE-TURBO, KOKORO)
- `advanced_keyword_researcher/` — módulo de pesquisa de keywords (collector, scorer, analyzer, cache)

## Referência rápida

Ver `z_scripts.md` para exemplos de uso com flags.
