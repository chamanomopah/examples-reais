#!/usr/bin/env python3
import argparse
import subprocess
import re
import os
import sys
from pathlib import Path


def parse_storyboard(storyboard_path):
    """Parse storyboard.md and extract scene info with CLIP_ID and duration."""
    scenes = []
    current_scene = None

    with open(storyboard_path, 'r', encoding='utf-8') as f:
        content = f.read()

    scene_pattern = re.compile(r'## Scene (\d+)', re.IGNORECASE)
    narration_pattern = re.compile(r'\*\*Narração:\*\*', re.IGNORECASE)
    duration_pattern = re.compile(r'\*\*Duração:\*\*\s*([\d.]+)s', re.IGNORECASE)
    timestamp_pattern = re.compile(r'\*\*Timestamp:\*\*', re.IGNORECASE)
    layer_pattern = re.compile(r'\*\*Layer\s+\d+\s*\([^)]+\):\*\*\s*(CLIP_\d+)', re.IGNORECASE)

    lines = content.split('\n')
    i = 0

    while i < len(lines):
        line = lines[i]

        scene_match = scene_pattern.match(line.strip())
        if scene_match:
            current_scene = {
                'scene_number': int(scene_match.group(1)),
                'clip_id': None,
                'duration': None
            }
            scenes.append(current_scene)

        elif current_scene:
            if not current_scene['duration']:
                duration_match = duration_pattern.search(line)
                if duration_match:
                    current_scene['duration'] = float(duration_match.group(1))

            if not current_scene['clip_id']:
                layer_match = layer_pattern.search(line)
                if layer_match:
                    current_scene['clip_id'] = layer_match.group(1)

        i += 1

    return scenes


def find_clip(clip_id, clips_dir):
    """Find the clip file for a given CLIP_ID."""
    clip_path = Path(clips_dir) / f"{clip_id}.mp4"
    if clip_path.exists():
        return clip_path
    return None


def trim_clip(clip_path, duration, output_path, log):
    """Trim clip using ffmpeg from start to specified duration."""
    cmd = [
        'ffmpeg',
        '-i', str(clip_path),
        '-t', str(duration),
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-y',
        str(output_path)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            log.write(f"[OK] Trimmed {clip_path.name} -> {output_path.name} ({duration}s)\n")
            return True
        else:
            log.write(f"[ERROR] ffmpeg failed for {clip_path.name}: {result.stderr}\n")
            return False
    except Exception as e:
        log.write(f"[ERROR] Exception processing {clip_path.name}: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(description='Trim clips based on storyboard durations')
    parser.add_argument('--storyboard', required=True, help='Path to storyboard.md')
    parser.add_argument('--clips-dir', required=True, help='Path to clips directory')
    parser.add_argument('--output-dir', default='./output/trimmed_clips', help='Output directory for trimmed clips')
    args = parser.parse_args()

    storyboard_path = Path(args.storyboard)
    clips_dir = Path(args.clips_dir)
    output_dir = Path(args.output_dir)

    if not storyboard_path.exists():
        print(f"Error: storyboard not found: {storyboard_path}", file=sys.stderr)
        sys.exit(1)

    if not clips_dir.exists():
        print(f"Error: clips directory not found: {clips_dir}", file=sys.stderr)
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    log_path = output_dir / 'trim_log.txt'
    with open(log_path, 'w', encoding='utf-8') as log:
        log.write(f"Trim Clips Log\n")
        log.write(f"Storyboard: {storyboard_path}\n")
        log.write(f"Clips dir: {clips_dir}\n")
        log.write(f"Output dir: {output_dir}\n")
        log.write("-" * 50 + "\n")

        scenes = parse_storyboard(storyboard_path)

        if not scenes:
            log.write("[ERROR] No scenes found in storyboard\n")
            print("Error: No scenes found in storyboard", file=sys.stderr)
            sys.exit(1)

        log.write(f"Found {len(scenes)} scenes\n\n")

        success_count = 0
        error_count = 0

        for scene in scenes:
            clip_id = scene['clip_id']
            duration = scene['duration']
            scene_number = scene['scene_number']

            if not clip_id:
                log.write(f"[SKIP] Scene {scene_number}: No CLIP_ID found\n")
                error_count += 1
                continue

            if not duration:
                log.write(f"[SKIP] Scene {scene_number}: No duration found\n")
                error_count += 1
                continue

            clip_path = find_clip(clip_id, clips_dir)
            if not clip_path:
                log.write(f"[ERROR] Scene {scene_number}: Clip not found: {clip_id}.mp4\n")
                error_count += 1
                continue

            output_filename = f"{clip_id}_scene_{scene_number:03d}_trimmed.mp4"
            output_path = output_dir / output_filename

            if trim_clip(clip_path, duration, output_path, log):
                success_count += 1
            else:
                error_count += 1

        log.write("-" * 50 + "\n")
        log.write(f"Summary: {success_count} success, {error_count} errors\n")

    print(f"Done: {success_count} clips trimmed, {error_count} errors")
    print(f"Log saved to: {log_path}")
    print(f"Output dir: {output_dir}")

    if error_count > 0:
        sys.exit(1)


if __name__ == '__main__':
    main()
