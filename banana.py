#!/usr/bin/env python3
"""
Nano Banana 2 API Client
Provider: https://kie.ai

Model:
- Nano Banana 2 (nano-banana-2) - Gemini 3.1 Flash Image

Base URL: https://api.kie.ai/api/v1
"""

import os
import sys
import time
import json
import argparse
import mimetypes
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load .env file
env_path = Path.home() / ".alfredo" / ".env"
load_dotenv(env_path)


# ============== Configuration ==============
BASE_URL = "https://api.kie.ai/api/v1"


def get_api_key() -> str:
    """Get API key from environment"""
    key = os.environ.get("KIE_AI_API_KEY")
    if not key:
        print("ERROR: KIE_AI_API_KEY not set")
        print(f"Checked: {env_path}")
        sys.exit(1)
    return key


def check_credits(api_key: str) -> int:
    """GET /api/v1/chat/credit - Check account balance"""
    resp = requests.get(
        f"{BASE_URL}/chat/credit",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", 0)


def get_image_task_status(task_id: str, api_key: str) -> dict:
    """GET /api/v1/jobs/recordInfo - Get Nano Banana image task status (unified endpoint)"""
    resp = requests.get(
        f"{BASE_URL}/jobs/recordInfo",
        params={"taskId": task_id},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", {})


def wait_for_image_task(task_id: str, api_key: str, interval: int = 5, max_wait: int = 30) -> dict:
    """Poll image task status until completion with retry on timeout"""

    def is_fatal_error(msg: str) -> bool:
        """Check if error is fatal (no retry)"""
        msg_lower = msg.lower()
        return any(x in msg_lower for x in ["insufficient credits", "api key", "unauthorized", "invalid key"])

    def poll_with_timeout() -> dict:
        """Internal poll with timeout"""
        start = time.time()
        while time.time() - start < max_wait:
            status = get_image_task_status(task_id, api_key)
            task_state = status.get("state", "")

            if task_state == "success":
                # Parse resultJson to get URLs
                result_json = status.get("resultJson")
                if result_json:
                    result_data = json.loads(result_json)
                    status["resultUrls"] = result_data.get("resultUrls", [])
                return status
            if task_state == "failed":
                fail_msg = status.get('failMsg', 'Unknown')
                if is_fatal_error(fail_msg):
                    raise Exception(f"Fatal error: {fail_msg}")
                raise Exception(f"Task failed: {fail_msg}")

            print(f"  Status: {task_state} ({int(time.time() - start)}s)")
            time.sleep(interval)
        return None  # Timeout

    # Main loop with retry
    max_retries = 3
    retry_delay = 15

    for attempt in range(max_retries):
        try:
            result = poll_with_timeout()
            if result:
                return result
            # Timeout occurred
            if attempt < max_retries - 1:
                print(f"  Timeout, waiting {retry_delay}s before retry {attempt + 2}/{max_retries}...")
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                raise Exception(f"Task timeout after {max_retries} retries")
        except Exception as e:
            error_msg = str(e)
            if is_fatal_error(error_msg):
                raise  # Fatal error, no retry
            if "timeout" in error_msg.lower() or "waiting" in error_msg.lower():
                if attempt < max_retries - 1:
                    print(f"  {error_msg}, retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise
            else:
                raise  # Other errors, propagate immediately


def generate_nano_banana_image(
    prompt: str,
    api_key: str,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    callback_url: str = None,
    image_input: list = None
) -> str:
    """POST /api/v1/jobs/createTask - Generate image with Nano Banana 2

    Args:
        prompt: Text description of the image
        aspect_ratio: auto, 1:1, 3:2, 2:3, 16:9, 9:16
        resolution: 1K, 2K, 4K
        output_format: png, jpg, webp
        callback_url: Optional webhook URL
        image_input: Optional list of base64 images for image-to-image
    """
    payload = {
        "model": "nano-banana-2",
        "input": {
            "prompt": prompt,
            "image_input": image_input or [],
            "aspect_ratio": aspect_ratio,
            "resolution": resolution,
            "output_format": output_format
        }
    }
    if callback_url:
        payload["callBackUrl"] = callback_url

    resp = requests.post(
        f"{BASE_URL}/jobs/createTask",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", {}).get("taskId", "")


def download_image(url: str, output_path: str) -> bool:
    """Download image from URL"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            with open(output_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"  Downloaded: {output_path} ({output_path.stat().st_size / 1024:.1f}KB)")
        return True
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64 string for API"""
    import base64
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def upload_image_to_kie(image_path: str, api_key: str) -> str:
    """Upload image to KIE AI storage and return public URL

    Args:
        image_path: Path to local image file
        api_key: KIE AI API key

    Returns:
        Public URL of uploaded image
    """
    import base64
    import mimetypes

    # Read and encode image
    with open(image_path, "rb") as f:
        image_data = f.read()
    base64_data = base64.b64encode(image_data).decode("utf-8")

    # Detect MIME type
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    filename = Path(image_path).name

    # Upload via base64 endpoint
    # Note: KIE AI changed base URL to https://kieai.redpandaai.co
    upload_url = "https://kieai.redpandaai.co/api/file-base64-upload"
    payload = {
        "base64Data": f"data:{mime_type};base64,{base64_data}",
        "uploadPath": "images/nano-banana",
        "fileName": filename
    }

    resp = requests.post(
        upload_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60
    )
    data = resp.json()
    if not data.get("success"):
        raise Exception(f"Upload failed: {data.get('msg')} | Full response: {data}")

    return data.get("data", {}).get("downloadUrl", "")


def get_base_image(category: str, base_path: Path) -> str:
    """Map category to base image path"""
    mapping = {
        "humans": "humans_base.png",
        "objects": "objects_base.png",
        "vehicles": "vehicles_base.png",
        "environments": "environments_base.png"
    }
    filename = mapping.get(category)
    if not filename:
        raise ValueError(f"Unknown category: {category}. Valid: {list(mapping.keys())}")
    path = base_path / filename
    if not path.exists():
        raise FileNotFoundError(f"Base image not found: {path}")
    return str(path)


def process_batch(
    prompts_file: str,
    api_key: str,
    wait: bool = False,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    limit: int = None
) -> dict:
    """Process multiple items from banana_prompts.json

    Args:
        prompts_file: Path to banana_prompts.json
        api_key: API key
        wait: Whether to wait for completion
        aspect_ratio, resolution, output_format: Image generation params
        limit: Maximum number of items to process (default: 1)

    Returns:
        Dict mapping ingredient_id to image_path
    """
    prompts_path = Path(prompts_file)
    work_dir = prompts_path.parent
    base_path = Path.home() / ".alfredo" / ".templates" / "images_base"

    # Load prompts
    items = json.loads(prompts_path.read_text())
    results = {}
    tasks = []

    # Apply limit
    if limit is not None and limit < len(items):
        items = items[:limit]
        print(f"Limite aplicado: processando {limit} de {len(items)} itens")
    else:
        print(f"Processing {len(items)} items from {prompts_file}")

    for idx, item in enumerate(items, 1):
        ingredient_id = item.get("ingredient_id")
        category = item.get("category")
        prompt = item.get("image_prompt")

        if not all([ingredient_id, category, prompt]):
            print(f"  Skipping item {idx}: missing fields")
            continue

        print(f"[{idx}/{len(items)}] {ingredient_id} ({category})")

        try:
            # Get base image for category
            base_image = get_base_image(category, base_path)

            # Upload image to get public URL
            print(f"  Uploading base image...")
            image_url = upload_image_to_kie(base_image, api_key)
            print(f"  Image URL: {image_url}")

            # Generate with image_input (array of URLs)
            task_id = generate_nano_banana_image(
                prompt=prompt,
                api_key=api_key,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                output_format=output_format,
                image_input=[image_url]
            )

            print(f"  Task ID: {task_id}")

            tasks.append((idx, ingredient_id, task_id))

            if not wait:
                results[ingredient_id] = {"task_id": task_id, "status": "pending"}

        except Exception as e:
            print(f"  ERROR: {e}")
            results[ingredient_id] = {"error": str(e)}

    # Wait for all tasks if requested
    if wait:
        ref_dir = work_dir / "ref_images"
        ref_dir.mkdir(exist_ok=True)

        for idx, ingredient_id, task_id in tasks:
            print(f"Waiting for {ingredient_id}...")
            max_item_retries = 2
            item_retry_delay = 15

            for item_attempt in range(max_item_retries + 1):
                try:
                    result = wait_for_image_task(task_id, api_key)
                    image_url = result.get("resultUrls", [""])[0]

                    if image_url:
                        output_path = ref_dir / f"{ingredient_id}.png"
                        if download_image(image_url, output_path):
                            results[ingredient_id] = {
                                "task_id": task_id,
                                "image_path": str(output_path),
                                "status": "completed"
                            }
                        else:
                            results[ingredient_id] = {"task_id": task_id, "status": "download_failed"}
                    else:
                        results[ingredient_id] = {"task_id": task_id, "status": "no_url"}
                    break  # Success, exit retry loop

                except Exception as e:
                    error_msg = str(e)
                    # Check if fatal error
                    is_fatal = any(x in error_msg.lower() for x in ["insufficient credits", "api key", "unauthorized", "invalid key"])
                    is_timeout = "timeout" in error_msg.lower()

                    if is_fatal or item_attempt >= max_item_retries or not is_timeout:
                        print(f"  ERROR: {e}")
                        results[ingredient_id] = {"task_id": task_id, "error": str(e)}
                        break
                    else:
                        print(f"  Timeout, retrying in {item_retry_delay}s...")
                        time.sleep(item_retry_delay)
                        item_retry_delay *= 2

    return results


# ============== CLI Interface ==============
def main():
    parser = argparse.ArgumentParser(
        description="Nano Banana 2 API Client - Image Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check credits
  python kie_ai.py credits

  # Generate image
  python kie_ai.py image "a cat in space" --ratio 16:9 --res 4K

  # Generate image and wait for result
  python kie_ai.py image "a cat in space" --wait
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Credits
    subparsers.add_parser("credits", help="Check account credit balance")

    # Image generation
    img_parser = subparsers.add_parser("image", help="Generate image with Nano Banana 2")
    img_parser.add_argument("prompt", help="Image description")
    img_parser.add_argument("--ratio", choices=["auto", "1:1", "3:2", "2:3", "16:9", "9:16"], default="auto")
    img_parser.add_argument("--res", choices=["1K", "2K", "4K"], default="1K", help="Resolution")
    img_parser.add_argument("--fmt", choices=["png", "jpg", "webp"], default="png", help="Output format")
    img_parser.add_argument("--wait", action="store_true", help="Wait for completion")
    img_parser.add_argument("--output", help="Output path for downloaded image")

    # Status check
    status_parser = subparsers.add_parser("status", help="Check task status")
    status_parser.add_argument("task_id", help="Task ID to check")

    # Batch processing
    batch_parser = subparsers.add_parser("batch", help="Process banana_prompts.json")
    batch_parser.add_argument("prompts_file", help="Path to banana_prompts.json")
    batch_parser.add_argument("--ratio", choices=["auto", "1:1", "3:2", "2:3", "16:9", "9:16"], default="auto")
    batch_parser.add_argument("--res", choices=["1K", "2K", "4K"], default="1K", help="Resolution")
    batch_parser.add_argument("--fmt", choices=["png", "jpg", "webp"], default="png", help="Output format")
    batch_parser.add_argument("--wait", action="store_true", help="Wait for completion and download")
    batch_parser.add_argument("--output", help="Output JSON path for mapping results")
    batch_parser.add_argument("--limite", "--limit", type=int, default=1, help="Max number of images to generate (default: 1)")

    args = parser.parse_args()
    api_key = get_api_key()

    try:
        match args.command:
            case "credits":
                credits = check_credits(api_key)
                print(f"Credits: {credits}")

            case "image":
                print(f"Generating image: {args.prompt}")
                task_id = generate_nano_banana_image(
                    prompt=args.prompt,
                    api_key=api_key,
                    aspect_ratio=args.ratio,
                    resolution=args.res,
                    output_format=args.fmt
                )
                print(f"Task ID: {task_id}")

                if args.wait:
                    result = wait_for_image_task(task_id, api_key)
                    print(f"Status: {result.get('state')}")
                    image_url = result.get("resultUrls", [""])[0] if result.get("resultUrls") else ""
                    print(f"Result: {image_url}")

                    # Download if output specified
                    if args.output and image_url:
                        download_image(image_url, args.output)

            case "status":
                status = get_image_task_status(args.task_id, api_key)
                print(json.dumps(status, indent=2))

            case "batch":
                results = process_batch(
                    prompts_file=args.prompts_file,
                    api_key=api_key,
                    wait=args.wait,
                    aspect_ratio=args.ratio,
                    resolution=args.res,
                    output_format=args.fmt,
                    limit=args.limite
                )

                if args.output:
                    Path(args.output).write_text(json.dumps(results, indent=2))
                    print(f"Results saved to: {args.output}")
                else:
                    print(json.dumps(results, indent=2))

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
