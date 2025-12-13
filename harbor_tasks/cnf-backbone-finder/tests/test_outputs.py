# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

import subprocess
import sys
from pathlib import Path
import random


SCRIPT = Path("/app/find_backbone.py")


def run_backbone(cnf_text: str, tmp_path: Path) -> str:
    """Write CNF to a file, run the CLI, and return backbone.txt contents (stripped)."""
    cnf_file = tmp_path / "formula.cnf"
    out_file = tmp_path / "backbone.txt"

    cnf_file.write_text(cnf_text, encoding="utf-8")

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--input",
            str(cnf_file),
            "--out",
            str(out_file),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    if not out_file.exists():
        return ""
    return out_file.read_text(encoding="utf-8").strip()


def get_raw_output(tmp_path: Path) -> str:
    """Get raw output file content without any processing."""
    out_file = tmp_path / "backbone.txt"
    if not out_file.exists():
        return ""
    return out_file.read_text(encoding="utf-8")


# ---------- Reference Solver (internal oracle) ----------

def parse_dimacs(cnf_text: str):
    n_vars = None
    clauses = []
    for line in cnf_text.splitlines():
        line = line.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            parts = line.split()
            assert parts[1] == "cnf"
            n_vars = int(parts[2])
        else:
            lits = list(map(int, line.split()))
            if not lits:
                continue
            if lits[-1] == 0:
                lits.pop()
            if len(lits) == 0:
                clauses.append([])  # empty clause
            else:
                clauses.append(lits)
    if n_vars is None:
        # derive n_vars from max abs literal
        max_var = 0
        for cl in clauses:
            for lit in cl:
                max_var = max(max_var, abs(lit))
        n_vars = max_var
    return n_vars, clauses


def dpll(clauses, n_vars, assignment):
    """
    clauses: list of lists of ints
    assignment: list of ints: 0 unassigned, 1 true, -1 false
    returns (sat, assignment_or_None)
    """

    # Unit propagation + pure backtracking DPLL
    while True:
        changed = False
        # Check for empty clause and unit clauses
        for cl in clauses:
            val = None
            unassigned = []
            for lit in cl:
                v = abs(lit)
                sign = 1 if lit > 0 else -1
                a = assignment[v]
                if a == 0:
                    unassigned.append(lit)
                elif a == sign:
                    val = True
                    break
            if val is True:
                continue
            if not unassigned:
                # All assigned but none true -> clause is false
                return False, None
            if len(unassigned) == 1:
                lit = unassigned[0]
                v = abs(lit)
                sign = 1 if lit > 0 else -1
                if assignment[v] == 0:
                    assignment[v] = sign
                    changed = True
        if not changed:
            break

    # Check if all assigned
    var = None
    for i in range(1, n_vars + 1):
        if assignment[i] == 0:
            var = i
            break
    if var is None:
        # model found
        return True, assignment

    # Branch on var = True then False
    for val in (1, -1):
        new_assign = assignment.copy()
        new_assign[var] = val
        sat, model = dpll(clauses, n_vars, new_assign)
        if sat:
            return True, model
    return False, None


def sat_solve(clauses, n_vars, forced_assignment=None):
    assignment = [0] * (n_vars + 1)
    if forced_assignment:
        for v, val in forced_assignment.items():
            assignment[v] = 1 if val else -1
    sat, model = dpll(clauses, n_vars, assignment)
    return sat, model


def reference_backbone(cnf_text: str):
    n_vars, clauses = parse_dimacs(cnf_text)

    sat, model = sat_solve(clauses, n_vars)
    if not sat:
        return "UNSAT"

    backbone = []
    for v in range(1, n_vars + 1):
        # If variable never appears, it can't be in backbone
        appears = any(v == abs(lit) for cl in clauses for lit in cl)
        if not appears:
            continue
        val = model[v] == 1
        # Force opposite value
        forced = {v: (not val)}
        sat2, _ = sat_solve(clauses, n_vars, forced_assignment=forced)
        if not sat2:
            lit = v if val else -v
            backbone.append(lit)

    backbone.sort(key=lambda x: abs(x))
    if not backbone:
        return ""
    return "\n".join(str(lit) for lit in backbone)


# ---------- Tests ----------

def test_unsat_basic(tmp_path: Path):
    """Unsatisfiable CNF must output UNSAT with strict formatting (newline required)."""
    # Moderate-sized UNSAT formula with implication cycle and unit contradiction
    cnf = """c UNSAT formula with implication cycle
p cnf 12 18
1 0
-1 2 0
-2 3 0
-3 4 0
-4 5 0
-5 6 0
-6 7 0
-7 8 0
-8 9 0
-9 10 0
-10 -1 0
1 2 3 4 5 0
-2 -3 -4 -5 -6 0
7 8 9 10 0
-7 -8 -9 -10 0
11 0
-11 0
-12 12 0
"""
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == "UNSAT"
    # Verify exact format: UNSAT followed by newline, no other content
    raw = get_raw_output(tmp_path)
    assert raw == "UNSAT\n"


