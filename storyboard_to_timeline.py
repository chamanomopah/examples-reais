#!/usr/bin/env python3
"""
Converte storyboard markdown em timeline HTML horizontal com suporte a 2 camadas.

Camadas:
- Layer 1: AI Video (prompt-based) + GFX Persistent/Anchored Graphics (A-roll)
- Layer 2: GFX Insert Graphics (B-roll)

Uso:
    python storyboard_to_timeline.py "storyboard.md"
    python storyboard_to_timeline.py "storyboard.md" --output "timeline.html"
"""

import re
import argparse
from pathlib import Path
from typing import List, Dict, Literal


SceneType = Literal['ai_video', 'gfx_persistent', 'gfx_insert', None]
Layer = Literal[1, 2]


def parse_storyboard(content: str) -> tuple[List[Dict], List[Dict]]:
    """Parse storyboard markdown into layer 1 and layer 2 scenes."""
    layer1: List[Dict] = []
    layer2: List[Dict] = []
    current_scene: Dict = {}
    current_field: str | None = None

    lines = content.strip().split('\n')

    for line in lines:
        line = line.strip()

        scene_match = re.match(r'^Scene\s+(\d+)', line, re.IGNORECASE)
        if scene_match:
            if current_scene:
                _assign_scene_to_layer(current_scene, layer1, layer2)
            current_scene = {'number': int(scene_match.group(1)), 'layer': 1}
            current_field = None
            continue

        field_match = re.match(r'^(\w+(?:\s+\w+)?)\s*:\s*(.*)$', line)
        if field_match:
            field = field_match.group(1).lower()
            if field in ['time', 'narration', 'visual', 'camera', 'assets', 'type', 'layer']:
                current_field = field
                value = field_match.group(2).strip()
                if field == 'layer':
                    current_scene[field] = int(value) if value.isdigit() else 1
                else:
                    current_scene[field] = value
            continue

        if current_field and line and current_scene:
            current_scene[current_field] += ' ' + line

    if current_scene:
        _assign_scene_to_layer(current_scene, layer1, layer2)

    return layer1, layer2


def _assign_scene_to_layer(scene: Dict, layer1: List[Dict], layer2: List[Dict]) -> None:
    """Assign scene to appropriate layer based on type or explicit layer field."""
    scene_layer = scene.get('layer', 1)
    scene_type = scene.get('type', '').lower()

    if scene_type == 'gfx_insert' and scene_layer == 1:
        scene_layer = 2

    if scene_layer == 2:
        layer2.append(scene)
    else:
        layer1.append(scene)


