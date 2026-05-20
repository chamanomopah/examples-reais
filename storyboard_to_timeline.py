#!/usr/bin/env python3
"""
Converte storyboard markdown em timeline HTML horizontal com suporte a 3 camadas.

Camadas:
- Layer 1: AI Video (prompt-based) + GFX Persistent/Anchored Graphics (A-roll)
- Layer 2: GFX Insert Graphics (B-roll)
- Layer 3: Overlay (lower thirds, text overlays, etc.) - renderizado sobre L1

Uso:
    python storyboard_to_timeline.py "storyboard.md"
    python storyboard_to_timeline.py "storyboard.md" --output "timeline.html"
"""

import re
import argparse
from pathlib import Path
from typing import List, Dict, Literal, Optional


SceneType = Literal['ai_video', 'gfx_persistent', 'gfx_insert', 'lower_third', 'text_overlay', 'image_overlay', None]
Layer = Literal[1, 2, 3]


def parse_storyboard(content: str) -> tuple[List[Dict], List[Dict], List[Dict]]:
    """Parse storyboard markdown into layer 1, layer 2, and layer 3 scenes."""
    layer1: List[Dict] = []
    layer2: List[Dict] = []
    layer3: List[Dict] = []

    lines = content.strip().split('\n')
    i = 0
    scene_number = 0

    while i < len(lines):
        line = lines[i].strip()

        scene_match = re.match(r'^Scene\s+(\d+)', line, re.IGNORECASE)
        if scene_match:
            scene_number = int(scene_match.group(1))
            i += 1
            l1, l2, l3 = _parse_scene(lines, i, scene_number)

            _validate_scene_combination(l1, l2, l3, scene_number)

            # Only add layers that have meaningful content
            if l1 and ('time' in l1 or 'visual' in l1):
                layer1.append(l1)
            if l2 and ('time' in l2 or 'visual' in l2):
                layer2.append(l2)
            if l3 and ('timein' in l3 or 'visual' in l3):
                layer3.append(l3)
            continue

        i += 1

    return layer1, layer2, layer3


def _validate_scene_combination(l1: Optional[Dict], l2: Optional[Dict], l3: Optional[Dict], scene_number: int) -> None:
    """Validate that scene layer combinations follow the rules.

    New format allows all 3 layers to coexist:
    - Layer 1 (A-Roll): Primary footage base
    - Layer 2 (B-Roll GFX): Secondary graphics/cutaways
    - Layer 3 (Overlay): Overlays on top of A-Roll
    """
    pass  # All combinations valid in new format


def _parse_scene(lines: List[str], start_idx: int, scene_number: int) -> tuple[Optional[Dict], Optional[Dict], Optional[Dict]]:
    """Parse a single scene with 3 layers."""
    l1: Optional[Dict] = None
    l2: Optional[Dict] = None
    l3: Optional[Dict] = None

    current_layer = None
    current_field = None

    i = start_idx
    while i < len(lines):
        line = lines[i].strip()

        scene_match = re.match(r'^Scene\s+\d+', line, re.IGNORECASE)
        if scene_match:
            break

        layer1_match = re.match(r'^Layer\s+1\s*[-:]?\s*(A-?Roll)?$', line, re.IGNORECASE)
        if layer1_match:
            l1 = {'number': scene_number, 'layer': 1}
            current_layer = l1
            current_field = None
            i += 1
            continue

        layer2_match = re.match(r'^Layer\s+2\s*[-:]?\s*(B-?Roll\s+GFX)?$', line, re.IGNORECASE)
        if layer2_match:
            l2 = {'number': scene_number, 'layer': 2}
            current_layer = l2
            current_field = None
            i += 1
            continue

        layer3_match = re.match(r'^Layer\s+3\s*[-:]?\s*(Overlay)?$', line, re.IGNORECASE)
        if layer3_match:
            l3 = {'number': scene_number, 'layer': 3}
            current_layer = l3
            current_field = None
            i += 1
            continue

        field_match = re.match(r'^(\w+(?:\s+\w+)?)\s*:\s*(.*)$', line)
        if field_match and current_layer:
            field = field_match.group(1).lower()
            if field in ['time', 'narration', 'visual', 'camera', 'assets', 'type', 'timein', 'timeout']:
                current_field = field
                value = field_match.group(2).strip()
                if value.lower() not in ['(empty)', '(vazio)', 'empty', '']:
                    current_layer[field] = value
            current_field = None
            i += 1
            continue

        if current_field and line and current_layer:
            current_layer[current_field] = current_layer.get(current_field, '') + ' ' + line

        i += 1

    if l1 and not l1.get('type'):
        l1['type'] = 'ai_video'

    return l1, l2, l3


