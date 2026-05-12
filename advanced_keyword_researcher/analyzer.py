"""LLM integration via Google Gemini."""

import json
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from scorer import format_number


class AudienceInsight(BaseModel):
    category: str
    insight: str


class TrendingTheme(BaseModel):
    theme: str
    frequency: int
    description: str


class TopicIdea(BaseModel):
    title: str
    targetAudience: str
    goal: str
    context: str
    tone: str
    narrative: str
    reasoning: str
    appeal: str
    keywordSuggestion: str


class LLMTopicsResponse(BaseModel):
    audienceInsights: list[AudienceInsight]
    trendingThemes: list[TrendingTheme]
    topicIdeas: list[TopicIdea]


def build_prompt(
    keyword: str,
    top_videos: list[dict],
    scores_dict: dict[str, Any],
) -> str:
    videos_text = []
    for i, v in enumerate(top_videos[:50], 1):
        videos_text.append(
            f"{i}. \"{v.get('title', '')}\" | {v.get('channelTitle', '')} | "
            f"Views: {format_number(v.get('viewCount', 0))} | "
            f"Views/day: {format_number(v.get('viewsPerDay', 0))} | "
            f"Duration: {v.get('duration', 'N/A')} | "
            f"Published: {v.get('published', 'N/A')}"
        )

    opp = scores_dict.get("opportunity", {})
    opp_metrics = opp.get("metrics", {})
    trend = scores_dict.get("trend", {})
    views_med = scores_dict.get("viewsMedian", {})
    dur = scores_dict.get("durationAnalysis", {})
    market = scores_dict.get("marketAnalysis", {})
    total_videos = len(top_videos)

    prompt = f"""You are a YouTube niche research analyst. Analyze the following data for the keyword: "{keyword}"

## Top Videos (sorted by performance)
{chr(10).join(videos_text)}

## Market Context
- Total search results: {format_number(market.get('resultCount', 0))}
- Market saturation: {market.get('saturation', 'Unknown')}
- Median views: {format_number(views_med.get('median', 0))}
- View range: {format_number(views_med.get('min', 0))} - {format_number(views_med.get('max', 0))}
- Q1: {format_number(views_med.get('q1', 0))} | Q3: {format_number(views_med.get('q3', 0))}

## Channel Size Distribution
- Micro (<10K subs): {opp_metrics.get('micro', {}).get('percent', 0)}%
- Small (10K-100K): {opp_metrics.get('small', {}).get('percent', 0)}%
- Medium (100K-500K): {opp_metrics.get('medium', {}).get('percent', 0)}%
- Large (500K+): {opp_metrics.get('large', {}).get('percent', 0)}%

## Content Analysis
- Dominant duration: {dur.get('category', 'Unknown')} (median {dur.get('medianDuration', 'N/A')})
- Trend score: {trend.get('score', 0)}/100 ({trend.get('category', 'Unknown')})
- Opportunity score: {opp.get('score', 0)}/100 ({opp.get('category', 'Unknown')})

## Your Task

Analyze this YouTube keyword data and return a JSON object with these exact fields:

{{
  "audienceInsights": [
    {{
      "category": "Subconscious Driver" | "Pain Point" | "Desire" | "Demographic Insight",
      "insight": "specific insight text (one per category minimum)"
    }}
  ],
  "trendingThemes": [
    {{
      "theme": "theme name (concise, 3-8 words)",
      "frequency": <integer, approximate count of videos matching this theme>,
      "description": "why this theme works and what pattern it represents"
    }}
  ],
  "topicIdeas": [
    {{
      "title": "video title with hook",
      "targetAudience": "specific audience segment",
      "goal": "what the video delivers",
      "context": "content context/format",
      "tone": "tone descriptor",
      "narrative": "First person" | "Second person",
      "reasoning": "why this topic has potential",
      "appeal": "High" | "Medium" | "Low",
      "keywordSuggestion": "related keyword for research"
    }}
  ]
}}

Rules:
- Return 8-12 audience insights covering all categories
- Return 5-7 trending themes
- Return 5 topic ideas
- frequency values should be realistic estimates based on the dataset
- All insights must be grounded in the provided video data
- Keep all text concise and actionable
- Return ONLY valid JSON, no markdown fences"""

    return prompt


@retry(stop=stop_after_attempt(5), wait=wait_exponential(min=2, max=30))
def call_llm(prompt: str, api_key: str, model: str = "gemini-3-flash") -> dict:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=LLMTopicsResponse,
        ),
    )

    return json.loads(response.text)


def compute_audience_size(median: int, saturation: str) -> dict:
    multipliers = {
        "Highly Saturated": 5,
        "Competitive": 4,
        "Moderate": 5,
        "Low": 6,
    }
    multiplier = multipliers.get(saturation, 5)
    size = round(median * multiplier / 1000) * 1000

    return {
        "size": size,
        "explanation": (
            f"Using the dataset median views ({format_number(median)}) multiplied by a "
            f"conservative {multiplier}x engagement multiplier to account for "
            f"repeat viewers, related-search reach and niche interest "
            f"({format_number(median)} x {multiplier} ~ {format_number(size)}, rounded to {format_number(size)})."
        ),
    }


def assemble_topics_and_trends(
    llm_response: dict,
    median: int,
    saturation: str,
) -> dict:
    audience = compute_audience_size(median, saturation)

    return {
        "audienceInsights": llm_response.get("audienceInsights", []),
        "trendingThemes": llm_response.get("trendingThemes", []),
        "topicIdeas": llm_response.get("topicIdeas", []),
        "estimatedAudienceSize": audience["size"],
        "audienceSizeExplanation": audience["explanation"],
    }
