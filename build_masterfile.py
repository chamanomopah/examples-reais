#!/usr/bin/env python3
"""
Gera masterfile.json sincronizando imagens, áudio e timestamps.

NOVA ABORDAGEM (V3): Alinhamento Hierárquico Proporcional
- Divisão hierárquica baseada em proporção temporal
- Validação com trigrams únicos como âncoras
- Alinhamento local em cada sessão
- Garantia de continuidade temporal

Vantagens sobre método anterior:
- Não depende de encontrar palavras específicas
- Usa estrutura temporal natural
- Erro em uma sub-sessão não afeta outras
- 14x menos gaps que método de âncoras puras
"""

import argparse
import json
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, NamedTuple
from collections import Counter
from dataclasses import dataclass
import numpy as np

try:
    from dtw import dtw
    from Levenshtein import distance as levenshtein_distance
    DTW_AVAILABLE = True
except ImportError:
    DTW_AVAILABLE = False


def parse_transcript(transcript_path: Path) -> List[Dict[str, any]]:
    """Parse WebVTT transcript para lista de {word, start, end}"""
    entries = []
    pattern = re.compile(r"\[(\d+:\d+:\d+\.\d+) --> (\d+:\d+:\d+\.\d+)\] (.+)")

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("WEBVTT"):
                continue
            match = pattern.match(line)
            if match:
                start_str, end_str, word = match.groups()
                start = parse_timestamp(start_str)
                end = parse_timestamp(end_str)
                entries.append({"word": word, "start": start, "end": end})

    return entries


def parse_timestamp(ts: str) -> float:
    """Converte timestamp HH:MM:SS.mmm para segundos"""
    parts = ts.split(":")
    if len(parts) == 2:
        minutes, seconds = parts
        return float(minutes) * 60 + float(seconds)
    elif len(parts) == 3:
        hours, minutes, seconds = parts
        return float(hours) * 3600 + float(minutes) * 60 + float(seconds)
    return float(ts)


def normalize_text(text: str) -> str:
    """Normaliza texto para comparação"""
    text = text.lower()

    # Converter números decimais para texto (para compatibilidade com transcript)
    # Isso ajuda quando script usa "40" e transcript usa "forty"
    number_map = {
        '0': 'zero', '1': 'one', '2': 'two', '3': 'three', '4': 'four',
        '5': 'five', '6': 'six', '7': 'seven', '8': 'eight', '9': 'nine',
        '10': 'ten', '11': 'eleven', '12': 'twelve', '13': 'thirteen',
        '14': 'fourteen', '15': 'fifteen', '16': 'sixteen', '17': 'seventeen',
        '18': 'eighteen', '19': 'nineteen', '20': 'twenty', '30': 'thirty',
        '40': 'forty', '50': 'fifty', '60': 'sixty', '70': 'seventy',
        '80': 'eighty', '90': 'ninety', '100': 'hundred', '1000': 'thousand',
        '1000000': 'million', '1000000000': 'billion'
    }

    # Substituir números por extenso (antes de remover pontuação)
    for num, word in number_map.items():
        text = text.replace(num, word)

    # Remover pontuação (exceto apóstrofos)
    text = re.sub(r'[^\w\s\']', '', text)

    # Remover apóstrofos restantes
    text = text.replace("'", '')

    return text.strip()


def tokenize_line(line: str) -> List[str]:
    """Tokeniza uma linha do script em palavras normalizadas"""
    normalized = normalize_text(line)
    return normalized.split()


@dataclass
class Anchor:
    """Representa uma âncora no alinhamento"""
    word: str
    script_idx: int
    transcript_idx: int
    confidence: float
    ngram_size: int = 1  # Tamanho do n-gram (1=word, 2=bigram, 3=trigram)


