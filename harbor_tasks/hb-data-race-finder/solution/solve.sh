#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

cat > /app/solution.py <<'PY'
from __future__ import annotations

from typing import Dict, List, Tuple


def _vc_leq(a: Dict[int, int], b: Dict[int, int]) -> bool:
    for k, va in a.items():
        if va > b.get(k, 0):
            return False
    return True


def _vc_join(a: Dict[int, int], b: Dict[int, int]) -> Dict[int, int]:
    if not a:
        return dict(b)
    out = dict(a)
    for k, vb in b.items():
        va = out.get(k, 0)
        if vb > va:
            out[k] = vb
    return out


def solve(lines: List[str]) -> str:
    # Filter comments & blank
    events: List[Tuple[int, str]] = []
    for line in lines:
        if line.startswith("#"):
            continue
        line = line.strip()
        if not line:
            continue
        events.append((len(events) + 1, line))

    parsed: List[Tuple[int, List[str]]] = []
    per_thread_positions: Dict[int, List[int]] = {}
    for idx, line in events:
        toks = line.split()
        parsed.append((idx, toks))
        if toks and toks[0] in ("T", "L", "R", "W"):
            try:
                tid = int(toks[1])
            except Exception:
                continue
            per_thread_positions.setdefault(tid, []).append(idx)

    last_pos: Dict[int, int] = {t: max(pos) for t, pos in per_thread_positions.items()}

    # Vector clocks per thread
    C: Dict[int, Dict[int, int]] = {}

    def ensure_tid(t: int) -> None:
        if t not in C:
            C[t] = {t: 0}

    def tick(t: int) -> None:
        ensure_tid(t)
        C[t][t] = C[t].get(t, 0) + 1

    def hb_before(a: Dict[int, int], b: Dict[int, int]) -> bool:
        return _vc_leq(a, b)

    # Lock release VC and reentrance
    Lrel: Dict[str, Dict[int, int]] = {}
    held: Dict[Tuple[int, str], int] = {}

    # Thread lifecycle
    started: Dict[int, int] = {}
    processed_upto: Dict[int, int] = {}
    finished_vc: Dict[int, Dict[int, int]] = {}

    # Race structures
    Wv: Dict[str, Tuple[int, int, Dict[int, int]]] = {}  # var -> (idx, tid, vc)
    Rv: Dict[str, Dict[int, Tuple[int, Dict[int, int]]]] = {}  # var -> tid -> (idx, vc)

    best: Tuple[int, int, str] | None = None  # (j, i, var)

    def consider(i: int, j: int, var: str) -> None:
        nonlocal best
        if i >= j:
            return
        cand = (j, i, var)
        if best is None or cand < best:
            best = cand

    # Process until first invalid
    for idx, toks in parsed:
        if not toks:
            break

        kind = toks[0]
        try:
            if kind == "T":
                tid = int(toks[1])
                op = toks[2]
                child = int(toks[3])
                ensure_tid(tid)
                tick(tid)

                if op == "START":
                    if child in started:
                        break
                    started[child] = idx
                    ensure_tid(child)
                    # Child initial vc joins parent's vc at START
                    C[child] = _vc_join(C[child], C[tid])

                elif op == "JOIN":
                    if child not in started:
                        break
                    # Must have finished all events in valid prefix (if it appears)
                    if child in last_pos and processed_upto.get(child, 0) < last_pos[child]:
                        break
                    if child in finished_vc:
                        C[tid] = _vc_join(C[tid], finished_vc[child])
                else:
                    break

            elif kind == "L":
                tid = int(toks[1])
                op = toks[2]
                lock = toks[3]
                ensure_tid(tid)
                tick(tid)

                if op == "ACQ":
                    if lock in Lrel:
                        C[tid] = _vc_join(C[tid], Lrel[lock])
                    held[(tid, lock)] = held.get((tid, lock), 0) + 1

                elif op == "REL":
                    cnt = held.get((tid, lock), 0)
                    if cnt <= 0:
                        break
                    cnt -= 1
                    if cnt == 0:
                        held.pop((tid, lock), None)
                        Lrel[lock] = dict(C[tid])
                    else:
                        held[(tid, lock)] = cnt
                else:
                    break

            elif kind in ("R", "W"):
                tid = int(toks[1])
                var = toks[2]
                ensure_tid(tid)
                tick(tid)
                vc_t = dict(C[tid])

                if kind == "W":
                    if var in Wv:
                        wi, wtid, wvc = Wv[var]
                        if wtid != tid and not hb_before(wvc, vc_t) and not hb_before(vc_t, wvc):
                            consider(wi, idx, var)
                    if var in Rv:
                        for rtid, (ri, rvc) in Rv[var].items():
                            if rtid != tid and not hb_before(rvc, vc_t) and not hb_before(vc_t, rvc):
                                consider(ri, idx, var)
                    Wv[var] = (idx, tid, vc_t)

                else:  # R
                    if var in Wv:
                        wi, wtid, wvc = Wv[var]
                        if wtid != tid and not hb_before(wvc, vc_t) and not hb_before(vc_t, wvc):
                            consider(wi, idx, var)
                    Rv.setdefault(var, {})[tid] = (idx, vc_t)

            else:
                break

        except Exception:
            break

        # update processed_upto for this tid if present
        if toks[0] in ("T", "L", "R", "W"):
            tid2 = int(toks[1])
            processed_upto[tid2] = idx
            if tid2 in last_pos and processed_upto.get(tid2, 0) == last_pos[tid2]:
                finished_vc[tid2] = dict(C[tid2])

    if best is None:
        return "NONE"
    j, i, var = best
    return f"{i} {j} {var}"
PY