def test_satisfiable_no_backbone(tmp_path: Path):
    """CNF with many models but no backbone -> empty file (strict zero-byte check)."""
    # Moderate-sized formula where every variable is free; no backbone literals
    cnf = """c No backbone - variables free
p cnf 20 19
1 2 0
-1 -2 0
3 4 0
-3 -4 0
5 6 0
-5 -6 0
7 8 0
-7 -8 0
9 10 0
-9 -10 0
11 12 0
-11 -12 0
13 14 0
-13 -14 0
15 16 0
-15 -16 0
17 18 0
-17 -18 0
19 20 0
-19 -20 0
"""
    out = run_backbone(cnf, tmp_path)
    assert out == ""
    # Strict format check: empty file with zero bytes - no newline, no whitespace, nothing
    raw = get_raw_output(tmp_path)
    assert raw == "", f"Expected empty file but got {len(raw)} bytes: {repr(raw)}"
    # Verify file is truly empty (byte-level check)
    out_file = tmp_path / "backbone.txt"
    assert out_file.stat().st_size == 0, "File must be exactly 0 bytes"


def test_simple_backbone_one_var(tmp_path: Path):
    """Single backbone var hidden in extremely complex formula requiring exhaustive enumeration."""
    # x1 must be true, but formula structure requires checking ALL models to prove it
    # Adversarial: many clauses make it appear x1 could be false, but exhaustive check proves otherwise
    # Tests that solver doesn't use shortcuts or incomplete heuristics
    cnf = """c Backbone x1 = true, hidden in extremely complex structure requiring full enumeration
p cnf 50 200
1 2 3 4 5 0
1 6 7 8 9 10 0
1 11 12 13 14 15 0
1 16 17 18 19 20 0
1 21 22 23 24 25 0
1 2 3 6 7 0
1 4 5 8 9 0
1 10 11 12 13 0
1 14 15 16 17 0
1 18 19 20 21 0
1 22 23 24 25 2 0
1 3 4 5 6 7 0
1 8 9 10 11 12 0
1 13 14 15 16 17 0
1 18 19 20 21 22 0
1 23 24 25 2 3 0
-1 2 3 4 5 6 0
-1 7 8 9 10 11 0
-1 12 13 14 15 16 0
-1 17 18 19 20 21 0
-1 22 23 24 25 2 0
-1 3 4 5 6 7 8 0
-1 9 10 11 12 13 14 0
-1 15 16 17 18 19 20 0
-1 21 22 23 24 25 2 0
-1 3 4 5 6 7 8 9 0
-1 10 11 12 13 14 15 16 0
-1 17 18 19 20 21 22 23 0
-1 24 25 2 3 4 5 0
-1 6 7 8 9 10 11 12 0
-1 13 14 15 16 17 18 19 0
-1 20 21 22 23 24 25 2 0
-1 3 4 5 6 7 8 9 10 0
-1 11 12 13 14 15 16 17 18 0
-1 19 20 21 22 23 24 25 2 0
-1 3 4 5 6 7 8 9 10 11 0
-1 12 13 14 15 16 17 18 19 20 0
-1 21 22 23 24 25 2 3 4 0
-1 5 6 7 8 9 10 11 12 13 0
-1 14 15 16 17 18 19 20 21 22 0
-1 23 24 25 2 3 4 5 6 0
-1 7 8 9 10 11 12 13 14 15 0
-1 16 17 18 19 20 21 22 23 24 0
-1 25 2 3 4 5 6 7 8 9 0
-1 10 11 12 13 14 15 16 17 18 19 0
-1 20 21 22 23 24 25 2 3 4 5 0
-1 6 7 8 9 10 11 12 13 14 15 16 0
-1 17 18 19 20 21 22 23 24 25 2 0
-1 3 4 5 6 7 8 9 10 11 12 13 0
-1 14 15 16 17 18 19 20 21 22 23 0
-1 24 25 2 3 4 5 6 7 8 9 0
-1 10 11 12 13 14 15 16 17 18 19 20 0
-1 21 22 23 24 25 2 3 4 5 6 7 0
-1 8 9 10 11 12 13 14 15 16 17 18 0
-1 19 20 21 22 23 24 25 2 3 4 5 0
-1 6 7 8 9 10 11 12 13 14 15 16 17 0
-1 18 19 20 21 22 23 24 25 2 3 4 0
-1 5 6 7 8 9 10 11 12 13 14 15 16 17 0
-1 18 19 20 21 22 23 24 25 2 3 4 5 0
-1 6 7 8 9 10 11 12 13 14 15 16 17 18 0
-1 19 20 21 22 23 24 25 2 3 4 5 6 0
-1 7 8 9 10 11 12 13 14 15 16 17 18 19 0
-1 20 21 22 23 24 25 2 3 4 5 6 7 0
-1 8 9 10 11 12 13 14 15 16 17 18 19 20 0
-1 21 22 23 24 25 2 3 4 5 6 7 8 0
-1 9 10 11 12 13 14 15 16 17 18 19 20 21 0
-1 22 23 24 25 2 3 4 5 6 7 8 9 0
-1 10 11 12 13 14 15 16 17 18 19 20 21 22 0
-1 23 24 25 2 3 4 5 6 7 8 9 10 0
-1 11 12 13 14 15 16 17 18 19 20 21 22 23 0
-1 24 25 2 3 4 5 6 7 8 9 10 11 0
-1 12 13 14 15 16 17 18 19 20 21 22 23 24 0
-1 25 2 3 4 5 6 7 8 9 10 11 12 0
1 26 27 28 29 30 0
1 31 32 33 34 35 0
1 36 37 38 39 40 0
1 41 42 43 44 45 0
1 46 47 48 49 50 0
-1 26 27 28 29 30 31 32 33 34 35 0
-1 36 37 38 39 40 41 42 43 44 45 0
-1 46 47 48 49 50 2 3 4 5 6 0
1 7 8 9 10 11 12 13 14 15 16 17 18 19 20 0
1 21 22 23 24 25 26 27 28 29 30 31 32 33 34 0
1 35 36 37 38 39 40 41 42 43 44 45 46 47 48 0
1 49 50 2 3 4 5 6 7 8 9 10 11 12 13 0
-1 14 15 16 17 18 19 20 21 22 23 24 25 26 27 0
-1 28 29 30 31 32 33 34 35 36 37 38 39 40 41 0
-1 42 43 44 45 46 47 48 49 50 2 3 4 5 6 7 0
1 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 0
1 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 0
1 38 39 40 41 42 43 44 45 46 47 48 49 50 2 3 0
-1 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 0
-1 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 0
-1 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 2 0
"""
    expected = reference_backbone(cnf)
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == expected.strip()
    # Strict format check: must be sorted by absolute value, one per line, no extra whitespace
    if out:
        lines = out.strip().split('\n')
        lits = [int(line.strip()) for line in lines if line.strip()]
        assert lits == sorted(lits, key=abs), f"Backbone not sorted by absolute value: {lits}"
        # Verify no duplicate literals
        assert len(lits) == len(set(lits)), f"Duplicate literals found: {lits}"
        # Verify exact format: one literal per line, no trailing spaces
        raw = get_raw_output(tmp_path)
        raw_lines = raw.rstrip('\n').split('\n') if raw else []
        assert len(raw_lines) == len(lits), f"Line count mismatch: {len(raw_lines)} vs {len(lits)}"
        for line in raw_lines:
            assert line.strip() == line, f"Line has trailing/leading whitespace: {repr(line)}"


