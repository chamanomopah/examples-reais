"""Configuration constants and env loading."""

import os
from pathlib import Path

from dotenv import load_dotenv

# --- Env loading ---

def load_env(env_file: str | None = None) -> dict[str, str]:
    path = env_file or str(Path.home() / ".alfredo" / ".env")
    load_dotenv(path, override=True)
    return {
        "YOUTUBE_API_KEY": os.environ.get("YOUTUBE_API_KEY", ""),
        "GEMINI_API_KEY": os.environ.get("GEMINI_API_KEY", ""),
    }

# --- Channel size thresholds ---

CHANNEL_SIZE_THRESHOLDS = {
    "micro": 10_000,
    "small": 100_000,
    "medium": 500_000,
    # large = anything >= 500K
}

# --- Saturation thresholds ---

SATURATION_THRESHOLDS = {
    "Low": 100_000,
    "Moderate": 500_000,
    "Competitive": 1_000_000,
    # Highly Saturated = anything >= 1M
}

# --- Defaults ---

MAX_PAGES = 2
MAX_RESULTS = 50
BATCH_SIZE = 50

# --- Video duration filter for search API ---

VIDEO_DURATION_FILTER = "medium"  # 4-20 minutes, excludes Shorts (<4min) and very long videos (>20min)

# --- Duration category thresholds (seconds) ---

DURATION_CATEGORIES = [
    (180, "Short-form"),
    (600, "Medium-form"),
    (1800, "Long-form"),
    (float("inf"), "Extended"),
]

# --- Duration suggestion templates ---

DURATION_SUGGESTIONS = {
    "Short-form": "Short-form content dominates this niche. Consider creating concise, high-impact videos under 60 seconds to match audience expectations.",
    "Medium-form": "Medium-form content is popular here. Videos of 3-10 minutes appear to perform well — aim for focused, value-dense content.",
    "Long-form": "Long-form content is the norm. This audience engages with detailed, comprehensive videos of 10-30 minutes.",
    "Extended": "Extended content dominates. Consider deep-dive, documentary-style videos over 30 minutes.",
}

# --- Market suggestion templates ---

MARKET_SUGGESTIONS = {
    "Low": "This is an underserved niche with low competition. Great opportunity for early movers — content here can capture significant organic reach.",
    "Moderate": "Moderate competition exists. Differentiation through unique angles, quality, or consistency can still yield strong results.",
    "Competitive": "This is a competitive niche. Focus on unique value propositions, underserved sub-topics, and superior production quality to stand out.",
    "Highly Saturated": "This is a highly saturated market. Success requires a very specific angle, exceptional quality, or targeting underserved sub-audiences.",
}

# --- Retry settings ---

MAX_RETRIES = 3
BASE_DELAY = 1.0

# --- Cache settings ---

CACHE_DIR = Path(__file__).parent / ".cache"
CACHE_TTL_HOURS = 24

# --- AI Model settings ---

AVAILABLE_GEMINI_MODELS = {
    "gemini-3-flash-preview": "Preview - High volume, fast (RECOMMENDED)",
    "gemini-3.1-flash-lite-preview": "Preview - Ultra fast, low latency",
    "gemini-2.5-flash": "GA - Balanced, production-ready",
    "gemini-2.5-flash-lite": "GA - Maximum scale, minimum cost",
    "gemini-2.0-flash": "GA - Legacy",
    "gemini-flash-latest": "Latest Flash (alias)",
}

DEFAULT_MODEL = "gemini-3-flash-preview"
