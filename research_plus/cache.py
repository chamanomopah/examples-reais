"""File-based cache for research_plus results."""

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def slugify_keyword(keyword: str) -> str:
    return hashlib.md5(keyword.lower().strip().encode()).hexdigest()[:12]


def get_cache_path(keyword: str, cache_dir: Path, last_days: int = 0, region: str = "US") -> Path:
    slug = slugify_keyword(keyword)
    parts = [slug]
    if region and region != "US":
        parts.append(region.lower())
    if last_days > 0:
        parts.append(f"{last_days}d")
    return cache_dir / "_".join(parts) + ".json"


def load_cache(keyword: str, cache_dir: Path, ttl_hours: int, last_days: int = 0, region: str = "US") -> dict | None:
    path = get_cache_path(keyword, cache_dir, last_days, region)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        cached_at = datetime.fromisoformat(data["cached_at"].replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - cached_at).total_seconds() / 3600
        if age_hours < ttl_hours:
            return data
    except Exception:
        pass
    return None


def save_cache(keyword: str, cache_dir: Path, response: dict, last_days: int = 0, region: str = "US"):
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = get_cache_path(keyword, cache_dir, last_days, region)
    data = {
        "cached_at": datetime.now(timezone.utc).isoformat(),
        "response": response,
    }
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clear_cache(cache_dir: Path, keyword: str | None = None) -> int:
    """Delete cache files. Returns count of files deleted."""
    if keyword:
        slug = slugify_keyword(keyword)
        deleted = 0
        for f in cache_dir.glob(f"{slug}*.json"):
            f.unlink()
            deleted += 1
        return deleted

    count = 0
    if cache_dir.exists():
        for f in cache_dir.glob("*.json"):
            f.unlink()
            count += 1
    return count
