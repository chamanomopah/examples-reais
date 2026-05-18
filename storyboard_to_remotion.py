#!/usr/bin/env python3
"""
Converte storyboard markdown em projeto Remotion com A-roll e B-roll.

Gerado projeto Remotion completo:
- src/Root.tsx
- src/compositions/Storyboard.tsx
- src/data/storyboard.json
- package.json
- tsconfig.json

Uso:
    python storyboard_to_remotion.py "storyboard.md" --output "remotion_project"
"""

import re
import json
import argparse
from pathlib import Path
from typing import List, Dict, Literal, Any

SceneType = Literal['ai_video', 'gfx_persistent', 'gfx_insert', None]
Layer = Literal[1, 2]


def parse_storyboard(content: str) -> tuple[List[Dict], List[Dict]]:
    """Parse storyboard markdown into layer 1 and layer 2 scenes."""
    layer1: List[Dict] = []
    layer2: List[Dict] = []
    current_scene: Dict = {}
    current_field: str | None = None
    in_scene_section = True

    lines = content.strip().split('\n')

    for line in lines:
        stripped = line.strip()
        original = line.rstrip()

        scene_match = re.match(r'^Scene\s+(\d+)', stripped, re.IGNORECASE)
        if scene_match:
            if current_scene:
                _assign_scene_to_layer(current_scene, layer1, layer2)
            current_scene = {'number': int(scene_match.group(1)), 'layer': 1}
            current_field = None
            in_scene_section = True
            continue

        # Stop parsing when hitting non-scene sections
        if in_scene_section and stripped and not scene_match:
            if re.match(r'^[A-Z][A-Za-z\s]+List\s*:?', stripped):
                in_scene_section = False
                continue
            if stripped.startswith('##') or stripped.startswith('#'):
                in_scene_section = False
                continue

        if not in_scene_section:
            continue

        if not current_scene:
            continue

        field_match = re.match(r'^(\w+(?:\s+\w+)?)\s*:\s*(.*)$', stripped)
        if field_match:
            field = field_match.group(1).lower()
            if field in ['time', 'narration', 'visual', 'camera', 'assets', 'type', 'layer']:
                current_field = field
                value = field_match.group(2).strip()
                if field == 'layer':
                    current_scene[field] = int(value) if value.isdigit() else 1
                else:
                    current_scene[field] = value
            else:
                current_field = None
            continue

        if current_field and stripped and current_scene:
            # Only append if not empty and doesn't look like a new field/section
            if ':' not in stripped or stripped.count(':') > 1:
                current_scene[current_field] += ' ' + stripped

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

    match = re.match(r'([\d:\.]+)\s*-\s*([\d:\.]+)', time_str)
    if match:
        return to_seconds(match.group(1)), to_seconds(match.group(2))
    return 0.0, 0.0


def seconds_to_frames(seconds: float, fps: int = 30) -> int:
    """Convert seconds to frames."""
    return int(seconds * fps)


def calculate_total_duration(layer1: List[Dict], layer2: List[Dict]) -> float:
    """Calculate total video duration from all scenes."""
    max_end = 0.0
    for scene in layer1 + layer2:
        if 'time' in scene:
            _, end = parse_time_range(scene['time'])
            max_end = max(max_end, end)
    return max_end


def generate_storyboard_json(layer1: List[Dict], layer2: List[Dict], fps: int = 30) -> Dict[str, Any]:
    """Generate storyboard data JSON for Remotion."""
    total_duration = calculate_total_duration(layer1, layer2)
    duration_in_frames = seconds_to_frames(total_duration, fps)

    scenes_data = []

    for scene in sorted(layer1 + layer2, key=lambda s: s.get('number', 0)):
        if 'time' not in scene:
            continue

        start, end = parse_time_range(scene['time'])
        scene_data = {
            'number': scene.get('number', 0),
            'layer': scene.get('layer', 1),
            'type': scene.get('type', ''),
            'time': scene['time'],
            'startFrame': seconds_to_frames(start, fps),
            'endFrame': seconds_to_frames(end, fps),
            'durationInFrames': seconds_to_frames(end - start, fps),
            'narration': scene.get('narration', ''),
            'visual': scene.get('visual', ''),
            'camera': scene.get('camera', ''),
            'assets': scene.get('assets', '')
        }
        scenes_data.append(scene_data)

    return {
        'metadata': {
            'title': 'Storyboard',
            'durationInSeconds': total_duration,
            'durationInFrames': duration_in_frames,
            'fps': fps
        },
        'scenes': scenes_data,
        'layer1Count': len(layer1),
        'layer2Count': len(layer2)
    }