def test_multiple_backbone_vars_mixed_signs(tmp_path: Path):
    """Many backbone variables with mixed signs requiring exhaustive model enumeration."""
    # Multiple backbone vars: x1=true, x2=false, x3=false, x4=true, x5=false, x6=true, x7=false, x8=true, x9=false
    # Adversarial structure: requires checking all models for each variable to identify backbone
    # Tests that solver doesn't use shortcuts or incomplete heuristics
    cnf = """c Many backbone vars mixed signs requiring exhaustive enumeration
p cnf 60 250
1 0
-2 0
-3 0
4 0
-5 0
6 0
-7 0
1 6 7 8 9 10 0
-2 11 12 13 14 15 0
-3 16 17 18 19 20 0
4 6 11 16 0
-5 7 12 17 0
1 8 13 18 0
-2 9 14 19 0
-3 10 15 20 0
4 6 7 8 9 0
-5 10 11 12 13 0
1 14 15 16 17 0
-2 18 19 20 6 0
-3 7 8 9 10 0
4 11 12 13 14 0
-5 15 16 17 18 0
1 19 20 6 7 0
-2 8 9 10 11 0
-3 12 13 14 15 0
4 16 17 18 19 0
-5 20 6 7 8 0
1 9 10 11 12 0
-2 13 14 15 16 0
-3 17 18 19 20 0
4 6 7 8 9 10 0
-5 11 12 13 14 15 0
1 16 17 18 19 20 0
-2 6 7 8 9 10 0
-3 11 12 13 14 15 0
4 16 17 18 19 20 0
-5 6 7 8 9 10 0
1 11 12 13 14 15 0
-2 16 17 18 19 20 0
-3 6 7 8 9 10 0
4 11 12 13 14 15 0
-5 16 17 18 19 20 0
6 21 22 23 24 25 0
-7 26 27 28 29 30 0
1 31 32 33 34 35 0
-2 6 7 8 9 10 0
-3 11 12 13 14 15 0
4 16 17 18 19 20 0
-5 21 22 23 24 25 0
6 26 27 28 29 30 0
-7 31 32 33 34 35 0
1 2 3 4 5 6 7 0
-1 -2 -3 -4 -5 -6 -7 0
1 8 9 10 11 12 13 0
-2 14 15 16 17 18 19 0
-3 20 21 22 23 24 25 0
4 26 27 28 29 30 31 0
-5 32 33 34 35 8 9 0
6 10 11 12 13 14 15 0
-7 16 17 18 19 20 21 0
1 22 23 24 25 26 27 0
-2 28 29 30 31 32 33 0
-3 34 35 8 9 10 11 0
4 12 13 14 15 16 17 0
-5 18 19 20 21 22 23 0
6 24 25 26 27 28 29 0
-7 30 31 32 33 34 35 0
1 8 9 10 11 12 13 14 0
-2 15 16 17 18 19 20 21 0
-3 22 23 24 25 26 27 28 0
4 29 30 31 32 33 34 35 0
-5 8 9 10 11 12 13 14 15 0
6 16 17 18 19 20 21 22 0
-7 23 24 25 26 27 28 29 0
1 30 31 32 33 34 35 8 9 0
-2 10 11 12 13 14 15 16 17 0
-3 18 19 20 21 22 23 24 25 0
4 26 27 28 29 30 31 32 33 0
-5 34 35 8 9 10 11 12 13 0
6 14 15 16 17 18 19 20 21 0
-7 22 23 24 25 26 27 28 29 0
1 30 31 32 33 34 35 8 9 10 0
-2 11 12 13 14 15 16 17 18 19 0
-3 20 21 22 23 24 25 26 27 28 0
4 29 30 31 32 33 34 35 8 9 0
-5 10 11 12 13 14 15 16 17 18 0
6 19 20 21 22 23 24 25 26 27 0
-7 28 29 30 31 32 33 34 35 8 0
1 9 10 11 12 13 14 15 16 17 18 0
-2 19 20 21 22 23 24 25 26 27 28 0
-3 29 30 31 32 33 34 35 8 9 10 0
4 11 12 13 14 15 16 17 18 19 20 0
-5 21 22 23 24 25 26 27 28 29 30 0
6 31 32 33 34 35 8 9 10 11 12 0
-7 13 14 15 16 17 18 19 20 21 22 0
1 23 24 25 26 27 28 29 30 31 32 0
-2 33 34 35 8 9 10 11 12 13 14 0
-3 15 16 17 18 19 20 21 22 23 24 0
4 25 26 27 28 29 30 31 32 33 34 0
-5 35 8 9 10 11 12 13 14 15 16 0
6 17 18 19 20 21 22 23 24 25 26 0
-7 27 28 29 30 31 32 33 34 35 8 0
8 0
-9 0
1 36 37 38 39 40 0
-2 41 42 43 44 45 0
-3 46 47 48 49 50 0
4 51 52 53 54 55 0
-5 56 57 58 59 60 0
6 36 41 46 51 56 0
-7 37 42 47 52 57 0
8 38 43 48 53 58 0
-9 39 44 49 54 59 0
1 40 45 50 55 60 0
-2 36 37 38 39 40 0
-3 41 42 43 44 45 0
4 46 47 48 49 50 0
-5 51 52 53 54 55 0
6 56 57 58 59 60 0
-7 36 37 38 39 40 41 0
8 42 43 44 45 46 47 0
-9 48 49 50 51 52 53 0
1 54 55 56 57 58 59 60 0
-2 36 37 38 39 40 41 42 0
-3 43 44 45 46 47 48 49 0
4 50 51 52 53 54 55 56 0
-5 57 58 59 60 36 37 38 0
6 39 40 41 42 43 44 45 0
-7 46 47 48 49 50 51 52 0
8 53 54 55 56 57 58 59 0
-9 60 36 37 38 39 40 41 0
1 42 43 44 45 46 47 48 49 0
-2 50 51 52 53 54 55 56 57 58 0
-3 59 60 36 37 38 39 40 41 42 0
4 43 44 45 46 47 48 49 50 51 0
-5 52 53 54 55 56 57 58 59 60 36 0
6 37 38 39 40 41 42 43 44 45 46 0
-7 47 48 49 50 51 52 53 54 55 56 0
8 57 58 59 60 36 37 38 39 40 41 0
-9 42 43 44 45 46 47 48 49 50 51 52 0
1 53 54 55 56 57 58 59 60 36 37 38 39 0
-2 40 41 42 43 44 45 46 47 48 49 50 51 0
-3 52 53 54 55 56 57 58 59 60 36 37 38 0
4 39 40 41 42 43 44 45 46 47 48 49 50 0
-5 51 52 53 54 55 56 57 58 59 60 36 37 0
6 38 39 40 41 42 43 44 45 46 47 48 49 0
-7 50 51 52 53 54 55 56 57 58 59 60 36 0
8 37 38 39 40 41 42 43 44 45 46 47 48 49 0
-9 50 51 52 53 54 55 56 57 58 59 60 36 37 0
1 38 39 40 41 42 43 44 45 46 47 48 49 50 0
-2 51 52 53 54 55 56 57 58 59 60 36 37 38 39 0
-3 40 41 42 43 44 45 46 47 48 49 50 51 52 53 0
4 54 55 56 57 58 59 60 36 37 38 39 40 41 0
-5 42 43 44 45 46 47 48 49 50 51 52 53 54 55 0
6 56 57 58 59 60 36 37 38 39 40 41 42 43 0
-7 44 45 46 47 48 49 50 51 52 53 54 55 56 57 0
8 58 59 60 36 37 38 39 40 41 42 43 44 45 0
-9 46 47 48 49 50 51 52 53 54 55 56 57 58 59 0
1 60 36 37 38 39 40 41 42 43 44 45 46 47 48 0
-2 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 0
-3 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 0
4 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 0
-5 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 0
6 59 60 36 37 38 39 40 41 42 43 44 45 46 47 0
-7 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 0
8 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 0
-9 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 0
1 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 0
-2 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 0
-3 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 0
4 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 0
-5 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 0
6 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 0
-7 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 0
8 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 0
-9 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 0
1 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 0
-2 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 48 49 0
-3 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 0
4 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 0
-5 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 0
6 60 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 0
-7 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 0
8 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 0
-9 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 0
1 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 0
-2 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 0
-3 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 0
4 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 52 53 54 0
-5 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 51 0
6 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 47 48 0
-7 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 45 46 0
8 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 44 0
-9 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 36 37 38 39 40 41 42 43 0
"""
    expected = reference_backbone(cnf)
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == expected.strip()
    # Strict format check: must be sorted by absolute value, one per line
    if out:
        lines = out.strip().split('\n')
        lits = [int(line.strip()) for line in lines if line.strip()]
        assert lits == sorted(lits, key=abs), f"Backbone not sorted by absolute value: {lits}"
        # Verify no duplicates
        assert len(lits) == len(set(lits)), f"Duplicate literals: {lits}"
        # Verify exact format: one literal per line, no trailing spaces
        raw = get_raw_output(tmp_path)
        raw_lines = raw.rstrip('\n').split('\n') if raw else []
        assert len(raw_lines) == len(lits), "Line count mismatch"
        for line in raw_lines:
            assert line.strip() == line, f"Line has whitespace: {repr(line)}"
        # Verify all backbone vars are present and correct
        assert 1 in lits or -1 in lits, "x1 should be in backbone"
        assert -2 in lits, "x2 should be in backbone as -2"


