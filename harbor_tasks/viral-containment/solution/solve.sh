#!/bin/bash
set -euo pipefail

python3 << 'EOF'
import json

# Path to the input data
INPUT_FILE = "/app/restoration_batches.json"
OUTPUT_FILE = "/app/restoration_report.txt"

def solve_batch(fragments, marker):
    wilds = 0
    countL = [0] * 26
    countR = [0] * 26
    
    X = marker

    for f in fragments:
        x_char, y_char = f[0], f[1]
        
        if x_char == X and y_char == X:
            wilds += 1
        elif x_char == X:
            countL[ord(y_char) - ord('a')] += 1
        elif y_char == X:
            countR[ord(x_char) - ord('a')] += 1

    pairs = 0
    free = 0
    
    for count in [countL, countR]:
        s = sum(count)       
        m = max(count)       

        p = min(s - m, s // 2)
        
        pairs += p
        free += s - 2 * p 

    used = min(wilds, free)
    wilds -= used
    
    extra = min(pairs, wilds // 2)
    
    return pairs + used + extra

with open(INPUT_FILE, 'r') as f:
    data = json.load(f)

results = []

for batch in data:
    bid = batch['id']
    frags = batch['fragments']
    marker = batch['marker']
    
    score = solve_batch(frags, marker)
    results.append((bid, score))

results.sort(key=lambda x: x[0])

with open(OUTPUT_FILE, 'w') as f:
    for bid, score in results:
        f.write(f"{bid} {score}\n")

EOF