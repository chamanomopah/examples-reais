#!/usr/bin/env python3
"""
Insert image paths into Veo 3.1 prompts based on ingredient IDs.

Reads veo3_prompts.json and banana_prompts.json, adds image_paths field
to each clip pointing to local reference images.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Any:
    """Load JSON file with error handling."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {path}: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Insert image paths into Veo 3.1 prompts based on ingredient IDs"
    )
    parser.add_argument(
        "--veo-prompts",
        type=Path,
        required=True,
        help="Path to veo3_prompts.json",
    )
    parser.add_argument(
        "--banana-prompts",
        type=Path,
        default=None,
        help="Path to banana_prompts.json (default: same dir as veo-prompts)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: veo3_prompts_with_imgpaths.json in veo-prompts dir)",
    )

    args = parser.parse_args()

    # Determine paths
    veo_prompts_path = args.veo_prompts
    work_dir = veo_prompts_path.parent
    ref_images_dir = work_dir / "ref_images"

    banana_prompts_path = args.banana_prompts or (work_dir / "banana_prompts.json")
    output_path = args.output or (work_dir / "veo3_prompts_with_imgpaths.json")

    # Load inputs
    veo_data = load_json(veo_prompts_path)
    banana_data = load_json(banana_prompts_path)

    # banana_prompts.json is a LIST of items with ingredient_id and "item" (name)
    # veo3_prompts.json uses item NAMES, not IDs
    # Build mapping: name -> ingredient_id
    name_to_id: Dict[str, str] = {}
    if isinstance(banana_data, list):
        for item in banana_data:
            if isinstance(item, dict):
                item_id = item.get("ingredient_id")
                item_name = item.get("item")
                if item_id and item_name:
                    name_to_id[item_name] = item_id

    warnings = []

    # Process clips
    for clip in veo_data:
        ingredient_names = clip.get("ingredients", [])
        image_paths = []

        for name in ingredient_names:
            # Look up ingredient_id by name
            ing_id = name_to_id.get(name)

            if not ing_id:
                warnings.append(f"Ingredient name '{name}' not found in banana_prompts.json")
                image_paths.append("")
                continue

            # Path is simply: ref_images/{ingredient_id}.png
            img_path = ref_images_dir / f"{ing_id}.png"

            if not img_path.exists():
                warnings.append(f"Image not found for ingredient '{name}' ({ing_id})")
                image_paths.append("")
                continue

            image_paths.append(str(img_path))

        clip["image_paths"] = image_paths

    # Write output - compact format
    def compact_json(obj, indent=2):
        """Custom JSON serializer with compact arrays."""
        raw = json.dumps(obj, indent=indent, ensure_ascii=False)
        # Remove spaces after commas in arrays: ["a", "b"] -> ["a","b"]
        import re
        return re.sub(r'(\[[^\]]*?)\s*,\s*', r'\1,', raw)

    output_path.write_text(
        compact_json(veo_data),
        encoding="utf-8",
    )

    # Print warnings
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)

    print(f"Output written to: {output_path}")
    print(f"Clips processed: {len(veo_data)}")
    print(f"Warnings: {len(warnings)}")


if __name__ == "__main__":
    main()
