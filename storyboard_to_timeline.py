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

    # Auto-detect layer from type if not explicitly set
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
            position: relative;
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 40px;
            overflow-x: auto;
        }}
        .timeline-wrapper {{
            display: flex;
            flex-direction: column;
            gap: 12px;
        }}
        .track {{
            position: relative;
            min-width: 100%;
        }}
        .track-layer1 {{
            height: 100px;
        }}
        .track-layer2 {{
            height: 80px;
        }}
        .track-label {{
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 80px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 11px;
            font-weight: bold;
            text-transform: uppercase;
            z-index: 10;
            background: #0f3460;
            border-radius: 8px 0 0 8px;
        }}
        .track-label.layer1 {{ color: #4ecca3; }}
        .track-label.layer2 {{ color: #ff6b6b; }}
        .track-content {{
            margin-left: 90px;
            height: 100%;
            display: flex;
            align-items: center;
        }}
        .scene {{
            position: relative;
            border: 2px solid;
            border-radius: 8px;
            margin: 0 2px;
            padding: 8px;
            flex-shrink: 0;
            overflow: hidden;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .scene.layer1 {{
            border-color: #4ecca3;
            background: rgba(78, 204, 163, 0.1);
        }}
        .scene.layer2 {{
            border-color: #ff6b6b;
            background: rgba(255, 107, 107, 0.1);
        }}
        .scene:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(255,255,255,0.2);
        }}
        .scene.layer1:hover {{ background: rgba(78, 204, 163, 0.2); }}
        .scene.layer2:hover {{ background: rgba(255, 107, 107, 0.2); }}
        .scene-number {{
            position: absolute;
            top: 3px;
            left: 5px;
            font-weight: bold;
            font-size: 11px;
        }}
        .scene.layer1 .scene-number {{ color: #4ecca3; }}
        .scene.layer2 .scene-number {{ color: #ff6b6b; }}
        .scene-time {{
            position: absolute;
            bottom: 3px;
            left: 5px;
            font-size: 10px;
            color: #aaa;
        }}
        .scene-visual {{
            position: absolute;
            top: 18px;
            left: 8px;
            right: 8px;
            font-size: 10px;
            line-height: 1.2;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .scene-type {{
            position: absolute;
            top: 3px;
            right: 5px;
            font-size: 9px;
            padding: 2px 4px;
            border-radius: 3px;
            text-transform: uppercase;
        }}
        .scene.layer1 .scene-type {{ background: rgba(78, 204, 163, 0.3); color: #4ecca3; }}
        .scene.layer2 .scene-type {{ background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }}
        .time-ruler {{
            display: flex;
            justify-content: space-between;
            margin-top: 10px;
            padding-top: 10px;
            border-top: 1px solid #333;
            color: #666;
            font-size: 12px;
        }}
        .scenes-list {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
        }}
        .scene-card {{
            background: #16213e;
            border-radius: 12px;
            padding: 20px;
        }}
        .scene-card.layer1 {{ border-left: 4px solid #4ecca3; }}
        .scene-card.layer2 {{ border-left: 4px solid #ff6b6b; }}
        .scene-card h3 {{
            margin-bottom: 10px;
            font-size: 14px;
        }}
        .scene-card.layer1 h3 {{ color: #4ecca3; }}
        .scene-card.layer2 h3 {{ color: #ff6b6b; }}
        .scene-card .field {{
            margin: 6px 0;
            font-size: 13px;
        }}
        .scene-card .field-label {{
            color: #666;
            font-size: 11px;
            text-transform: uppercase;
        }}
        .scene-card .field-value {{
            color: #eee;
        }}
        .layer-badge {{
            display: inline-block;
            padding: 2px 6px;
            border-radius: 3px;
            font-size: 10px;
            margin-left: 8px;
        }}
        .layer-badge.l1 {{ background: rgba(78, 204, 163, 0.3); color: #4ecca3; }}
        .layer-badge.l2 {{ background: rgba(255, 107, 107, 0.3); color: #ff6b6b; }}
    </style>
</head>
<body>
    <h1>{title}</h1>

    <div class="timeline-container">
        <div class="timeline-wrapper">
            <div class="track track-layer1">
                <div class="track-label layer1">Layer 1</div>
                <div class="track-content">
"""

    total_duration = max_end

    for scene in layer1:
        if 'time' not in scene:
            continue
        html += _render_scene_block(scene, total_duration, 'layer1')

    html += f"""
                </div>
            </div>
            <div class="track track-layer2">
                <div class="track-label layer2">Layer 2</div>
                <div class="track-content">
"""

    for scene in layer2:
        if 'time' not in scene:
            continue
        html += _render_scene_block(scene, total_duration, 'layer2')

    html += f"""
                </div>
            </div>
        </div>
        <div class="time-ruler">
            <span>00:00:00</span>
            <span>{format_time(total_duration / 4)}</span>
            <span>{format_time(total_duration / 2)}</span>
            <span>{format_time(total_duration * 3 / 4)}</span>
            <span>{format_time(total_duration)}</span>
        </div>
    </div>

    html += _generate_scenes_detail(layer1, layer2)
    html += """
</body>
</html>
"""

    return html


def _render_scene_block(scene: Dict, total_duration: float, layer_class: str) -> str:
    """Render a single scene block for the timeline."""
    start, end = parse_time_range(scene['time'])
    duration = end - start
    width_pct = (duration / total_duration) * 100 if total_duration > 0 else 0

    visual = scene.get('visual', '')[:60]
    scene_type = scene.get('type', '')
    type_badge = f'<span class="scene-type">{scene_type[:10]}</span>' if scene_type else ''

    return f"""
                    <div class="scene {layer_class}" style="width: {width_pct}%; min-width: 50px;" title="{scene.get('visual', '')}">
                        <div class="scene-number">#{scene.get('number', '?')}</div>
                        {type_badge}
                        <div class="scene-visual">{visual}</div>
                        <div class="scene-time">{format_time(start)}</div>
                    </div>"""


def _generate_scenes_detail(layer1: List[Dict], layer2: List[Dict]) -> str:
    """Generate the detailed scenes list section."""
    html = """
    <h2>Scenes Detail</h2>
    <div class="scenes-list">
"""

    all_scenes = sorted(layer1 + layer2, key=lambda s: s.get('number', 0))

    for scene in all_scenes:
        layer_num = scene.get('layer', 1)
        layer_class = 'layer1' if layer_num == 1 else 'layer2'
        layer_badge = f'<span class="layer-badge l{layer_num}">L{layer_num}</span>'

        html += f"""
        <div class="scene-card {layer_class}">
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

    html += "    </div>"
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
