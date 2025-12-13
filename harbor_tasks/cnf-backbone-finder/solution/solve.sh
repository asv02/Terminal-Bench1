#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

set -euo pipefail

SCRIPT="/app/find_backbone.py"
mkdir -p /app

cat > "$SCRIPT" << 'PY_EOF'
#!/usr/bin/env python3
"""
CNF Backbone Finder

CLI:
    python find_backbone.py --input formula.cnf --out backbone.txt
"""

import argparse
from pathlib import Path
from typing import List, Tuple, Dict


def parse_dimacs_file(path: Path) -> Tuple[int, List[List[int]]]:
    text = path.read_text(encoding="utf-8")
    n_vars = None
    clauses: List[List[int]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            parts = line.split()
            if len(parts) < 4 or parts[1] != "cnf":
                raise ValueError("Invalid DIMACS header")
            n_vars = int(parts[2])
            # num_clauses = int(parts[3])  # not strictly needed
        else:
            lits = [int(x) for x in line.split()]
            if not lits:
                continue
            if lits[-1] == 0:
                lits.pop()
            # Allow empty clause as []
            clauses.append(lits)
    if n_vars is None:
        max_var = 0
        for cl in clauses:
            for l in cl:
                max_var = max(max_var, abs(l))
        n_vars = max_var
    return n_vars, clauses


def dpll(clauses: List[List[int]], n_vars: int, assignment: List[int]):
    """
    Basic recursive DPLL with unit propagation.

    assignment[i] in {0,1,-1}:
        0: unassigned
        1: true
        -1: false

    Returns (sat: bool, assignment_or_None)
    """

    while True:
        changed = False
        # Unit propagation
        for cl in clauses:
            val = None
            unassigned_lits = []
            for lit in cl:
                v = abs(lit)
                sign = 1 if lit > 0 else -1
                a = assignment[v]
                if a == 0:
                    unassigned_lits.append(lit)
                elif a == sign:
                    val = True
                    break
            if val is True:
                continue
            if not unassigned_lits:
                # All assigned and none true: clause is false
                return False, None
            if len(unassigned_lits) == 1:
                # Unit clause
                lit = unassigned_lits[0]
                v = abs(lit)
                sign = 1 if lit > 0 else -1
                if assignment[v] == 0:
                    assignment[v] = sign
                    changed = True
        if not changed:
            break

    # Check if all assigned
    var = 0
    for i in range(1, n_vars + 1):
        if assignment[i] == 0:
            var = i
            break
    if var == 0:
        # All assigned; we already know no clause is false => model
        return True, assignment

    # Branch on var
    for val in (1, -1):
        new_assignment = assignment.copy()
        new_assignment[var] = val
        sat, model = dpll(clauses, n_vars, new_assignment)
        if sat:
            return True, model
    return False, None


def sat_solve(clauses: List[List[int]], n_vars: int, forced: Dict[int, bool] = None):
    assignment = [0] * (n_vars + 1)
    if forced:
        for v, val in forced.items():
            assignment[v] = 1 if val else -1
    return dpll(clauses, n_vars, assignment)


def compute_backbone(n_vars: int, clauses: List[List[int]]) -> str:
    # First, solve original CNF
    sat, model = sat_solve(clauses, n_vars)
    if not sat:
        return "UNSAT"

    backbone: List[int] = []

    # Precompute which vars actually appear
    appears = [False] * (n_vars + 1)
    for cl in clauses:
        for l in cl:
            v = abs(l)
            if 1 <= v <= n_vars:
                appears[v] = True

    for v in range(1, n_vars + 1):
        if not appears[v]:
            # Free variable, never constrained => cannot be backbone
            continue
        val = (model[v] == 1)
        # Force opposite value
        forced = {v: (not val)}
        sat2, _ = sat_solve(clauses, n_vars, forced)
        if not sat2:
            lit = v if val else -v
            backbone.append(lit)

    backbone.sort(key=lambda x: abs(x))
    if not backbone:
        return ""
    return "\n".join(str(l) for l in backbone)


def main() -> int:
    parser = argparse.ArgumentParser(description="CNF Backbone Finder")
    parser.add_argument("--input", required=True, help="DIMACS CNF file")
    parser.add_argument("--out", required=True, help="Output backbone file")
    args = parser.parse_args()

    in_path = Path(args.input)
    out_path = Path(args.out)

    n_vars, clauses = parse_dimacs_file(in_path)
    result = compute_backbone(n_vars, clauses)

    # Write result exactly as required
    if result == "UNSAT":
        out_path.write_text("UNSAT\n", encoding="utf-8")
    else:
        # May be empty string => empty file
        out_path.write_text(result + ("\n" if result else ""), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
PY_EOF

chmod +x "$SCRIPT"








