#!/usr/bin/env python3
"""
Video Frame Extractor
A simple script to extract frames from videos at 1-second intervals.

Usage:
    python video_frame_extractor.py "https://www.youtube.com/watch?v=VIDEO_ID"
    python video_frame_extractor.py "file:///C:/Users/JOSE/Videos/video.mp4"
    python video_frame_extractor.py "C:/Videos/video.mp4"
"""

import cv2
import os
import re
import sys
import argparse
from pathlib import Path
from urllib.parse import urlparse

# Fix encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def limpar_url(url: str) -> str:
    """
    Limpa a URL removendo parâmetros que podem causar problemas.
    
    Args:
        url: URL original
        
    Returns:
        URL limpa
    """
    # Remove parâmetros de timestamp (t=) e outros problemáticos
    if 'youtube.com/watch' in url or 'youtu.be/' in url:
        # Para YouTube, mantém apenas o parâmetro v=
        from urllib.parse import urlparse, parse_qs, urlencode
        
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Mantém apenas o ID do vídeo
        video_id = params.get('v', [None])[0]
        if video_id:
            # Reconstrói a URL limpa
            clean_url = f"https://www.youtube.com/watch?v={video_id}"
            if clean_url != url:
                print(f"[INFO] URL limpa: {clean_url}")
                print(f"[INFO] (removidos parâmetros extras: &t=, &list=, etc)")
            return clean_url
    
    return url


def limpar_nome_arquivo(nome: str) -> str:
    """
    Remove caracteres inválidos de nomes de arquivo.
    
    Args:
        nome: String com o nome original
        
    Returns:
        String com nome limpo (apenas caracteres seguros)
    """
    # Remove caracteres especiais e mantém apenas alfanuméricos, hífens e underscores
    nome_limpo = re.sub(r'[<>:"/\\|?*]', '', nome)
    # Remove espaços extras
    nome_limpo = nome_limpo.strip().replace(' ', '_')
    # Limita tamanho do nome
    return nome_limpo[:50] if len(nome_limpo) > 50 else nome_limpo


def converter_file_url_to_path(url: str) -> str:
    """
    Converte URLs no formato file:/// para caminhos do sistema de arquivos.
    
    Suporta:
    - file:///c:/path/file.mp4 -> c:\\path\\file.mp4 (Windows)
    - file:///C:/path/file.mp4 -> C:\\path\\file.mp4 (Windows)
    - file:///home/user/file.mp4 -> /home/user/file.mp4 (Linux/Mac)
    
    Args:
        url: URL no formato file:///
        
    Returns:
        Caminho do arquivo no formato do sistema operacional
    """
    if not url.startswith('file:///'):
        return url
    
    # Remove o prefixo file:///
    path = url[8:]  # Remove 'file:///'
    
    # No Windows, o caminho começa com a letra da unidade (ex: C:/)
    # No Linux/Mac, o caminho começa com /
    
    # Verifica se é caminho do Windows (tem letra seguida de :)
    if len(path) >= 2 and path[1] == ':':
        # Windows: C:/path -> C:\\path
        # OpenCV aceita ambos os formatos no Windows, mas vamos normalizar
        return path.replace('/', '\\')
    else:
        # Linux/Mac: /home/user/path (precisa manter a barra inicial)
        # O URL já tem a barra, então retornamos como está
        return '/' + path if not path.startswith('/') else path


def extrair_id_video(url: str) -> str:
    """
    Extrai um identificador único do vídeo da URL.
    Funciona com URLs do YouTube, file:///, e caminhos locais.
    
    Args:
        url: URL ou caminho do vídeo
        
    Returns:
        String com identificador único
    """
    # Tenta extrair ID do YouTube
    if 'youtube.com' in url or 'youtu.be' in url:
        if 'v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
    
    # Para arquivos locais ou outras URLs, usa o nome do arquivo
    # Primeiro converte file:/// para caminho normal, se necessário
    caminho = converter_file_url_to_path(url)
    
    # Extrai o nome do arquivo do caminho
    if '/' in caminho or '\\' in caminho:
        nome_arquivo = os.path.basename(caminho)
    else:
        nome_arquivo = caminho
    
    return limpar_nome_arquivo(nome_arquivo) if nome_arquivo else "video_desconhecido"