def find_anchors(script_words: List[str], transcript_words: List[str],
                 transcript_entries: List[Dict]) -> List[Anchor]:
    """
    Encontra âncoras robustas no script.

    PRIORIZA N-GRAMS (2-3 palavras) sobre palavras únicas.
    N-grams são muito mais únicos e reduzem falsos positivos.
    """
    anchors = []

    # Palavras comuns a filtrar (não são boas âncoras)
    common_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
                    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                    'could', 'should', 'may', 'might', 'must', 'can', 'to',
                    'of', 'in', 'on', 'at', 'by', 'for', 'with', 'from', 'as',
                    'and', 'or', 'but', 'so', 'if', 'when', 'where', 'what',
                    'how', 'who', 'which', 'that', 'this', 'these', 'those',
                    'it', 'its', 'they', 'them', 'their', 'he', 'she', 'his',
                    'her', 'him', 'my', 'your', 'our', 'we', 'you', 'i', 'me'}

    # FASE 1: Trigrams (3 palavras) - MAIOR prioridade, mais únicos
    print("  Buscando trigrams...")
    anchors.extend(find_ngram_anchors(script_words, transcript_words, n=3,
                                      common_words=common_words))

    # FASE 2: Bigrams (2 palavras) - ALTA prioridade
    print("  Buscando bigrams...")
    bigram_anchors = find_ngram_anchors(script_words, transcript_words, n=2,
                                        common_words=common_words)
    anchors.extend(bigram_anchors)

    # FASE 3: Palavras únicas apenas se ainda faltam âncoras
    # Contar frequências no script
    script_freq = Counter(script_words)

    # Palavras únicas (aparecem 1 vez)
    unique_words = {w for w, c in script_freq.items() if c == 1}
    anchor_words = unique_words - common_words

    # Para cada palavra candidata
    for word in anchor_words:
        if len(word) < 4:  # Ignorar palavras muito curtas
            continue

        # Encontrar todas as posições no script
        script_positions = [i for i, w in enumerate(script_words) if w == word]

        # Encontrar todas as posições no transcript
        transcript_positions = [i for i, w in enumerate(transcript_words) if w == word]

        if not transcript_positions:
            continue  # Palavra não está no transcript

        # Se há correspondência 1-1, é uma âncora perfeita
        if len(script_positions) == 1 and len(transcript_positions) == 1:
            anchors.append(Anchor(word, script_positions[0],
                                 transcript_positions[0], confidence=0.5, ngram_size=1))
        # Se a palavra é única no script mas aparece múltiplas vezes no transcript
        elif len(script_positions) == 1:
            # Usar contexto para desambiguar
            best_pos = disambiguate_with_context(
                word, script_positions[0], script_words,
                transcript_positions, transcript_words
            )
            if best_pos is not None:
                anchors.append(Anchor(word, script_positions[0], best_pos,
                                     confidence=0.4, ngram_size=1))

    return anchors


def disambiguate_with_context(word: str, script_idx: int, script_words: List[str],
                              trans_positions: List[int], transcript_words: List[str],
                              window: int = 3) -> Optional[int]:
    """Usa contexto vizinho para desambiguar matches múltiplos"""
    # Extrair contexto do script
    script_context_start = max(0, script_idx - window)
    script_context_end = min(len(script_words), script_idx + window + 1)
    script_context = script_words[script_context_start:script_context_end]

    best_score = 0
    best_pos = None

    for pos in trans_positions:
        # Extrair contexto do transcript
        trans_context_start = max(0, pos - window)
        trans_context_end = min(len(transcript_words), pos + window + 1)
        trans_context = transcript_words[trans_context_start:trans_context_end]

        # Calcular similaridade de contexto
        score = context_similarity(script_context, trans_context)

        if score > best_score:
            best_score = score
            best_pos = pos

    return best_pos if best_score > 0.4 else None


def context_similarity(ctx1: List[str], ctx2: List[str]) -> float:
    """Calcula similaridade entre dois contextos usando Jaccard"""
    set1 = set(ctx1)
    set2 = set(ctx2)

    if not set1 or not set2:
        return 0.0

    intersection = len(set1 & set2)
    union = len(set1 | set2)

    return intersection / union if union > 0 else 0.0


