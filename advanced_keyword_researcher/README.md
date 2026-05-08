# Advanced Keyword Researcher

Ferramenta de análise de nicho para YouTube. Coleta dados via YouTube Data API v3 e gera insights com Gemini LLM — ideal para planejamento de conteúdo em canais faceless.

## Instalação

```bash
pip install -r requirements.txt
```

API keys necessárias em `C:\Users\JOSE\.alfredo\.env`:
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `GEMINI_API_KEY` — Google Gemini

## Uso

```bash
# Análise rápida (economy mode, ~103 quota units)
py advanced_keyword_researcher.py "psychology" --markdown

# Análise completa (full mode, ~406 quota units)
py advanced_keyword_researcher.py "psychology of money" --markdown --full

# Sem LLM (economiza chamadas Gemini)
py advanced_keyword_researcher.py "psychology" --skip-llm --markdown
```

## Parâmetros

| Flag | Descrição |
|------|-----------|
| `--markdown` | Saída em markdown (padrão: JSON) |
| `--full` | Full mode (~406 quota). Padrão: economy (~103) |
| `--skip-llm` | Pula análise Gemini |
| `--stdout` | Imprime no terminal em vez de salvar |
| `--output FILE` | Caminho customizado de saída |
| `--no-cache` | Ignora cache |
| `--cache-ttl H` | TTL do cache em horas (padrão: 24) |
| `--pages N` | Páginas de search no modo full (padrão: 2) |
| `--region CODE` | País alvo ISO 3166-1 alpha-2 (padrão: US) |
| `--last-days N` | Filtra vídeos dos últimos N dias |

## Cache

```bash
py advanced_keyword_researcher.py clear-cache              # limpa tudo
py advanced_keyword_researcher.py clear-cache psychology   # limpa por keyword
```

## Consumo de Quota

| Modo | Por keyword | Keywords/dia (10K quota) |
|------|-------------|--------------------------|
| Economy (padrão) | ~103 | ~97 |
| Full | ~406 | ~24 |
| Cache hit | 0 | Ilimitado |

## Arquitetura

| Arquivo | Responsabilidade |
|---------|-----------------|
| `main.py` | CLI + orquestração |
| `config.py` | Constantes, thresholds, configuração de cache |
| `collector.py` | Coleta de dados (YouTube Data API v3) |
| `scorer.py` | Algoritmos de scoring (trend, opportunity, median, duration, market) |
| `analyzer.py` | Análise via Gemini LLM (topics, audience, psychographics) |
| `formatter.py` | Montagem JSON + formatação markdown |
| `cache.py` | Cache baseado em arquivo |

Resultados em `output/` · Cache em `.cache/`
