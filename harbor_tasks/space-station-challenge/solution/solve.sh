#!/bin/bash
set -euo pipefail

python3 << 'EOF'
import json
from bisect import bisect_left
from sortedcontainers import SortedList

with open("/app/gauntlet_scenarios.json") as f:
    data = json.load(f)

def compute_total_score(hp, damage, req):
    st = SortedList()
    res = 0
    cur_total_damage = 0

    for d, r in zip(damage[::-1], req[::-1]):
        st.add(hp + cur_total_damage - r)
        cur_total_damage += d
        res += len(st) - st.bisect_left(cur_total_damage)

    return res

results = []
for sc in data["scenarios"]:
    cid = sc["id"]
    hp = sc["hp"]
    damage = sc["damage"]
    requirement = sc["requirement"]
    total = compute_total_score(hp, damage, requirement)
    results.append((cid, total))

results.sort(key=lambda x: x[0])

with open("/app/gauntlet_report.txt", "w") as f:
    for cid, val in results:
        f.write(f"{cid} {val}\n")
EOF
