"""Scoring algorithms."""

from datetime import datetime, timezone

import numpy as np

from config import CHANNEL_SIZE_THRESHOLDS, SATURATION_THRESHOLDS, DURATION_CATEGORIES, DURATION_SUGGESTIONS, MARKET_SUGGESTIONS


def compute_velocity(videos: list[dict]) -> dict:
    """Compute velocity data. 'week' and 'month' are LABELS, not time filters.
    Both include ALL videos (with viewsPerDay > 0), sorted by viewsPerDay descending."""
    all_entries = []

    for v in videos:
        vpd = v.get("viewsPerDay", 0.0)
        if vpd > 0:
            all_entries.append({
                "videoId": v.get("videoId", ""),
                "title": v.get("title", ""),
                "channelTitle": v.get("channelTitle", ""),
                "viewCount": v.get("viewCount", 0),
                "publishedAt": v.get("publishedAt", ""),
                "daysAgo": v.get("daysAgo", 0),
                "viewsPerDay": vpd,
            })

    all_entries.sort(key=lambda x: x["viewsPerDay"], reverse=True)

    return {"week": all_entries, "month": list(all_entries)}


def compute_trend_score(velocity_data: dict) -> dict:
    """Compute trend score using per-video median viewsPerDay."""
    videos = velocity_data["week"]  # same as month

    if not videos:
        return {"score": 0, "category": "Unknown", "velocities": {}, "growth": {}}

    vpd_values = [v["viewsPerDay"] for v in videos if v.get("viewsPerDay", 0) > 0]

    if not vpd_values:
        return {"score": 0, "category": "Unknown", "velocities": {}, "growth": {}}

    arr = np.array(vpd_values)

    median_vpd = float(np.median(arr))
    p25_vpd = float(np.percentile(arr, 25))
    p75_vpd = float(np.percentile(arr, 75))

    velocities = {
        "day": round(median_vpd),
        "week": round(median_vpd * 7),
        "month": round(median_vpd * 30),
        "year": round(median_vpd * 365),
    }

    # Growth ratio: compare recent videos vs older videos
    recent_vpd = [v["viewsPerDay"] for v in videos if v.get("daysAgo", 999) <= 30 and v.get("viewsPerDay", 0) > 0]
    older_vpd = [v["viewsPerDay"] for v in videos if v.get("daysAgo", 999) > 30 and v.get("viewsPerDay", 0) > 0]

    recent_median = float(np.median(recent_vpd)) if recent_vpd else median_vpd
    older_median = float(np.median(older_vpd)) if older_vpd else median_vpd

    if older_median > 0:
        weekToYear = round(recent_median / older_median, 2)
    else:
        weekToYear = 1.0

    growth = {
        "weekToYear": weekToYear,
        "recentMedianVpd": round(recent_median),
        "olderMedianVpd": round(older_median),
    }

    w2y = weekToYear
    score = min(100, round(w2y * 50))

    if w2y >= 2.0:
        category = "Accelerating"
    elif w2y >= 1.0:
        category = "Growing"
    elif w2y >= 0.5:
        category = "Stable"
    else:
        category = "Declining"

    return {
        "score": score,
        "category": category,
        "velocities": velocities,
        "growth": growth,
    }


def classify_channel_size(subscriber_count: int) -> str:
    if subscriber_count < CHANNEL_SIZE_THRESHOLDS["micro"]:
        return "micro"
    if subscriber_count < CHANNEL_SIZE_THRESHOLDS["small"]:
        return "small"
    if subscriber_count < CHANNEL_SIZE_THRESHOLDS["medium"]:
        return "medium"
    return "large"