def test_variables_not_appearing_are_not_backbone(tmp_path: Path):
    """Extremely many variables that never appear must be correctly excluded from backbone."""
    # Only x1 appears and is forced true, but many other variables declared
    # Adversarial: large variable count makes it easy to accidentally include non-appearing vars
    # Tests strict adherence to rule: only variables appearing in clauses can be in backbone
    cnf = """c Extremely many variables don't appear, only x1 does - strict exclusion test
p cnf 100 1
1 0
"""
    expected = reference_backbone(cnf)
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == expected.strip()
    if out:
        lits = [int(x) for x in out.split()]
        assert all(abs(lit) == 1 for lit in lits), f"Only x1 should appear, got: {lits}"
        # Strict check: no variables > 1 appear
        assert all(abs(lit) <= 1 for lit in lits), f"Variables > 1 found: {[lit for lit in lits if abs(lit) > 1]}"
        # Verify exact format
        raw = get_raw_output(tmp_path)
        raw_lits = [int(line.strip()) for line in raw.rstrip('\n').split('\n') if line.strip()]
        assert raw_lits == lits, "Raw output format mismatch"


def test_tautological_clauses_do_not_break_backbone(tmp_path: Path):
    """Extremely many complex tautologies requiring careful handling to identify backbone."""
    # Adversarial: many tautologies that could confuse incomplete solvers or cause incorrect pruning
    # x1 must be true, but solver must correctly handle tautologies without breaking backbone detection
    # Tests that solver doesn't incorrectly eliminate clauses or skip model checks
    cnf = """c Extremely many complex tautologies and redundancies - adversarial tautology handling
p cnf 40 200
1 0
1 -1 0
2 -2 0
3 -3 0
4 -4 0
5 -5 0
1 2 -1 -2 0
1 3 -1 -3 0
1 4 -1 -4 0
1 5 -1 -5 0
1 6 -1 -6 0
1 7 -1 -7 0
1 8 -1 -8 0
1 9 -1 -9 0
1 10 -1 -10 0
1 11 -1 -11 0
1 12 -1 -12 0
1 2 3 -1 -2 -3 0
1 4 5 -1 -4 -5 0
1 6 7 -1 -6 -7 0
1 8 9 -1 -8 -9 0
1 10 11 -1 -10 -11 0
1 2 3 4 5 -1 -2 -3 -4 -5 0
1 6 7 8 9 10 -1 -6 -7 -8 -9 -10 0
1 11 12 13 14 15 -1 -11 -12 -13 -14 -15 0
1 16 17 18 19 20 -1 -16 -17 -18 -19 -20 0
1 21 22 23 24 25 -1 -21 -22 -23 -24 -25 0
1 2 3 4 5 6 7 -1 -2 -3 -4 -5 -6 -7 0
1 8 9 10 11 12 13 14 -1 -8 -9 -10 -11 -12 -13 -14 0
1 15 16 17 18 19 20 21 -1 -15 -16 -17 -18 -19 -20 -21 0
1 22 23 24 25 2 3 4 -1 -22 -23 -24 -25 -2 -3 -4 0
1 5 6 7 8 9 10 11 12 -1 -5 -6 -7 -8 -9 -10 -11 -12 0
1 13 14 15 16 17 18 19 20 21 -1 -13 -14 -15 -16 -17 -18 -19 -20 -21 0
1 22 23 24 25 2 3 4 5 6 7 -1 -22 -23 -24 -25 -2 -3 -4 -5 -6 -7 0
1 8 9 10 11 12 13 14 15 16 17 -1 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 0
1 18 19 20 21 22 23 24 25 2 3 4 -1 -18 -19 -20 -21 -22 -23 -24 -25 -2 -3 -4 0
1 5 6 7 8 9 10 11 12 13 14 15 16 -1 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 0
1 17 18 19 20 21 22 23 24 25 2 3 4 5 6 -1 -17 -18 -19 -20 -21 -22 -23 -24 -25 -2 -3 -4 -5 -6 0
1 7 8 9 10 11 12 13 14 15 16 17 18 19 20 -1 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 0
1 21 22 23 24 25 2 3 4 5 6 7 8 9 10 11 -1 -21 -22 -23 -24 -25 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 0
1 12 13 14 15 16 17 18 19 20 21 22 23 24 25 2 3 -1 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 -2 -3 0
1 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 -1 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 0
1 23 24 25 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 -1 -23 -24 -25 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 0
1 20 21 22 23 24 25 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 -1 -20 -21 -22 -23 -24 -25 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 0
1 21 22 23 24 25 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 -1 -21 -22 -23 -24 -25 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 0
1 23 24 25 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 -1 -23 -24 -25 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 0
"""
    expected = reference_backbone(cnf)
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == expected.strip()
    # x1 must be true in all models despite many tautologies