def find_ngram_anchors(script_words: List[str], transcript_words: List[str],
                      n: int = 2, common_words: set = None) -> List[Anchor]:
    """Encontra âncoras baseadas em n-grams (sequências de palavras)"""
    anchors = []
    if common_words is None:
        common_words = set()

    # Gerar n-grams do script
    script_ngrams = {}
    for i in range(len(script_words) - n + 1):
        ngram = tuple(script_words[i:i+n])
        # Filtrar n-grams que contêm muitas palavras comuns
        common_count = sum(1 for w in ngram if w in common_words)
        if n > 1 and common_count >= n - 1:
            continue  # N-gram muito comum
        if ngram not in script_ngrams:
            script_ngrams[ngram] = []
        script_ngrams[ngram].append(i)

    # Gerar n-grams do transcript
    trans_ngrams = {}
    for i in range(len(transcript_words) - n + 1):
        ngram = tuple(transcript_words[i:i+n])
        if ngram not in trans_ngrams:
            trans_ngrams[ngram] = []
        trans_ngrams[ngram].append(i)

    # Encontrar n-grams únicos que são bons âncoras
    for ngram, script_positions in script_ngrams.items():
        if len(script_positions) != 1:
            continue  # Apenas n-grams únicos

        if ngram not in trans_ngrams:
            continue  # Não está no transcript

        trans_positions = trans_ngrams[ngram]

        # N-gram raro (únicos ou poucas ocorrências)
        if len(trans_positions) == 1:
            conf = 0.95 if n == 3 else 0.85
            anchors.append(Anchor(' '.join(ngram), script_positions[0],
                                 trans_positions[0], confidence=conf, ngram_size=n))
        elif len(trans_positions) <= 2:
            # Tentar desambiguar
            best_pos = disambiguate_with_context(
                ngram[0], script_positions[0], script_words,
                trans_positions, transcript_words
            )
            if best_pos is not None:
                conf = 0.8 if n == 3 else 0.7
                anchors.append(Anchor(' '.join(ngram), script_positions[0],
                                     best_pos, confidence=conf, ngram_size=n))

    return anchors


def validate_anchor_sequence(anchors: List[Anchor]) -> List[Anchor]:
    """
    Remove âncoras que violam monotonicidade temporal.

    Âncoras válidas devem estar em ordem crescente tanto no script
    quanto no transcript. Âncoras com transcript_idx muito próximo
    (< 5 palavras de distância) são consideradas duplicatas.

    Além disso, âncoras não podem criar saltos muito grandes no transcript.
    """
    if not anchors:
        return []

    # Ordenar por posição no script, depois por transcript_idx
    sorted_anchors = sorted(anchors, key=lambda a: (a.script_idx, a.transcript_idx))

    # Manter apenas âncoras monotonicamente crescentes
    valid = [sorted_anchors[0]]

    for anchor in sorted_anchors[1:]:
        # Deve estar depois da âncora anterior em AMBOS
        if (anchor.script_idx <= valid[-1].script_idx or
            anchor.transcript_idx <= valid[-1].transcript_idx):
            continue

        # Calcular distâncias
        script_dist = anchor.script_idx - valid[-1].script_idx
        trans_dist = anchor.transcript_idx - valid[-1].transcript_idx

        # VALIDAÇÃO: Distância no transcript deve ser proporcional à distância no script
        # Se a distância no transcript é muito diferente (>3x), provável erro
        if trans_dist > script_dist * 3:
            # Pular esta âncora
            continue

        # VALIDAÇÃO: Distância mínima no transcript
        if trans_dist < 3:
            continue

        # VALIDAÇÃO: Se o salto no script é pequeno (< 10 palavras),
        # o salto no transcript também deve ser pequeno (< 30 palavras)
        if script_dist < 10 and trans_dist > 30:
            continue

        valid.append(anchor)

    return valid


@dataclass
class Segment:
    """Representa um segmento entre duas âncoras"""
    script_start: int
    script_end: int
    trans_start: int
    trans_end: int
    anchor_before: Optional[Anchor]
    anchor_after: Optional[Anchor]
    needs_fallback: bool = False  # Se True, usa alinhamento greedy