def compute_opportunity_score(videos_with_channels: list[dict]) -> dict:
    """Compute opportunity score based on channel size distribution and outliers."""
    total = len(videos_with_channels)
    if total == 0:
        return {"score": 0, "category": "Poor", "metrics": {}, "outlierPercent": 0, "smallChannelPercent_combined": 0}

    counts = {"micro": 0, "small": 0, "medium": 0, "large": 0}
    outlier_count = 0

    for v in videos_with_channels:
        channel_info = v.get("channelInfo", {})
        subs = channel_info.get("subscriberCount", 0)
        size = classify_channel_size(subs)
        counts[size] += 1

        # Check if video is a view/sub outlier
        vsr = v.get("viewSubRatio", 0.0)
        if vsr > 1.0:
            outlier_count += 1

    metrics = {
        "micro": {"count": counts["micro"], "percent": round(counts["micro"] / total * 100, 1)},
        "small": {"count": counts["small"], "percent": round(counts["small"] / total * 100, 1)},
        "medium": {"count": counts["medium"], "percent": round(counts["medium"] / total * 100, 1)},
        "large": {"count": counts["large"], "percent": round(counts["large"] / total * 100, 1)},
    }

    combined = metrics["micro"]["percent"] + metrics["small"]["percent"]
    outlier_percent = round(outlier_count / total * 100, 1)

    if combined >= 80 and outlier_percent >= 25:
        score = 100
    elif combined >= 80:
        score = 90
    elif combined >= 70:
        score = 80
    elif combined >= 60:
        score = 70
    elif combined >= 50:
        score = 60
    elif combined >= 40:
        score = 50
    else:
        score = round(combined * 0.8)

    if score >= 90:
        category = "Excellent"
    elif score >= 70:
        category = "Good"
    elif score >= 50:
        category = "Fair"
    elif score >= 30:
        category = "Low"
    else:
        category = "Poor"

    return {
        "score": score,
        "category": category,
        "metrics": metrics,
        "outlierPercent": outlier_percent,
        "smallChannelPercent_combined": combined,
    }


def compute_channel_view_median(videos: list[dict], min_videos: int = 1) -> dict[str, float]:
    """Compute per-channel median view count from videos in the dataset.

    Returns dict mapping channelId -> median viewCount.
    Channels with fewer than min_videos are excluded (unreliable median).
    """
    from collections import defaultdict

    channel_views: dict[str, list[int]] = defaultdict(list)
    for v in videos:
        cid = v.get("channelId", "")
        views = v.get("viewCount", 0)
        if cid and views > 0:
            channel_views[cid].append(views)

    result: dict[str, float] = {}
    for cid, views in channel_views.items():
        if len(views) >= min_videos:
            arr = np.array(views, dtype=np.float64)
            result[cid] = float(np.median(arr))

    return result


def compute_views_median(videos: list[dict]) -> dict:
    """Compute median and quartiles of view counts."""
    views = [v.get("viewCount", 0) for v in videos if v.get("viewCount", 0) > 0]
    if not views:
        return {"median": 0, "min": 0, "max": 0, "q1": 0, "q3": 0}

    arr = np.array(views, dtype=np.float64)
    try:
        median_val = int(np.percentile(arr, 50, method="interpolated_inverted_cdf"))
        q1_val = int(np.percentile(arr, 25, method="interpolated_inverted_cdf"))
        q3_val = int(np.percentile(arr, 75, method="interpolated_inverted_cdf"))
    except Exception:
        median_val = int(np.percentile(arr, 50, method="nearest"))
        q1_val = int(np.percentile(arr, 25, method="nearest"))
        q3_val = int(np.percentile(arr, 75, method="nearest"))
    return {
        "median": median_val,
        "min": int(np.min(arr)),
        "max": int(np.max(arr)),
        "q1": q1_val,
        "q3": q3_val,
    }


