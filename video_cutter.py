#!/usr/bin/env python3
"""
Video Cutter
Cut videos by timestamp using FFmpeg.

Usage:
    python video_cutter.py "C:/path/video.mp4" --start "00:00:10" --end "00:01:30"
    python video_cutter.py "video.mp4" -s 10 -e 90 --output "clip.mp4"
"""

import sys
import argparse
from pathlib import Path

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def parse_timestamp(timestamp: str) -> str:
    """
    Convert various timestamp formats to FFmpeg format.

    Accepts:
    - HH:MM:SS (00:01:30)
    - M:SS or MM:SS (1:30, 01:30, 9:02)
    - Seconds (90)

    Returns: HH:MM:SS format
    """
    if ':' in timestamp:
        parts = timestamp.split(':')
        if len(parts) == 3:
            return timestamp  # Already HH:MM:SS
        elif len(parts) == 2:
            # M:SS or MM:SS format
            return f"00:{timestamp}"  # -> HH:MM:SS
    else:
        # Assume seconds
        try:
            seconds = int(timestamp)
            h = seconds // 3600
            m = (seconds % 3600) // 60
            s = seconds % 60
            return f"{h:02d}:{m:02d}:{s:02d}"
        except ValueError:
            pass
    return timestamp


def calculate_duration(start: str, end: str) -> str:
    """Calculate duration between two timestamps in seconds."""
    def to_seconds(ts: str) -> int:
        parts = ts.split(':')
        if len(parts) == 3:
            h, m, s = map(int, parts)
            return h * 3600 + m * 60 + s
        elif len(parts) == 2:
            m, s = map(int, parts)
            return m * 60 + s
        else:
            return int(ts)

    return str(to_seconds(end) - to_seconds(start))


def cut_video(input_path: str, output_path: str, start: str, end: str) -> bool:
    """
    Cut video using FFmpeg.

    Args:
        input_path: Input video file path
        output_path: Output video file path
        start: Start timestamp (HH:MM:SS or MM:SS or seconds)
        end: End timestamp (HH:MM:SS or MM:SS or seconds)

    Returns:
        True if successful, False otherwise
    """
    try:
        import subprocess

        # Normalize timestamps
        start_norm = parse_timestamp(start)
        end_norm = parse_timestamp(end)

        # Calculate duration
        duration = calculate_duration(start_norm, end_norm)

        cmd = [
            'ffmpeg', '-y',
            '-ss', start_norm,
            '-i', input_path,
            '-t', duration,
            '-c:v', 'libx264', '-preset', 'fast',
            '-c:a', 'aac',
            output_path
        ]

        print(f"Cutting from {start_norm} to {end_norm} (duration: {duration}s)")

        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0

    except FileNotFoundError:
        print("Error: FFmpeg not found. Install FFmpeg to use this script.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Cut videos by timestamp using FFmpeg',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Timestamp formats:
  HH:MM:SS    00:01:30 (1 minute 30 seconds)
  M:SS / MM:SS  1:30, 01:30, 9:02
  Seconds     90

Examples:
  py video_cutter.py "video.mp4" --start "0:00" --end "1:30"
  py video_cutter.py "video.mp4" -s 10 -e 90 -o "clip.mp4"
  py video_cutter.py "video.mp4" --start "9:02" --end "12:15"
        """
    )

    parser.add_argument('input', help='Input video file path')
    parser.add_argument('-s', '--start', default='0',
                        help='Start timestamp (HH:MM:SS, M:SS, or seconds, default: 0)')
    parser.add_argument('-e', '--end', required=True,
                        help='End timestamp (HH:MM:SS, M:SS, or seconds)')
    parser.add_argument('-o', '--output',
                        help='Output file path (default: <input>_cut.<ext>)')

    args = parser.parse_args()

    # Validate input file
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        name = input_path.stem + '_cut'
        ext = input_path.suffix
        output_path = input_path.parent / f"{name}{ext}"

    print(f"Input:  {input_path}")
    print(f"Output: {output_path}")
    print()

    # Cut video
    if cut_video(str(input_path), str(output_path), args.start, args.end):
        print()
        print("Cut completed successfully!")
        return 0
    else:
        print()
        print("Cut failed!", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
