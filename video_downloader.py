#!/usr/bin/env python3
"""
YouTube Video Downloader
Download YouTube videos with quality and format options.

Usage:
    python video_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python video_downloader.py "https://youtu.be/VIDEO_ID" --output "C:/path/video.mp4"
"""

import sys
import re
import argparse
from pathlib import Path

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Install it with: pip install yt-dlp")
    sys.exit(1)


def extract_video_id(url: str) -> str | None:
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def download_video(url: str, output_path: str, quality: str = 'best') -> bool:
    format_selectors = {
        'best': 'bestvideo+bestaudio/best',
        '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
    }

    format_selector = format_selectors.get(quality, format_selectors['best'])

    ydl_opts = {
        'format': format_selector,
        'merge_output_format': 'mp4',
        'outtmpl': output_path,
        'quiet': False,
        'no_warnings': False,
        'progress': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return True
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download videos from YouTube',
        epilog="""
Examples:
  py video_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ" -o video.mp4
  py video_downloader.py "URL" -o video.mp4 --quality 720
        """
    )

    parser.add_argument('url', help='YouTube URL or video ID')
    parser.add_argument('-o', '--output', required=True, help='Output file path')
    parser.add_argument('-q', '--quality', default='best', choices=['best', '1080', '720', '480'], help='Video quality')

    args = parser.parse_args()

    url = args.url
    video_id = extract_video_id(url)

    if not video_id:
        if len(url) == 11 and re.match(r'^[\w-]+$', url):
            url = f'https://www.youtube.com/watch?v={url}'
        else:
            print("Error: Invalid YouTube URL", file=sys.stderr)
            sys.exit(1)

    print(f"Video ID: {video_id}")
    print(f"Output: {args.output}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    if download_video(url, str(args.output), args.quality):
        print("Download completed!")
        return 0
    else:
        print("Download failed!", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