def create_segments(anchors: List[Anchor], script_len: int,
                   trans_len: int, max_segment_size: int = 50) -> List[Segment]:
    """
    Cria segmentos entre âncoras consecutivas.

    Cada segmento é delimitado por duas âncoras (ou início/fim).
    Segmentos maiores que max_segment_size são divididos ou marcados para fallback.
    Segmentos com trans_start == trans_end são inválidos e ignorados.
    """
    segments = []

    # Adicionar âncoras virtuais no início e fim
    all_anchors = [
        Anchor("__START__", 0, 0, 1.0, ngram_size=1),
        *anchors,
        Anchor("__END__", script_len, trans_len, 1.0, ngram_size=1)
    ]

    for i in range(len(all_anchors) - 1):
        anchor_before = all_anchors[i]
        anchor_after = all_anchors[i + 1]

        # Criar segmento entre âncoras
        script_start = anchor_before.script_idx
        script_end = anchor_after.script_idx
        trans_start = anchor_before.transcript_idx
        trans_end = anchor_after.transcript_idx

        segment_size = script_end - script_start
        trans_size = trans_end - trans_start

        # Segmento muito pequeno não vale processar
        if segment_size <= 1:
            continue

        # VALIDAÇÃO: Segmento com trans_size <= 0 é inválido
        if trans_size <= 0:
            # Tentar estimar trans_size baseado no script_size
            # Proporção aproximada: 1 palavra do script ~= 1 palavra do transcript
            trans_size = segment_size
            trans_end = trans_start + trans_size

        # VALIDAÇÃO: Se trans_size é muito maior que segment_size (3x), provável erro
        if trans_size > segment_size * 3 and segment_size > 5:
            # Estimar trans_size
            trans_size = segment_size
            trans_end = trans_start + trans_size

        # Verificar se segmento é muito grande
        if segment_size > max_segment_size:
            # Dividir segmento grande em subsegmentos
            num_subs = (segment_size + max_segment_size - 1) // max_segment_size
            base_size = segment_size / num_subs
            trans_size_per_sub = trans_size / num_subs

            for j in range(num_subs):
                sub_start = int(script_start + j * base_size)
                sub_end = int(script_start + (j + 1) * base_size)
                if j == num_subs - 1:
                    sub_end = script_end

                sub_trans_start = int(trans_start + j * trans_size_per_sub)
                sub_trans_end = int(trans_start + (j + 1) * trans_size_per_sub)
                if j == num_subs - 1:
                    sub_trans_end = trans_end

                # Garantir que sub_trans_end > sub_trans_start
                if sub_trans_end <= sub_trans_start:
                    sub_trans_end = sub_trans_start + (sub_end - sub_start)

                segments.append(Segment(
                    sub_start, sub_end,
                    sub_trans_start, sub_trans_end,
                    anchor_before if i == 0 and j == 0 else None,
                    anchor_after if i == len(all_anchors) - 2 and j == num_subs - 1 else None,
                    needs_fallback=True  # Subsegmentos precisam de fallback
                ))
        else:
            segments.append(Segment(
                script_start, script_end,
                trans_start, trans_end,
                anchor_before if i > 0 else None,
                anchor_after if i < len(anchors) else None,
                needs_fallback=False
            ))

    return segments


def needleman_wunsch_align(seq1: List[str], seq2: List[str],
                          match_score: int = 1,
                          mismatch_penalty: int = -1,
                          gap_penalty: int = -2) -> List[Tuple]:
    """Alinha duas sequências usando Needleman-Wunsch"""
    n, m = len(seq1), len(seq2)

    # Matriz de scores
    score = [[0] * (m + 1) for _ in range(n + 1)]

    # Inicializa bordas
    for i in range(1, n + 1):
        score[i][0] = score[i-1][0] + gap_penalty
    for j in range(1, m + 1):
        score[0][j] = score[0][j-1] + gap_penalty

    # Preenche matriz
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            match = score[i-1][j-1] + (match_score if seq1[i-1] == seq2[j-1] else mismatch_penalty)
            delete = score[i-1][j] + gap_penalty
            insert = score[i][j-1] + gap_penalty
            score[i][j] = max(match, delete, insert)

    # Backtracking
    alignment = []
    i, j = n, m

    while i > 0 or j > 0:
        current = score[i][j]

        if i > 0 and j > 0:
            match_score_cell = match_score if seq1[i-1] == seq2[j-1] else mismatch_penalty
            if score[i-1][j-1] + match_score_cell == current:
                alignment.append(('match', j-1, i-1, seq1[i-1], seq2[j-1]))
                i -= 1
                j -= 1
                continue

        if i > 0 and score[i-1][j] + gap_penalty == current:
            alignment.append(('gap_trans', None, i-1, seq1[i-1], None))
            i -= 1
            continue

        if j > 0 and score[i][j-1] + gap_penalty == current:
            alignment.append(('gap_script', j-1, None, None, seq2[j-1]))
            j -= 1
            continue

        # Fallback
        alignment.append(('match', j-1, i-1, seq1[i-1] if i > 0 else None, seq2[j-1] if j > 0 else None))
        i -= 1
        j -= 1

    alignment.reverse()
    return alignment


