#!/usr/bin/env python3
"""
YouTube Transcript Downloader
A simple script to download and format YouTube video transcripts.

Usage:
    python youtube_transcript_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python youtube_transcript_downloader.py "https://youtu.be/VIDEO_ID"
"""

import sys
import re
import argparse
from typing import Optional

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        TranscriptsDisabled,
        NoTranscriptFound,
        VideoUnavailable,
        CouldNotRetrieveTranscript
    )
except ImportError as e:
    print("Error: youtube-transcript-api is not installed.")
    print(f"Import error: {e}")
    print("Install it with: pip install youtube-transcript-api")
    print("Or: py -m pip install youtube-transcript-api")
    sys.exit(1)


def extract_video_id(url: str) -> Optional[str]:
    """Extract video ID from various YouTube URL formats."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&\n?#]+)',
        r'youtube\.com\/watch\?.*v=([^&\n?#]+)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def format_transcript_organic(transcript_data) -> str:
    """
    Format transcript as organic sentences - combine segments into complete sentences.

    Rules:
    - Join transcript segments until finding a period (.)
    - Each complete sentence (from start to a period) goes on one line
    - Double line break between sentences
    - Don't split in the middle of sentences

    Args:
        transcript_data: Raw transcript data from YouTube API

    Returns:
        Formatted transcript text with organic sentence structure
    """
    if not transcript_data:
        return ""
    
    # Combine all transcript segments into one continuous text
    full_text = ""
    for entry in transcript_data:
        text = entry.text.strip()
        
        # Skip empty entries
        if not text:
            continue
        
        # Clean up common issues
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'&#39;', "'", text)  # Fix HTML entities
        text = re.sub(r'&quot;', '"', text)
        text = re.sub(r'&amp;', '&', text)
        
        # Add space between segments if needed
        if full_text and not full_text.endswith(' ') and not text.startswith(' '):
            full_text += ' '
        full_text += text
    
    # Ensure proper spacing after punctuation
    full_text = re.sub(r'([.!?])([A-Z])', r'\1 \2', full_text)
    full_text = re.sub(r'([.!?])([a-z])', r'\1 \2', full_text)
    
    # Add proper capitalization after sentence endings
    sentences_with_ends = []
    parts = re.split(r'([.!?]+\s*)', full_text)
    
    for i in range(0, len(parts), 2):
        sentence_part = parts[i] if i < len(parts) else ''
        end_part = parts[i + 1] if i + 1 < len(parts) else ''
        
        if sentence_part:
            # Capitalize first letter if it's lowercase
            if sentence_part and sentence_part[0].isalpha():
                sentence_part = sentence_part[0].upper() + sentence_part[1:]
        
        sentences_with_ends.append(sentence_part + end_part)
    
    full_text = ''.join(sentences_with_ends)
    
    # Now split by periods to create organic sentences
    # We'll split on period, exclamation mark, or question mark followed by space
    sentence_ends = re.finditer(r'([.!?])\s+', full_text)
    
    sentences = []
    last_end = 0
    
    for match in sentence_ends:
        end_pos = match.end()
        sentence = full_text[last_end:end_pos].strip()
        
        if sentence:
            # Ensure it ends with punctuation
            if not sentence[-1] in '.!?':
                sentence += match.group(1)
            sentences.append(sentence)
        
        last_end = end_pos
    
    # Add remaining text as final sentence if exists
    if last_end < len(full_text):
        remaining = full_text[last_end:].strip()
        if remaining:
            sentences.append(remaining)
    
    # Join sentences with double line breaks
    formatted_text = '\n\n'.join(sentences)
    
    return formatted_text


def get_transcript(video_id: str, language_pref: str = 'auto') -> tuple:
    """
    Get transcript for a YouTube video.

    Returns:
        tuple: (transcript_data, language_code, actual_language)
    """
    # Common language codes to try
    if language_pref == 'auto':
        language_priority = [
            ['pt', 'pt-BR', 'pt-PT'],  # Portuguese variants
            ['en', 'en-US', 'en-GB'],  # English variants
            ['en'],  # Fallback to English
        ]
    else:
        language_priority = [language_pref.split(',')]

    last_error = None
    ytt_api = YouTubeTranscriptApi()

    for languages in language_priority:
        try:
            transcript_list = ytt_api.list(video_id)

            # Try to find a transcript in the preferred languages
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    transcript_data = transcript.fetch()
                    return transcript_data, languages[0], lang
                except NoTranscriptFound:
                    continue

            # If no exact match, try auto-generated transcripts
            for lang in languages:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    transcript_data = transcript.fetch()
                    return transcript_data, languages[0], f"{lang} (manual)"
                except NoTranscriptFound:
                    pass

                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    transcript_data = transcript.fetch()
                    return transcript_data, languages[0], f"{lang} (auto-generated)"
                except NoTranscriptFound:
                    pass

        except (VideoUnavailable, TranscriptsDisabled, CouldNotRetrieveTranscript) as e:
            last_error = e
            continue
        except Exception as e:
            last_error = e
            continue

    # If all else fails, try to get any available transcript
    try:
        transcript_list = ytt_api.list(video_id)
        for transcript in transcript_list:
            transcript_data = transcript.fetch()
            return transcript_data, 'en', f"{transcript.language_code} (available)"
    except Exception as e:
        last_error = e

    raise last_error or Exception("Could not retrieve transcript")


def main():
    parser = argparse.ArgumentParser(
        description='Download and format YouTube video transcripts',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_transcript_downloader.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python youtube_transcript_downloader.py "https://youtu.be/dQw4w9WgXcQ" --language pt
  python youtube_transcript_downloader.py "URL" --output my_transcript.txt
        """
    )
    
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-o', '--output', default='transcript.txt', 
                        help='Output file name (default: transcript.txt)')
    parser.add_argument('-l', '--language', default='auto',
                        help='Language preference (default: auto-detect, tries PT first then EN)')
    parser.add_argument('--no-display', action='store_true',
                        help='Don\'t display transcript in terminal (only save to file)')
    
    args = parser.parse_args()
    
    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print("❌ Error: Invalid YouTube URL format")
        print(f"   URL provided: {args.url}")
        print("\nValid formats:")
        print("  • https://www.youtube.com/watch?v=VIDEO_ID")
        print("  • https://youtu.be/VIDEO_ID")
        print("  • https://www.youtube.com/embed/VIDEO_ID")
        sys.exit(1)
    
    try:
        # Get transcript (silent - no output)
        transcript_data, lang_code, actual_lang = get_transcript(video_id, args.language)

        if not transcript_data:
            print("Error: No transcript data available", file=sys.stderr)
            sys.exit(1)

        # Format transcript with organic sentence structure
        formatted = format_transcript_organic(transcript_data)

        # Save to file (silent - no output)
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(formatted)

        # Display in terminal - ONLY the transcript, nothing else
        if not args.no_display:
            print(formatted, end='')

    except VideoUnavailable:
        print("Error: Video is unavailable or private", file=sys.stderr)
        sys.exit(1)
    except TranscriptsDisabled:
        print("Error: Transcripts are disabled for this video", file=sys.stderr)
        sys.exit(1)
    except NoTranscriptFound:
        print("Error: No transcript found for this video", file=sys.stderr)
        sys.exit(1)
    except CouldNotRetrieveTranscript as e:
        print(f"Error: Could not retrieve transcript: {str(e)}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
