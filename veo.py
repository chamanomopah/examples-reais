#!/usr/bin/env python3
"""
Veo 3.1 API Client
Provider: https://kie.ai

Models:
- Veo 3.1 Fast (veo3_fast) - Fast video generation
- Veo 3.1 Quality (veo3) - High-quality video generation

Base URL: https://api.kie.ai/api/v1

Video Generation Modes:
- TEXT_2_VIDEO: Text prompt only
- FIRST_AND_LAST_FRAMES_2_VIDEO: 1 or 2 images (first/last frame)
- REFERENCE_2_VIDEO: 1-3 images (ingredients/materials) - veo3_fast only
"""

import os
import sys
import time
import json
import argparse
from typing import Optional
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


# ============== API Endpoints ==============
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


def get_task_status(task_id: str, api_key: str) -> dict:
    """GET /api/v1/veo/record-info - Get Veo task status

    Response structure:
    - successFlag: 0=processing, 1=success, 2=failed, 3=generation_failed
    - response.resultUrls: array of video URLs
    - response.originUrls: array of original URLs
    """
    resp = requests.get(
        f"{BASE_URL}/veo/record-info",
        params={"taskId": task_id},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")

    task_data = data.get("data", {})
    success_flag = task_data.get("successFlag", 0)

    # Map successFlag to status
    status_map = {0: "processing", 1: "succeeded", 2: "failed", 3: "failed"}
    task_data["status"] = status_map.get(success_flag, "processing")

    return task_data


def get_download_url(file_url: str, api_key: str) -> str:
    """POST /api/v1/common/download-url - Get temporary download link (20min expiry)"""
    resp = requests.post(
        f"{BASE_URL}/common/download-url",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={"url": file_url},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", "")


def wait_for_task(task_id: str, api_key: str, interval: int = 10, max_wait: int = 600) -> dict:
    """Poll task status until completion"""
    start = time.time()
    while time.time() - start < max_wait:
        status = get_task_status(task_id, api_key)

        if status.get("status") == "succeeded":
            return status
        if status.get("status") == "failed":
            raise Exception(f"Task failed: {status.get('errorMsg', 'Unknown')}")

        print(f"  Status: {status.get('status')} ({int(time.time() - start)}s)")
        time.sleep(interval)

    raise Exception("Task timeout")


def get_video_url_from_result(result: dict) -> Optional[str]:
    """Extract first video URL from task result

    Handles different response formats:
    - Veo record-info: response.resultUrls or response.originUrls
    - Legacy: info.resultUrls or resultUrl
    """
    # Try Veo record-info format
    response = result.get("response", {})
    urls = response.get("resultUrls") or response.get("originUrls")
    if urls and isinstance(urls, list) and len(urls) > 0:
        return urls[0]

    # Try legacy format
    info = result.get("info", {})
    urls = info.get("resultUrls") or info.get("originUrls") or []
    if urls and isinstance(urls, list) and len(urls) > 0:
        return urls[0]

    # Fallback to direct resultUrl
    return result.get("resultUrl")


# ============== Veo 3.1 (Video) ==============
def generate_veo3_video(
    prompt: str,
    api_key: str,
    model: str = "veo3_fast",
    aspect_ratio: str = "16:9",
    image_urls: Optional[list[str]] = None,
    generation_type: str = "TEXT_2_VIDEO",
    seeds: Optional[int] = None,
    watermark: Optional[str] = None,
    enable_translation: bool = True,
    negative_prompt: Optional[str] = None,
    callback_url: Optional[str] = None
) -> str:
    """POST /api/v1/veo/generate - Generate video with Veo 3.1

    Args:
        prompt: Text description of the video
        model: veo3 (quality) or veo3_fast (fast, cheaper)
        aspect_ratio: 16:9, 9:16, Auto
        image_urls: List of image URLs for image-to-video
        generation_type:
            - TEXT_2_VIDEO: Text prompt only
            - FIRST_AND_LAST_FRAMES_2_VIDEO: 1-2 images (first/last frame transition)
            - REFERENCE_2_VIDEO: 1-3 images (ingredients/materials, veo3_fast only)
        seeds: Random seed 10000-99999 for reproducibility
        watermark: Optional watermark text
        enable_translation: Auto-translate prompt to English
        callback_url: Optional webhook URL

    Image URLs by generation_type:
        - TEXT_2_VIDEO: No images needed
        - FIRST_AND_LAST_FRAMES_2_VIDEO: 1 or 2 images
            * 1 image: Generate video based on the image
            * 2 images: First = first frame, Second = last frame (transition)
        - REFERENCE_2_VIDEO: 1-3 images (ingredients/materials for style/character)
    """
    payload = {
        "prompt": prompt,
        "model": model,
        "aspect_ratio": aspect_ratio,
        "enableTranslation": enable_translation
    }

    if negative_prompt:
        payload["negativePrompt"] = negative_prompt

    if image_urls:
        payload["imageUrls"] = image_urls
    if generation_type != "TEXT_2_VIDEO":
        payload["generationType"] = generation_type
    if seeds is not None:
        payload["seeds"] = seeds
    if watermark:
        payload["watermark"] = watermark
    if callback_url:
        payload["callBackUrl"] = callback_url

    resp = requests.post(
        f"{BASE_URL}/veo/generate",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=payload,
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", {}).get("taskId", "")


def get_veo3_1080p_video(task_id: str, api_key: str) -> str:
    """GET /api/v1/veo/get-1080p-video - Upgrade to 1080p (16:9 only)"""
    resp = requests.get(
        f"{BASE_URL}/veo/get-1080p-video",
        params={"taskId": task_id},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", {}).get("taskId", "")


def get_veo3_4k_video(task_id: str, api_key: str) -> str:
    """GET /api/v1/veo/get-4k-video - Upgrade to 4K (16:9 only)"""
    resp = requests.get(
        f"{BASE_URL}/veo/get-4k-video",
        params={"taskId": task_id},
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30
    )
    data = resp.json()
    if data.get("code") != 200:
        raise Exception(f"Failed: {data.get('msg')}")
    return data.get("data", {}).get("taskId", "")


def download_video(
    url: str,
    output_path: str,
    api_key: Optional[str] = None,
    max_retries: int = 3,
    chunk_size: int = 8192
) -> bool:
    """Download video from URL with retry and progress bar

    Args:
        url: Direct URL or Kie.ai storage URL
        output_path: Local file path to save
        api_key: Optional Kie.ai API key (needed for storage URLs)
        max_retries: Number of retry attempts
        chunk_size: Download chunk size in bytes

    Returns:
        True if successful, False otherwise
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # If it's a Kie.ai storage URL, get temp download link
    download_url = url
    if api_key and "storage.kie.ai" in url:
        try:
            download_url = get_download_url(url, api_key)
        except Exception as e:
            print(f"  WARNING: Could not get download URL: {e}")

    for attempt in range(1, max_retries + 1):
        try:
            print(f"  Downloading to {output_path.name}...")
            with requests.get(download_url, stream=True, timeout=60) as r:
                r.raise_for_status()
                total_size = int(r.headers.get("content-length", 0))

                downloaded = 0
                with open(output_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                pct = int(50 * downloaded / total_size)
                                print(f"\r    [{'=' * pct}{' ' * (50 - pct)}] {downloaded / 1024 / 1024:.1f}MB", end="")

                print()  # New line after progress bar

            file_size = output_path.stat().st_size
            if file_size < 1000:
                print(f"  WARNING: Downloaded file too small ({file_size} bytes)")
                if attempt < max_retries:
                    time.sleep(2 ** attempt)
                    continue
                return False

            print(f"  Downloaded: {output_path} ({file_size / 1024 / 1024:.1f}MB)")
            return True

        except requests.exceptions.RequestException as e:
            print(f"  ERROR (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"  Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return False

    return False


def process_batch_results(
    results_file: str,
    api_key: str,
    outdir: str = ".",
    download: bool = True,
    interval: int = 10,
    max_wait: int = 600
) -> list:
    """Process batch_results.json: wait for tasks and download videos

    Args:
        results_file: Path to batch_results.json
        api_key: Kie.ai API key
        outdir: Output directory for videos
        download: If True, download completed videos
        interval: Polling interval in seconds
        max_wait: Max wait time per task

    Returns:
        Updated results list with local paths
    """
    with open(results_file, "r", encoding="utf-8") as f:
        results = json.load(f)

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for i, result in enumerate(results):
        clip_id = result.get("clip_id", f"CLIP_{i:03d}")
        task_id = result.get("task_id")
        status = result.get("status")

        if status == "failed":
            print(f"[{clip_id}] Already failed, skipping")
            continue

        if status == "succeeded" and "local_path" in result:
            print(f"[{clip_id}] Already downloaded: {result['local_path']}")
            continue

        print(f"\n[{clip_id}] Task ID: {task_id}")

        # Wait for completion if pending
        if status == "pending":
            try:
                print(f"  Waiting for completion...")
                task_result = wait_for_task(task_id, api_key, interval, max_wait)
                result["status"] = task_result.get("status")
                result["result_url"] = get_video_url_from_result(task_result)
                print(f"  Status: {result['status']}")
            except Exception as e:
                result["status"] = "failed"
                result["error"] = str(e)
                print(f"  ERROR: {e}")
                continue

        # Download if succeeded
        if download and result.get("status") == "succeeded":
            result_url = result.get("result_url")
            if not result_url:
                print(f"  WARNING: No result URL")
                continue

            video_filename = f"{clip_id}.mp4"
            video_path = outdir / video_filename

            if download_video(result_url, str(video_path), api_key):
                result["local_path"] = str(video_path)
            else:
                result["download_error"] = "Failed to download"

    # Save updated results
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"\nUpdated results saved to: {results_file}")
    return results


# ============== CLI Interface ==============
def main():
    parser = argparse.ArgumentParser(
        description="Veo 3.1 API Client - Video Generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check credits
  python veo_ai.py credits

  # Generate video from text (Veo 3.1 Fast)
  python veo_ai.py video "a dog playing in a park" --fast

  # Generate video from single image
  python veo_ai.py video "make the person wave" --image https://example.com/img.jpg

  # Generate video with first and last frames (transition)
  python veo_ai.py video "transition between scenes" \\
      --first https://example.com/frame1.jpg \\
      --last https://example.com/frame2.jpg

  # Generate video with ingredients/materials (1-3 reference images)
  python veo_ai.py video "a character in this style" \\
      --ingredients https://ex.com/char.jpg https://ex.com/style.jpg https://ex.com/bg.jpg

  # Check task status
  python veo_ai.py status abc123

  # Get download link
  python veo_ai.py download "https://storage.kie.ai/..."
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Credits
    subparsers.add_parser("credits", help="Check account credit balance")

    # Video generation
    vid_parser = subparsers.add_parser("video", help="Generate video with Veo 3.1")
    vid_parser.add_argument("prompt", help="Video description")
    vid_parser.add_argument("--model", choices=["veo3", "veo3_fast"], default="veo3_fast",
                          help="veo3=quality, veo3_fast=fast (default)")
    vid_parser.add_argument("--ratio", choices=["16:9", "9:16", "Auto"], default="16:9")
    vid_parser.add_argument("--fast", action="store_true", help="Alias for --model veo3_fast")
    vid_parser.add_argument("--quality", action="store_true", help="Alias for --model veo3")
    vid_parser.add_argument("--no-translate", action="store_true", help="Disable auto-translation")
    vid_parser.add_argument("--seeds", type=int, help="Random seed (10000-99999)")
    vid_parser.add_argument("--watermark", help="Watermark text")
    vid_parser.add_argument("--wait", action="store_true", help="Wait for completion")
    vid_parser.add_argument("--1080p", action="store_true", help="Get 1080p version after completion")
    vid_parser.add_argument("--4k", action="store_true", help="Get 4K version after completion")

    # Image input modes (mutually exclusive)
    img_group = vid_parser.add_mutually_exclusive_group()
    img_group.add_argument("--image", help="Single image URL (image-to-video)")
    img_group.add_argument("--first", help="First frame URL (for --last transition)")
    img_group.add_argument("--ingredients", nargs="+", help="1-3 ingredient/material image URLs")

    vid_parser.add_argument("--last", help="Last frame URL (for --first transition)")

    # Status check
    status_parser = subparsers.add_parser("status", help="Check task status")
    status_parser.add_argument("task_id", help="Task ID to check")

    # Download
    dl_parser = subparsers.add_parser("download", help="Get download link")
    dl_parser.add_argument("url", help="Kie.ai storage URL")

    # Batch processing from JSON
    batch_parser = subparsers.add_parser("batch", help="Process JSON file with multiple clips")
    batch_parser.add_argument("json_file", help="Path to JSON file with clips")
    batch_parser.add_argument("--outdir", default=".", help="Output directory for results")
    batch_parser.add_argument("--model", choices=["veo3", "veo3_fast"], default="veo3_fast")
    batch_parser.add_argument("--ratio", choices=["16:9", "9:16", "Auto"], default="16:9")
    batch_parser.add_argument("--wait", action="store_true", help="Wait for each clip to complete")
    batch_parser.add_argument("--download", action="store_true", help="Download completed videos")
    batch_parser.add_argument("--limit", type=int, help="Limit number of clips to process")

    # Download batch results
    dl_batch_parser = subparsers.add_parser("download-batch", help="Download videos from batch_results.json")
    dl_batch_parser.add_argument("results_file", help="Path to batch_results.json")
    dl_batch_parser.add_argument("--outdir", default=".", help="Output directory for videos (overrides paths in file)")

    args = parser.parse_args()
    api_key = get_api_key()

    try:
        match args.command:
            case "credits":
                credits = check_credits(api_key)
                print(f"Credits: {credits}")

            case "video":
                # Determine model
                model = "veo3"
                if args.fast or (args.model == "veo3_fast" and not args.quality):
                    model = "veo3_fast"

                # Determine generation type and collect images
                gen_type = "TEXT_2_VIDEO"
                images = None

                if args.ingredients:
                    gen_type = "REFERENCE_2_VIDEO"
                    images = args.ingredients
                    if len(images) > 3:
                        print("WARNING: REFERENCE_2_VIDEO supports max 3 images, using first 3")
                        images = images[:3]
                    if model != "veo3_fast":
                        print("WARNING: REFERENCE_2_VIDEO requires veo3_fast, switching model")
                        model = "veo3_fast"

                elif args.first or args.last:
                    gen_type = "FIRST_AND_LAST_FRAMES_2_VIDEO"
                    if args.first and args.last:
                        images = [args.first, args.last]
                    elif args.first:
                        images = [args.first]
                    else:
                        print("ERROR: --last requires --first")
                        sys.exit(1)

                elif args.image:
                    images = [args.image]

                print(f"Generating video (model={model}, type={gen_type})")
                task_id = generate_veo3_video(
                    prompt=args.prompt,
                    api_key=api_key,
                    model=model,
                    aspect_ratio=args.ratio,
                    image_urls=images,
                    generation_type=gen_type,
                    seeds=args.seeds,
                    watermark=args.watermark,
                    enable_translation=not args.no_translate
                )
                print(f"Task ID: {task_id}")

                if args.wait or args.p or args.p:
                    result = wait_for_task(task_id, api_key)
                    print(f"Status: {result.get('status')}")
                    print(f"Result: {get_video_url_from_result(result)}")

                    if args.p and args.ratio == "16:9":
                        print("Upgrading to 1080p...")
                        hd_id = get_veo3_1080p_video(task_id, api_key)
                        print(f"1080p Task ID: {hd_id}")

                    if args.p and args.ratio == "16:9":
                        print("Upgrading to 4K...")
                        fourk_id = get_veo3_4k_video(task_id, api_key)
                        print(f"4K Task ID: {fourk_id}")

            case "status":
                status = get_task_status(args.task_id, api_key)
                print(json.dumps(status, indent=2))

            case "download":
                dl_url = get_download_url(args.url, api_key)
                print(f"Download URL (valid 20min): {dl_url}")

            case "batch":
                if not os.path.exists(args.json_file):
                    print(f"ERROR: File not found: {args.json_file}")
                    sys.exit(1)

                with open(args.json_file, "r", encoding="utf-8") as f:
                    clips = json.load(f)

                total = len(clips)
                if args.limit:
                    clips = clips[:args.limit]
                print(f"Processing {len(clips)}/{total} clips from {args.json_file}")
                os.makedirs(args.outdir, exist_ok=True)

                results = []

                for i, clip in enumerate(clips, 1):
                    clip_id = clip.get("clip_id", f"CLIP_{i:03d}")
                    prompt = clip.get("prompt", "")
                    negative = clip.get("negative", "")
                    ingredients = clip.get("ingredients", [])
                    veo_duration = clip.get("veo_duration", 4)

                    if not prompt:
                        print(f"[{clip_id}] SKIP: no prompt")
                        continue

                    print(f"\n[{i}/{len(clips)}] {clip_id}")
                    print(f"  Duration: {veo_duration}s")

                    gen_type = "TEXT_2_VIDEO"
                    images = None

                    if ingredients:
                        # Check if ingredients are valid URLs (start with http)
                        valid_urls = [url for url in ingredients if isinstance(url, str) and url.startswith(("http://", "https://"))]
                        if valid_urls:
                            gen_type = "REFERENCE_2_VIDEO"
                            images = valid_urls[:3]  # Max 3 images
                            print(f"  Ingredients: {len(images)} images (REFERENCE_2_VIDEO)")
                        else:
                            print(f"  Ingredients: {len(ingredients)} items (no valid URLs, using TEXT_2_VIDEO)")

                    try:
                        task_id = generate_veo3_video(
                            prompt=prompt,
                            api_key=api_key,
                            model=args.model,
                            aspect_ratio=args.ratio,
                            image_urls=images,
                            generation_type=gen_type,
                            negative_prompt=negative
                        )
                        print(f"  Task ID: {task_id}")

                        result_entry = {
                            "clip_id": clip_id,
                            "task_id": task_id,
                            "status": "pending"
                        }

                        if args.wait or args.download:
                            result = wait_for_task(task_id, api_key)
                            result_entry["status"] = result.get("status")
                            result_entry["result_url"] = get_video_url_from_result(result)
                            print(f"  Result: {get_video_url_from_result(result)}")

                            # Download if requested
                            if args.download and result.get("status") == "succeeded":
                                video_path = os.path.join(args.outdir, f"{clip_id}.mp4")
                                if download_video(get_video_url_from_result(result), video_path, api_key):
                                    result_entry["local_path"] = video_path

                        results.append(result_entry)

                    except Exception as e:
                        print(f"  ERROR: {e}")
                        results.append({
                            "clip_id": clip_id,
                            "status": "failed",
                            "error": str(e)
                        })

                results_file = os.path.join(args.outdir, "batch_results.json")
                with open(results_file, "w", encoding="utf-8") as f:
                    json.dump(results, f, indent=2)
                print(f"\nResults saved to: {results_file}")

            case "download-batch":
                if not os.path.exists(args.results_file):
                    print(f"ERROR: File not found: {args.results_file}")
                    sys.exit(1)

                process_batch_results(
                    results_file=args.results_file,
                    api_key=api_key,
                    outdir=args.outdir,
                    download=True
                )

    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