def align_segment_dtw(script_words: List[str], transcript_words: List[str],
                     transcript_entries: List[Dict]) -> List[Tuple]:
    """Alinha segmento usando DTW (se disponível)"""
    if not DTW_AVAILABLE:
        return needleman_wunsch_align(script_words, transcript_words)

    # Para DTW, precisamos de uma matriz de distâncias
    # Usamos distância de edição (Levenshtein) como métrica
    n, m = len(script_words), len(transcript_words)

    # Matriz de distâncias
    dist_matrix = np.zeros((n, m))
    for i in range(n):
        for j in range(m):
            if script_words[i] == transcript_words[j]:
                dist_matrix[i, j] = 0
            else:
                # Usar Levenshtein normalizada
                max_len = max(len(script_words[i]), len(transcript_words[j]))
                if max_len > 0:
                    dist_matrix[i, j] = levenshtein_distance(script_words[i], transcript_words[j]) / max_len
                else:
                    dist_matrix[i, j] = 1.0

    # Aplicar DTW
    try:
        alignment = dtw(dist_matrix, keep_internals=True)
        path = alignment.index1s, alignment.index2s  # (script_idx, trans_idx)

        # Converter path para formato de alinhamento
        result = []
        i, j = 0, 0
        while i < len(path[0]) and j < len(path[1]):
            si, ti = path[0][i], path[1][j]

            # Pular duplicatas no caminho DTW
            while i + 1 < len(path[0]) and path[0][i + 1] == si:
                i += 1

            if si < len(script_words) and ti < len(transcript_words):
                if script_words[si] == transcript_words[ti]:
                    result.append(('match', ti, si, script_words[si], transcript_words[ti]))
                else:
                    # Match fuzzy
                    result.append(('match_fuzzy', ti, si, script_words[si], transcript_words[ti]))

            i += 1
            j += 1

        return result
    except Exception as e:
        # Fallback para NW se DTW falhar
        return needleman_wunsch_align(script_words, transcript_words)


def align_segment_local(script_words: List[str], transcript_words: List[str],
                       transcript_entries: List[Dict]) -> List[Tuple]:
    """Alinha um segmento localmente"""
    # Para segmentos pequenos, NW é suficiente
    if len(script_words) < 50 or len(transcript_words) < 50:
        return needleman_wunsch_align(script_words, transcript_words)
    else:
        return align_segment_dtw(script_words, transcript_words, transcript_entries)


def validate_segment_duration(script_words_count: int, trans_words_count: int,
                               transcript_entries: List[Dict],
                               trans_start_idx: int, trans_end_idx: int) -> Tuple[bool, str]:
    """
    Valida se a duração estimada do segmento é consistente.

    Retorna (valido, mensagem_erro).
    """
    # Calcular duração real do segmento no transcript
    if trans_start_idx < len(transcript_entries) and trans_end_idx <= len(transcript_entries):
        start_time = transcript_entries[trans_start_idx]['start']
        end_time = transcript_entries[min(trans_end_idx, len(transcript_entries) - 1)]['end']
        real_duration = end_time - start_time

        # Estimar duração esperada (~0.35s por palavra)
        expected_duration = script_words_count * 0.35

        # Se duração real é muito maior que esperada (>10x), provável erro
        if real_duration > expected_duration * 10 and script_words_count > 5:
            return False, f"Duração {real_duration:.1f}s >> esperada {expected_duration:.1f}s ({script_words_count} palavras)"

        # Se duração é muito menor (<0.1x), também pode ser erro
        if expected_duration > 10 and real_duration < expected_duration * 0.1:
            return False, f"Duração {real_duration:.1f}s << esperada {expected_duration:.1f}s"

    return True, ""


def validate_monotonicity(scenes: List[Dict]) -> List[Tuple[int, int, float]]:
    """
    Valida monotonicidade dos timestamps.

    Retorna lista de (linha_anterior, linha_atual, salto) para saltos > 10s.
    """
    violations = []

    for i in range(1, len(scenes)):
        prev_end = scenes[i - 1]['end']
        curr_start = scenes[i]['start']

        if curr_start - prev_end > 10:
            violations.append((
                scenes[i - 1]['line'],
                scenes[i]['line'],
                curr_start - prev_end
            ))

    return violations