def parse_time_range(time_str: str) -> tuple[float, float]:
    """Parse time range '00:00:00.000 - 00:00:05.000' into seconds."""
    def to_seconds(t: str) -> float:
        parts = t.split(':')
        if len(parts) == 3:
            h, m, s = parts
            return int(h) * 3600 + int(m) * 60 + float(s)
        elif len(parts) == 2:
            m, s = parts
            return int(m) * 60 + float(s)
        return float(t)

    match = re.match(r'([\d:.]+)\s*-\s*([\d:.]+)', time_str)
    if match:
        return to_seconds(match.group(1)), to_seconds(match.group(2))
    return 0.0, 0.0


def parse_time(time_str: str) -> float:
    """Parse single time value '00:00:05.000' into seconds."""
    parts = time_str.split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return float(time_str)


def format_time(seconds: float) -> str:
    """Format seconds to HH:MM:SS.mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def generate_html(layer1: List[Dict], layer2: List[Dict], layer3: List[Dict], title: str = "Storyboard Timeline") -> str:
    """Generate horizontal timeline HTML with 3 layers."""
    if not layer1 and not layer2 and not layer3:
        return "<html><body>No scenes found</body></html>"

    all_scenes = layer1 + layer2 + layer3
    max_end = 0.0
    for scene in all_scenes:
        if 'time' in scene:
            _, end = parse_time_range(scene['time'])
            max_end = max(max_end, end)
        elif scene.get('layer') == 3 and 'timeout' in scene:
            max_end = max(max_end, parse_time(scene['timeout']))

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
        .track-label.layer3 {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
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
        .scene.layer3 {{
            background: rgba(255, 193, 7, 0.15);
            border-color: #ffc107;
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
        .scene.layer3 .scene-number {{ color: #ffc107; }}
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
        .scene.layer3 .scene-type {{ background: rgba(255, 193, 7, 0.3); color: #ffc107; }}
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
        .scene-card.layer3 {{ border-left: 3px solid #ffc107; }}
        .scene-card h3 {{
            margin-bottom: 12px;
            font-size: 14px;
        }}
        .scene-card.layer1 h3 {{ color: #4ecca3; }}
        .scene-card.layer2 h3 {{ color: #ff6b6b; }}
        .scene-card.layer3 h3 {{ color: #ffc107; }}
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
        .layer-badge.l3 {{ background: rgba(255, 193, 7, 0.2); color: #ffc107; }}
    </style>
</head>
<body>
    <h1>{title}</h1>

    <div class="timeline-container">
"""

    html += _render_track(layer1, total_duration, 'layer1', 'Layer 1 - A-Roll', 'l1_l2')
    html += _render_track(layer2, total_duration, 'layer2', 'Layer 2 - B-Roll GFX', 'l1_l2')
    html += _render_track(layer3, total_duration, 'layer3', 'Layer 3 - Overlay', 'l3')

    html += """    </div>

    <h2 style="color: #4ecca3; margin: 30px 0 20px;">Scenes Detail</h2>
    <div class="scenes-list">
"""

    all_scenes = sorted(layer1 + layer2 + layer3, key=lambda s: (s.get('number', 0), s.get('layer', 1)))
    for scene in all_scenes:
        layer_num = scene.get('layer', 1)
        layer_class = f'layer{layer_num}'
        layer_badge = f'<span class="layer-badge l{layer_num}">L{layer_num}</span>'

        time_display = scene.get('time', '-')
        if layer_num == 3:
            timein = scene.get('timein', '-')
            timeout = scene.get('timeout', '-')
            time_display = f"{timein} - {timeout}"

        html += f"""        <div class="scene-card {layer_class}">
            <h3>Scene {scene.get('number', '?')} {layer_badge}</h3>
            <div class="field">
                <div class="field-label">Time</div>
                <div class="field-value">{time_display}</div>
            </div>
            <div class="field">
                <div class="field-label">Type</div>
                <div class="field-value">{scene.get('type', '-')}</div>
            </div>
            <div class="field">
                <div class="field-label">Layer</div>
                <div class="field-value">{layer_num}</div>
            </div>"""

        if layer_num != 3 and 'narration' in scene:
            html += f"""
            <div class="field">
                <div class="field-label">Narration</div>
                <div class="field-value">{scene.get('narration', '-')}</div>
            </div>"""

        if 'visual' in scene:
            html += f"""
            <div class="field">
                <div class="field-label">Visual</div>
                <div class="field-value">{scene.get('visual', '-')}</div>
            </div>"""

        if 'camera' in scene:
            html += f"""
            <div class="field">
                <div class="field-label">Camera</div>
                <div class="field-value">{scene.get('camera', '-')}</div>
            </div>"""

        if 'assets' in scene:
            html += f"""
            <div class="field">
                <div class="field-label">Assets</div>
                <div class="field-value">{scene.get('assets', '-')}</div>
            </div>"""

        html += """
        </div>
"""

    html += """    </div>
</body>
</html>"""

    return html