def parse_time_range(time_str: str) -> tuple[float, float]:
    """Parse time range '00:00-00:05' into seconds."""
    def to_seconds(t: str) -> float:
        parts = t.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return float(t)

    match = re.match(r'([\d:]+)\s*-\s*([\d:]+)', time_str)
    if match:
        return to_seconds(match.group(1)), to_seconds(match.group(2))
    return 0.0, 0.0


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def generate_html(layer1: List[Dict], layer2: List[Dict], title: str = "Storyboard Timeline") -> str:
    """Generate horizontal timeline HTML with 2 layers."""
    if not layer1 and not layer2:
        return "<html><body>No scenes found</body></html>"

    all_scenes = layer1 + layer2
    max_end = 0.0
    for scene in all_scenes:
        if 'time' in scene:
            _, end = parse_time_range(scene['time'])
            max_end = max(max_end, end)

    total_duration = max_end

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
        }}
        h1 {{ color: #4ecca3; margin-bottom: 20px; }}
        .timeline-container {{
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 40px;
        }}
        .track {{
            margin-bottom: 16px;
        }}
        .track:last-child {{ margin-bottom: 0; }}
        .track-header {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
        }}
        .track-label {{
            width: 80px;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
            padding: 6px 10px;
            border-radius: 6px;
            text-align: center;
        }}
        .track-label.layer1 {{ background: rgba(78, 204, 163, 0.2); color: #4ecca3; }}
        .track-label.layer2 {{ background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }}
        .track-info {{
            margin-left: 12px;
            font-size: 11px;
            color: #666;
        }}
        .track-timeline {{
            height: 70px;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            overflow: hidden;
            position: relative;
        }}
        .time-marker {{
            position: absolute;
            top: 0;
            bottom: 0;
            width: 1px;
            background: rgba(255,255,255,0.1);
        }}
        .time-marker-label {{
            position: absolute;
            bottom: 2px;
            font-size: 9px;
            color: #666;
            transform: translateX(-50%);
        }}
        .scene {{
            height: 100%;
            border: 1px solid;
            border-radius: 6px;
            padding: 8px;
            overflow: hidden;
            cursor: pointer;
            transition: all 0.2s;
            position: absolute;
            top: 0;
        }}
        .scene:hover {{ filter: brightness(1.2); }}
        .scene.layer1 {{
            background: rgba(78, 204, 163, 0.15);
            border-color: #4ecca3;
        }}
        .scene.layer2 {{
            background: rgba(255, 107, 107, 0.15);
            border-color: #ff6b6b;
        }}
        .scene-number {{
            position: absolute;
            top: 4px;
            left: 6px;
            font-size: 11px;
            font-weight: bold;
        }}
        .scene.layer1 .scene-number {{ color: #4ecca3; }}
        .scene.layer2 .scene-number {{ color: #ff6b6b; }}
        .scene-time {{
            position: absolute;
            bottom: 4px;
            left: 6px;
            font-size: 9px;
            color: #888;
        }}
        .scene-type {{
            position: absolute;
            top: 4px;
            right: 6px;
            font-size: 8px;
            padding: 2px 4px;
            border-radius: 3px;
            text-transform: uppercase;
        }}
        .scene.layer1 .scene-type {{ background: rgba(78, 204, 163, 0.3); color: #4ecca3; }}
        .scene.layer2 .scene-type {{ background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }}
        .scene-visual {{
            position: absolute;
            top: 22px;
            left: 6px;
            right: 6px;
            font-size: 9px;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: #ccc;
        }}
        .scenes-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
            gap: 16px;
        }}
        .scene-card {{
            background: #16213e;
            border-radius: 10px;
            padding: 16px;
        }}
        .scene-card.layer1 {{ border-left: 3px solid #4ecca3; }}
        .scene-card.layer2 {{ border-left: 3px solid #ff6b6b; }}
        .scene-card h3 {{
            margin-bottom: 12px;
            font-size: 14px;
        }}
        .scene-card.layer1 h3 {{ color: #4ecca3; }}
        .scene-card.layer2 h3 {{ color: #ff6b6b; }}
        .scene-card .field {{
            margin: 6px 0;
            font-size: 12px;
        }}
        .scene-card .field-label {{
            color: #666;
            font-size: 10px;
            text-transform: uppercase;
        }}
        .scene-card .field-value {{
            color: #ddd;
        }}
        .layer-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 9px;
            margin-left: 8px;
        }}
        .layer-badge.l1 {{ background: rgba(78, 204, 163, 0.2); color: #4ecca3; }}
        .layer-badge.l2 {{ background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }}
    </style>
</head>
<body>
    <h1>{title}</h1>

    <div class="timeline-container">
"""

    html += _render_track(layer1, total_duration, 'layer1', 'Layer 1 - AI Video / GFX Persistent')
    html += _render_track(layer2, total_duration, 'layer2', 'Layer 2 - GFX Insert (B-roll)')

    html += """    </div>

    <h2 style="color: #4ecca3; margin: 30px 0 20px;">Scenes Detail</h2>
    <div class="scenes-list">
"""

    all_scenes = sorted(layer1 + layer2, key=lambda s: s.get('number', 0))
    for scene in all_scenes:
        layer_num = scene.get('layer', 1)
        layer_class = 'layer1' if layer_num == 1 else 'layer2'
        layer_badge = f'<span class="layer-badge l{layer_num}">L{layer_num}</span>'

        html += f"""        <div class="scene-card {layer_class}">
            <h3>Scene {scene.get('number', '?')} {layer_badge}</h3>
            <div class="field">
                <div class="field-label">Time</div>
                <div class="field-value">{scene.get('time', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Type</div>
                <div class="field-value">{scene.get('type', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Layer</div>
                <div class="field-value">{scene.get('layer', 1)}</div>
            </div>
            <div class="field">
                <div class="field-label">Narration</div>
                <div class="field-value">{scene.get('narration', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Visual</div>
                <div class="field-value">{scene.get('visual', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Camera</div>
                <div class="field-value">{scene.get('camera', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Assets</div>
                <div class="field-value">{scene.get('assets', '-')}</div>
            </div>
        </div>
"""

    html += """    </div>
</body>
</html>"""

    return html


def _render_track(scenes: List[Dict], total_duration: float, layer_class: str, label: str) -> str:
    """Render a single track with scenes."""
    duration_sum = sum(parse_time_range(s['time'])[1] - parse_time_range(s['time'])[0] for s in scenes if 'time' in s)

    html = f"""        <div class="track">
            <div class="track-header">
                <div class="track-label {layer_class}">{layer_class.upper()}</div>
                <div class="track-info">{len(scenes)} scenes · {format_time(duration_sum)} total</div>
            </div>
            <div class="track-timeline">
"""

    for scene in scenes:
        if 'time' not in scene:
            continue
        start, end = parse_time_range(scene['time'])
        duration = end - start
        start_pct = (start / total_duration) * 100 if total_duration > 0 else 0
        width_pct = (duration / total_duration) * 100 if total_duration > 0 else 0

        visual = (scene.get('visual', '') or '')[:50]
        scene_type = (scene.get('type', '') or '')[:8]
        scene_num = scene.get('number', '?')
        start_time = format_time(start)

        type_badge = f'<span class="scene-type">{scene_type}</span>' if scene_type else ''

        html += f"""                <div class="scene {layer_class}" style="left: {start_pct:.2f}%; width: {width_pct:.2f}%;" title="{visual}">
                    <div class="scene-number">#{scene_num}</div>
                    {type_badge}
                    <div class="scene-visual">{visual}</div>
                    <div class="scene-time">{start_time}</div>
                </div>"""

    html += f"""            </div>
        </div>
"""

    return html


def main():
    parser = argparse.ArgumentParser(description='Convert storyboard markdown to HTML timeline with 2 layers')
    parser.add_argument('input', help='Input storyboard markdown file')
    parser.add_argument('--output', '-o', help='Output HTML file (default: timeline.html)')
    parser.add_argument('--title', '-t', default='Storyboard Timeline', help='Page title')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    content = input_path.read_text(encoding='utf-8')
    layer1, layer2 = parse_storyboard(content)

    if not layer1 and not layer2:
        print("Error: No scenes found in storyboard")
        return 1

    output_path = Path(args.output) if args.output else input_path.with_suffix('.html')
    html = generate_html(layer1, layer2, args.title)

    output_path.write_text(html, encoding='utf-8')
    print(f"Generated: {output_path}")
    print(f"Layer 1 scenes: {len(layer1)}")
    print(f"Layer 2 scenes: {len(layer2)}")
    print(f"Total scenes: {len(layer1) + len(layer2)}")

    return 0


if __name__ == '__main__':
    exit(main())