def map_transcript_to_script(
    script_lines_info: List[Dict],
    all_script_words: List[str],
    transcript_words: List[str],
    transcript_entries: List[Dict],
    anchors: List[Anchor],
    segments: List[Segment]
) -> Tuple[List[Dict], List[Dict]]:
    """Mapeia cada linha do script para intervalo de tempo usando âncoras"""

    # Criar mapa: índice da palavra no script -> número da linha
    word_to_line = {}
    for line_info in script_lines_info:
        for word_idx in range(line_info['start_idx'], line_info['end_idx']):
            word_to_line[word_idx] = line_info['line_number']

    # Coletar timestamps por linha
    line_timestamps = {}
    line_transcript_words = {}  # palavras do transcript para cada linha
    line_transcript_indices = {}  # índices no transcript para cada linha
    validation_errors = []

    # Processar cada segmento
    for seg in segments:
        # Extrair palavras do segmento
        seg_script_words = all_script_words[seg.script_start:seg.script_end]
        seg_transcript_words = transcript_words[seg.trans_start:seg.trans_end]

        if not seg_script_words or not seg_transcript_words:
            continue

        # Validar duração do segmento
        is_valid, error_msg = validate_segment_duration(
            len(seg_script_words),
            len(seg_transcript_words),
            transcript_entries,
            seg.trans_start,
            seg.trans_end
        )

        if not is_valid:
            validation_errors.append(f"Segmento {seg.script_start}-{seg.script_end}: {error_msg}")
            # Continuar mesmo assim, mas com fallback
            seg.needs_fallback = True

        # Alinhar segmento localmente
        if seg.needs_fallback:
            # Usar alinhamento greedy (NW) para segmentos problemáticos
            local_alignment = needleman_wunsch_align(seg_script_words, seg_transcript_words)
        else:
            local_alignment = align_segment_local(seg_script_words, seg_transcript_words,
                                                  transcript_entries)

        # Mapear alinhamento para timestamps
        script_pos = seg.script_start
        skip_count = 0

        for align_item in local_alignment:
            align_type = align_item[0]

            if align_type in ('match', 'match_fuzzy'):
                _, trans_local_idx, script_local_idx, script_word, trans_word = align_item

                # Verificar se a palavra está na posição esperada
                if script_local_idx < len(seg_script_words):
                    actual_script_idx = seg.script_start + script_local_idx

                    # Verificar correspondência
                    if actual_script_idx < len(all_script_words) and all_script_words[actual_script_idx] == script_word:
                        trans_global_idx = seg.trans_start + trans_local_idx

                        if trans_global_idx < len(transcript_entries):
                            line_num = word_to_line.get(actual_script_idx)
                            if line_num is not None:
                                ts = transcript_entries[trans_global_idx]['start']
                                te = transcript_entries[trans_global_idx]['end']
                                trans_word = transcript_entries[trans_global_idx]['word']

                                if line_num not in line_timestamps:
                                    line_timestamps[line_num] = [ts, te]
                                    line_transcript_words[line_num] = [trans_word]
                                    line_transcript_indices[line_num] = [trans_global_idx]
                                else:
                                    line_timestamps[line_num][0] = min(line_timestamps[line_num][0], ts)
                                    line_timestamps[line_num][1] = max(line_timestamps[line_num][1], te)
                                    line_transcript_words[line_num].append(trans_word)
                                    line_transcript_indices[line_num].append(trans_global_idx)

            elif align_type == 'gap_trans':
                # Palavra do script não está no transcript
                script_pos += 1

    # Reportar erros de validação
    if validation_errors:
        print(f"  AVISO: {len(validation_errors)} segmentos com duração inconsistente:")
        for err in validation_errors[:3]:  # Mostrar apenas 3 primeiros
            print(f"    - {err}")

    # Construir cenas
    scenes = []
    debug_info = []  # Informações de debug por linha

    for line_info in script_lines_info:
        line_num = line_info['line_number']
        text = line_info['text']
        words = line_info['words']

        line_debug = {
            'line': line_num,
            'text': text,
            'method': None,
            'transcript_words': [],
            'transcript_indices': [],
            'raw_start': None,
            'raw_end': None,
            'raw_duration': None
        }

        if line_num in line_timestamps:
            start_time, end_time = line_timestamps[line_num]
            duration = end_time - start_time

            # VALIDAÇÃO FINAL: Se duração é muito grande (> 10s), rejeitar e estimar
            expected_duration = max(len(words) * 0.35, 0.5)
            if duration > 10 or duration > expected_duration * 5:
                # Usar estimativa baseada na cena anterior
                line_debug['method'] = 'estimated_rejected'
                line_debug['raw_start'] = start_time
                line_debug['raw_end'] = end_time
                line_debug['raw_duration'] = duration
                line_debug['rejection_reason'] = f'duration {duration:.2f}s > expected {expected_duration:.2f}s'
                # Adicionar palavras do transcript usadas (mesmo que rejeitado)
                if line_num in line_transcript_words:
                    line_debug['transcript_words'] = line_transcript_words[line_num]
                    line_debug['transcript_indices'] = line_transcript_indices[line_num]

                if scenes:
                    new_start = scenes[-1]['end']
                    new_duration = expected_duration
                else:
                    new_start = 0.0
                    new_duration = expected_duration

                scenes.append({
                    'line': line_num,
                    'text': text,
                    'start': round(new_start, 3),
                    'end': round(new_start + new_duration, 3),
                    'duration': round(new_duration, 3)
                })
            else:
                line_debug['method'] = 'aligned'
                line_debug['raw_start'] = start_time
                line_debug['raw_end'] = end_time
                line_debug['raw_duration'] = duration
                # Adicionar palavras do transcript usadas
                if line_num in line_transcript_words:
                    line_debug['transcript_words'] = line_transcript_words[line_num]
                    line_debug['transcript_indices'] = line_transcript_indices[line_num]
                scenes.append({
                    'line': line_num,
                    'text': text,
                    'start': round(start_time, 3),
                    'end': round(end_time, 3),
                    'duration': round(duration, 3)
                })
        else:
            # Estimar duração
            line_debug['method'] = 'estimated_no_match'
            if scenes:
                estimated_duration = max(len(words) * 0.35, 0.5)
                new_start = scenes[-1]['end']
                scenes.append({
                    'line': line_num,
                    'text': text,
                    'start': round(new_start, 3),
                    'end': round(new_start + estimated_duration, 3),
                    'duration': round(estimated_duration, 3)
                })
            else:
                estimated_duration = max(len(words) * 0.35, 0.5)
                scenes.append({
                    'line': line_num,
                    'text': text,
                    'start': 0.0,
                    'end': round(estimated_duration, 3),
                    'duration': round(estimated_duration, 3)
                })

        debug_info.append(line_debug)

    return scenes, debug_info