def _parse_layer3_time(scene: Dict) -> tuple[float, float]:
    """Parse time for layer 3 overlays using timein/timeout."""
    if 'timein' in scene and 'timeout' in scene:
        return parse_time(scene['timein']), parse_time(scene['timeout'])
    return 0.0, 0.0


def _render_track(scenes: List[Dict], total_duration: float, layer_class: str, label: str, time_parser_type: str) -> str:
    """Render a single track with scenes.

    time_parser_type: 'l1_l2' for Layer 1/2 (uses time field), 'l3' for Layer 3 (uses timein/timeout)
    """
    duration_sum = 0
    for s in scenes:
        if time_parser_type == 'l3':
            start, end = _parse_layer3_time(s)
        else:
            time_str = s.get('time', '')
            start, end = parse_time_range(time_str) if time_str else (0.0, 0.0)
        duration_sum += end - start

    html = f"""        <div class="track">
            <div class="track-header">
                <div class="track-label {layer_class}">{layer_class.upper()}</div>
                <div class="track-info">{len(scenes)} scenes · {format_time(duration_sum)} total</div>
            </div>
            <div class="track-timeline">
"""

    for scene in scenes:
        if time_parser_type == 'l3':
            start, end = _parse_layer3_time(scene)
        else:
            time_str = scene.get('time', '')
            start, end = parse_time_range(time_str) if time_str else (0.0, 0.0)
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
    parser = argparse.ArgumentParser(description='Convert storyboard markdown to HTML timeline with 3 layers')
    parser.add_argument('input', help='Input storyboard markdown file')
    parser.add_argument('--output', '-o', help='Output HTML file (default: timeline.html)')
    parser.add_argument('--title', '-t', default='Storyboard Timeline', help='Page title')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        return 1

    content = input_path.read_text(encoding='utf-8')
    layer1, layer2, layer3 = parse_storyboard(content)

    if not layer1 and not layer2 and not layer3:
        print("Error: No scenes found in storyboard")
        return 1

    output_path = Path(args.output) if args.output else input_path.with_suffix('.html')
    html = generate_html(layer1, layer2, layer3, args.title)

    output_path.write_text(html, encoding='utf-8')
    print(f"Generated: {output_path}")
    print(f"Layer 1 (A-Roll) scenes: {len(layer1)}")
    print(f"Layer 2 (B-Roll) scenes: {len(layer2)}")
    print(f"Layer 3 (Overlay) scenes: {len(layer3)}")
    print(f"Total scenes: {len(layer1) + len(layer2) + len(layer3)}")

    return 0


if __name__ == '__main__':
    exit(main())