def compute_duration_analysis(videos: list[dict]) -> dict:
    """Analyze video durations."""
    durations = []
    for v in videos:
        ls = v.get("lengthSeconds", 0)
        if ls > 0:
            durations.append(ls)

    if not durations:
        return {
            "medianDuration": "0:00",
            "avgDuration": "0:00",
            "medianSeconds": 0,
            "avgSeconds": 0,
            "minDuration": "0:00",
            "maxDuration": "0:00",
            "category": "Unknown",
            "suggestion": "",
        }

    from collector import format_duration

    median_s = int(np.percentile(durations, 50, method="linear"))
    avg_s = int(np.mean(durations))

    category = "Short-form"
    for threshold, cat in DURATION_CATEGORIES:
        if median_s < threshold:
            category = cat
            break

    return {
        "medianDuration": format_duration(median_s),
        "avgDuration": format_duration(avg_s),
        "medianSeconds": median_s,
        "avgSeconds": avg_s,
        "minDuration": format_duration(min(durations)),
        "maxDuration": format_duration(max(durations)),
        "category": category,
        "suggestion": DURATION_SUGGESTIONS.get(category, ""),
    }


def compute_market_analysis(result_count: int) -> dict:
    """Analyze market saturation."""
    if result_count < SATURATION_THRESHOLDS["Low"]:
        saturation = "Low"
    elif result_count < SATURATION_THRESHOLDS["Moderate"]:
        saturation = "Moderate"
    elif result_count < SATURATION_THRESHOLDS["Competitive"]:
        saturation = "Competitive"
    else:
        saturation = "Highly Saturated"

    return {
        "resultCount": result_count,
        "saturation": saturation,
        "suggestion": MARKET_SUGGESTIONS.get(saturation, ""),
    }


def build_channels(
    all_videos: list[dict], channel_stats_map: dict[str, dict]
) -> list[dict]:
    """Build deduplicated, enriched channel list sorted by viewsSeen."""
    channel_map: dict[str, dict] = {}

    for v in all_videos:
        cid = v.get("channelId", "")
        if not cid:
            continue

        if cid not in channel_map:
            stats = channel_stats_map.get(cid, {})
            channel_map[cid] = {
                "channelId": cid,
                "channelTitle": v.get("channelTitle", ""),
                "subscriberCount": stats.get("subscriberCount", 0),
                "totalViews": stats.get("totalViews", 0),
                "videoCount": stats.get("videoCount", 0),
                "avgViewsPerVideo": stats.get("avgViewsPerVideo", 0),
                "avgViewsPerVideoMean": stats.get("avgViewsPerVideoMean", 0),
                "avgViewsPerVideoMedian": stats.get("avgViewsPerVideoMedian", 0),
                "meanMedianRatio": stats.get("meanMedianRatio", 0),
                "videos": [],
                "viewsSeen": 0,
            }

        channel_map[cid]["videos"].append(
            {
                "videoId": v.get("videoId", ""),
                "title": v.get("title", ""),
                "viewCount": v.get("viewCount", 0),
            }
        )
        channel_map[cid]["viewsSeen"] += v.get("viewCount", 0)

    for ch in channel_map.values():
        vids = ch["videos"]
        ch["isShortsOnly"] = all(v.get("isShort", False) for v in vids) if vids else False
        ch["channelSize"] = classify_channel_size(ch["subscriberCount"])
        del ch["videos"]

    channels = list(channel_map.values())
    channels.sort(key=lambda x: x["viewsSeen"], reverse=True)
    return channels


