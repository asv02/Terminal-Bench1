# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from __future__ import annotations

from pathlib import Path
import importlib.util
import random
from typing import Dict, List, Tuple


SOLUTION = Path("/app/solution.py")


def load_solution():
    assert SOLUTION.exists(), "Solution file /app/solution.py does not exist"
    spec = importlib.util.spec_from_file_location("sol", str(SOLUTION))
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert hasattr(module, "solve"), "solve(lines) not found in solution.py"
    return module.solve


# ---------------- Reference Implementation (Vector Clocks) ---------------- #

def _vc_leq(a: Dict[int, int], b: Dict[int, int]) -> bool:
    # a <= b iff for all k, a[k] <= b[k] (missing -> 0)
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


def reference_solve(lines: List[str]) -> str:
    # Filter comments, keep mapping to 1-based event indices
    events: List[Tuple[int, str]] = []
    for line in lines:
        if line.startswith("#"):
            continue
        line = line.strip()
        if not line:
            continue
        events.append((len(events) + 1, line))

    # Pre-scan to know last index per thread, and which threads appear
    per_thread_positions: Dict[int, List[int]] = {}
    parsed: List[Tuple[int, List[str]]] = []
    for idx, line in events:
        toks = line.split()
        parsed.append((idx, toks))
        if toks[0] in ("T", "L", "R", "W"):
            try:
                tid = int(toks[1])
            except Exception:
                tid = None
            if tid is not None:
                per_thread_positions.setdefault(tid, []).append(idx)

    last_pos: Dict[int, int] = {t: max(pos) for t, pos in per_thread_positions.items()}

    # Vector clock per thread
    C: Dict[int, Dict[int, int]] = {}
    def ensure_tid(t: int):
        if t not in C:
            C[t] = {t: 0}

    # Lock release VC (when fully released)
    Lrel: Dict[str, Dict[int, int]] = {}
    # lock reentrance count per thread
    held: Dict[Tuple[int, str], int] = {}

    # START relations: child initial VC joins parent's VC at START
    started: Dict[int, int] = {}  # child -> start_event_idx (for validity)
    parent_of: Dict[int, int] = {}  # child -> parent

    # For JOIN, we need child's "final VC"
    finished_vc: Dict[int, Dict[int, int]] = {}

    # Track last event idx processed per thread to detect "ended" on join
    # (Ended means child's last_pos <= current_valid_prefix_end and we've processed all its events.)
    processed_upto: Dict[int, int] = {}

    # Race tracking: store last read/write per var (vector clocks)
    # For canonical race selection we need earliest (j,i,var) according to rules.
    # We'll do precise HB race detection (like DJIT+ style simplified):
    # - Track last write clock per var (Wv)
    # - Track last read clock per var per thread (Rv[var][tid])
    Wv: Dict[str, Tuple[int, int, int, Dict[int, int]]] = {}
    # var -> tid -> (event_idx, tid, is_write?, vc)
    Rv: Dict[str, Dict[int, Tuple[int, int, Dict[int, int]]]] = {}

    best = None  # (j, i, var) with i<j

    def consider_race(i: int, j: int, var: str):
        nonlocal best
        if i >= j:
            return
        cand = (j, i, var)
        if best is None or cand < best:
            best = cand

    def tick(t: int):
        ensure_tid(t)
        C[t][t] = C[t].get(t, 0) + 1

    def hb_before(vc_a: Dict[int, int], vc_b: Dict[int, int]) -> bool:
        return _vc_leq(vc_a, vc_b)

    # Validity cutoff
    for idx, toks in parsed:
        if not toks:
            continue

        kind = toks[0]
        # Parse and validate formats
        try:
            if kind == "T":
                tid = int(toks[1])
                op = toks[2]
                x = int(toks[3])
                ensure_tid(tid)
                tick(tid)
                if op == "START":
                    # invalid if already started
                    if x in started:
                        break
                    started[x] = idx
                    parent_of[x] = tid
                    ensure_tid(x)
                    # Child initial clock joins parent's current clock
                    C[x] = _vc_join(C[x], C[tid])
                elif op == "JOIN":
                    # must have been started
                    if x not in started:
                        break
                    # must have ended: we must have processed all child's events already
                    if x in last_pos:
                        # child has events in trace
                        if processed_upto.get(x, 0) < last_pos[x]:
                            break
                    # Join parent's clock with child's finished clock if exists
                    if x in finished_vc:
                        C[tid] = _vc_join(C[tid], finished_vc[x])
                else:
                    break

            elif kind == "L":
                tid = int(toks[1])
                op = toks[2]
                lock = toks[3]
                ensure_tid(tid)
                tick(tid)
                if op == "ACQ":
                    # lock rule: join with last release
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
                    # check races with last write
                    if var in Wv:
                        (i_idx, i_tid, _, i_vc) = Wv[var]
                        if i_tid != tid and not hb_before(i_vc, vc_t) and not hb_before(vc_t, i_vc):
                            consider_race(i_idx, idx, var)
                    # check races with reads of other threads
                    if var in Rv:
                        for r_tid, (r_idx, _, r_vc) in Rv[var].items():
                            if r_tid != tid and not hb_before(r_vc, vc_t) and not hb_before(vc_t, r_vc):
                                consider_race(r_idx, idx, var)
                    # update write
                    Wv[var] = (idx, tid, 1, vc_t)

                else:  # R
                    # check races with last write
                    if var in Wv:
                        (w_idx, w_tid, _, w_vc) = Wv[var]
                        if w_tid != tid and not hb_before(w_vc, vc_t) and not hb_before(vc_t, w_vc):
                            consider_race(w_idx, idx, var)
                    Rv.setdefault(var, {})[tid] = (idx, tid, vc_t)

            else:
                break
        except Exception:
            break

        processed_upto[int(toks[1])] = idx if toks[0] in ("T", "L", "R", "W") else processed_upto.get(int(toks[1]), 0)

        # if a thread reaches its last event in valid prefix, store finished VC
        if toks[0] in ("T", "L", "R", "W"):
            tid2 = int(toks[1])
            if tid2 in last_pos and processed_upto.get(tid2, 0) == last_pos[tid2]:
                finished_vc[tid2] = dict(C[tid2])

    if best is None:
        return "NONE"
    j, i, var = best
    return f"{i} {j} {var}"


