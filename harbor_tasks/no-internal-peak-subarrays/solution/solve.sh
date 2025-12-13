#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.


cat > /app/solution.py << 'EOF'

def solve(arr: list[int]) -> int:
    """
    Count the number of good contiguous subarrays.

    A subarray a[l..r] is good if it has no strict local maximum inside:
    there is no index i with l < i < r such that
        arr[i] > arr[i-1] and arr[i] > arr[i+1].

    We maintain a sliding window [left, right] that is always good.
    Whenever we see that the triple (right-2, right-1, right) forms a
    local maximum at right-1, we forbid any window that starts at or
    before (right-2). So we keep track of the largest such forbidden
    start index and move `left` accordingly.
    """

    n = len(arr)
    if n == 0:
        return 0

    left = 0
    # last_forbid is the largest index s such that subarrays containing
    # indices [s, s+1, s+2] are invalid because there is a peak at s+1.
    last_forbid = -1

    answer = 0

    for right in range(n):
        if right >= 2:
            mid = right - 1
            # Check if arr[mid] is a strict local maximum with neighbours
            if arr[mid] > arr[mid - 1] and arr[mid] > arr[right]:
                # The triple starts at mid-1 == right-2
                last_forbid = max(last_forbid, right - 2)

        if last_forbid >= 0 and left <= last_forbid:
            left = last_forbid + 1

        # All subarrays ending at `right` with start in [left..right] are good
        answer += (right - left + 1)

    return answer

EOF


