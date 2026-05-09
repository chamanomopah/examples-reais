# Advanced Keyword Researcher

Ferramenta de analise de nicho para YouTube. Coleta dados via YouTube Data API v3 e gera insights com Gemini LLM — ideal para planejamento de conteudo em canais faceless.

## Instalacao

```bash
pip install -r requirements.txt
```

API keys necessarias em `C:\Users\JOSE\.alfredo\.env`:
- `YOUTUBE_API_KEY` — YouTube Data API v3
- `GEMINI_API_KEY` — Google Gemini (gemini-2.5-flash)

## Uso

```bash
# Analise rapida (economy mode, ~103 quota units) — saida Excel (padrao)
py main.py "psychology"

# Analise completa (full mode, ~406 quota units)
py main.py "psychology of money" --full

# Sem LLM (economiza chamadas Gemini)
py main.py "psychology" --skip-llm

# Saida em markdown
py main.py "psychology" --format markdown

# Filtrar videos dos ultimos 30 dias
py main.py "psychology" --last-days 30
```

## Parametros

| Flag | Descricao |
|------|-----------|
| `--format` | `excel` (padrao), `markdown` ou `json` |
| `--full` | Full mode (~406 quota). Padrao: economy (~103) |
| `--skip-llm` | Pula analise Gemini |
| `--stdout` | Imprime no terminal em vez de salvar |
| `--output FILE` | Caminho customizado de saida |
| `--output-dir DIR` | Diretorio customizado de saida (incompativel com `--output`) |
| `--no-cache` | Ignora cache |
| `--cache-ttl H` | TTL do cache em horas (padrao: 24) |
| `--pages N` | Paginas de search (padrao: 2) |
| `--last-days N` | Filtra videos dos ultimos N dias (0=todos) |
| `--env-file FILE` | Caminho customizado do .env |

## Cache

```bash
py main.py clear-cache              # limpa tudo
py main.py clear-cache psychology   # limpa por keyword
```

## Consumo de Quota

| Modo | Por keyword | Keywords/dia (10K quota) |
|------|-------------|--------------------------|
| Economy (padrao) | ~103 | ~97 |
| Full | ~406 | ~24 |
| Cache hit | 0 | Ilimitado |

## Pipeline de Processamento

1. **Search** — busca videos por keyword (order: date + viewCount no full mode)
2. **Stats** — coleta views, likes, comments, duracao, idioma
3. **Channel Stats** — subs, total views, video count por canal
4. **Filters** — remove videos nao-ingleses (Shorts ja excluidos via `videoDuration=medium` na requisicao)
5. **Scoring** — trend, opportunity, views median, duration, market saturation
6. **Outlier Detection** — outlierMultiplier (views vs media do canal), 5x+ opportunities
7. **Title DNA** — n-grams (bigramas/trigramas) com TF-IDF ranking, lift de performance, padroes estruturais (regex) com correlacao outlier
8. **Engagement** — top 15 videos por outlierMultiplier com eng rate
9. **LLM Analysis** — topics, audience intent, psychographics (Gemini 2.5 Flash)
10. **Output** — Excel (11 abas), markdown ou JSON

## Output Excel (11 abas)

| Aba | Conteudo |
|-----|----------|
| Overview | Scores principais, competition, saturation |
| Channels | Top 60 canais com subs, avg views (mean/median), ratio |
| Outliers | Videos por outlierMultiplier |
| Small Outliers | Outliers de canais <100K subs |
| Opportunities | Videos 5x+ acima da media com angulo extraido |
| Title DNA - Words | Top 15 n-grams (bigramas/trigramas) por TF-IDF, com views medias e lift de performance |
| Title DNA - Patterns | Padroes estruturais (regex) com avg multiplier, outlier rate e avg views |
| Engagement | Top 15 engajamento com sinal (Fraco/Normal/Bom/Excelente) |
| Audience | Intent, pain points, motivacoes, psychographics |
| Topics | Discovered + suggested topics com potencial |
| Insights | Resumo LLM do nicho |

## Arquitetura

| Arquivo | Responsabilidade |
|---------|-----------------|
| `main.py` | CLI + orquestracao |
| `config.py` | Constantes, thresholds, configuracao de cache |
| `collector.py` | Coleta de dados (YouTube Data API v3) |
| `scorer.py` | Scoring (trend, opportunity, median, duration, market, title DNA, channel stats) |
| `analyzer.py` | Analise via Gemini LLM (topics, audience, psychographics, audience size) |
| `formatter.py` | Formatacao unificada (excel, markdown, json) |
| `cache.py` | Cache baseado em arquivo (JSON) |

Resultados em `output/` · Cache em `.cache/`
