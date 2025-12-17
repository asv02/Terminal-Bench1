#!/bin/bash
set -euo pipefail

python3 << 'EOF'
import json
from bisect import bisect_left, bisect_right

# Read the input file
try:
    with open("transmission_logs.json", "r") as f:
        data = json.load(f)
except FileNotFoundError:
    print("Input file not found.")
    exit(1)

def get_min_disturbances(nums, k):
    n = len(nums)
    sl = []
    inv_count = 0
    ans = float('inf')

    for i in range(n):
        # Remove the element that is sliding out of the window
        if i >= k:
            out_val = nums[i - k]
            smaller_count = bisect_left(sl, (out_val, 0))
            inv_count -= smaller_count
            
            pos = bisect_left(sl, (out_val, i - k))
            if pos < len(sl) and sl[pos] == (out_val, i - k):
                sl.pop(pos)

        in_val = nums[i]

        greater_count = len(sl) - bisect_right(sl, (in_val, 10**18))
        inv_count += greater_count
        
        pos = bisect_right(sl, (in_val, i))
        sl.insert(pos, (in_val, i))

        if i >= k - 1:
            ans = min(ans, inv_count)

    return ans if ans != float('inf') else 0

results = []

# Process each session
for session in data:
    s_id = session["id"]
    stream = session["stream"]
    window_size = session["window_size"]
    
    min_score = get_min_disturbances(stream, window_size)
    results.append((s_id, min_score))

# Sort by ID alphabetically
results.sort(key=lambda x: x[0])

# Write the report
with open("stability_report.txt", "w") as f:
    for s_id, val in results:
        f.write(f"{s_id} {val}\n")

EOF