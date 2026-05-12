"""CLI entry point for advanced_keyword_researcher."""

import os
import re
import sys
from datetime import datetime, timezone, timedelta

import click

from config import load_env, MAX_PAGES, CACHE_DIR, CACHE_TTL_HOURS, VIDEO_DURATION_FILTER, DEFAULT_MODEL, AVAILABLE_GEMINI_MODELS
from cache import load_cache, save_cache, clear_cache, get_cache_path
from collector import (
    YouTubeCollector,
    format_duration,
    format_relative_time,
)
from scorer import (
    compute_velocity,
    compute_trend_score,
    compute_opportunity_score,
    compute_views_median,
    compute_channel_view_median,
    compute_duration_analysis,
    compute_market_analysis,
    build_channels,
    classify_channel_size,
    analyze_title_dna,
)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("keyword")
@click.option("--format", "output_fmt", type=click.Choice(["json", "markdown", "excel"], case_sensitive=False), default="excel", help="Output format (default: excel)")
@click.option("--output", "output_file", type=click.Path(), default=None, help="Save to specific file path")
@click.option("--stdout", "use_stdout", is_flag=True, default=False, help="Force output to terminal")
@click.option("--skip-llm", is_flag=True, default=False, help="Skip LLM analysis")
@click.option("--pages", default=MAX_PAGES, type=int, help="Max search pages")
@click.option("--env-file", default=None, type=click.Path(), help="Path to .env file")
@click.option("--full", is_flag=True, default=False, help="Full mode (~406 quota units, more precise)")
@click.option("--no-cache", "no_cache", is_flag=True, default=False, help="Force fresh API calls, ignore cache")
@click.option("--cache-ttl", "cache_ttl", default=CACHE_TTL_HOURS, type=int, help="Cache TTL in hours (default: 24)")
@click.option("--last-days", "last_days", default=0, type=int, help="Filter videos published in the last N days (0=all time, 30 or 90 common)")
@click.option("--from", "date_from", default=None, type=str, help="Start date YYYY-MM-DD (mutually exclusive with --last-days)")
@click.option("--to", "date_to", default=None, type=str, help="End date YYYY-MM-DD (default: today, mutually exclusive with --last-days)")
@click.option("--output-dir", "output_dir", default=None, type=click.Path(), help="Custom output directory (mutually exclusive with --output)")
@click.option("--model", "llm_model", default=DEFAULT_MODEL, type=click.Choice(list(AVAILABLE_GEMINI_MODELS.keys()), case_sensitive=False), help=f"AI model for LLM analysis (default: {DEFAULT_MODEL})")
def research(
    keyword: str,
    output_fmt: str,
    output_file: str | None,
    use_stdout: bool,
    skip_llm: bool,
    pages: int,
    env_file: str | None,
    full: bool,
    no_cache: bool,
    cache_ttl: int,
    last_days: int,
    date_from: str | None,
    date_to: str | None,
    output_dir: str | None,
    llm_model: str,
):
    # Validate --output-dir / --output mutual exclusivity
    if output_dir and output_file:
        click.echo("Error: --output-dir is mutually exclusive with --output", err=True)
        sys.exit(1)

    env = load_env(env_file)
    yt_api_key = env["YOUTUBE_API_KEY"]
    gemini_api_key = env["GEMINI_API_KEY"]
    economy = not full

    if not yt_api_key:
        click.echo("Error: YOUTUBE_API_KEY not found in .env", err=True)
        sys.exit(1)

    # --- Cache check ---
    use_cache = not no_cache
    cached_data = None

    # --- Compute publishedAfter / publishedBefore ---
    published_after = None
    published_before = None
    period_label = None  # for filenames and logs

    # Validate mutual exclusivity
    if last_days > 0 and (date_from or date_to):
        click.echo("Error: --last-days is mutually exclusive with --from/--to", err=True)
        sys.exit(1)

    if last_days > 0:
        cutoff = datetime.now(timezone.utc) - timedelta(days=last_days)
        published_after = cutoff.strftime("%Y-%m-%dT00:00:00Z")
        period_label = f"{last_days}d"
        click.echo(f"Filtering videos from last {last_days} days...", err=True)
    elif date_from or date_to:
        # Parse --from
        if date_from:
            try:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                click.echo(f"Error: --from date must be YYYY-MM-DD, got '{date_from}'", err=True)
                sys.exit(1)
            published_after = dt_from.strftime("%Y-%m-%dT00:00:00Z")
        else:
            # --to alone: from 365 days before --to
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            dt_from = dt_to - timedelta(days=365)
            published_after = dt_from.strftime("%Y-%m-%dT00:00:00Z")

        # Parse --to (default: today)
        if date_to:
            try:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            except ValueError:
                click.echo(f"Error: --to date must be YYYY-MM-DD, got '{date_to}'", err=True)
                sys.exit(1)
        else:
            dt_to = datetime.now(timezone.utc)

        # publishedBefore is the day AFTER --to (exclusive boundary)
        published_before = (dt_to + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00Z")

        # Build compact label for filenames
        from_str = date_from or dt_from.strftime("%Y-%m-%d")
        to_str = date_to or dt_to.strftime("%Y-%m-%d")
        period_label = f"{from_str}_to_{to_str}"
        click.echo(f"Filtering videos from {from_str} to {to_str}...", err=True)

    if use_cache:
        cached_data = load_cache(keyword, CACHE_DIR, cache_ttl, last_days, date_from, date_to)
        if cached_data:
            age_hours = 0.0
            try:
                cached_at = datetime.fromisoformat(
                    cached_data["cached_at"].replace("Z", "+00:00")
                )
                age_hours = (
                    datetime.now(timezone.utc) - cached_at
                ).total_seconds() / 3600
            except Exception:
                pass
            if age_hours < 1:
                click.echo(
                    f"Using cached result (cached {int(age_hours * 60)} minutes ago)",
                    err=True,
                )
            else:
                click.echo(
                    f"Using cached result (cached {int(age_hours)} hours ago)",
                    err=True,
                )
            response = cached_data["response"]
        else:
            click.echo("Cache miss, fetching from API...", err=True)
    else:
        click.echo("Cache disabled, fetching from API...", err=True)

    # --- Economy mode status ---
    if full:
        click.echo("Full mode: ~406 quota units estimated", err=True)
    else:
        click.echo("Economy mode (default): ~103 quota units estimated", err=True)

    # --- If we have cached data, skip API calls ---
    if cached_data:
        _output_response(response, output_fmt, output_file, keyword, use_stdout, last_days, economy, skip_llm, date_from, date_to, output_dir)
        return

    click.echo(f"Researching: {keyword} (en/US)", err=True)

    collector = YouTubeCollector(yt_api_key)

    if economy:
        # Economy: single search, viewCount order
        click.echo("Searching videos (view count order, economy)...", err=True)
        view_videos, result_count = collector.search_videos(keyword, "viewCount", pages, published_after=published_after, published_before=published_before, video_duration=VIDEO_DURATION_FILTER)
        date_videos = []
    else:
        # Full: two searches, pages each
        click.echo("Searching videos (date order)...", err=True)
        date_videos, result_count = collector.search_videos(keyword, "date", pages, published_after=published_after, published_before=published_before, video_duration=VIDEO_DURATION_FILTER)

        click.echo("Searching videos (view count order)...", err=True)
        view_videos, _ = collector.search_videos(keyword, "viewCount", pages, published_after=published_after, published_before=published_before, video_duration=VIDEO_DURATION_FILTER)

    # Merge and deduplicate by videoId
    all_video_map: dict[str, dict] = {}
    for v in date_videos + view_videos:
        vid = v["videoId"]
        if vid not in all_video_map:
            all_video_map[vid] = v

    all_videos = list(all_video_map.values())
    click.echo(f"Found {len(all_videos)} unique videos", err=True)

    if not all_videos:
        click.echo("No videos found.", err=True)
        sys.exit(1)

    # Step 3: Get video stats
    click.echo("Fetching video stats...", err=True)
    all_video_ids = [v["videoId"] for v in all_videos]
    video_stats = collector.get_video_stats(all_video_ids)

    # Step 4: Get channel stats
    click.echo("Fetching channel stats...", err=True)
    all_channel_ids = list(set(v["channelId"] for v in all_videos))
    channel_stats = collector.get_channel_stats(all_channel_ids)

    # Step 5: Enrich videos with stats
    now = datetime.now(timezone.utc)
    for v in all_videos:
        vid = v["videoId"]
        stats = video_stats.get(vid, {})
        v["viewCount"] = stats.get("viewCount", 0)
        v["likeCount"] = stats.get("likeCount", 0)
        v["commentCount"] = stats.get("commentCount", 0)
        v["lengthSeconds"] = stats.get("lengthSeconds", 0)
        v["isShort"] = stats.get("isShort", False)
        v["duration"] = format_duration(stats.get("lengthSeconds", 0))
        v["defaultAudioLanguage"] = stats.get("defaultAudioLanguage", "")

        ch_stats = channel_stats.get(v["channelId"], {})
        v["channelInfo"] = ch_stats

        # Compute days ago and viewsPerDay
        pub = v.get("publishedAt", "")
        try:
            pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            days_ago = max(0.125, (now - pub_dt).total_seconds() / 86400)
        except Exception:
            days_ago = 0.125
        v["daysAgo"] = days_ago
        v["viewsPerDay"] = v["viewCount"] / days_ago
        v["published"] = format_relative_time(pub)

        # Compute viewSubRatio (outlierMultiplier computed later with median)
        subs = ch_stats.get("subscriberCount", 0)
        if subs > 0:
            v["viewSubRatio"] = v["viewCount"] / subs
        else:
            v["viewSubRatio"] = 0.0
        v["isViewSubOutlier"] = v["viewSubRatio"] > 1.0
        v["isChannelOutlier"] = v["isViewSubOutlier"]
        v["channelSize"] = classify_channel_size(subs)

    # Step 5.1: Compute per-channel median views for outlierMultiplier
    click.echo("Computing per-channel view medians...", err=True)
    channel_median_map = compute_channel_view_median(all_videos)

    # Inject median into channel_stats (keep mean separate)
    for cid, median_views in channel_median_map.items():
        if cid in channel_stats:
            channel_stats[cid]["avgViewsPerVideoMedian"] = median_views
            mean_views = channel_stats[cid].get("avgViewsPerVideoMean", 0)
            if mean_views > 0 and median_views > 0:
                channel_stats[cid]["meanMedianRatio"] = round(mean_views / median_views, 1)

    # Compute outlierMultiplier using median (preferred) or mean fallback
    for v in all_videos:
        ch_stats = v.get("channelInfo", {})
        avg_ch_views = ch_stats.get("avgViewsPerVideoMedian", 0)
        if avg_ch_views <= 0:
            avg_ch_views = ch_stats.get("avgViewsPerVideoMean", 0)
        if avg_ch_views > 0:
            v["outlierMultiplier"] = v["viewCount"] / avg_ch_views
        else:
            v["outlierMultiplier"] = 0.0

    # Step 5.4: Filter non-English videos
    # - Skip if defaultAudioLanguage is set and not en
    # - Also skip if title contains non-Latin characters (catches mislabeled videos)
    import re as _re
    _has_non_latin = _re.compile(r'[^\x00-\x7F]')
    pre_lang_count = len(all_videos)
    filtered_videos = []
    for v in all_videos:
        lang = v.get("defaultAudioLanguage", "")
        if lang and not lang.startswith("en"):
            continue
        if _has_non_latin.search(v.get("title", "")):
            continue
        filtered_videos.append(v)
    all_videos = filtered_videos
    lang_filtered = pre_lang_count - len(all_videos)
    if lang_filtered > 0:
        click.echo(f"Filtered out {lang_filtered} non-English videos, {len(all_videos)} remaining", err=True)

    # Step 5.5: Filter out Shorts
    pre_filter_count = len(all_videos)
    all_videos = [v for v in all_videos if not v.get("isShort", False) and v.get("lengthSeconds", 0) > 60]
    filtered_count = pre_filter_count - len(all_videos)
    if filtered_count > 0:
        click.echo(f"Filtered out {filtered_count} shorts, {len(all_videos)} videos remaining", err=True)

    # Rebuild video maps after Shorts filter
    all_video_map: dict[str, dict] = {}
    for v in all_videos:
        vid = v["videoId"]
        if vid not in all_video_map:
            all_video_map[vid] = v

    # Step 5.6: Post-filter safety net for date range
    if last_days > 0:
        before_count = len(all_videos)
        all_videos = [v for v in all_videos if v.get("daysAgo", 999) <= last_days]
        click.echo(f"Time filter: kept {len(all_videos)}/{before_count} videos from last {last_days} days", err=True)

        # Rebuild video maps after time filter
        all_video_map: dict[str, dict] = {}
        for v in all_videos:
            vid = v["videoId"]
            if vid not in all_video_map:
                all_video_map[vid] = v
    elif date_from or date_to:
        before_count = len(all_videos)
        filtered = []
        for v in all_videos:
            pub = v.get("publishedAt", "")
            if not pub:
                continue
            try:
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            except Exception:
                continue
            if date_from:
                dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                if pub_dt < dt_from:
                    continue
            if date_to:
                dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
                if pub_dt >= dt_to:
                    continue
            filtered.append(v)
        all_videos = filtered
        click.echo(f"Time filter: kept {len(all_videos)}/{before_count} videos in date range", err=True)

        # Rebuild video maps after time filter
        all_video_map: dict[str, dict] = {}
        for v in all_videos:
            vid = v["videoId"]
            if vid not in all_video_map:
                all_video_map[vid] = v

    # Step 6: Compute scores
    click.echo("Computing scores...", err=True)

    # In economy mode, date_videos is empty so use view_videos for velocity
    velocity_source = date_videos if date_videos else view_videos
    velocity_source = [v for v in velocity_source if not v.get("isShort", False) and v.get("lengthSeconds", 0) > 60]
    velocity_data = compute_velocity(velocity_source)
    trend_score = compute_trend_score(velocity_data)

    # Build opportunity-only video list (viewCount ordered search results)
    opp_videos = []
    for v in view_videos:
        vid = v["videoId"]
        if vid in all_video_map:
            opp_videos.append(all_video_map[vid])

    opportunity_score_data = compute_opportunity_score(opp_videos)

    opp_score_out = {
        "score": opportunity_score_data["score"],
        "category": opportunity_score_data["category"],
    }

    views_median = compute_views_median(opp_videos)
    duration_analysis = compute_duration_analysis(opp_videos)
    market_analysis = compute_market_analysis(result_count)
    channels = build_channels(all_videos, channel_stats)

    # --- New v2 computations ---
    # Title DNA
    title_dna = analyze_title_dna(opp_videos)

    # Outlier videos: all opp_videos (sorted by viewCount already from search)
    import math
    outlier_videos = []
    for v in opp_videos:
        mult = v.get("outlierMultiplier", 0)
        if mult and not (math.isinf(mult) or math.isnan(mult)):
            outlier_videos.append(v)

    # Engagement data: top 15 by outlierMultiplier
    engagement_sorted = sorted(outlier_videos, key=lambda x: x.get("outlierMultiplier", 0), reverse=True)
    engagement_data = []
    for v in engagement_sorted[:15]:
        views = v.get("viewCount", 0)
        likes = v.get("likeCount", 0)
        eng_rate = 0.0
        if views > 0 and likes > 0:
            eng_rate = (likes / views) * 100
        engagement_data.append({
            "title": v.get("title", ""),
            "viewCount": views,
            "likeCount": likes,
            "engagementRate": eng_rate,
        })
    # --- End new v2 computations ---

    # Step 7: LLM analysis
    topics_and_trends = None
    if not skip_llm and gemini_api_key:
        click.echo(f"Running LLM analysis... (model: {llm_model})", err=True)
        try:
            from analyzer import build_prompt, call_llm, assemble_topics_and_trends

            top_videos = sorted(
                all_videos, key=lambda x: x.get("viewsPerDay", 0), reverse=True
            )
            scores_dict = {
                "trend": trend_score,
                "opportunity": opportunity_score_data,
                "viewsMedian": views_median,
                "durationAnalysis": duration_analysis,
                "marketAnalysis": market_analysis,
            }
            prompt = build_prompt(keyword, top_videos, scores_dict)
            llm_response = call_llm(prompt, gemini_api_key, llm_model)
            topics_and_trends = assemble_topics_and_trends(
                llm_response, views_median["median"], market_analysis["saturation"]
            )
        except Exception as e:
            click.echo(f"LLM analysis failed: {e}", err=True)
            topics_and_trends = None

    # Step 8: Assemble and output
    click.echo("Building response...", err=True)
    from formatter import build_response
    response = build_response(
        query=keyword,
        velocity_data=velocity_data,
        opportunity_data=opportunity_score_data,
        channels=channels,
        trend_score=trend_score,
        opp_score=opp_score_out,
        views_median=views_median,
        duration_analysis=duration_analysis,
        market_analysis=market_analysis,
        topics_and_trends=topics_and_trends,
        title_dna=title_dna,
        outlier_videos=outlier_videos,
        engagement_data=engagement_data,
    )

    # Save to cache
    if use_cache:
        click.echo("Saving to cache...", err=True)
        save_cache(keyword, CACHE_DIR, response, last_days, date_from, date_to)

    _output_response(response, output_fmt, output_file, keyword, use_stdout, last_days, economy, skip_llm, date_from, date_to, output_dir)


def _sanitize_keyword(keyword: str) -> str:
    """Convert keyword to a safe filename component (lowercase, max 30 chars)."""
    safe = re.sub(r"[^\w\-]", "_", keyword.lower())
    safe = re.sub(r"_+", "_", safe).strip("_")
    return (safe[:30] if len(safe) > 30 else safe) or "untitled"


def _build_filename(keyword: str, last_days: int, economy: bool, skip_llm: bool, ext: str, date_from: str | None = None, date_to: str | None = None) -> str:
    kw = _sanitize_keyword(keyword)
    if date_from or date_to:
        period = f"{date_from or 'unknown'}_to_{date_to or 'unknown'}"
    elif last_days > 0:
        period = f"{last_days}d"
    else:
        period = "all"
    parts = [kw, period]
    if not economy:
        parts.append("full")
    if skip_llm:
        parts.append("nollm")
    return "_".join(parts) + f".{ext}"


def _output_response(
    response: dict,
    fmt: str,
    output_file: str | None,
    keyword: str,
    use_stdout: bool,
    last_days: int = 0,
    economy: bool = False,
    skip_llm: bool = False,
    date_from: str | None = None,
    date_to: str | None = None,
    output_dir: str | None = None,
):
    from formatter import format_output

    result = format_output(response, fmt)

    # Resolve output directory
    if output_file:
        save_dir = None
    elif output_dir:
        save_dir = output_dir
        os.makedirs(save_dir, exist_ok=True)
    else:
        save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
        os.makedirs(save_dir, exist_ok=True)

    if isinstance(result, bytes):
        ext = "xlsx"
        if use_stdout:
            sys.stdout.buffer.write(result)
            return
        if output_file:
            save_path = output_file
        else:
            filename = _build_filename(keyword, last_days, economy, skip_llm, ext, date_from, date_to)
            save_path = os.path.join(save_dir, filename)
        with open(save_path, "wb") as f:
            f.write(result)
        click.echo(f"Saved to {save_path}", err=True)
        return

    ext = "md" if fmt == "markdown" else "json"
    if use_stdout:
        sys.stdout.buffer.write(result.encode("utf-8"))
        sys.stdout.buffer.write(b"\n")
        return
    if output_file:
        save_path = output_file
    else:
        filename = _build_filename(keyword, last_days, economy, skip_llm, ext, date_from, date_to)
        save_path = os.path.join(save_dir, filename)
    with open(save_path, "w", encoding="utf-8") as f:
        f.write(result)
    click.echo(f"Saved to {save_path}", err=True)


@cli.command("clear-cache")
@click.argument("keyword", required=False)
def clear_cache_cmd(keyword: str | None):
    """Clear cache files. Optionally specify a keyword to clear only that cache."""
    count = clear_cache(CACHE_DIR, keyword)
    if keyword:
        if count:
            click.echo(f"Deleted cache for '{keyword}'", err=True)
        else:
            click.echo(f"No cache found for '{keyword}'", err=True)
    else:
        if count:
            click.echo(f"Deleted {count} cache file(s)", err=True)
        else:
            click.echo("No cache files found", err=True)


# Backwards compatibility: default to research command if first arg is not a known subcommand
if __name__ == "__main__":
    import sys as _sys
    _args = _sys.argv[1:]
    if not _args or _args[0] != "clear-cache":
        # Prepend "research" so `python main.py psychology --markdown` still works
        _sys.argv.insert(1, "research")
    cli()