def test_random_cnf_small(tmp_path: Path):
    """Random CNFs with extremely large n and many clauses requiring exhaustive solving."""
    # Adversarial random generation: creates formulas that require full DPLL enumeration
    # Tests that solver handles large random instances correctly without shortcuts
    random.seed(0)
    for _ in range(30):
        n = random.randint(40, 60)
        m = random.randint(100, 200)
        clauses = []
        for _ in range(m):
            k = random.randint(4, 10)
            lits = []
            seen_vars = set()
            for _ in range(k):
                v = random.randint(1, n)
                # Avoid duplicate literals in same clause (but allow same var with different signs)
                while v in seen_vars or -v in seen_vars:
                    v = random.randint(1, n)
                sign = random.choice([-1, 1])
                lits.append(sign * v)
                seen_vars.add(abs(v))
            # Avoid trivial 0 clause here; keep some variety
            clause_str = " ".join(str(lit) for lit in lits) + " 0"
            clauses.append(clause_str)

        header = f"p cnf {n} {len(clauses)}"
        cnf = "c random larger\n" + header + "\n" + "\n".join(clauses) + "\n"
        expected = reference_backbone(cnf)
        out = run_backbone(cnf, tmp_path)
        assert out.strip() == expected.strip(), f"Mismatch on CNF:\n{cnf}"
        # Strict format validation for random tests
        if out:
            lines = out.strip().split('\n')
            lits = [int(line.strip()) for line in lines if line.strip()]
            assert lits == sorted(lits, key=abs), f"Not sorted by abs: {lits}"
            assert len(lits) == len(set(lits)), f"Duplicates: {lits}"
        elif expected:
            assert False, "Expected backbone but got empty output"


