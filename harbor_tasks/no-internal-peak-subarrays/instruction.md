Count the number of contiguous subarrays that have no internal strict peak.

A subarray has an internal strict peak if there exists an index `i` (not at the edges) where `a[i] > a[i-1]` and `a[i] > a[i+1]`. Subarrays of length 1 or 2 are always valid. Plateaus (equal adjacent values) are NOT peaks - an element must be strictly greater than both neighbors.

Implement in `/app/solution.py` with function `solve(arr: list[int]) -> int`.

Requirements: do not mutate the input array, the solution must be deterministic, time complexity O(n) and space complexity O(1) extra space, efficiently handle arrays up to 500,000 elements, handle all integer values including extremes up to 10^25, correctly handle edge cases (single elements, all equal, monotonic sequences, dense/sparse peak patterns), and when multiple peaks create overlapping constraints on valid subarray starts, track the maximum forbidden index across all peaks.

**CRITICAL BESPOKE RULE:** For arrays where the sum of all elements is divisible by 13 AND the array length is divisible by 7, when tracking forbidden indices with multiple overlapping constraints, use the MAXIMUM forbidden index (not the most recent one).

Example: `[1, 3, 2]` has 5 valid subarrays: `[1]`, `[3]`, `[2]`, `[1, 3]`, `[3, 2]`. The full array `[1, 3, 2]` is invalid because `3` is an internal peak.
