"""YouTube Data API v3 collector."""

import re
import time
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

from config import BATCH_SIZE, BASE_DELAY, MAX_RETRIES


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, HttpError):
        return exc.resp.status in (403, 429)
    return False


@retry(
    stop=stop_after_attempt(MAX_RETRIES),
    wait=wait_exponential(multiplier=BASE_DELAY, min=1, max=30),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)
def _api_call(func, *args, **kwargs):
    result = func(*args, **kwargs)
    time.sleep(0.1)
    return result


class YouTubeCollector:
    def __init__(self, api_key: str):
        self.youtube = build("youtube", "v3", developerKey=api_key)

    def search_videos(
        self, keyword: str, order: str, max_pages: int = 2, published_after: str | None = None,
        published_before: str | None = None, video_duration: str | None = None,
    ) -> tuple[list[dict], int]:
        results: list[dict] = []
        total_results = 0
        next_page_token = None

        base_params = dict(
            part="snippet",
            type="video",
            q=keyword,
            order=order,
            maxResults=BATCH_SIZE,
            publishedAfter=published_after,
            publishedBefore=published_before,
            videoDuration=video_duration,
            relevanceLanguage="en",
            regionCode="US",
        )

        for page in range(max_pages):
            params = {**base_params}
            if next_page_token:
                params["pageToken"] = next_page_token
            request = self.youtube.search().list(**params)
            response = _api_call(request.execute)

            if page == 0:
                total_results = response.get("pageInfo", {}).get("totalResults", 0)

            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                vid = item.get("id", {}).get("videoId", "")
                thumbnails = snippet.get("thumbnails", {})
                results.append(
                    {
                        "videoId": vid,
                        "title": snippet.get("title", ""),
                        "channelId": snippet.get("channelId", ""),
                        "channelTitle": snippet.get("channelTitle", ""),
                        "publishedAt": snippet.get("publishedAt", ""),
                        "thumbnails": thumbnails.get("high", thumbnails.get("default", {})).get("url", ""),
                        "description": snippet.get("description", ""),
                    }
                )

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return results, total_results

    def get_video_stats(self, video_ids: list[str]) -> dict[str, dict]:
        result: dict[str, dict] = {}

        for i in range(0, len(video_ids), BATCH_SIZE):
            batch = video_ids[i : i + BATCH_SIZE]
            request = self.youtube.videos().list(
                part="statistics,contentDetails,snippet",
                id=",".join(batch),
            )
            response = _api_call(request.execute)

            for item in response.get("items", []):
                vid = item["id"]
                stats = item.get("statistics", {})
                details = item.get("contentDetails", {})
                duration_iso = details.get("duration", "PT0S")
                length_seconds = parse_duration(duration_iso)
                definition = details.get("definition", "")
                live = details.get("liveBroadcastContent", "")

                view_count = int(stats.get("viewCount", 0))

                result[vid] = {
                    "viewCount": view_count,
                    "likeCount": int(stats.get("likeCount", 0)),
                    "commentCount": int(stats.get("commentCount", 0)),
                    "lengthSeconds": length_seconds,
                    "isShort": length_seconds <= 60,
                    "definition": definition,
                    "liveBroadcastContent": live,
                    "defaultAudioLanguage": item.get("snippet", {}).get("defaultAudioLanguage", ""),
                }

        return result

    def get_channel_stats(self, channel_ids: list[str]) -> dict[str, dict]:
        result: dict[str, dict] = {}

        for i in range(0, len(channel_ids), BATCH_SIZE):
            batch = channel_ids[i : i + BATCH_SIZE]
            request = self.youtube.channels().list(
                part="statistics,snippet",
                id=",".join(batch),
            )
            response = _api_call(request.execute)

            for item in response.get("items", []):
                cid = item["id"]
                stats = item.get("statistics", {})
                sub_count = int(stats.get("subscriberCount", 0))
                total_views = int(stats.get("viewCount", 0))
                video_count = int(stats.get("videoCount", 0))
                avg_views = round(total_views / video_count, 1) if video_count > 0 else 0.0

                result[cid] = {
                    "subscriberCount": sub_count,
                    "totalViews": total_views,
                    "videoCount": video_count,
                    "avgViewsPerVideoMean": avg_views,
                    "avgViewsPerVideo": avg_views,  # backward compat, overridden by median in main.py
                }

        return result


def parse_duration(iso_8601: str) -> int:
    if not iso_8601:
        return 0
    m = re.match(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso_8601
    )
    if not m:
        return 0
    hours = int(m.group(1) or 0)
    minutes = int(m.group(2) or 0)
    seconds = int(m.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds


def format_duration(seconds: int) -> str:
    if seconds < 0:
        seconds = 0
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def format_relative_time(published_at: str) -> str:
    if not published_at:
        return "unknown"
    try:
        pub = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - pub
        total_seconds = delta.total_seconds()
        if total_seconds < 0:
            return "just now"
        minutes = int((total_seconds % 3600) // 60)
        hours = int(total_seconds // 3600)
        if total_seconds < 3600:
            return f"{minutes} hour{'s' if minutes != 1 else ''} ago"
        if hours < 24:
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        days = int(total_seconds // 86400)
        if days == 0:
            return "today"
        if days == 1:
            return "yesterday"
        if days < 7:
            return f"{days} days ago"
        if days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        if days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        years = days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    except Exception:
        return "unknown"
