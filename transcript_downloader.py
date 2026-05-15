#!/usr/bin/env python3
"""
YouTube Transcript Downloader
Simple CLI tool to download YouTube video transcripts.

Usage:
    python transcript_downloader.py "https://youtu.be/VIDEO_ID"
    python transcript_downloader.py "URL" --output-dir "./transcripts"
"""

import sys
import re
import argparse
import json
import html
import os
from typing import Optional, List, Dict, Tuple
from urllib.parse import urlencode
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    error_response = {"success": False, "error": "requests module not installed"}
    print(json.dumps(error_response))
    sys.exit(1)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
except ImportError:
    YouTubeTranscriptApi = None


# =============================================================================
# CONFIGURATION
# =============================================================================

TIMEOUT = 30
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


# =============================================================================
# RESULT CLASS
# =============================================================================

class Result:
    """Consistent result object for all operations."""

    def __init__(self, success: bool, data=None, error: str = None):
        self.success = success
        self.data = data
        self.error = error

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        result = {"success": self.success}
        if self.success:
            result["data"] = self.data
        else:
            result["error"] = self.error
        return result


# =============================================================================
# VIDEO ID EXTRACTION
# =============================================================================

def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def validate_url(url: str) -> Result:
    """Validate YouTube URL and extract video ID."""
    if not url or not isinstance(url, str):
        return Result(False, error="URL must be a non-empty string")

    url = url.strip()
    if not url:
        return Result(False, error="URL cannot be empty")

    video_id = extract_video_id(url)
    if not video_id:
        return Result(False, error=f"Invalid YouTube URL: {url}")

    return Result(True, data={"video_id": video_id, "url": url})


# =============================================================================
# TRANSCRIPT FETCHING
# =============================================================================

class TimedTextParser:
    """Parser for YouTube timedtext format."""

    @staticmethod
    def parse_xml(xml_content: str) -> List[Dict]:
        """Parse YouTube timedtext XML format."""
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError:
            return []

        transcripts = []
        text_tag = '{http://www.w3.org/2006/10/ttaf1}text'

        for trans in root.findall(text_tag):
            text = trans.text or ""
            start = float(trans.get('start', 0))
            dur = float(trans.get('dur', 0))

            text = html.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()

            if text:
                transcripts.append({'text': text, 'start': start, 'duration': dur})

        return transcripts

    @staticmethod
    def parse_jsonv2(json_content: str) -> List[Dict]:
        """Parse YouTube JSONv2 format."""
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError:
            return []

        transcripts = []
        events = data.get('events', [])

        for event in events:
            segments = event.get('segs', [])
            text_parts = []

            for seg in segments:
                utf8_text = seg.get('utf8', '')
                if utf8_text:
                    text_parts.append(utf8_text)

            text = ''.join(text_parts).strip()
            text = html.unescape(text)
            text = re.sub(r'\s+', ' ', text).strip()

            if text:
                transcripts.append({
                    'text': text,
                    'start': event.get('tStartMs', 0) / 1000,
                    'duration': event.get('dDurationMs', 0) / 1000
                })

        return transcripts