def generate_package_json(project_name: str = "remotion-storyboard") -> str:
    """Generate package.json for Remotion project."""
    return json.dumps({
        "name": project_name,
        "version": "1.0.0",
        "type": "module",
        "description": "Remotion storyboard project",
        "scripts": {
            "start": "remotion studio",
            "build": "remotion render",
            "upgrade": "remotion upgrade",
            "lint": "eslint src",
            "format": "prettier --write src"
        },
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "remotion": "^4.0.270",
            "@remotion/cli": "^4.0.270"
        },
        "devDependencies": {
            "@remotion/eslint-config": "^4.0.270",
            "@types/react": "^18.3.0",
            "@types/react-dom": "^18.3.0",
            "@types/node": "^20.0.0",
            "eslint": "^8.57.0",
            "prettier": "^3.2.0",
            "typescript": "^5.4.0"
        }
    }, indent=2)


def generate_tsconfig_json() -> str:
    """Generate tsconfig.json for Remotion project."""
    return json.dumps({
        "compilerOptions": {
            "target": "ES2022",
            "lib": ["DOM", "DOM.Iterable", "ES2022"],
            "jsx": "react-jsx",
            "module": "ES2022",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "allowJs": True,
            "strict": True,
            "esModuleInterop": True,
            "skipLibCheck": True,
            "forceConsistentCasingInFileNames": True,
            "isolatedModules": True,
            "noEmit": True,
            "baseUrl": ".",
            "paths": {
                "@/*": ["./src/*"]
            }
        },
        "include": ["src", "remotion.config.ts"],
        "exclude": ["node_modules"]
    }, indent=2)


def generate_root_tsx(storyboard_data: Dict[str, Any]) -> str:
    """Generate src/Root.tsx with storyboard composition."""
    metadata = storyboard_data['metadata']
    duration = metadata['durationInFrames']
    fps = metadata['fps']

    return '''import {Composition} from 'remotion';
import {Storyboard} from './compositions/Storyboard';
import storyboardData from './data/storyboard.json';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="Storyboard"
        component={Storyboard}
        durationInFrames={'''+str(duration)+'''}
        fps={'''+str(fps)+'''}
        width={1920}
        height={1080}
        defaultProps={{
          storyboardData: storyboardData as any
        }}
      />
    </>
  );
};

// Allow JSON imports
declare module '*.json' {
  const value: unknown;
  export default value;
}
'''