def test_random_cnf_with_empty_clause(tmp_path: Path):
    """Extremely large random CNF plus empty clause => UNSAT (tests empty clause detection)."""
    # Adversarial: large formula that appears satisfiable until empty clause is processed
    # Tests that solver correctly identifies empty clause even in large formulas
    cnf = """c Extremely large formula with empty clause makes UNSAT
p cnf 60 150
1 2 3 0
4 5 6 0
7 8 9 0
10 11 12 0
-1 4 7 0
-2 5 8 0
-3 6 9 0
-4 10 1 0
-5 11 2 0
-6 12 3 0
-7 1 4 0
-8 2 5 0
-9 3 6 0
-10 7 1 0
-11 8 2 0
-12 9 3 0
1 4 7 10 0
2 5 8 11 0
3 6 9 12 0
13 14 15 16 17 18 0
19 20 21 22 23 24 0
25 26 27 28 29 30 0
-13 16 19 22 0
-14 17 20 23 0
-15 18 21 24 0
-16 25 13 19 0
-17 26 14 20 0
-18 27 15 21 0
-19 13 16 25 0
-20 14 17 26 0
-21 15 18 27 0
-22 19 13 16 0
-23 20 14 17 0
-24 21 15 18 0
13 16 19 22 25 0
14 17 20 23 26 0
15 18 21 24 27 0
28 29 30 13 14 15 0
16 17 18 19 20 21 0
22 23 24 25 26 27 0
-28 13 16 19 22 0
-29 14 17 20 23 0
-30 15 18 21 24 0
1 13 19 25 28 0
2 14 20 26 29 0
3 15 21 27 30 0
-1 16 22 13 19 0
-2 17 23 14 20 0
-3 18 24 15 21 0
1 2 3 4 5 6 7 8 9 10 0
11 12 13 14 15 16 17 18 19 20 0
21 22 23 24 25 26 27 28 29 30 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 0
-11 -12 -13 -14 -15 -16 -17 -18 -19 -20 0
-21 -22 -23 -24 -25 -26 -27 -28 -29 -30 0
31 32 33 34 35 36 0
37 38 39 40 41 42 0
43 44 45 46 47 48 0
49 50 51 52 53 54 0
55 56 57 58 59 60 0
-31 34 37 40 0
-32 35 38 41 0
-33 36 39 42 0
-34 43 31 37 0
-35 44 32 38 0
-36 45 33 39 0
-37 31 34 43 0
-38 32 35 44 0
-39 33 36 45 0
-40 37 31 34 0
-41 38 32 35 0
-42 39 33 36 0
31 34 37 40 43 0
32 35 38 41 44 0
33 36 39 42 45 0
46 47 48 31 32 33 0
34 35 36 37 38 39 0
40 41 42 43 44 45 0
-46 31 34 37 40 0
-47 32 35 38 41 0
-48 33 36 39 42 0
1 31 37 43 46 0
2 32 38 44 47 0
3 33 39 45 48 0
-1 34 40 31 37 0
-2 35 41 32 38 0
-3 36 42 33 39 0
1 2 3 4 5 6 7 8 9 10 11 12 0
13 14 15 16 17 18 19 20 21 22 23 24 0
25 26 27 28 29 30 31 32 33 34 35 36 0
37 38 39 40 41 42 43 44 45 46 47 48 0
49 50 51 52 53 54 55 56 57 58 59 60 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 0
-13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 0
-25 -26 -27 -28 -29 -30 -31 -32 -33 -34 -35 -36 0
-37 -38 -39 -40 -41 -42 -43 -44 -45 -46 -47 -48 0
-49 -50 -51 -52 -53 -54 -55 -56 -57 -58 -59 -60 0
1 13 25 37 49 2 14 26 38 50 3 15 27 39 51 0
4 16 28 40 52 5 17 29 41 53 6 18 30 42 54 0
7 19 31 43 55 8 20 32 44 56 9 21 33 45 57 0
10 22 34 46 58 11 23 35 47 59 12 24 36 48 60 0
-1 -13 -25 -37 -49 -2 -14 -26 -38 -50 -3 -15 -27 -39 -51 0
-4 -16 -28 -40 -52 -5 -17 -29 -41 -53 -6 -18 -30 -42 -54 0
-7 -19 -31 -43 -55 -8 -20 -32 -44 -56 -9 -21 -33 -45 -57 0
-10 -22 -34 -46 -58 -11 -23 -35 -47 -59 -12 -24 -36 -48 -60 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 0
21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 0
41 42 43 44 45 46 47 48 49 50 51 52 53 54 55 56 57 58 59 60 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 0
-21 -22 -23 -24 -25 -26 -27 -28 -29 -30 -31 -32 -33 -34 -35 -36 -37 -38 -39 -40 0
-41 -42 -43 -44 -45 -46 -47 -48 -49 -50 -51 -52 -53 -54 -55 -56 -57 -58 -59 -60 0
0
"""
    out = run_backbone(cnf, tmp_path)
    assert out.strip() == "UNSAT"
    # Strict format check: UNSAT followed by exactly one newline, no other content
    raw = get_raw_output(tmp_path)
    assert raw == "UNSAT\n", f"Expected 'UNSAT\\n' but got {repr(raw)}"
    assert len(raw) == 6, f"Expected 6 bytes (UNSAT + \\n) but got {len(raw)}"
    assert raw.encode('utf-8') == b"UNSAT\n", "Byte-level format check failed"