def analyze_title_dna(videos: list[dict]) -> dict:
    """Analyze title patterns: word frequency, structure, and length stats."""
    import math
    import re
    from collections import Counter

    STOPWORDS = frozenset({
        "the", "of", "to", "and", "in", "is", "it", "you", "that", "a", "an",
        "for", "on", "with", "as", "at", "by", "this", "be", "are", "was",
        "from", "or", "but", "not", "what", "all", "were", "we", "when",
        "your", "can", "said", "there", "use", "an", "each", "which", "she",
        "do", "how", "their", "if", "will", "up", "about", "out", "many",
        "then", "them", "these", "so", "some", "her", "would", "make", "like",
        "him", "into", "time", "has", "look", "two", "more", "write", "go",
        "see", "no", "way", "could", "people", "my", "than", "first", "water",
        "been", "call", "who", "oil", "its", "now", "find", "long", "down",
        "day", "did", "get", "come", "made", "may", "part",
    })

    LIST_WORDS = frozenset({
        "things", "reasons", "ways", "habits", "signs", "rules", "steps",
        "types", "secrets", "mistakes", "facts", "tricks", "tips", "myths",
        "truths", "stages", "phases", "levels", "forms", "kinds",
    })

    ALL_CAPS_EXCLUDE = frozenset({
        "THE", "OF", "AND", "A", "I", "AN", "IN", "IS", "IT", "TO", "ON",
        "FOR", "AT", "BY", "OR", "AS", "BE", "DO", "WE", "HE", "SO", "NO",
        "IF", "UP", "US", "MY",
    })

    titled_videos = [v for v in videos if v.get("title", "")]
    titles = [v.get("title", "") for v in titled_videos]

    if not titles:
        return {
            "wordFrequency": [],
            "titlePatterns": [],
            "titleLengthStats": {"median": 0, "min": 0, "max": 0},
        }

    total_titles = len(titles)
    overall_avg_views = (
        sum(v.get("viewCount", 0) for v in titled_videos)
        / total_titles
        if total_titles else 1
    )

    # ── TF-IDF n-gram extraction ──

    # Build document frequency (DF) for each word
    word_df: Counter = Counter()
    title_words_list: list[list[str]] = []
    for title in titles:
        words = re.findall(r"[a-zA-Z]+", title.lower())
        title_words_list.append(words)
        unique_words = set(words)
        for w in unique_words:
            word_df[w] += 1

    # Calculate IDF for each word
    word_idf: dict[str, float] = {}
    for w, df in word_df.items():
        word_idf[w] = math.log(total_titles / (1 + df))

    # Extract n-grams and score with TF-IDF
    ngram_counter: Counter = Counter()
    ngram_views: dict[str, list[int]] = {}
    ngram_tfidf: dict[str, float] = {}

    for title, video in zip(titles, titled_videos):
        words = title_words_list[titles.index(title)]
        for n in (2, 3):
            for i in range(len(words) - n + 1):
                gram = tuple(words[i : i + n])
                if any(len(w) <= 1 for w in gram):
                    continue
                if all(w in STOPWORDS for w in gram):
                    continue
                phrase = " ".join(gram)
                ngram_counter[phrase] += 1
                views = video.get("viewCount", 0)
                ngram_views.setdefault(phrase, []).append(views)
                # TF-IDF: count * min(IDF of component words)
                min_idf = min(word_idf.get(w, 0) for w in gram)
                ngram_tfidf[phrase] = ngram_counter[phrase] * min_idf

    # Sort by TF-IDF score, take top 15
    top_ngrams = sorted(ngram_tfidf.items(), key=lambda x: x[1], reverse=True)[:15]
    word_frequency = []
    for phrase, tfidf_score in top_ngrams:
        count = ngram_counter[phrase]
        views_list = ngram_views[phrase]
        avg_views = sum(views_list) / len(views_list)
        lift = round(avg_views / overall_avg_views, 1) if count > 1 else None
        word_frequency.append({
            "word": phrase,
            "count": count,
            "avgViews": int(round(avg_views)),
            "lift": lift,
        })

    # ── Title length stats ──

    lengths = [len(t) for t in titles]
    lengths.sort()
    n = len(lengths)
    if n % 2 == 0:
        median_len = (lengths[n // 2 - 1] + lengths[n // 2]) // 2
    else:
        median_len = lengths[n // 2]

    title_length_stats = {
        "median": median_len,
        "min": min(lengths),
        "max": max(lengths),
    }

    # ── Structural pattern detection ──

    # Precompile regex patterns
    re_subtitle_sep = re.compile(r"[:—]|\s-\s")
    re_number_start = re.compile(r"^\d+")
    re_question = re.compile(r"\?$")
    re_ellipsis = re.compile(r"\.\.\.")
    re_all_caps = re.compile(r"\b[A-Z]{3,}\b")
    re_x_of_y = re.compile(r"\b\w+\s+of\s+\w+", re.IGNORECASE)
    re_trigger_consequence = re.compile(
        r"\b(if so|here's why|here's how|this is why|that's why)\b",
        re.IGNORECASE,
    )

    # Collect all pattern matches per title
    pattern_titles: dict[str, list[tuple[str, dict]]] = {}

    for title, video in zip(titles, titled_videos):
        lower = title.lower().strip()
        matched_patterns: list[str] = []

        # 1. [Keyword] of [Target]: [Subtitle]
        if re_subtitle_sep.search(title) and re_x_of_y.search(title):
            matched_patterns.append("[Keyword] of [Target]: [Subtitle]")

        # 2. [Question]?
        if re_question.search(title):
            matched_patterns.append("[Question]?")

        # 3. [N] [Things/Reasons/Ways/...]
        num_match = re_number_start.match(title)
        if num_match:
            after_num = title[num_match.end():].strip().lower()
            first_word = re.findall(r"[a-zA-Z]+", after_num)
            if first_word and first_word[0] in LIST_WORDS:
                matched_patterns.append("[N] [Things/Reasons/Ways...]")

        # 4. [Ellipsis]...
        if re_ellipsis.search(title):
            matched_patterns.append("[Ellipsis]...")

        # 5. [All Caps Word]
        caps_words = re_all_caps.findall(title)
        if any(w not in ALL_CAPS_EXCLUDE for w in caps_words):
            matched_patterns.append("[All Caps Word]")

        # 6. [Keyword] of [Target] (without subtitle separator)
        if re_x_of_y.search(title) and not re_subtitle_sep.search(title):
            matched_patterns.append("[Keyword] of [Target]")

        # 7. [Trigger] + [Consequence]
        if "?" in title and any(c.isalpha() for c in title[title.index("?") + 1:]):
            matched_patterns.append("[Trigger] + [Consequence]")
        elif re_trigger_consequence.search(lower):
            matched_patterns.append("[Trigger] + [Consequence]")

        # 8. Outro (fallback for titles with no matches)
        if not matched_patterns:
            matched_patterns.append("Outro")

        for pattern_key in matched_patterns:
            if pattern_key not in pattern_titles:
                pattern_titles[pattern_key] = []
            pattern_titles[pattern_key].append((title, video))

    # Build pattern stats with performance correlation
    total_pattern_matches = sum(len(v) for v in pattern_titles.values())
    title_patterns = []
    for pattern_key, entries in sorted(
        pattern_titles.items(), key=lambda x: len(x[1]), reverse=True
    ):
        count = len(entries)
        pct = round(count / total_titles * 100) if total_titles > 0 else 0

        # Performance correlation
        multipliers = []
        outlier_count = 0
        view_sums = 0
        for _, video in entries:
            mult = video.get("outlierMultiplier", 0)
            if mult and mult > 0 and not (math.isinf(mult) or math.isnan(mult)):
                multipliers.append(mult)
            if mult and mult >= 1.0:
                outlier_count += 1
            view_sums += video.get("viewCount", 0)

        avg_mult = round(sum(multipliers) / len(multipliers), 1) if multipliers else 0
        outlier_pct = round(outlier_count / count * 100) if count > 0 else 0
        avg_views = round(view_sums / count) if count > 0 else 0

        # Up to 2 examples (first two)
        examples = [e[0] for e in entries[:2]]

        title_patterns.append({
            "format": pattern_key,
            "example": examples[0] if examples else "",
            "example2": examples[1] if len(examples) > 1 else "",
            "frequency": f"{pct}%",
            "count": count,
            "avgMultiplier": avg_mult,
            "outlierRate": f"{outlier_pct}%",
            "avgViews": avg_views,
        })

    return {
        "wordFrequency": word_frequency,
        "titlePatterns": title_patterns,
        "titleLengthStats": title_length_stats,
    }


def format_number(n: int | float) -> str:
    """Format number as human-readable string."""
    n = float(n)
    if n >= 1_000_000_000:
        return f"{n / 1_000_000_000:.1f}B"
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        k_val = n / 1_000
        if k_val >= 1000:
            return f"{n / 1_000_000:.1f}M"
        return f"{k_val:.1f}K"
    return str(int(n))