def generate_storyboard_tsx() -> str:
    """Generate src/compositions/Storyboard.tsx component."""
    return '''import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Sequence,
} from 'remotion';
import React, {FC} from 'react';

interface Scene {
  number: number;
  layer: number;
  type: string;
  time: string;
  startFrame: number;
  endFrame: number;
  durationInFrames: number;
  narration: string;
  visual: string;
  camera: string;
  assets: string;
}

interface StoryboardData {
  metadata: {
    title: string;
    durationInSeconds: number;
    durationInFrames: number;
    fps: number;
  };
  scenes: Scene[];
  layer1Count: number;
  layer2Count: number;
}

interface StoryboardProps {
  storyboardData: StoryboardData;
}

// Type badge colors
const getTypeColor = (type: string): string => {
  const t = type.toLowerCase();
  if (t.includes('gfx') && t.includes('persistent')) return '#4ecca3';
  if (t.includes('gfx') && t.includes('insert')) return '#ff6b6b';
  if (t.includes('ai') && t.includes('video')) return '#6c5ce7';
  return '#74b9ff';
};

const ARollScene: FC<{scene: Scene; progress: number}> = ({ scene, progress }) => {
  const opacity = interpolate(progress, [0, 0.15, 0.85, 1], [0, 1, 1, 0]);
  const slideIn = interpolate(progress, [0, 0.15], [50, 0], {
    extrapolateRight: 'clamp',
  });
  const scale = interpolate(progress, [0, 0.15], [0.9, 1], {
    extrapolateRight: 'clamp',
  });

  const typeColor = getTypeColor(scene.type);

  return (
    <AbsoluteFill style={{
      opacity,
      transform: `translateY(${slideIn}px) scale(${scale})`,
    }}>
      {/* Background gradient */}
      <AbsoluteFill style={{
        background: `linear-gradient(135deg, #0f0f1e 0%, #1a1a2e 50%, #16213e 100%)`,
      }} />

      {/* Scene number watermark */}
      <div style={{
        position: 'absolute',
        bottom: 40,
        right: 40,
        fontSize: 120,
        fontWeight: 'bold',
        color: 'rgba(255,255,255,0.03)',
        fontFamily: 'Arial, sans-serif',
      }}>
        {String(scene.number).padStart(2, '0')}
      </div>

      {/* Main content */}
      <AbsoluteFill style={{
        justifyContent: 'center',
        alignItems: 'center',
        padding: 80,
      }}>
        {/* Scene header */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 20,
          marginBottom: 40,
        }}>
          <div style={{
            fontSize: 72,
            fontWeight: 'bold',
            color: typeColor,
            fontFamily: 'Arial, sans-serif',
            textShadow: `0 0 40px ${typeColor}40`,
          }}>
            {String(scene.number).padStart(2, '0')}
          </div>

          {scene.type && (
            <div style={{
              padding: '10px 24px',
              background: `${typeColor}20`,
              border: `2px solid ${typeColor}`,
              borderRadius: 30,
              color: typeColor,
              fontSize: 16,
              fontWeight: 'bold',
              textTransform: 'uppercase',
              letterSpacing: 2,
            }}>
              {scene.type.replace('_', ' ')}
            </div>
          )}
        </div>

        {/* Visual description */}
        <div style={{
          fontSize: 28,
          color: '#eee',
          textAlign: 'center',
          maxWidth: 1400,
          lineHeight: 1.5,
          marginBottom: 30,
          fontFamily: 'Georgia, serif',
        }}>
          {scene.visual}
        </div>

        {/* Camera info */}
        {scene.camera && (
          <div style={{
            fontSize: 16,
            color: '#888',
            fontStyle: 'italic',
            marginBottom: 40,
          }}>
            <span style={{color: '#666'}}>CAMERA:</span> {scene.camera}
          </div>
        )}

        {/* Narration bar */}
        {scene.narration && (
          <div style={{
            position: 'absolute',
            bottom: 100,
            left: 80,
            right: 80,
            padding: '25px 40px',
            background: 'rgba(0, 0, 0, 0.75)',
            backdropFilter: 'blur(20px)',
            borderRadius: 20,
            border: '1px solid rgba(255,255,255,0.1)',
          }}>
            <div style={{
              fontSize: 12,
              color: '#666',
              textTransform: 'uppercase',
              letterSpacing: 2,
              marginBottom: 8,
            }}>
              Narration
            </div>
            <div style={{
              fontSize: 22,
              color: '#fff',
              lineHeight: 1.4,
            }}>
              {scene.narration}
            </div>
          </div>
        )}
      </AbsoluteFill>

      {/* Top info bar */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: 60,
        background: 'rgba(0,0,0,0.5)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 40',
      }}>
        <div style={{fontSize: 14, color: '#888'}}>
          A-Roll Layer
        </div>
        <div style={{fontSize: 14, color: typeColor}}>
          {scene.time}
        </div>
      </div>
    </AbsoluteFill>
  );
};

const BRollOverlay: FC<{scene: Scene; progress: number}> = ({ scene, progress }) => {
  const opacity = interpolate(progress, [0, 0.1, 0.9, 1], [0, 1, 1, 0]);
  const scale = interpolate(progress, [0, 0.1, 0.9, 1], [0.95, 1, 1, 0.95]);

  return (
    <AbsoluteFill style={{
      justifyContent: 'center',
      alignItems: 'center',
      pointerEvents: 'none',
    }}>
      <div style={{
        width: '70%',
        height: '70%',
        background: 'rgba(255, 107, 107, 0.08)',
        border: '3px solid #ff6b6b',
        borderRadius: 24,
        padding: 40,
        opacity,
        transform: `scale(${scale})`,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        alignItems: 'center',
        backdropFilter: 'blur(10px)',
      }}>
        <div style={{
          fontSize: 14,
          color: '#ff6b6b',
          textTransform: 'uppercase',
          letterSpacing: 3,
          marginBottom: 20,
        }}>
          B-Roll Insert
        </div>
        <div style={{
          fontSize: 48,
          fontWeight: 'bold',
          color: '#ff6b6b',
          marginBottom: 20,
        }}>
          {String(scene.number).padStart(2, '0')}
        </div>
        <div style={{
          fontSize: 20,
          color: '#eee',
          textAlign: 'center',
          maxWidth: 600,
          lineHeight: 1.5,
        }}>
          {scene.visual}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// Timeline bar component
const TimelineBar: FC<{storyboardData: StoryboardData; currentFrame: number}> = ({ storyboardData, currentFrame }) => {
  const totalFrames = storyboardData.metadata.durationInFrames;
  const progress = (currentFrame / totalFrames) * 100;

  return (
    <div style={{
      position: 'absolute',
      bottom: 0,
      left: 0,
      right: 0,
      height: 8,
      background: 'rgba(255,255,255,0.1)',
    }}>
      <div style={{
        height: '100%',
        width: `${progress}%`,
        background: 'linear-gradient(90deg, #4ecca3 0%, #6c5ce7 100%)',
        transition: 'width 0.1s linear',
      }} />
    </div>
  );
};

// Scene indicators
const SceneIndicators: FC<{storyboardData: StoryboardData; currentFrame: number}> = ({ storyboardData, currentFrame }) => {
  const totalFrames = storyboardData.metadata.durationInFrames;

  return (
    <div style={{
      position: 'absolute',
      bottom: 20,
      left: 40,
      right: 40,
      display: 'flex',
      gap: 4,
    }}>
      {storyboardData.scenes.map((scene) => {
        const left = (scene.startFrame / totalFrames) * 100;
        const width = (scene.durationInFrames / totalFrames) * 100;
        const isActive = currentFrame >= scene.startFrame && currentFrame < scene.endFrame;
        const isPast = currentFrame >= scene.endFrame;

        return (
          <div
            key={scene.number}
            style={{
              position: 'absolute',
              left: `${left}%`,
              width: `${width}%`,
              height: 4,
              background: isActive ? '#4ecca3' : isPast ? '#333' : '#222',
              borderRadius: 2,
              transition: 'background 0.2s',
            }}
            title={`Scene ${scene.number}: ${scene.time}`}
          />
        );
      })}
    </div>
  );
};

export const Storyboard: FC<StoryboardProps> = ({ storyboardData }) => {
  const { fps, durationInFrames } = useVideoConfig();
  const frame = useCurrentFrame();

  const currentSecond = (frame / fps).toFixed(1);
  const totalSeconds = (durationInFrames / fps).toFixed(1);

  // Get active scene
  const activeScene = storyboardData.scenes.find(
    s => frame >= s.startFrame && frame < s.endFrame
  );

  return (
    <AbsoluteFill style={{backgroundColor: '#0a0a0a'}}>
      {/* Render all A-roll scenes */}
      {storyboardData.scenes
        .filter(s => s.layer === 1)
        .map((scene) => {
          const sceneProgress = (frame - scene.startFrame) / scene.durationInFrames;

          return (
            <Sequence
              key={`aroll-${scene.number}`}
              from={scene.startFrame}
              durationInFrames={scene.durationInFrames}
            >
              <ARollScene scene={scene} progress={sceneProgress} />
            </Sequence>
          );
        })}

      {/* Render all B-roll overlays */}
      {storyboardData.scenes
        .filter(s => s.layer === 2)
        .map((scene) => {
          const sceneProgress = (frame - scene.startFrame) / scene.durationInFrames;

          return (
            <Sequence
              key={`broll-${scene.number}`}
              from={scene.startFrame}
              durationInFrames={scene.durationInFrames}
            >
              <BRollOverlay scene={scene} progress={sceneProgress} />
            </Sequence>
          );
        })}

      {/* Timeline bar */}
      <TimelineBar storyboardData={storyboardData} currentFrame={frame} />

      {/* Scene indicators */}
      <SceneIndicators storyboardData={storyboardData} currentFrame={frame} />

      {/* Debug overlay */}
      <div style={{
        position: 'absolute',
        top: 20,
        left: 20,
        fontSize: 13,
        fontFamily: 'monospace',
        color: '#666',
      }}>
        <div>Frame: {frame} / {durationInFrames}</div>
        <div>Time: {currentSecond}s / {totalSeconds}s</div>
        {activeScene && (
          <div style={{color: '#4ecca3', marginTop: 8}}>
            Scene {activeScene.number} ({activeScene.type})
          </div>
        )}
      </div>

      {/* Stats overlay */}
      <div style={{
        position: 'absolute',
        top: 20,
        right: 20,
        fontSize: 12,
        color: '#444',
        textAlign: 'right',
      }}>
        <div>A-Roll: {storyboardData.layer1Count}</div>
        <div>B-Roll: {storyboardData.layer2Count}</div>
        <div>{storyboardData.metadata.fps} fps</div>
      </div>
    </AbsoluteFill>
  );
};
'''


