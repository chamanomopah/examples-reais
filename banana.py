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


def wait_for_image_task(task_id: str, api_key: str, interval: int = 5, max_wait: int = 180) -> dict:
    """Poll image task status until completion"""
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
            raise Exception(f"Task failed: {status.get('failMsg', 'Unknown')}")

        print(f"  Status: {task_state} ({int(time.time() - start)}s)")
        time.sleep(interval)

    raise Exception("Task timeout")


def generate_nano_banana_image(
    prompt: str,
    api_key: str,
    aspect_ratio: str = "auto",
    resolution: str = "1K",
    output_format: str = "png",
    callback_url: str = None
) -> str:
    """POST /api/v1/jobs/createTask - Generate image with Nano Banana 2

    Args:
        prompt: Text description of the image
        aspect_ratio: auto, 1:1, 3:2, 2:3, 16:9, 9:16
        resolution: 1K, 2K, 4K
        output_format: png, jpg, webp
        callback_url: Optional webhook URL
    """
    payload = {
        "model": "nano-banana-2",
        "input": {
            "prompt": prompt,
            "image_input": [],
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

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