class TranscriptFetcher:
    """Fetches transcripts from YouTube using various methods."""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': USER_AGENT})

    def _fetch_url(self, url: str) -> Optional[str]:
        """Fetch URL content."""
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text
        except requests.RequestException:
            return None

    def get_transcript_from_html(self, video_id: str) -> Optional[List[Dict]]:
        """Extract transcript from YouTube watch page HTML."""
        url = f"https://www.youtube.com/watch?v={video_id}"

        try:
            content = self._fetch_url(url)
            if not content:
                return None
        except Exception:
            return None

        pattern = r'ytInitialPlayerResponse\s*=\s*({.+?})\s*;</script>'
        match = re.search(pattern, content)

        if not match:
            return None

        try:
            player_response = json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

        captions = player_response.get('captions', {})
        renderer = captions.get('playerCaptionsTracklistRenderer', {})

        if not renderer:
            return None

        caption_tracks = renderer.get('captionTracks', [])
        if not caption_tracks:
            return None

        # Prioritize Portuguese, then English, then any
        lang_priority = ['pt', 'pt-BR', 'pt-PT', 'en', 'en-US', 'en-GB']
        selected_track = None

        for lang in lang_priority:
            for track in caption_tracks:
                track_lang = track.get('languageCode', '')
                if track_lang.startswith(lang):
                    selected_track = track
                    break
            if selected_track:
                break

        if not selected_track and caption_tracks:
            selected_track = caption_tracks[0]

        if not selected_track:
            return None

        base_url = selected_track.get('baseUrl')
        if not base_url:
            return None

        caption_content = self._fetch_url(base_url)
        if not caption_content:
            return None

        # Try parsing
        parsed = TimedTextParser.parse_jsonv2(caption_content)
        if parsed:
            return parsed

        parsed = TimedTextParser.parse_xml(caption_content)
        if parsed:
            return parsed

        return None


def get_transcript(video_id: str) -> Result:
    """
    Get transcript for a YouTube video.

    Returns Result with transcript data or error.
    """
    # Try youtube-transcript-api first
    if YouTubeTranscriptApi:
        try:
            languages = ['pt', 'pt-BR', 'pt-PT', 'en', 'en-US', 'en-GB']
            api = YouTubeTranscriptApi()

            for lang in languages:
                try:
                    transcript_list = api.list(video_id)
                    transcript = transcript_list.find_transcript([lang])
                    data = transcript.fetch()
                    converted = [{'text': t.text, 'start': t.start, 'duration': t.duration} for t in data]
                    return Result(True, data={"transcript": converted, "lang": lang, "source": "api"})
                except Exception:
                    continue
        except Exception:
            pass

    # Fallback: HTML extraction
    fetcher = TranscriptFetcher()
    try:
        transcript_data = fetcher.get_transcript_from_html(video_id)
        if transcript_data:
            return Result(True, data={"transcript": transcript_data, "lang": "unknown", "source": "html"})
    except Exception:
        pass

    return Result(False, error=f"No transcript available for video {video_id}")


# =============================================================================
# FORMATTING
# =============================================================================

def format_transcript_organic(transcript_data: List[Dict]) -> str:
    """Format transcript as organic sentences."""
    if not transcript_data:
        return ""

    full_text = ""
    for entry in transcript_data:
        text = entry.get('text', '').strip()
        if not text:
            continue

        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'&#39;', "'", text)
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&amp;', '&', text)

        if full_text and not full_text.endswith(' ') and not text.startswith(' '):
            full_text += ' '
        full_text += text

    full_text = re.sub(r'([.!?])([A-Z])', r'\1 \2', full_text)
    full_text = re.sub(r'([.!?])([a-z])', r'\1 \2', full_text)

    sentences_with_ends = []
    parts = re.split(r'([.!?]+\s*)', full_text)

    for i in range(0, len(parts), 2):
        sentence_part = parts[i] if i < len(parts) else ''
        end_part = parts[i + 1] if i + 1 < len(parts) else ''

        if sentence_part and sentence_part[0].isalpha():
            sentence_part = sentence_part[0].upper() + sentence_part[1:]

        sentences_with_ends.append(sentence_part + end_part)

    full_text = ''.join(sentences_with_ends)

    sentence_ends = re.finditer(r'([.!?])\s+', full_text)

    sentences = []
    last_end = 0

    for match in sentence_ends:
        end_pos = match.end()
        sentence = full_text[last_end:end_pos].strip()

        if sentence:
            if not sentence[-1] in '.!?':
                sentence += match.group(1)
            sentences.append(sentence)

        last_end = end_pos

    if last_end < len(full_text):
        remaining = full_text[last_end:].strip()
        if remaining:
            sentences.append(remaining)

    return '\n\n'.join(sentences)


# =============================================================================
# FILE OPERATIONS
# =============================================================================