def generate_remotion_config() -> str:
    """Generate remotion.config.ts for Remotion 4.x."""
    return '''import {Config} from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
Config.setPixelFormat('yuv420p');
Config.setCodec('h264');
Config.setConcurrency(null);
'''


def generate_index_ts() -> str:
    """Generate src/index.ts - entry point for Remotion 4.x."""
    return '''import {registerRoot} from 'remotion';
import {RemotionRoot} from './Root';

registerRoot(RemotionRoot);
'''


def generate_storyboard_types() -> str:
    """Generate src/types/storyboard.d.ts - TypeScript types."""
    return '''export interface Scene {
  number: number;
  layer: number;
  type: string;
  time: string;
  startFrame: number;
  endFrame: number;
  durationInFrames: number;
  narration: string;
  visual: string;
  camera: string;
  assets: string;
}

export interface StoryboardData {
  metadata: {
    title: string;
    durationInSeconds: number;
    durationInFrames: number;
    fps: number;
  };
  scenes: Scene[];
  layer1Count: number;
  layer2Count: number;
}
'''


def generate_gitignore() -> str:
    """Generate .gitignore for Remotion project."""
    return '''# Dependencies
node_modules/

# Build output
out/
dist/
render/

# Remotion
.remotion/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
npm-debug.log*

# Environment
.env
.env.local
'''