def criar_pasta_saida(id_video: str) -> Path:
    """
    Cria uma pasta específica para os frames do vídeo.
    
    Args:
        id_video: Identificador único do vídeo
        
    Returns:
        Path object da pasta criada
    """
    # Cria pasta na estrutura: frames/<id_video>/
    pasta_base = Path("frames")
    pasta_base.mkdir(exist_ok=True)
    
    pasta_saida = pasta_base / id_video
    pasta_saida.mkdir(exist_ok=True)
    
    print(f"Pasta criada: {pasta_saida.absolute()}")
    return pasta_saida


def baixar_video(url: str, verbose: bool = False) -> str:
    """
    Baixa o vídeo usando yt-dlp (para URLs do YouTube, etc).
    
    Args:
        url: URL do vídeo
        verbose: Se True, mostra saida detalhada do yt-dlp
        
    Returns:
        Caminho do arquivo baixado
    """
    print("Baixando video...")
    
    # Limpa a URL removendo parâmetros problemáticos
    url_limpa = limpar_url(url)
    if url_limpa != url:
        print(f"[INFO] URL original: {url}")
        print(f"[INFO] URL limpa: {url_limpa}")
        url = url_limpa
    
    print(f"URL: {url}")
    print()
    
    # Usa yt-dlp se disponível
    import subprocess
    
    # Limpa arquivos temporários anteriores
    for arquivo in os.listdir('.'):
        if arquivo.startswith('video_temp.'):
            try:
                os.remove(arquivo)
                print(f"[DEBUG] Removido arquivo temporario anterior: {arquivo}")
            except Exception as e:
                print(f"[DEBUG] Aviso: nao foi possivel remover {arquivo}: {e}")
    
    # Tenta diferentes estratégias de formato
    formatos = [
        'best[ext=mp4]/best',  # Primeira opção: MP4 ou melhor
        'bestvideo+bestaudio/best',  # Segunda opção: vídeo + áudio separados
        'worst',  # Último recurso: pior qualidade
    ]
    
    for i, formato in enumerate(formatos, 1):
        print(f"[TENTATIVA {i}/{len(formatos)}] Format: {formato}")
        
        # Comando yt-dlp com opções melhoradas
        comando = [
            'yt-dlp',
            '-f', formato,
            '-o', 'video_temp.%(ext)s',
            '--no-playlist',  # Não baixa playlists
            '--no-warnings',  # Suprime avisos na saída normal
            '--no-check-certificates',  # Ignora erros de certificado
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',  # User agent de browser
        ]
        
        # Adiciona verbose se solicitado
        if verbose:
            comando.append('--verbose')
            print(f"[DEBUG] Comando: {' '.join(comando)}")
            print()
        
        try:
            print(f"[INFO] Executando yt-dlp...")
            
            resultado = subprocess.run(
                comando + [url],
                capture_output=True,
                text=True,
                check=False,
                timeout=300  # 5 minutos de timeout
            )
            
            # Mostra stdout se houver (informações úteis)
            if resultado.stdout and verbose:
                print("[STDOUT] yt-dlp output (últimas 20 linhas):")
                linhas = resultado.stdout.strip().split('\n')
                print('\n'.join(linhas[-20:]))
                print()
            
            # Verifica se há erros 403 (Forbidden) que indicam bloqueio do YouTube
            if '403' in resultado.stderr or 'Forbidden' in resultado.stderr:
                print("[AVISO] YouTube está bloqueando o download (HTTP 403)")
                print()
                print("Soluções possíveis:")
                print("  1. Atualize o yt-dlp: pip install --upgrade yt-dlp")
                print("  2. Use cookies de autenticacao (veja documentacao do yt-dlp)")
                print("  3. Baixe o vídeo manualmente e use o arquivo local")
                print("  4. Tente usar uma VPN")
                print()
                
                # Tenta a próxima estratégia
                if i < len(formatos):
                    print(f"[INFO] Tentando próxima estratégia de formato...")
                    continue
                else:
                    raise Exception("YouTube bloqueou o download (HTTP 403). Tente as soluções acima.")
            
            # Mostra stderr se houver erros importantes
            if resultado.stderr:
                stderr_lines = resultado.stderr.strip().split('\n')
                erros_importantes = [
                    line for line in stderr_lines
                    if any(keyword in line.lower() for keyword in [
                        'error', 'failed', 'corrupt', 'unavailable',
                        'copyright', 'private', 'not found'
                    ]) and 'warning' not in line.lower()
                ]
                
                if erros_importantes and not verbose:
                    print("[STDERR] Erros detectados:")
                    for erro in erros_importantes[:5]:  # Primeiros 5 erros
                        print(f"  {erro}")
                    print()
            
            # Verifica se o comando foi bem-sucedido
            if resultado.returncode != 0:
                print(f"[AVISO] Tentativa {i} falhou (código {resultado.returncode})")
                
                # Se não for a última tentativa, continua
                if i < len(formatos):
                    print(f"[INFO] Tentando próxima estratégia...")
                    print()
                    continue
                else:
                    # Última tentativa falhou, mostra detalhes
                    print(f"[ERRO] Todas as tentativas falharam")
                    print()
                    print("Detalhes do erro:")
                    if resultado.stderr:
                        # Mostra apenas erros relevantes
                        for linha in resultado.stderr.split('\n'):
                            if any(p in linha.lower() for p in ['error', 'failed', '403', 'forbidden']):
                                print(f"  {linha}")
                    print()
                    print("Possiveis soluções:")
                    print("  1. Verifique se a URL está correta")
                    print("  2. Atualize o yt-dlp: pip install --upgrade yt-dlp")
                    print("  3. Baixe o vídeo manualmente e use o arquivo local")
                    print("  4. Verifique se o vídeo está disponível na sua região")
                    raise Exception(f"yt-dlp falhou com código {resultado.returncode}")
            
            # Encontra o arquivo baixado
            print("[INFO] Buscando arquivo baixado...")
            arquivos_encontrados = []
            for arquivo in os.listdir('.'):
                if arquivo.startswith('video_temp.'):
                    # Verifica se é um arquivo de vídeo válido
                    if os.path.isfile(arquivo):
                        tamanho = os.path.getsize(arquivo)
                        print(f"[INFO] Arquivo encontrado: {arquivo} ({tamanho} bytes)")
                        if tamanho > 1000:  # Pelo menos 1KB
                            arquivos_encontrados.append(arquivo)
                        else:
                            print(f"[AVISO] Arquivo muito pequeno, pode estar corrompido")
            
            if not arquivos_encontrados:
                print(f"[AVISO] Tentativa {i} não produziu arquivo válido")
                if i < len(formatos):
                    print(f"[INFO] Tentando próxima estratégia...")
                    print()
                    continue
                else:
                    raise Exception("Nenhum arquivo de vídeo foi baixado")
            
            # Sucesso! Retorna o maior arquivo encontrado
            arquivo_final = max(arquivos_encontrados, key=lambda f: os.path.getsize(f))
            print(f"[SUCESSO] Video baixado: {arquivo_final}")
            return arquivo_final
            
        except FileNotFoundError:
            print("[ERRO] yt-dlp nao encontrado no sistema")
            print()
            print("Para instalar o yt-dlp, execute:")
            print("  pip install yt-dlp")
            print()
            print("Ou no Linux:")
            print("  sudo apt install yt-dlp")
            raise Exception("yt-dlp não encontrado. Instale com: pip install yt-dlp")
        
        except subprocess.TimeoutExpired:
            print(f"[AVISO] Tentativa {i} excedeu o tempo limite (5 minutos)")
            if i < len(formatos):
                print(f"[INFO] Tentando próxima estratégia...")
                continue
            else:
                raise Exception("Download excedeu o tempo limite. O vídeo pode ser muito grande.")
        
        except Exception as e:
            if i < len(formatos):
                print(f"[AVISO] Tentativa {i} falhou: {e}")
                print(f"[INFO] Tentando próxima estratégia...")
                print()
                continue
            else:
                print(f"[ERRO] Todas as tentativas falharam: {e}")
                raise


