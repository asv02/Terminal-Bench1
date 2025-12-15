#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

cat > /app/solution.py << 'PY'
from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple


def solve(lines: List[str]) -> str:
    # Track writes and reads encountered
    writes: List[Tuple[int, int, int]] = []  # (time, tid, val)
    values_written: Set[int] = {0}
    earliest_read_of_value_time: Dict[int, int] = {}

    invalid = False

    def latest_write_before(time: int) -> Optional[Tuple[int, int, int]]:
        candidate = None
        for wt, wid, wv in writes:
            if wt < time:
                if candidate is None or wt > candidate[0]:
                    candidate = (wt, wid, wv)
        return candidate

    def latest_write_of_value_before(time: int, value: int) -> Optional[Tuple[int, int, int]]:
        candidate = None
        for wt, wid, wv in writes:
            if wv == value and wt < time:
                if candidate is None or wt > candidate[0]:
                    candidate = (wt, wid, wv)
        return candidate

    def prior_read_exists(value: int, time: int) -> bool:
        return value in earliest_read_of_value_time and earliest_read_of_value_time[value] < time

    for line in lines:
        if not line.strip() or line.startswith("#"):
            continue

        parts = line.split()
        if len(parts) != 4:
            invalid = True
            break

        try:
            t = int(parts[0])
            tid = int(parts[1])
            op = parts[2]
            val = int(parts[3])
        except Exception:
            invalid = True
            break

        if val < 0:
            invalid = True
            break

        if op == "WRITE":
            writes.append((t, tid, val))
            values_written.add(val)

        elif op == "READ":
            if val not in values_written:
                invalid = True
                break

            # record earliest read of this value
            if val not in earliest_read_of_value_time:
                earliest_read_of_value_time[val] = t

            lw = latest_write_before(t)
            if lw is None:
                lw = (-1, -1, 0)  # initial value

            lw_time, lw_tid, lw_val = lw

            if val == lw_val:
                continue  # consistent

            # violation: choose witness per canonical rules
            lv = latest_write_of_value_before(t, val)
            if lv is None and val == 0:
                lv = (-1, -1, 0)

            # If a prior read of this value exists, prefer the write that produced this value; else use latest conflicting write
            if lv and prior_read_exists(val, t):
                witness = lv
            else:
                witness = lw

            w_time, w_tid, _ = witness
            return f"R={tid}@{t} <- W={w_tid}@{w_time}"

        else:
            invalid = True
            break

    if invalid:
        return "NONE"
    return "NONE"
PY