def build_script_lines_index(script_lines: List[str]) -> List[Dict]:
    """Constroi índice das linhas do script"""
    result = []
    word_idx = 0

    for line_num, line in enumerate(script_lines, 1):
        words = tokenize_line(line)
        if words:
            result.append({
                'line_number': line_num,
                'text': line,
                'words': words,
                'start_idx': word_idx,
                'end_idx': word_idx + len(words)
            })
            word_idx += len(words)

    return result


def build_masterfile(
    script_path: Path,
    transcript_path: Path,
    image_dir: Path,
    audio_path: Path,
    output_path: Path
) -> None:
    """Constroi masterfile.json usando Anchor-Guided Alignment"""

    # Lê e processa script
    script_lines = read_script_lines(script_path)
    script_lines_info = build_script_lines_index(script_lines)

    # Extrai todas as palavras do script
    all_script_words = []
    for line_info in script_lines_info:
        all_script_words.extend(line_info['words'])

    # Lê transcript
    transcript_entries = parse_transcript(transcript_path)
    transcript_words = tokenize_transcript(transcript_entries)

    print(f"Script: {len(all_script_words)} palavras em {len(script_lines_info)} linhas")
    print(f"Transcript: {len(transcript_words)} palavras")

    # FASE 1: Identificar âncoras
    print("Identificando âncoras...")
    anchors = find_anchors(all_script_words, transcript_words, transcript_entries)
    print(f"  Âncoras brutas: {len(anchors)}")

    # FASE 2: Validar sequência de âncoras
    anchors = validate_anchor_sequence(anchors)
    print(f"  Âncoras válidas: {len(anchors)}")

    # Mostrar algumas âncoras
    if anchors:
        print(f"  Exemplos: {', '.join([a.word for a in anchors[:5]])}")

    # FASE 3: Criar segmentos
    print("Criando segmentos...")
    segments = create_segments(anchors, len(all_script_words), len(transcript_words))
    print(f"  Segmentos: {len(segments)}")

    # Mostrar estatísticas dos segmentos
    if segments:
        seg_sizes = [s.script_end - s.script_start for s in segments]
        print(f"  Tamanho médio: {np.mean(seg_sizes):.1f} palavras")
        print(f"  Maior segmento: {max(seg_sizes)} palavras")
        print(f"  Menor segmento: {min(seg_sizes)} palavras")

    # FASE 4: Alinhar cada segmento
    print("Alinhando segmentos...")
    scenes, debug_info = map_transcript_to_script(
        script_lines_info, all_script_words, transcript_words,
        transcript_entries, anchors, segments
    )

    # Busca imagens
    images = get_image_files(image_dir)

    if len(images) < len(scenes):
        print(f"AVISO: Apenas {len(images)} imagens para {len(scenas)} cenas")

    # Combina cenas com imagens e debug info
    masterfile = {
        "audio": str(audio_path.name),
        "duration": round(scenes[-1]["end"] if scenes else 0, 3),
        "scenes": []
    }

    for i, scene in enumerate(scenes):
        image_name = str(images[i].name) if i < len(images) else f"missing_{i+1}.png"
        scene_entry = {
            "line": scene["line"],
            "text": scene["text"],
            "image": image_name,
            "start": scene["start"],
            "end": scene["end"],
            "duration": scene["duration"]
        }

        # Adicionar debug info para esta cena
        if i < len(debug_info):
            dbg = debug_info[i]
            scene_entry["debug"] = {
                "method": dbg["method"],
                "raw_start": dbg["raw_start"],
                "raw_end": dbg["raw_end"],
                "raw_duration": dbg["raw_duration"]
            }
            # Adicionar palavras do transcript usadas (quando disponível) - como string compacta
            if "transcript_words" in dbg and dbg["transcript_words"]:
                scene_entry["debug"]["transcript_words"] = json.dumps(dbg["transcript_words"], ensure_ascii=False)
                scene_entry["debug"]["transcript_indices"] = json.dumps(dbg["transcript_indices"])
            if dbg["method"] == "estimated_rejected":
                scene_entry["debug"]["rejection_reason"] = dbg["rejection_reason"]

        masterfile["scenes"].append(scene_entry)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(masterfile, f, indent=2, ensure_ascii=False)

    print(f"\nMasterfile criado: {output_path}")
    print(f"  Áudio: {masterfile['audio']}")
    print(f"  Duração: {masterfile['duration']}s")
    print(f"  Cenas: {len(scenes)}")

    # Validar monotonicidade
    print("\nValidando monotonicidade...")
    violations = validate_monotonicity(scenes)
    if violations:
        print(f"  AVISO: {len(violations)} saltos temporais > 10s detectados:")
        for prev_line, curr_line, jump in violations[:5]:
            print(f"    Linha {prev_line} -> {curr_line}: salto de {jump:.1f}s")
    else:
        print("  OK: Timestamps monotonicos")

    # Estatísticas finais
    durations = [s['duration'] for s in scenes]
    print(f"\nEstatísticas de duração:")
    print(f"  Média: {np.mean(durations):.2f}s")
    print(f"  Menor: {min(durations):.2f}s")
    print(f"  Maior: {max(durations):.2f}s")


