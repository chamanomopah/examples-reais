#!/usr/bin/env python3
"""
YouTube Thumbnail Downloader
A simple script to download thumbnails from YouTube videos.

Supports multiple quality levels:
- maxres:    1280x720 (highest)
- high:      480x360
- medium:    320x180
- default:   120x90 (lowest)

Usage:
    python thumbnail_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python thumbnail_downloader.py "https://youtu.be/VIDEO_ID" --quality high
    python thumbnail_downloader.py "URL" --output my_thumbnail.jpg
"""

import sys
import re
import argparse
from typing import Optional
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


# Thumbnail quality levels and their URLs
THUMBNAIL_URLS = {
    'maxres': 'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
    'high': 'https://img.youtube.com/vi/{video_id}/hqdefault.jpg',
    'medium': 'https://img.youtube.com/vi/{video_id}/mqdefault.jpg',
    'default': 'https://img.youtube.com/vi/{video_id}/default.jpg',
}

# Quality fallback order (try highest first, fallback to lower)
QUALITY_FALLBACK = ['maxres', 'high', 'medium', 'default']


def extract_video_id(url: str) -> Optional[str]:
    """
    Extract video ID from various YouTube URL formats.
    
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    
    Args:
        url: YouTube video URL
        
    Returns:
        Video ID string or None if not found
    """
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/|youtube\.com\/shorts\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_thumbnail_url(video_id: str, quality: str) -> str:
    """
    Generate thumbnail URL for a video ID and quality level.
    
    Args:
        video_id: YouTube video ID
        quality: Quality level (maxres, high, medium, default)
        
    Returns:
        Full URL to the thumbnail image
    """
    if quality not in THUMBNAIL_URLS:
        quality = 'high'
    
    return THUMBNAIL_URLS[quality].format(video_id=video_id)


def check_thumbnail_exists(url: str) -> bool:
    """
    Check if a thumbnail URL is valid (image exists).
    
    YouTube returns a 404 or a small placeholder image for non-existent thumbnails.
    The placeholder is typically less than 2KB.
    
    Args:
        url: Thumbnail URL to check
        
    Returns:
        True if thumbnail exists, False otherwise
    """
    try:
        # Create request with user agent to avoid being blocked
        request = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        with urlopen(request, timeout=10) as response:
            # Check content length (placeholder images are small)
            content_length = response.getheader('Content-Length')
            if content_length:
                size = int(content_length)
                # YouTube placeholder is typically small (under 3KB)
                return size > 3000
            
            # If no Content-Length, read first few KB to check
            data = response.read(4096)
            return len(data) > 3000
    
    except (HTTPError, URLError):
        return False


def find_best_quality(video_id: str, preferred_quality: str) -> tuple[str, bool]:
    """
    Find the best available thumbnail quality for a video.
    
    Tries the preferred quality first, then falls back to lower qualities
    if the preferred one doesn't exist.
    
    Args:
        video_id: YouTube video ID
        preferred_quality: Preferred quality level
        
    Returns:
        Tuple of (quality_level, exists)
    """
    # Try preferred quality first
    url = get_thumbnail_url(video_id, preferred_quality)
    if check_thumbnail_exists(url):
        return preferred_quality, True
    
    # If not available, try fallback options
    # Get index of preferred quality
    try:
        start_idx = QUALITY_FALLBACK.index(preferred_quality)
    except ValueError:
        start_idx = 0
    
    # Try each quality from preferred down to lowest
    for quality in QUALITY_FALLBACK[start_idx:]:
        url = get_thumbnail_url(video_id, quality)
        if check_thumbnail_exists(url):
            return quality, True
    
    # No quality available
    return preferred_quality, False


def download_thumbnail(url: str, output_path: Path) -> int:
    """
    Download thumbnail from URL to file.
    
    Args:
        url: Thumbnail URL
        output_path: Path where to save the thumbnail
        
    Returns:
        Number of bytes downloaded
        
    Raises:
        Exception: If download fails
    """
    try:
        # Create request with user agent
        request = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        
        with urlopen(request, timeout=30) as response:
            data = response.read()
            
            # Create parent directories if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write to file
            with open(output_path, 'wb') as f:
                f.write(data)
            
            return len(data)
    
    except HTTPError as e:
        raise Exception(f"HTTP Error {e.code}: {e.reason}")
    except URLError as e:
        raise Exception(f"URL Error: {e.reason}")
    except Exception as e:
        raise Exception(f"Download failed: {e}")