# ----------------------- Tests ----------------------- #

def test_solution_file_exists():
    """Check that /app/solution.py exists."""
    assert SOLUTION.exists(), "Solution file /app/solution.py does not exist"


def test_has_solve_function():
    """Check that solution.py defines solve(lines)."""
    txt = SOLUTION.read_text(encoding="utf-8", errors="ignore")
    assert "def solve(" in txt, "solve function not found in solution"


def test_no_race_single_thread():
    """Single-thread accesses cannot race; should return NONE."""
    solve = load_solution()
    lines = [
        "W 0 x",
        "R 0 x",
        "W 0 x",
    ]
    assert solve(lines) == "NONE"


def test_simple_two_thread_race():
    """Two threads write same var with no HB relation -> earliest canonical race."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "W 0 x",
        "W 1 x",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp


def test_lock_prevents_race():
    """Same lock protects critical sections -> no race."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "L 0 ACQ m",
        "W 0 x",
        "L 0 REL m",
        "L 1 ACQ m",
        "W 1 x",
        "L 1 REL m",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp == "NONE"


def test_reentrant_lock_handling():
    """Re-entrant locks must not release to others until count reaches 0."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "L 0 ACQ m",
        "L 0 ACQ m",
        "W 0 x",
        "L 0 REL m",   # still held
        "W 1 x",       # should still race (no acquire)
        "L 0 REL m",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp


def test_join_creates_hb():
    """JOIN must enforce child's last event HB before join; after join, parent write HB ordered."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "W 1 x",
        "T 0 JOIN 1",
        "W 0 x",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp == "NONE"


def test_invalid_rel_cutoff():
    """First invalid REL (not held) must stop processing; later lines ignored."""
    solve = load_solution()
    lines = [
        "L 0 REL m",     # invalid immediately
        "T 0 START 1",
        "W 0 x",
        "W 1 x",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp == "NONE"


def test_invalid_join_cutoff_child_not_finished():
    """JOIN of a child that still has future events is invalid and cuts off."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "W 1 x",
        "T 0 JOIN 1",   # invalid because thread 1 has future event below
        "W 1 x",
        "W 0 x",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp  # usually NONE due to cutoff


def test_canonical_tie_breaking():
    """Multiple races: choose smallest j, then i, then var name."""
    solve = load_solution()
    lines = [
        "T 0 START 1",
        "T 0 START 2",
        "W 0 b",
        "W 1 a",
        "W 2 b",
        "W 1 b",
        "W 2 a",
    ]
    exp = reference_solve(lines)
    assert solve(lines) == exp


def test_large_deterministic_random_family():
    """Large deterministic trace compared against reference (vector clocks)."""
    solve = load_solution()
    random.seed(0)

    # Build a deterministic stress trace with forks, locks, and accesses.
    # Keep within time/memory: ~50k events.
    lines = []
    # Start threads
    lines.append("T 0 START 1")
    lines.append("T 0 START 2")
    lines.append("T 0 START 3")

    locks = ["m0", "m1", "m2"]
    vars_ = ["x", "y", "z", "a", "b"]

    for k in range(50000):
        tid = random.randint(0, 3)
        r = random.random()
        if r < 0.10:
            lines.append(f"L {tid} ACQ {random.choice(locks)}")
        elif r < 0.20:
            lines.append(f"L {tid} REL {random.choice(locks)}")
        else:
            op = "W" if random.random() < 0.4 else "R"
            lines.append(f"{op} {tid} {random.choice(vars_)}")

    # Make joins valid by ensuring threads have no future events after joins.
    # We'll just not join here; the reference can handle it. Also avoids invalid cutoff.
    exp = reference_solve(lines)
    got = solve(lines)
    assert got == exp
