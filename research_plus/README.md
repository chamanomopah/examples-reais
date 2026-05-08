# research_plus

Análise de nicho YouTube via API (YouTube Data API v3 + Gemini LLM).

## Setup

```bash
pip install -r requirements.txt
```

API keys em `C:\Users\JOSE\.alfredo\.env`:
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `GEMINI_API_KEY` — Google Gemini (LLM analysis)

## Uso

A partir de `.scripts/`:
```bash
py research_plus.py "psychology" --markdown
py research_plus.py "psychology of money" --markdown --full
py research_plus.py "psychology" --skip-llm --markdown
```

Diretamente em `research_plus/`:
```bash
python main.py "psychology" --markdown
```

### Flags

| Flag | Default | Descrição |
|------|---------|-----------|
| `--markdown` | off | Saída em markdown (default: JSON) |
| `--full` | off | Full mode (~406 quota units). Default: economy (~103) |
| `--skip-llm` | off | Pula análise Gemini |
| `--stdout` | off | Imprime no terminal em vez de salvar |
| `--output FILE` | auto | Caminho customizado de saída |
| `--no-cache` | off | Ignora cache |
| `--cache-ttl H` | 24 | TTL do cache em horas |
| `--pages N` | 2 | Páginas de search (modo full) |
| `--region CODE` | US | País alvo (ISO 3166-1 alpha-2) |
| `--last-days N` | 0 | Filtra vídeos dos últimos N dias |

### Cache

```bash
py research_plus.py clear-cache              # limpa todo cache
py research_plus.py clear-cache psychology   # limpa cache de 1 keyword
```

## Output

Arquivos salvos em `research_plus/output/`: `{keyword}_{periodo}[_full][_nollm].{ext}`

## Custo de Quota

| Modo | Unidades/keyword | Keywords/dia (10K quota) |
|------|-----------------|-------------------------|
| Economy (default) | ~103 | ~97 |
| Full | ~406 | ~24 |
| Cache hit | 0 | ilimitado |

## Estrutura

```
research_plus/
  main.py          CLI + orquestração
  config.py        Constants, thresholds, cache config
  collector.py     YouTube Data API v3
  scorer.py        Algoritmos (trend, opportunity, median, duration, market)
  analyzer.py      Gemini LLM (topics, audience, psychographics)
  formatter.py     JSON assembly + markdown
  cache.py         Cache file-based
  output/          Resultados salvos
  .cache/          Cache de queries
```
