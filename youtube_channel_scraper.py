#!/usr/bin/env python3
"""
YouTube Channel Scraper
Lista todos vídeos do canal ordenados por views (decrescente), retorna top 3.

Usage:
    python youtube_channel_scraper.py "https://www.youtube.com/@channelname/videos"
    python youtube_channel_scraper.py "https://www.youtube.com/channel/UC..." --limit 5
    python youtube_channel_scraper.py "URL" --output videos.json
"""

import sys
import re
import json
import argparse
from typing import Optional, List, Dict

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import yt_dlp
except ImportError as e:
    print("Error: yt-dlp is not installed.")
    print(f"Import error: {e}")
    print("Install it with: pip install yt-dlp")
    print("Or: py -m pip install yt-dlp")
    sys.exit(1)


def extract_channel_name(url: str) -> Optional[str]:
    """
    Extrai informações do canal da URL.
    
    Suporta:
    - https://www.youtube.com/@channelname/videos
    - https://www.youtube.com/channel/UC...
    - https://www.youtube.com/c/channelname
    """
    # Padrão @username
    match = re.search(r'youtube\.com/@([^/]+)', url)
    if match:
        return f"@{match.group(1)}"
    
    # Padrão channel/UC...
    match = re.search(r'youtube\.com/channel/([^/]+)', url)
    if match:
        return match.group(1)
    
    # Padrão /c/channelname
    match = re.search(r'youtube\.com/c/([^/]+)', url)
    if match:
        return match.group(1)
    
    # Padrão /user/username
    match = re.search(r'youtube\.com/user/([^/]+)', url)
    if match:
        return match.group(1)
    
    return None


def get_channel_videos(channel_url: str, limit: int = 3) -> List[Dict]:
    """
    Obtém vídeos do canal ordenados por views (decrescente).
    
    Args:
        channel_url: URL do canal do YouTube
        limit: Número de vídeos a retornar (padrão: 3)
        
    Returns:
        Lista de dicionários com informações dos vídeos
    """
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': True,  # Mais rápido, não baixa metadados completos
        'playlistend': limit * 10,  # Pega mais vídeos para garantir ordenação correta
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Buscando vídeos do canal: {channel_url}")
            
            # Extrai informações do canal/vídeos
            info = ydl.extract_info(channel_url, download=False)
            
            videos = []
            
            # Verifica se é uma playlist ou canal
            if 'entries' in info:
                entries = info['entries']
            else:
                # Se não for playlist, pode ser um vídeo único
                print("Aviso: URL não parece ser um canal. Tentando extração...")
                entries = [info] if 'title' in info else []
            
            # Coleta metadados dos vídeos
            for entry in entries:
                if entry is None:
                    continue
                    
                video_id = entry.get('id', '')
                title = entry.get('title', 'Sem título')
                view_count = entry.get('view_count', 0)
                duration = entry.get('duration', 0)
                url = entry.get('url', f"https://www.youtube.com/watch?v={video_id}")
                thumbnail = entry.get('thumbnail', '')
                
                if not video_id:
                    continue
                
                # Formata duração (segundos -> MM:SS ou HH:MM:SS)
                if duration:
                    try:
                        duration_int = int(duration)
                        hours = duration_int // 3600
                        minutes = (duration_int % 3600) // 60
                        seconds = duration_int % 60
                        
                        if hours > 0:
                            duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
                        else:
                            duration_str = f"{minutes}:{seconds:02d}"
                    except (ValueError, TypeError):
                        duration_str = "N/A"
                else:
                    duration_str = "N/A"
                
                videos.append({
                    'video_id': video_id,
                    'title': title,
                    'url': url,
                    'views': view_count,
                    'duration': duration_str,
                    'thumbnail': thumbnail
                })
            
            # Ordena por views (decrescente)
            videos.sort(key=lambda x: x['views'], reverse=True)
            
            # Retorna top N
            return videos[:limit]
    
    except Exception as e:
        print(f"Erro ao extrair vídeos: {e}")
        return []


def format_views(view_count: int) -> str:
    """Formata número de views para legível."""
    if view_count >= 1_000_000:
        return f"{view_count / 1_000_000:.1f}M"
    elif view_count >= 1_000:
        return f"{view_count / 1_000:.1f}K"
    else:
        return str(view_count)


def main():
    parser = argparse.ArgumentParser(
        description='List top videos from a YouTube channel sorted by views',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python youtube_channel_scraper.py "https://www.youtube.com/@PsychologyIsSimplified/videos"
  python youtube_channel_scraper.py "https://www.youtube.com/@channelname/videos" --limit 5
  python youtube_channel_scraper.py "URL" --output videos.json
        """
    )
    
    parser.add_argument('url', help='YouTube channel URL')
    parser.add_argument('-l', '--limit', type=int, default=3,
                        help='Number of top videos to return (default: 3)')
    parser.add_argument('-o', '--output', 
                        help='Output JSON file path (optional)')
    parser.add_argument('--json-only', action='store_true',
                        help='Output only JSON (no text)')
    
    args = parser.parse_args()
    
    # Valida URL
    channel_name = extract_channel_name(args.url)
    if not channel_name:
        print("❌ Error: Invalid YouTube channel URL format")
        print(f"   URL provided: {args.url}")
        print("\nValid formats:")
        print("  • https://www.youtube.com/@channelname/videos")
        print("  • https://www.youtube.com/channel/UC...")
        print("  • https://www.youtube.com/c/channelname")
        sys.exit(1)
    
    # Busca vídeos
    videos = get_channel_videos(args.url, args.limit)
    
    if not videos:
        print("❌ Error: No videos found")
        sys.exit(1)
    
    # Output em JSON
    json_output = json.dumps(videos, indent=2, ensure_ascii=False)
    
    # Salva em arquivo se solicitado
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(json_output)
        print(f"✅ Saved to: {args.output}")
    
    # Imprime JSON
    if args.json_only:
        print(json_output, end='')
    else:
        # Output legível
        print("\n" + "=" * 80)
        print(f"  TOP {len(videos)} VIDEOS FROM CHANNEL")
        print("=" * 80)
        print()
        
        for i, video in enumerate(videos, 1):
            print(f"#{i}")
            print(f"  Title:   {video['title']}")
            print(f"  URL:     {video['url']}")
            print(f"  Views:   {format_views(video['views'])} ({video['views']:,})")
            print(f"  Duration: {video['duration']}")
            print()
        
        print("-" * 80)
        print("JSON OUTPUT:")
        print("-" * 80)
        print(json_output)
        print("-" * 80)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
