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


def compute_channel_view_median(videos: list[dict], min_videos: int = 3) -> dict[str, float]:
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

    DEMOGRAPHIC_WORDS = frozenset({
        "men", "women", "man", "woman", "gen x", "gen z", "millennial",
        "millennials", "boomer", "boomers", "elder", "older", "younger",
        "teen", "teens", "teenager", "teenagers", "kids", "boys", "girls",
        "introverts", "extroverts", "narcissist", "narcissists",
    })

    EMOTIONAL_TRIGGERS = frozenset({
        "signs", "habits", "actually", "terrifying", "hidden", "secret",
        "secrets", "shocking", "dangerous", "disturbing", "creepy",
        "warning", "mistake", "mistakes", "never", "always", "stop",
        "why", "truth", "reveals", "destroy", "manipulate", "toxic",
    })

    titles = [v.get("title", "") for v in videos if v.get("title", "")]

    if not titles:
        return {
            "wordFrequency": [],
            "titlePatterns": [],
            "titleLengthStats": {"median": 0, "min": 0, "max": 0},
        }

    # Word frequency
    word_counter: Counter = Counter()
    for title in titles:
        words = re.findall(r"[a-zA-Z]+", title.lower())
        for w in words:
            if w not in STOPWORDS and len(w) > 1:
                word_counter[w] += 1

    top_words = word_counter.most_common(15)
    word_frequency = [{"word": w, "count": c} for w, c in top_words]

    # Title length stats
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

    # Pattern detection
    pattern_counts: Counter = Counter()
    pattern_examples: dict[str, str] = {}

    for title in titles:
        lower = title.lower().strip()

        if re.match(r"^\d+", title):
            pattern_key = "[N] [Word]..."
            if pattern_key not in pattern_examples:
                pattern_examples[pattern_key] = title
            pattern_counts[pattern_key] += 1
        elif "psychology of" in lower:
            pattern_key = "Psychology of [Grupo]"
            if pattern_key not in pattern_examples:
                pattern_examples[pattern_key] = title
            pattern_counts[pattern_key] += 1
        elif any(d in lower for d in DEMOGRAPHIC_WORDS):
            pattern_key = "[Grupo] + [Comportamento]"
            if pattern_key not in pattern_examples:
                pattern_examples[pattern_key] = title
            pattern_counts[pattern_key] += 1
        elif any(t in lower for t in EMOTIONAL_TRIGGERS):
            pattern_key = "[Gatilho Emocional] + [Consequencia]"
            if pattern_key not in pattern_examples:
                pattern_examples[pattern_key] = title
            pattern_counts[pattern_key] += 1
        else:
            pattern_key = "Outro"
            if pattern_key not in pattern_examples:
                pattern_examples[pattern_key] = title
            pattern_counts[pattern_key] += 1

    total = sum(pattern_counts.values())
    title_patterns = []
    for pattern, count in pattern_counts.most_common():
        pct = round(count / total * 100) if total > 0 else 0
        title_patterns.append({
            "format": pattern,
            "example": pattern_examples.get(pattern, ""),
            "frequency": f"{pct}%",
            "count": count,
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
