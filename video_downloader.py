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
import subprocess
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp is not installed.")
    print("Install it with: pip install yt-dlp")
    print("Or: py -m pip install yt-dlp")
    sys.exit(1)


def extract_video_id(url: str) -> str | None:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def convert_to_aac(input_path: str, output_path: str) -> bool:
    """Convert video audio to AAC using FFmpeg for better compatibility."""
    try:
        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k',
            '-movflags', '+faststart',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def download_video(url: str, output_path: str, quality: str = 'best', format_type: str = 'mp4') -> bool:
    """
    Download video from YouTube using yt-dlp.

    Args:
        url: YouTube video URL
        output_path: Output file path
        quality: Video quality preference (best, 1080, 720, 480)
        format_type: Output format (mp4, webm, mkv)

    Returns:
        True if successful, False otherwise
    """
    # Build format selector based on quality
    format_selectors = {
        'best': 'bestvideo+bestaudio/best',
        '1080': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
    }

    format_selector = format_selectors.get(quality, format_selectors['best'])

    # Temp file for download
    temp_path = str(Path(output_path).with_suffix(f'.downloaded.{format_type}'))

    ydl_opts = {
        'format': format_selector,
        'merge_output_format': format_type,
        'outtmpl': temp_path,
        'quiet': False,
        'no_warnings': False,
        'progress': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Convert to AAC for compatibility
        output_file = Path(output_path)
        temp_file = Path(temp_path)

        if temp_file.exists():
            print("\nConverting audio to AAC for better compatibility...")
            if convert_to_aac(str(temp_file), str(output_file)):
                temp_file.unlink(missing_ok=True)
                return True
            else:
                # Fallback: rename temp file if conversion fails
                temp_file.rename(output_file)
                print("Warning: Could not convert to AAC, using original audio.", file=sys.stderr)
                return True
        return False

    except Exception as e:
        print(f"Error downloading video: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Download videos from YouTube',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py video_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  py video_downloader.py "https://youtu.be/dQw4w9WgXcQ" --output "C:/videos/video.mp4"
  py video_downloader.py "URL" --quality 720
  py video_downloader.py "VIDEO_ID" --output "video.mp4"
        """
    )

    parser.add_argument('url', help='YouTube video URL or video ID')
    parser.add_argument('-o', '--output', required=True,
                        help='Output file path (required)')
    parser.add_argument('-q', '--quality', default='best',
                        choices=['best', '1080', '720', '480'],
                        help='Video quality (default: best)')
    parser.add_argument('-f', '--format', default='mp4',
                        choices=['mp4', 'webm', 'mkv'],
                        help='Output format (default: mp4)')

    args = parser.parse_args()

    # Convert video ID to full URL if needed
    url = args.url
    video_id = extract_video_id(url)

    if not video_id:
        # Might be a raw video ID
        if len(url) == 11 and re.match(r'^[\w-]+$', url):
            video_id = url
            url = f'https://www.youtube.com/watch?v={video_id}'
        else:
            print("Error: Invalid YouTube URL or video ID", file=sys.stderr)
            sys.exit(1)

    print(f"Video ID: {video_id}")
    print(f"Output: {args.output}")
    print(f"Quality: {args.quality}")
    print()

    # Create parent directories if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Download video
    if download_video(url, str(output_path), args.quality, args.format):
        print()
        print("Download completed successfully!")
        return 0
    else:
        print()
        print("Download failed!", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