def format_size(bytes_count: int) -> str:
    """
    Format byte count to human-readable size.
    
    Args:
        bytes_count: Number of bytes
        
    Returns:
        Formatted size string (e.g., "15.2 KB")
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} TB"


def main():
    parser = argparse.ArgumentParser(
        description='Download thumbnails from YouTube videos',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quality Levels:
  maxres   1280x720 (highest quality, may not exist for older videos)
  high     480x360  (recommended, most videos have this)
  medium   320x180  (fallback option)
  default  120x90   (lowest quality, always exists)

Examples:
  python thumbnail_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python thumbnail_downloader.py "https://youtu.be/dQw4w9WgXcQ" --quality high
  python thumbnail_downloader.py "URL" --output my_thumbnail.jpg
  python thumbnail_downloader.py "URL" --quality maxres --no-fallback
  python thumbnail_downloader.py "URL" --output-dir "C:/output/path"
        """
    )
    
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-q', '--quality', default='high',
                        choices=['maxres', 'high', 'medium', 'default'],
                        help='Thumbnail quality (default: high)')
    parser.add_argument('-od', '--output-dir',
                        help='Output directory where thumbnail will be saved')
    parser.add_argument('-o', '--output',
                        help='Output file name (default: <video_id>_<quality>.jpg, used with --output-dir)')
    parser.add_argument('--no-fallback', action='store_true',
                        help='Do not fallback to lower quality if preferred is unavailable')
    parser.add_argument('--check-only', action='store_true',
                        help='Only check if thumbnail exists, do not download')
    
    args = parser.parse_args()
    
    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print("❌ Error: Invalid YouTube URL format")
        print(f"   URL provided: {args.url}")
        print("\nValid formats:")
        print("  • https://www.youtube.com/watch?v=VIDEO_ID")
        print("  • https://youtu.be/VIDEO_ID")
        print("  • https://www.youtube.com/embed/VIDEO_ID")
        print("  • https://www.youtube.com/shorts/VIDEO_ID")
        sys.exit(1)
    
    print("=" * 60)
    print("  YOUTUBE THUMBNAIL DOWNLOADER")
    print("=" * 60)
    print()
    print(f"Video ID: {video_id}")
    print(f"Quality:  {args.quality}")
    print()
    
    # Determine output path
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # Usa args.output como nome do arquivo, ou default <video_id>_<quality>.jpg
        filename = args.output if args.output else f"{video_id}_{args.quality}.jpg"
        output_path = output_dir / filename
    elif args.output:
        # Comportamento original: args.output é o caminho completo
        output_path = Path(args.output)
    else:
        # Create thumbnails directory
        thumbnails_dir = Path("thumbnails")
        thumbnails_dir.mkdir(exist_ok=True)
        output_path = thumbnails_dir / f"{video_id}_{args.quality}.jpg"
    
    print(f"Output:   {output_path.absolute()}")
    print()
    
    # Check if thumbnail exists and find best quality
    if args.no_fallback:
        # Use exact quality requested
        thumbnail_url = get_thumbnail_url(video_id, args.quality)
        exists = check_thumbnail_exists(thumbnail_url)
        final_quality = args.quality if exists else None
    else:
        # Find best available quality
        final_quality, exists = find_best_quality(video_id, args.quality)
        thumbnail_url = get_thumbnail_url(video_id, final_quality)
    
    # Report results
    if not exists:
        print("❌ Error: Thumbnail not available")
        print(f"   Tried quality: {args.quality}")
        if not args.no_fallback:
            print(f"   Tried fallback: {', '.join(QUALITY_FALLBACK)}")
        sys.exit(1)
    
    print(f"✓ Thumbnail available at quality: {final_quality}")
    print(f"  URL: {thumbnail_url}")
    print()
    
    # Check-only mode
    if args.check_only:
        print("✓ Check complete (no download requested)")
        return 0
    
    # Download thumbnail
    print("Downloading...")
    try:
        bytes_downloaded = download_thumbnail(thumbnail_url, output_path)
        
        print()
        print("=" * 60)
        print("✓ SUCCESS!")
        print(f"  Size:     {format_size(bytes_downloaded)} ({bytes_downloaded:,} bytes)")
        print(f"  Quality:  {final_quality}")
        print(f"  Saved to: {output_path.absolute()}")
        print("=" * 60)
        
        return 0
    
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ Error: {e}")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