def test_determinism_on_same_input(tmp_path: Path):
    """Running twice on same extremely complex CNF must yield identical backbone (determinism test)."""
    # Adversarial: very large formula testing that solver is fully deterministic
    # No randomness, no non-deterministic choices, exact same output every time
    # Tests strict determinism requirement under computational load
    cnf = """c Determinism test with extremely complex formula requiring exhaustive solving
p cnf 50 200
1 0
2 0
3 0
1 4 5 6 7 8 0
2 9 10 11 12 13 0
3 14 15 4 5 6 0
-1 7 8 9 10 11 0
-2 12 13 14 15 4 0
-3 5 6 7 8 9 0
1 10 11 12 13 14 0
2 15 4 5 6 7 0
3 8 9 10 11 12 0
-1 13 14 15 4 5 0
-2 6 7 8 9 10 0
-3 11 12 13 14 15 0
1 4 5 6 7 8 9 0
2 10 11 12 13 14 15 0
3 4 5 6 7 8 9 10 0
-1 11 12 13 14 15 4 0
-2 5 6 7 8 9 10 11 0
-3 12 13 14 15 4 5 0
1 6 7 8 9 10 11 12 0
2 13 14 15 4 5 6 7 0
3 8 9 10 11 12 13 14 0
-1 15 4 5 6 7 8 9 0
-2 10 11 12 13 14 15 4 0
-3 5 6 7 8 9 10 11 12 0
4 16 17 18 19 20 0
5 21 22 23 24 25 0
6 26 27 28 29 30 0
-4 16 17 18 19 20 0
-5 21 22 23 24 25 0
-6 26 27 28 29 30 0
7 8 9 10 11 12 13 14 15 0
16 17 18 19 20 21 22 23 24 0
25 26 27 28 29 30 4 5 6 0
-7 8 9 10 11 12 13 14 15 0
-16 17 18 19 20 21 22 23 24 0
-25 26 27 28 29 30 4 5 6 0
1 4 7 10 13 16 19 22 25 28 0
2 5 8 11 14 17 20 23 26 29 0
3 6 9 12 15 18 21 24 27 30 0
-1 4 7 10 13 16 19 22 25 28 0
-2 5 8 11 14 17 20 23 26 29 0
-3 6 9 12 15 18 21 24 27 30 0
1 2 3 4 5 6 7 8 9 10 11 12 0
13 14 15 16 17 18 19 20 21 22 23 24 0
25 26 27 28 29 30 1 2 3 4 5 6 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 0
-13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 0
-25 -26 -27 -28 -29 -30 -1 -2 -3 -4 -5 -6 0
1 4 7 10 13 16 19 22 25 28 2 5 8 0
11 14 17 20 23 26 29 3 6 9 12 15 18 0
21 24 27 30 1 4 7 10 13 16 19 22 25 0
-1 4 7 10 13 16 19 22 25 28 2 5 8 0
-11 14 17 20 23 26 29 3 6 9 12 15 18 0
-21 24 27 30 1 4 7 10 13 16 19 22 25 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 0
16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 0
17 18 19 20 21 22 23 24 25 26 27 28 29 30 1 2 0
3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 0
19 20 21 22 23 24 25 26 27 28 29 30 1 2 3 4 0
5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 0
21 22 23 24 25 26 27 28 29 30 1 2 3 4 5 6 0
7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 0
23 24 25 26 27 28 29 30 1 2 3 4 5 6 7 8 0
9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 0
25 26 27 28 29 30 1 2 3 4 5 6 7 8 9 10 0
11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 0
27 28 29 30 1 2 3 4 5 6 7 8 9 10 11 12 0
13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 0
29 30 1 2 3 4 5 6 7 8 9 10 11 12 13 14 0
15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 0
31 32 33 34 35 36 37 38 39 40 0
41 42 43 44 45 46 47 48 49 50 0
1 31 41 2 32 42 3 33 43 4 34 44 5 35 45 0
6 36 46 7 37 47 8 38 48 9 39 49 10 40 50 0
-1 -31 -41 -2 -32 -42 -3 -33 -43 -4 -34 -44 -5 -35 -45 0
-6 -36 -46 -7 -37 -47 -8 -38 -48 -9 -39 -49 -10 -40 -50 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 0
26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 0
-26 -27 -28 -29 -30 -31 -32 -33 -34 -35 -36 -37 -38 -39 -40 -41 -42 -43 -44 -45 -46 -47 -48 -49 -50 0
1 4 7 10 13 16 19 22 25 28 31 34 37 40 43 46 49 2 5 8 11 14 17 20 23 26 29 32 35 38 41 44 47 50 0
3 6 9 12 15 18 21 24 27 30 33 36 39 42 45 48 1 4 7 10 13 16 19 22 25 28 31 34 37 40 43 46 49 0
-1 -4 -7 -10 -13 -16 -19 -22 -25 -28 -31 -34 -37 -40 -43 -46 -49 -2 -5 -8 -11 -14 -17 -20 -23 -26 -29 -32 -35 -38 -41 -44 -47 -50 0
-3 -6 -9 -12 -15 -18 -21 -24 -27 -30 -33 -36 -39 -42 -45 -48 -1 -4 -7 -10 -13 -16 -19 -22 -25 -28 -31 -34 -37 -40 -43 -46 -49 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 0
41 42 43 44 45 46 47 48 49 50 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 0
31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 -26 -27 -28 -29 -30 -31 -32 -33 -34 -35 -36 -37 -38 -39 -40 0
-41 -42 -43 -44 -45 -46 -47 -48 -49 -50 -1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 -26 -27 -28 -29 -30 0
-31 -32 -33 -34 -35 -36 -37 -38 -39 -40 -41 -42 -43 -44 -45 -46 -47 -48 -49 -50 -1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 0
1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47 48 49 50 0
-1 -2 -3 -4 -5 -6 -7 -8 -9 -10 -11 -12 -13 -14 -15 -16 -17 -18 -19 -20 -21 -22 -23 -24 -25 -26 -27 -28 -29 -30 -31 -32 -33 -34 -35 -36 -37 -38 -39 -40 -41 -42 -43 -44 -45 -46 -47 -48 -49 -50 0
"""
    out1 = run_backbone(cnf, tmp_path)
    raw1 = get_raw_output(tmp_path)
    out2 = run_backbone(cnf, tmp_path)
    raw2 = get_raw_output(tmp_path)
    assert out1.strip() == out2.strip(), "Content must be deterministic"
    # Strict format check: exact byte-level match required
    assert raw1 == raw2, f"Output format must be deterministic: {repr(raw1)} != {repr(raw2)}"
    assert raw1.encode('utf-8') == raw2.encode('utf-8'), "Byte-level determinism check failed"
    # Verify format consistency
    if out1:
        lines1 = out1.strip().split('\n')
        lines2 = out2.strip().split('\n')
        assert lines1 == lines2, "Line-by-line determinism check failed"

