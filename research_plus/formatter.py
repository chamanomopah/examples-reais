"""Output formatting."""

import math

from scorer import format_number


def build_response(
    query: str,
    velocity_data: dict,
    opportunity_data: dict,
    channels: list[dict],
    trend_score: dict,
    opp_score: dict,
    views_median: dict,
    duration_analysis: dict,
    market_analysis: dict,
    topics_and_trends: dict | None,
    title_dna: dict | None = None,
    outlier_videos: list[dict] | None = None,
    engagement_data: list[dict] | None = None,
) -> dict:
    return {
        "query": query,
        "trendScore": trend_score,
        "opportunityScore": opp_score,
        "opportunityData": opportunity_data,
        "velocityData": velocity_data,
        "viewsMedian": views_median,
        "durationAnalysis": duration_analysis,
        "marketAnalysis": market_analysis,
        "channels": channels[:60],
        "topicsAndTrends": topics_and_trends,
        "titleDna": title_dna,
        "outlierVideos": outlier_videos,
        "engagementData": engagement_data,
    }


def format_markdown(resp: dict) -> str:
    lines: list[str] = []
    query = resp.get("query", "")
    lines.append(f"# Research Report: {query}")
    lines.append("")

    ts = resp.get("trendScore", {})
    os_ = resp.get("opportunityScore", {})
    od = resp.get("opportunityData", {})
    vm = resp.get("viewsMedian", {})
    da = resp.get("durationAnalysis", {})
    ma = resp.get("marketAnalysis", {})
    channels = resp.get("channels", [])
    tat = resp.get("topicsAndTrends", {})

    # Key Metrics
    lines.append("## Metricas Principais")
    lines.append("")
    lines.append("| Metrica | Valor |")
    lines.append("|---------|-------|")
    lines.append(f"| Trend Score | {ts.get('score', 0)}/100 ({ts.get('category', '')}) |")
    # Velocity rows
    velocities = ts.get("velocities", {})
    lines.append(f"| Views Per Day | {format_number(velocities.get('day', 0))} |")
    lines.append(f"| Views/Ano | {format_number(velocities.get('year', 0))} |")
    lines.append(f"| Views/Mes | {format_number(velocities.get('month', 0))} |")
    lines.append(f"| Views/Semana | {format_number(velocities.get('week', 0))} |")
    growth = ts.get("growth", {})
    w2y = growth.get("weekToYear", 0)
    lines.append(f"| Growth | {w2y}x |")
    lines.append(f"| Opportunity Score | {os_.get('score', 0)}/100 ({os_.get('category', '')}) |")
    lines.append(f"| View:Sub Outliers | {od.get('outlierPercent', 0)}% |")
    lines.append(f"| Competition | {ma.get('saturation', '')} ({format_number(ma.get('resultCount', 0))} resultados) |")
    lines.append("")

    # Channel Size Distribution
    metrics = od.get("metrics", {})
    lines.append("## Channel Size Distribution")
    lines.append("")
    lines.append("| Size | Count | Percent |")
    lines.append("|------|-------|---------|")
    for size in ["micro", "small", "medium", "large"]:
        m = metrics.get(size, {})
        label = {"micro": "Micro (<10K)", "small": "Small (10K-100K)", "medium": "Medium (100K-500K)", "large": "Large (500K+)"}[size]
        lines.append(f"| {label} | {m.get('count', 0)} | {m.get('percent', 0)}% |")
    lines.append(f"| **Outlier Videos** | | {od.get('outlierPercent', 0)}% |")
    lines.append(f"| **Small Channel Combined** | | {od.get('smallChannelPercent_combined', 0)}% |")
    lines.append("")

    # Duration Analysis
    lines.append("## Duration Analysis")
    lines.append("")
    lines.append("| Metrica | Valor |")
    lines.append("|---------|-------|")
    lines.append(f"| Mediana de duracao | {da.get('medianDuration', '')} |")
    lines.append(f"| Mediana de views (search + algo) | {format_number(vm.get('median', 0))} |")
    lines.append(f"| Q1 views | {format_number(vm.get('q1', 0))} |")
    lines.append(f"| Q3 views | {format_number(vm.get('q3', 0))} |")
    lines.append(f"| IQR (consistencia) | {format_number(vm.get('q3', 0) - vm.get('q1', 0))} |")
    lines.append("")

    # Estimated Audience Size
    if tat:
        lines.append("## Estimated Audience Size")
        lines.append("")
        lines.append(f"**{format_number(tat.get('estimatedAudienceSize', 0))}** {tat.get('audienceSizeExplanation', '')}")
        lines.append("")

    # Top Channels
    ch_limit = min(len(channels), 60)
    lines.append(f"## Top {ch_limit} Channels -- Ordem por Views Seen")
    lines.append("")
    lines.append("| # | Canal | Views Seen | Avg Views (Mean) | Avg Views (Median) |")
    lines.append("|---|-------|------------|-----------------|-------------------|")
    for i, ch in enumerate(channels[:ch_limit], 1):
        cid = ch.get('channelId', '')
        title = ch.get('channelTitle', '')
        channel_link = f"[{title}](https://www.youtube.com/channel/{cid})" if cid else title
        mean_str = format_number(ch.get('avgViewsPerVideoMean', 0))
        median_val = ch.get('avgViewsPerVideoMedian', 0)
        median_str = format_number(median_val) if median_val > 0 else "-"
        lines.append(f"| {i} | {channel_link} | {format_number(ch.get('viewsSeen', 0))} | {mean_str} | {median_str} |")
    lines.append("")

    # --- NEW SECTIONS ---

    # Top Videos by Outlier Score
    opp_videos_all = resp.get("outlierVideos", [])
    if opp_videos_all:
        # Sort by outlierMultiplier descending, filter out 0/inf/nan
        valid_videos = []
        for v in opp_videos_all:
            mult = v.get("outlierMultiplier", 0)
            if mult and not (math.isinf(mult) or math.isnan(mult)):
                valid_videos.append(v)
        valid_videos.sort(key=lambda x: x.get("outlierMultiplier", 0), reverse=True)

        if valid_videos:
            lines.append("### Top Videos por Outlier Score")
            lines.append("")
            lines.append("| # | Titulo | Canal | Views | Subs | Mult. | Dias |")
            lines.append("|---|--------|-------|-------|------|-------|------|")
            for i, v in enumerate(valid_videos, 1):
                vid = v.get("videoId", "")
                title = v.get("title", "")
                title_link = f"[{title}](https://www.youtube.com/watch?v={vid})" if vid else title
                ch_title = v.get("channelTitle", "")
                ch_info = v.get("channelInfo", {})
                subs = ch_info.get("subscriberCount", 0)
                mult = v.get("outlierMultiplier", 0)
                days = round(v.get("daysAgo", 0))
                lines.append(
                    f"| {i} | {title_link} | {ch_title} | "
                    f"{format_number(v.get('viewCount', 0))} | {format_number(subs)} | "
                    f"**{mult:.1f}x** | {days} |"
                )
            lines.append("")

    # Small Channel Outliers (<100K subs)
    if opp_videos_all:
        small_outliers = [
            v for v in opp_videos_all
            if v.get("channelSize") in ("micro", "small")
            and v.get("outlierMultiplier", 0) >= 1.0
            and not (math.isinf(v.get("outlierMultiplier", 0)) or math.isnan(v.get("outlierMultiplier", 0)))
        ]
        small_outliers.sort(key=lambda x: x.get("outlierMultiplier", 0), reverse=True)

        if small_outliers:
            lines.append("### Outliers de Canais Pequenos (<100K inscritos)")
            lines.append("")
            lines.append("| # | Titulo | Canal | Views | Subs | Mult. | Dias | Tamanho |")
            lines.append("|---|--------|-------|-------|------|-------|------|---------|")
            for i, v in enumerate(small_outliers, 1):
                vid = v.get("videoId", "")
                title = v.get("title", "")
                title_link = f"[{title}](https://www.youtube.com/watch?v={vid})" if vid else title
                ch_title = v.get("channelTitle", "")
                ch_info = v.get("channelInfo", {})
                subs = ch_info.get("subscriberCount", 0)
                mult = v.get("outlierMultiplier", 0)
                days = round(v.get("daysAgo", 0))
                size = v.get("channelSize", "")
                size_label = "Micro" if size == "micro" else "Small"
                lines.append(
                    f"| {i} | {title_link} | {ch_title} | "
                    f"{format_number(v.get('viewCount', 0))} | {format_number(subs)} | "
                    f"**{mult:.1f}x** | {days} | {size_label} |"
                )
            lines.append("")

    # Outlier Videos (5x+)
    if opp_videos_all:
        outliers_5x = [
            v for v in opp_videos_all
            if v.get("outlierMultiplier", 0) >= 5.0
            and not (math.isinf(v.get("outlierMultiplier", 0)) or math.isnan(v.get("outlierMultiplier", 0)))
        ]
        outliers_5x.sort(key=lambda x: x.get("outlierMultiplier", 0), reverse=True)

        lines.append("### Oportunidades Reais (videos 5x+ acima da media do canal)")
        lines.append("")

        if not outliers_5x:
            lines.append("Nenhum video com outlier 5x+ encontrado.")
            lines.append("")
        else:
            lines.append("| Titulo | Canal | Views | Mult. | Angulo provavel |")
            lines.append("|--------|-------|-------|-------|-----------------|")

            import re
            STOPWORDS_SHORT = frozenset({
                "the", "of", "to", "and", "in", "is", "it", "you", "that", "a", "an",
                "for", "on", "with", "as", "at", "by", "this", "be", "are", "was",
                "from", "or", "but", "not", "what", "all", "were", "we", "when",
                "your", "can", "said", "there", "use", "each", "which", "she",
                "do", "how", "their", "if", "will", "up", "about", "out", "many",
                "then", "them", "these", "so", "some", "her", "would", "make", "like",
                "him", "into", "time", "has", "look", "two", "more", "write", "go",
                "see", "no", "way", "could", "people", "my", "than", "first", "water",
                "been", "call", "who", "oil", "its", "now", "find", "long", "down",
                "day", "did", "get", "come", "made", "may", "part",
            })

            for v in outliers_5x:
                vid = v.get("videoId", "")
                title = v.get("title", "")
                title_link = f"[{title}](https://www.youtube.com/watch?v={vid})" if vid else title
                ch_title = v.get("channelTitle", "")
                mult = v.get("outlierMultiplier", 0)

                # Extract angle: non-stopword words + keyword
                words = re.findall(r"[a-zA-Z]+", title.lower())
                angle_words = [w for w in words if w not in STOPWORDS_SHORT and len(w) > 1]
                angle = " + ".join(angle_words[:5]) if angle_words else title[:40]

                lines.append(
                    f"| {title_link} | {ch_title} | "
                    f"{format_number(v.get('viewCount', 0))} | {mult:.1f}x | {angle} |"
                )
            lines.append("")

    # Title DNA
    title_dna = resp.get("titleDna")
    if title_dna:
        lines.append("### Titulo DNA -- Padroes dos Titulos")
        lines.append("")

        # Word frequency (top 10)
        word_freq = title_dna.get("wordFrequency", [])[:10]
        if word_freq:
            lines.append("| Palavra | Vezes | O que sugere |")
            lines.append("|---------|-------|---------------|")
            suggestions = {
                "psychology": "base do nicho (esperado)",
                "people": "foco em comportamento humano",
                "who": "formato de identificacao",
                "signs": "promessa de revelacao",
                "habits": "conteudo pratico",
                "men": "segmento popular",
                "women": "segmento popular",
                "gen x": "segmento popular",
                "gen z": "segmento popular",
                "millennial": "segmento popular",
                "actually": "subversao de expectativa",
                "secret": "promessa de exclusividade",
                "hidden": "promessa de revelacao",
                "sign": "promessa de revelacao",
                "habit": "conteudo pratico",
                "man": "segmento popular",
                "woman": "segmento popular",
                "why": "curiosidade",
                "how": "tutorial/educativo",
                "dont": "comportamento negativo",
                "don't": "comportamento negativo",
                "never": "intensidade/urgencia",
                "always": "generalizacao poderosa",
                "narcissist": "topicos de personalidade",
                "narcissists": "topicos de personalidade",
                "introvert": "segmento de personalidade",
                "introverts": "segmento de personalidade",
                "extrovert": "segmento de personalidade",
                "extroverts": "segmento de personalidade",
            }
            for wf in word_freq:
                word = wf.get("word", "")
                count = wf.get("count", 0)
                suggestion = suggestions.get(word.lower(), "")
                lines.append(f"| {word.capitalize()} | {count} | {suggestion} |")
            lines.append("")

        # Title structure patterns
        title_patterns = title_dna.get("titlePatterns", [])
        if title_patterns:
            lines.append("| Formato | Exemplo | Frequencia |")
            lines.append("|---------|---------|------------|")
            for tp in title_patterns:
                lines.append(
                    f"| {tp.get('format', '')} | {tp.get('example', '')[:50]} | "
                    f"{tp.get('frequency', '')} |"
                )
            lines.append("")

        # Enhanced section (only if LLM data exists)
        tat = resp.get("topicsAndTrends")
        if tat:
            lines.append("**Enhanced (LLM):**")
            lines.append("")
            # Show suggested topics if available
            suggested = tat.get("suggestedTopics", [])
            if suggested:
                lines.append("| Angulo | Potencial |")
                lines.append("|--------|-----------|")
                for t in suggested:
                    if isinstance(t, dict):
                        lines.append(f"| {t.get('topic', '')} | {t.get('opportunity', '')} |")
                lines.append("")

    # Engagement
    engagement_data = resp.get("engagementData", [])
    if engagement_data:
        lines.append("### Engajamento dos Top Videos")
        lines.append("")

        lines.append("| Titulo | Views | Likes | Eng. Rate | Sinal |")
        lines.append("|--------|-------|-------|-----------|-------|")
        for e in engagement_data:
            title = e.get("title", "")
            views = e.get("viewCount", 0)
            likes = e.get("likeCount", 0)
            eng_rate = e.get("engagementRate", 0)

            if likes == 0:
                eng_str = "N/A"
                signal = "N/A"
            else:
                eng_str = f"{eng_rate:.1f}%"
                if eng_rate < 2.0:
                    signal = "Fraco"
                elif eng_rate < 4.0:
                    signal = "Normal"
                elif eng_rate < 6.0:
                    signal = "Bom"
                else:
                    signal = "Excelente"

            lines.append(
                f"| {title} | {format_number(views)} | "
                f"{format_number(likes)} | {eng_str} | {signal} |"
            )
        lines.append("")

    # --- END NEW SECTIONS ---

    if tat:
        # Discovered Topics
        discovered = tat.get("discoveredTopics", [])
        if discovered:
            lines.append("## Discovered Topics")
            lines.append("")
            lines.append("| Topico | Videos | Avg Views |")
            lines.append("|--------|--------|-----------|")
            for t in discovered:
                if isinstance(t, dict):
                    lines.append(f"| {t.get('topic', '')} | {t.get('frequency', '')} | {format_number(t.get('avgViews', 0))} |")
                else:
                    lines.append(f"| {t} | - | - |")
            lines.append("")

        # Suggested Content Angles
        suggested = tat.get("suggestedTopics", [])
        if suggested:
            lines.append("## Suggested Content Angles")
            lines.append("")
            lines.append("| Angulo | Potencial | Justificativa |")
            lines.append("|--------|-----------|---------------|")
            for t in suggested:
                if isinstance(t, dict):
                    lines.append(f"| {t.get('topic', '')} | {t.get('opportunity', '')} | {t.get('reasoning', '')} |")
                else:
                    lines.append(f"| {t} | - | - |")
            lines.append("")

        # Audience Intent
        intent = tat.get("audienceIntent", {})
        if intent:
            lines.append("## Audience Intent")
            lines.append("")
            if isinstance(intent, dict):
                lines.append(f"**Primary:** {intent.get('primaryIntent', '')}")
                lines.append("")
                secondary = intent.get("secondaryIntents", [])
                if secondary:
                    lines.append("**Secondary:**")
                    for s in secondary:
                        lines.append(f"- {s}")
                    lines.append("")
                pain = intent.get("painPoints", [])
                if pain:
                    lines.append("**Pain Points:**")
                    for p in pain:
                        lines.append(f"- {p}")
                    lines.append("")
                motiv = intent.get("motivations", [])
                if motiv:
                    lines.append("**Motivations:**")
                    for m in motiv:
                        lines.append(f"- {m}")
                    lines.append("")
            else:
                lines.append(str(intent))
                lines.append("")

        # Psychographics
        psycho = tat.get("psychographics", {})
        if psycho:
            lines.append("## Audience Psychographics")
            lines.append("")
            if isinstance(psycho, dict):
                interests = psycho.get("interests", [])
                if interests:
                    lines.append(f"**Interesses:** {', '.join(interests)}")
                    lines.append("")
                values = psycho.get("values", [])
                if values:
                    lines.append(f"**Values:** {', '.join(values)}")
                    lines.append("")
                prefs = psycho.get("contentPreferences", [])
                if prefs:
                    lines.append("**Content Preferences:**")
                    for p in prefs:
                        lines.append(f"- {p}")
                    lines.append("")
            else:
                for p in (psycho if isinstance(psycho, list) else [psycho]):
                    lines.append(f"- {p}")
                lines.append("")

        # Key Insights
        summary = tat.get("summary", "")
        if summary:
            lines.append("## Key Insights")
            lines.append("")
            lines.append(summary)
            lines.append("")

    return "\n".join(lines)