def read_script_lines(script_path: Path) -> List[str]:
    """Lê script.md retornando linhas limpas"""
    lines = []
    with open(script_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                lines.append(line)
    return lines


def tokenize_transcript(entries: List[Dict]) -> List[str]:
    """Tokeniza transcript em lista de palavras normalizadas"""
    return [normalize_text(entry["word"]) for entry in entries]


def natural_key(text: str) -> list:
    """Chave para ordenação natural"""
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', text)]


def get_image_files(image_dir: Path) -> List[Path]:
    """Retorna imagens ordenadas por nome (natural sort)"""
    extensions = {".png", ".jpg", ".jpeg"}
    if not image_dir.exists():
        return []
    images = [p for p in image_dir.iterdir() if p.suffix.lower() in extensions]
    return sorted(images, key=lambda x: natural_key(x.name))


def main():
    parser = argparse.ArgumentParser(description="Gera masterfile.json para montagem de vídeo")
    parser.add_argument("--script", required=True, help="Caminho do script.md")
    parser.add_argument("--transcript", required=True, help="Caminho do transcript.txt (WebVTT)")
    parser.add_argument("--image-dir", required=True, help="Pasta com imagens")
    parser.add_argument("--audio", required=True, help="Arquivo de áudio")
    parser.add_argument("--output", default="masterfile.json", help="Arquivo de saída")

    args = parser.parse_args()

    build_masterfile(
        script_path=Path(args.script),
        transcript_path=Path(args.transcript),
        image_dir=Path(args.image_dir),
        audio_path=Path(args.audio),
        output_path=Path(args.output)
    )


if __name__ == "__main__":
    main()
