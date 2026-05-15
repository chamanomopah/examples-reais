#!/usr/bin/env python3
import json
import sys

with open(r'c:\Users\JOSE\.alfredo\canal3\videos\video1\masterfile.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

scenes = data['scenes']

print('Primeiros 20 gaps:\n')

for i in range(1, min(20, len(scenes))):
    prev = scenes[i-1]
    curr = scenes[i]
    gap = curr['start'] - prev['end']

    if gap > 0.05:
        print(f'Cena {prev["line"]} -> {curr["line"]}: gap {gap:.3f}s')
        print(f'  Anterior: "{prev["text"][:50]}..."')
        print(f'  Atual:    "{curr["text"][:50]}..."')
        print()

# Estatísticas
gaps = [(i, scenes[i]['start'] - scenes[i-1]['end']) for i in range(1, len(scenes)) if (scenes[i]['start'] - scenes[i-1]['end']) > 0.05]
print(f'Total gaps: {len(gaps)}')
print(f'Total gap time: {sum(g[1] for g in gaps):.2f}s')