def extrair_frames(caminho_video: str, pasta_saida: Path) -> int:
    """
    Extrai frames do vídeo a cada segundo.
    
    Args:
        caminho_video: Caminho do arquivo de vídeo
        pasta_saida: Pasta onde os frames serão salvos
        
    Returns:
        Número de frames extraídos
    """
    print(f"Processando video: {caminho_video}")
    
    # Abre o vídeo
    captura = cv2.VideoCapture(caminho_video)
    
    if not captura.isOpened():
        raise Exception("Nao foi possivel abrir o arquivo de video")
    
    # Obtém propriedades do vídeo
    fps = captura.get(cv2.CAP_PROP_FPS)
    total_frames = int(captura.get(cv2.CAP_PROP_FRAME_COUNT))
    duracao_segundos = total_frames / fps if fps > 0 else 0
    
    print(f"Informacoes do video:")
    print(f"   - FPS: {fps:.2f}")
    print(f"   - Total de frames: {total_frames}")
    print(f"   - Duracao: {duracao_segundos:.2f} segundos")
    
    # Calcula um frame a cada segundo
    intervalo_frames = int(fps)  # Frames a pular (1 frame por segundo)
    
    frame_count = 0
    salvo_count = 0
    
    while True:
        # Define a posição do próximo frame (a cada segundo)
        captura.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        
        ret, frame = captura.read()
        
        if not ret:
            break  # Fim do vídeo
        
        # Salva o frame
        timestamp_segundos = frame_count / fps
        nome_arquivo = pasta_saida / f"frame_{timestamp_segundos:06.2f}s.jpg"
        
        cv2.imwrite(str(nome_arquivo), frame)
        salvo_count += 1
        
        # Mostra progresso a cada 10 frames
        if salvo_count % 10 == 0:
            print(f"   Extraido frame {salvo_count} ({timestamp_segundos:.1f}s)")
        
        # Avança para o próximo segundo
        frame_count += intervalo_frames
    
    captura.release()
    
    return salvo_count


