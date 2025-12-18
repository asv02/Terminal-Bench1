#!/bin/bash
set -euo pipefail

python3 << 'EOF'
import json
from functools import lru_cache

try:
    with open("/app/reactor_status.json") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Input file not found.")
    exit(1)

def is_palin(x):
    s = bin(x)[2:]
    return s == s[::-1]

@lru_cache(maxsize=None)
def get_step_count(num):
    steps = 1 - (num % 2)
    
    while True:
        if (num - steps) >= 0 and is_palin(num - steps):
            return steps
        if is_palin(num + steps):
            return steps
        
        steps += 2

results = []

for sector in data["scenarios"]:
    s_id = sector["id"]
    nums = sector["frequencies"]
    
    total_cost = sum(get_step_count(n) for n in nums)
    results.append((s_id, total_cost))

results.sort(key=lambda x: x[0])

with open("/app/stabilization_costs.txt", "w") as f:
    for s_id, cost in results:
        f.write(f"{s_id} {cost}\n")

EOF