def create_remotion_project(
    storyboard_path: Path,
    output_dir: Path,
    fps: int = 30
) -> None:
    """Create complete Remotion project from storyboard."""
    if not storyboard_path.exists():
        raise FileNotFoundError(f"Storyboard not found: {storyboard_path}")

    # Parse storyboard
    content = storyboard_path.read_text(encoding='utf-8')
    layer1, layer2 = parse_storyboard(content)

    if not layer1 and not layer2:
        raise ValueError("No scenes found in storyboard")

    # Create output directory structure
    src_dir = output_dir / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    (src_dir / "compositions").mkdir(exist_ok=True)
    (src_dir / "data").mkdir(exist_ok=True)
    (src_dir / "types").mkdir(exist_ok=True)
    (output_dir / "out").mkdir(exist_ok=True)

    # Generate storyboard data
    storyboard_data = generate_storyboard_json(layer1, layer2, fps)

    # Write files
    (output_dir / "package.json").write_text(generate_package_json(output_dir.name), encoding='utf-8')
    (output_dir / "tsconfig.json").write_text(generate_tsconfig_json(), encoding='utf-8')
    (output_dir / "remotion.config.ts").write_text(generate_remotion_config(), encoding='utf-8')
    (output_dir / ".gitignore").write_text(generate_gitignore(), encoding='utf-8')
    (src_dir / "index.ts").write_text(generate_index_ts(), encoding='utf-8')
    (src_dir / "Root.tsx").write_text(generate_root_tsx(storyboard_data), encoding='utf-8')
    (src_dir / "compositions" / "Storyboard.tsx").write_text(generate_storyboard_tsx(), encoding='utf-8')
    (src_dir / "types" / "storyboard.d.ts").write_text(generate_storyboard_types(), encoding='utf-8')
    (src_dir / "data" / "storyboard.json").write_text(json.dumps(storyboard_data, indent=2), encoding='utf-8')

    # Create README
    readme = f"""# Remotion Storyboard Project

Generated from: {storyboard_path.name}

## Setup

```bash
npm install
```

## Development

```bash
npm start
```

## Render

```bash
npm run build Storyboard out/video.mp4
```

## Project Info

- Total Duration: {storyboard_data['metadata']['durationInSeconds']:.2f}s
- Total Frames: {storyboard_data['metadata']['durationInFrames']}
- FPS: {fps}
- Layer 1 Scenes (A-roll): {storyboard_data['layer1Count']}
- Layer 2 Scenes (B-roll): {storyboard_data['layer2Count']}
"""
    (output_dir / "README.md").write_text(readme, encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description='Convert storyboard markdown to Remotion project')
    parser.add_argument('input', help='Input storyboard markdown file')
    parser.add_argument('--output', '-o', help='Output directory (default: remotion_storyboard)')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second (default: 30)')

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else Path('remotion_storyboard')

    try:
        create_remotion_project(input_path, output_path, args.fps)

        print(f"[OK] Remotion project created: {output_path}")
        print(f"  - cd {output_path}")
        print(f"  - npm install")
        print(f"  - npm start")

    except Exception as e:
        print(f"[ERROR] {e}")
        return 1

    return 0


if __name__ == '__main__':
    exit(main())