def limpar_arquivo_temporario(caminho: str):
    """Remove arquivo temporario de video baixado."""
    if os.path.exists(caminho) and caminho.startswith('video_temp.'):
        os.remove(caminho)
        print(f"Arquivo temporario removido: {caminho}")


def main():
    parser = argparse.ArgumentParser(
        description='Extract frames from videos at 1-second intervals',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python video_frame_extractor.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
  python video_frame_extractor.py "file:///C:/Users/JOSE/Videos/video.mp4"
  python video_frame_extractor.py "C:/Videos/video.mp4"
  python video_frame_extractor.py "/home/user/videos/video.mp4"
        """
    )
    
    parser.add_argument('url', help='Video URL or file path (supports: http/https, file:///, local paths)')
    parser.add_argument('-o', '--output', help='Output folder name (default: auto-generated based on video ID)')
    parser.add_argument('-f', '--fps', type=int, default=1,
                        help='Frames per second to extract (default: 1)')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Enable verbose output (show yt-dlp details)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug mode (more detailed error messages)')
    
    args = parser.parse_args()
    
    # Ativa modo debug se solicitado
    if args.debug:
        print("[DEBUG] Modo debug ativado")
        print(f"[DEBUG] URL: {args.url}")
        print(f"[DEBUG] Output: {args.output}")
        print(f"[DEBUG] FPS: {args.fps}")
        print(f"[DEBUG] Verbose: {args.verbose}")
        print()
    
    print("=" * 60)
    print("  EXTRATOR DE FRAMES DE VIDEO")
    print("=" * 60)
    print()
    
    # 1. Detecta o tipo de URL
    is_file_url = args.url.startswith('file:///')
    is_remote_url = args.url.startswith(('http://', 'https://'))
    is_local_path = not is_file_url and not is_remote_url
    
    # 2. Extrai identificador do vídeo
    id_video = extrair_id_video(args.url)
    print(f"ID do video: {id_video}")
    
    # Mostra informações sobre o tipo de entrada
    if is_file_url:
        print(f"Tipo: Arquivo local (file:///)")
    elif is_remote_url:
        print(f"Tipo: URL remota")
    else:
        print(f"Tipo: Caminho local")
    print()
    
    # 3. Cria pasta para os frames
    pasta_output = criar_pasta_saida(id_video)
    print()
    
    # 4. Determina o caminho do arquivo de vídeo
    video_file = None
    
    try:
        if is_remote_url:
            # Baixa o vídeo de URL remota
            print("Video remoto detectado, baixando...")
            video_file = baixar_video(args.url, verbose=args.verbose or args.debug)
        elif is_file_url:
            # Converte file:/// para caminho do sistema
            video_file = converter_file_url_to_path(args.url)
            print(f"Caminho convertido: {video_file}")
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"Arquivo nao encontrado: {video_file}")
        else:
            # Usa caminho local diretamente
            video_file = args.url
            if not os.path.exists(video_file):
                raise FileNotFoundError(f"Arquivo nao encontrado: {video_file}")
        
        print()
        
        # 5. Extrai os frames
        frames_extraidos = extrair_frames(video_file, pasta_output)
        
        print()
        print("=" * 60)
        print(f"SUCESSO!")
        print(f"   Total de frames extraidos: {frames_extraidos}")
        print(f"   Pasta de saida: {pasta_output.absolute()}")
        print("=" * 60)
        
    except Exception as e:
        print()
        print("=" * 60)
        print(f"ERRO: {e}")
        print("=" * 60)
        return 1
    
    finally:
        # Limpa arquivos temporários (apenas para vídeos baixados)
        if is_remote_url and video_file:
            limpar_arquivo_temporario(video_file)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