def ensure_output_directory(path: str) -> Result:
    """
    Ensure output directory exists, creating if necessary.

    Args:
        path: Directory path (relative or absolute)

    Returns:
        Result with absolute path on success
    """
    if not path:
        return Result(False, error="Output directory path is empty")

    try:
        output_path = Path(path).expanduser().resolve()

        # Create directory if it doesn't exist
        output_path.mkdir(parents=True, exist_ok=True)

        # Verify it's actually a directory
        if not output_path.is_dir():
            return Result(False, error=f"Path exists but is not a directory: {path}")

        return Result(True, data={"path": str(output_path)})

    except PermissionError:
        return Result(False, error=f"Permission denied creating directory: {path}")
    except Exception as e:
        return Result(False, error=f"Failed to create directory: {str(e)}")


def write_transcript(content: str, output_dir: str, filename: str) -> Result:
    """
    Write transcript content to file.

    Args:
        content: Transcript text content
        output_dir: Directory path (must exist)
        filename: Output filename

    Returns:
        Result with file path on success
    """
    if not content:
        return Result(False, error="Transcript content is empty")

    if not filename:
        return Result(False, error="Filename is empty")

    try:
        dir_path = Path(output_dir).expanduser().resolve()
        file_path = dir_path / filename

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        return Result(True, data={"file": str(file_path)})

    except PermissionError:
        return Result(False, error=f"Permission denied writing to: {filename}")
    except Exception as e:
        return Result(False, error=f"Failed to write file: {str(e)}")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Download YouTube video transcripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python transcript_downloader.py "https://youtu.be/VIDEO_ID"
  python transcript_downloader.py "URL" --output-dir "./transcripts"
  python transcript_downloader.py "URL" -od "C:/output" -f "custom_name.md"
        """
    )

    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-od', '--output-dir', default='.',
                        help='Output directory (default: current directory)')
    parser.add_argument('-f', '--filename',
                        help='Output filename (default: {video_id}.md)')
    parser.add_argument('--json', action='store_true',
                        help='Output result as JSON (machine-readable)')

    args = parser.parse_args()

    # Step 1: Validate URL and extract video ID
    url_result = validate_url(args.url)
    if not url_result.success:
        print(json.dumps(url_result.to_dict()))
        sys.exit(0)

    video_id = url_result.data["video_id"]

    # Step 2: Ensure output directory exists
    dir_result = ensure_output_directory(args.output_dir)
    if not dir_result.success:
        error_result = Result(False, error=dir_result.error)
        error_result.data = {"video_id": video_id}
        print(json.dumps(error_result.to_dict()))
        sys.exit(0)

    output_dir = dir_result.data["path"]

    # Step 3: Get transcript
    transcript_result = get_transcript(video_id)
    if not transcript_result.success:
        error_result = Result(False, error=transcript_result.error)
        error_result.data = {"video_id": video_id}
        print(json.dumps(error_result.to_dict()))
        sys.exit(0)

    transcript_data = transcript_result.data["transcript"]

    # Step 4: Format transcript
    formatted = format_transcript_organic(transcript_data)

    # Step 5: Determine filename
    if args.filename:
        filename = args.filename
    else:
        filename = f"{video_id}.md"

    # Step 6: Write file
    write_result = write_transcript(formatted, output_dir, filename)
    if not write_result.success:
        error_result = Result(False, error=write_result.error)
        error_result.data = {"video_id": video_id}
        print(json.dumps(error_result.to_dict()))
        sys.exit(0)

    # Step 7: Output result
    result_data = {
        "video_id": video_id,
        "file": write_result.data["file"],
        "lang": transcript_result.data["lang"],
        "source": transcript_result.data["source"],
        "lines": len(formatted.split('\n'))
    }

    success_result = Result(True, data=result_data)

    if args.json:
        print(json.dumps(success_result.to_dict()))
    else:
        print(json.dumps(success_result.to_dict()))

    sys.exit(0)


if __name__ == "__main__":
    main()
