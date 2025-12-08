## CNF Minimal Clause Set Reducer (Debugging & Reasoning Task)

You are given a CNF in DIMACS form. A clause is logically redundant
if removing it keeps the formula logically equivalent (i.e., every
assignment that satisfies the reduced CNF also satisfies the original,
and vice versa).

**DEBUGGING REQUIREMENT**: This task requires deep reasoning about why clauses are redundant. You must not only identify redundant clauses but also understand the root cause of redundancy through systematic debugging. When a clause appears redundant, you must verify by checking all possible truth assignments - a clause that seems redundant in one context may be essential in another. This requires exhaustive enumeration and careful analysis of the logical structure.

You must remove all redundant clauses, obtaining a MINIMAL clause set
(no clause can be removed without changing the set of satisfying
assignments). Among all such minimal clause sets, choose the one whose
sorted list of clause indices is lexicographically smallest.

**BESPOKE RULE (CRITICAL - EASY TO MISS)**: When comparing minimal sets lexicographically, you must compare the clause indices as they appear in the original file order (1-based), NOT as they appear in your internal data structures. Additionally, when multiple minimal sets have the same first k indices but differ at position k+1, the set with the smaller (k+1)th index is lexicographically smaller, even if it's longer overall. This means [1,2,3] < [1,2,4] < [1,3] < [2,1] when all are minimal sets. However, there's a subtle exception: if one minimal set is a proper prefix of another, the shorter one is always smaller. This rule is buried in standard lexicographic ordering but has a critical nuance: you must ensure you're comparing 1-based indices, not 0-based array positions.

If the formula is UNSAT, output all clause indices (no removal).

Otherwise output the chosen minimal set, sorted, 1 per line.

### CLI

Create a shell script `/app/solution.sh` that accepts command-line arguments:

```
bash solution.sh --input input.cnf --out /app/result.txt
```

**Script Structure:**
- The script must be located at `/app/solution.sh`
- **The script must have the executable bit set**: After creating the script, run `chmod +x /app/solution.sh` to make it executable
- The script must start with a shebang: `#!/usr/bin/env bash` or `#!/bin/bash`
- The script must parse the `--input` and `--out` (or `--output`) arguments exactly as shown in the example below
- The script can be a pure shell script or a wrapper that calls Python code
- You can use Python's standard library (including `argparse`) for argument parsing if calling Python code

**Important Shell Script Guidelines:**
- **Variable expansion**: Use `"$VARIABLE"` (with quotes) to prevent word splitting and pathname expansion. Use `${VARIABLE}` only when necessary for disambiguation.
- **Heredoc for Python code**: When embedding Python code in a shell script, use a heredoc with single quotes (`'EOF'`) to prevent shell variable expansion in the Python code, then use double quotes when passing shell variables to Python.
- **Error handling**: Consider using `set -euo pipefail` at the start of your script to exit on errors, undefined variables, and pipe failures.
- **Python invocation**: Use `python` or `python3` depending on what's available: `if command -v python >/dev/null 2>&1; then PY=python; else PY=python3; fi`

**Argument Parsing:**
- The script must accept exactly these command-line arguments:
  - `--input <path>`: Path to the input CNF file (required)
  - `--out <path>` or `--output <path>`: Path to the output file where results should be written (required)
- **Important**: The argument names must be exactly `--input` and `--out` (or `--output`). Do not use different names like `-i`, `-o`, `--in`, `--output-file`, etc.
- Example bash argument parsing:
  ```bash
  INPUT_FILE=""
  OUTPUT_FILE=""
  
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --input) INPUT_FILE="$2"; shift 2;;
      --out|--output) OUTPUT_FILE="$2"; shift 2;;
      *) shift;;
    esac
  done
  
  if [[ -z "$INPUT_FILE" ]] || [[ -z "$OUTPUT_FILE" ]]; then
    echo "Error: --input and --out/--output are required" >&2
    exit 1
  fi
  ```
- If using Python's `argparse`, use:
  ```python
  parser.add_argument("--input", required=True)
  parser.add_argument("--out", dest="output")
  parser.add_argument("--output", dest="output")
  ```

**Complete Example: Shell Script Calling Python**

Here is a complete working example of a shell script that parses arguments and calls Python:

```bash
#!/usr/bin/env bash
set -euo pipefail

INPUT_FILE=""
OUTPUT_FILE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) INPUT_FILE="$2"; shift 2;;
    --out|--output) OUTPUT_FILE="$2"; shift 2;;
    *) shift;;
  esac
done

if [[ -z "$INPUT_FILE" ]] || [[ -z "$OUTPUT_FILE" ]]; then
  echo "Error: --input and --out/--output are required" >&2
  exit 1
fi

# Determine Python command
if command -v python >/dev/null 2>&1; then
  PY=python
else
  PY=python3
fi

# Create temporary file for Python code
TMP=$(mktemp)

# Write Python code using heredoc with single quotes to prevent variable expansion
cat >"$TMP" <<'PYEOF'
import argparse
import sys

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    
    # Your Python code here
    # Access the input file path via: args.input
    # Access the output file path via: getattr(args, 'out')
    # Read from the input file, process the data, and write results to the output file
    
if __name__ == "__main__":
    main()
PYEOF

# Call Python with shell variables (use double quotes for variable expansion)
"$PY" "$TMP" --input "$INPUT_FILE" --out "$OUTPUT_FILE"

# Clean up
rm -f "$TMP"
```

**Key Points:**
- Use `'PYEOF'` (single quotes) in the heredoc to prevent shell variable expansion in Python code
- Use `"$VARIABLE"` (double quotes) when passing shell variables to Python
- Always quote variables to handle paths with spaces correctly
- Use `"$PY"` and `"$TMP"` (quoted) when invoking Python to handle paths correctly

**Common Mistakes to Avoid:**
- **Don't use `${INPUT_FILE}` without quotes**: Use `"$INPUT_FILE"` not `${INPUT_FILE}` (though `${INPUT_FILE}` works, quotes are safer)
- **Don't use double quotes in heredoc for Python code**: Use `'EOF'` not `"EOF"` to prevent shell variable expansion
- **Always quote variables**: Use `"$VAR"` not `$VAR` to handle spaces in paths
- **Don't forget to pass variables to Python**: After parsing arguments in shell, you must pass them to Python via command-line arguments
- **Don't use uninitialized variables**: Check that variables are set before using them
- **Test your script**: Make sure the script actually executes and produces output files

**File I/O:**
- Read the input CNF file from the path specified by `--input`
- Write the output (one clause index per line) to the path specified by `--out` or `--output`
- **Critical**: Always write at least one clause index to the output file. The output file must never be empty (except in error cases, but the script should handle errors appropriately)
- Ensure the output file is created/overwritten with the results
- **Error Handling**: If the input file cannot be read or parsed, the script must handle the error and exit with a non-zero status code. The following cases are considered parsing errors that must result in a non-zero exit:
  - **Missing problem line**: The file does not contain a line starting with `p cnf`
  - **Invalid problem line format**: The problem line exists but is malformed (e.g., `p cnf` without variable and clause counts, or with invalid syntax)
  - **File cannot be read**: The input file does not exist or cannot be opened for reading
  - Note: Clause count mismatches (fewer clauses than declared) may be handled gracefully by processing available clauses, or treated as an error - either behavior is acceptable

### Input format (input.cnf)

Standard DIMACS CNF format with specific requirements:

- **Comment lines**: Lines starting with `c` (lowercase) are comments and must be ignored. Comments can appear anywhere in the file, including before the problem line, between clauses, or after all clauses.
- **Problem line**: Must be exactly `p cnf <num_vars> <num_clauses>` where:
  - `<num_vars>` is the number of variables (positive integer)
  - `<num_clauses>` is the number of clauses (non-negative integer, can be 0)
  - The problem line must appear exactly once, after any initial comments
  - **Critical niche knowledge**: The problem line declares the number of clauses, but the actual clauses follow. If fewer clauses are provided than declared, you must handle this gracefully (process available clauses) or exit with error - either is acceptable.
- **Clauses**: Each clause is a sequence of integers (literals) terminated by `0`:
  - Variables are numbered `1..N` (not 0-indexed - this is critical DIMACS format knowledge)
  - Literals are positive (`x`) or negative (`-x`) integers
  - Each clause must end with `0` (the terminator)
  - **Critical niche knowledge**: Empty clauses (just `0`) are valid and represent the unsatisfiable clause (always false)
  - **Critical niche knowledge**: Clauses can contain duplicate literals (e.g., `1 1 2 0`), which are logically equivalent to `1 2 0` (idempotency of disjunction)
  - **Critical niche knowledge**: Clauses can be in any order, but clause indices are assigned based on the order they appear after the problem line (comment lines don't count)
- **Clause numbering**: Clauses are numbered `1..num_clauses` in the order they appear after the `p cnf` line:
  - The first non-comment line after `p cnf` is clause 1
  - The second non-comment line after `p cnf` is clause 2
  - And so on
  - **BESPOKE RULE (CRITICAL)**: Clause indices in the output must correspond to this numbering scheme. When outputting clause indices, you must use 1-based indexing matching the order clauses appear in the file, NOT 0-based array indexing. This is a common source of errors - many implementations use 0-based indexing internally but must convert to 1-based for output.
  - **NICHE KNOWLEDGE (CRITICAL)**: The DIMACS format specification (SAT Competition format) requires that clause indices follow the exact order of appearance in the file, including handling of comments. However, there's a subtle edge case: if a comment line appears between the problem line and the first clause, the first clause is still numbered 1. Similarly, if multiple comment lines appear between clauses, they don't affect numbering. This is standard DIMACS behavior but requires careful parsing logic. Many implementations incorrectly count comment lines or renumber clauses when comments are present.
  - **NICHE KNOWLEDGE (DEBUGGING REQUIRED)**: When clauses contain duplicate literals (e.g., `1 1 2 0`), they are logically equivalent to the deduplicated version (`1 2 0`) due to idempotency of disjunction. However, for the purpose of clause numbering and minimal set selection, you must treat them as distinct clauses if they appear as separate lines in the file. Only if the exact same clause (same literals in same order) appears multiple times should you consider them for redundancy checking. This requires careful comparison logic that accounts for duplicate literals within clauses.
  - **BESPOKE RULE (EASY TO MISS)**: When a clause appears multiple times in the file (exact duplicate), they have different clause indices but are logically redundant. However, when selecting the lexicographically smallest minimal set, you must prefer the clause with the smaller index. For example, if clauses 2 and 5 are identical, and both are needed for minimality, you must include clause 2 (not clause 5) in your minimal set. This rule is critical for correctness but easy to overlook when implementing redundancy detection.

### Output format (/app/result.txt)

One clause index per line (sorted ascending).
If UNSAT, output all indices.

**BESPOKE RULE (CRITICAL)**: The clause indices must be 1-based, matching the DIMACS standard where the first clause after the problem line is clause 1, the second is clause 2, etc. If you use 0-based indexing internally (common in programming), you must convert to 1-based when writing output. This rule is easy to miss but critical for correctness.

### Multi-Step Algorithm Process

You must implement the following multi-step process. Each step has specific failure points that must be handled correctly:

**Step 1: Parse and Validate DIMACS Input**
- Read the input file line by line
- Skip comment lines (starting with `c`)
- Find and parse the problem line `p cnf <num_vars> <num_clauses>`
- **Failure point**: If no problem line exists, exit with non-zero status
- **Failure point**: If problem line is malformed, exit with non-zero status
- Parse all clauses after the problem line
- **Failure point**: Handle cases where fewer clauses are provided than declared (either process available clauses or exit with error)
- **Niche knowledge**: Variables are 1-indexed in DIMACS (not 0-indexed)
- **Niche knowledge**: Empty clauses (`0`) are valid and represent unsatisfiable clauses
- **Niche knowledge**: Duplicate literals in clauses are valid (idempotency)

**Step 2: Pre-process Clauses (Debugging/Reasoning Required)**
- **Debugging requirement**: Identify and handle duplicate clauses. If the same clause appears multiple times, you must reason about whether they are truly redundant or if they serve a purpose. This requires checking: (1) Are the clauses lexically identical (same literals in same order)? (2) Are they logically equivalent after accounting for duplicate literals within clauses? (3) Which clause index should be preferred in the minimal set? You must debug why certain clauses appear redundant when they're not, or vice versa.
- **Niche knowledge**: In CNF, duplicate clauses are logically redundant (the same clause twice is equivalent to the clause once). However, for the purpose of this task, you must preserve the original clause indices - do not remove duplicates during parsing, as they affect clause numbering. **CRITICAL NICHE KNOWLEDGE**: When comparing clauses for equality, you must normalize them first: remove duplicate literals within the clause, then sort the literals (or maintain original order - DIMACS doesn't require sorting, but for comparison purposes, you may need to handle both sorted and unsorted cases). However, be careful: clauses `1 2 0` and `2 1 0` are logically equivalent but may be considered different for indexing purposes unless you normalize. The task requires you to identify logical equivalence, not just lexical equality.
- **Debugging requirement**: Identify tautological clauses (clauses that are always true, e.g., `1 -1 0`). You must reason about whether tautological clauses can be removed while maintaining logical equivalence. **DEBUGGING CHALLENGE**: A clause like `1 -1 2 0` contains both `1` and `-1`, making it tautological. However, a clause like `1 2 -1 0` also contains both `1` and `-1` but may not be immediately obvious as tautological if you're checking sequentially. You must implement a robust tautology detection that checks if a clause contains both a variable and its negation, regardless of order. This requires careful debugging to catch all cases.
- **Niche knowledge**: Tautological clauses are always satisfied and can be removed without changing the formula's satisfiability, but they may affect minimal set selection. **BESPOKE RULE (EASY TO MISS)**: Even if all clauses in a formula are tautological, you must still output at least one clause index (the empty set is excluded). When selecting which tautological clause to keep, you must choose the one with the smallest index that appears in some minimal set. This requires reasoning about which tautological clauses are "needed" even though they're all always true - the answer is: you need at least one, and you should prefer the lexicographically smallest minimal set that includes at least one clause.

**Step 3: Check UNSAT Status (Must be First)**
- Before searching for minimal sets, check if the original formula is UNSAT
- Enumerate all 2^N truth assignments
- For each assignment, check if it satisfies all clauses
- **Failure point**: If no assignment satisfies the formula, it is UNSAT - output all clause indices (1 through num_clauses) and stop
- **Failure point**: If you skip this step and proceed to minimal set search, you may incorrectly reduce an UNSAT formula

**Step 4: Enumerate All Clause Subsets (Brute-Force Required)**
- Enumerate all possible subsets of clauses
- **CRITICAL**: Start from subsets of size 1 (k=1), NOT size 0
- **BESPOKE RULE (CRITICAL)**: The empty set (size 0) must NEVER be considered, even if it would be logically equivalent to the original formula. This rule is explicitly stated but easy to miss when implementing enumeration loops. **DEBUGGING REQUIREMENT**: You must verify that your enumeration loop starts at k=1, not k=0. A common mistake is to write `for k in range(num_clauses+1)` which includes k=0. You must write `for k in range(1, num_clauses+1)` or `for k in range(1, len(clauses)+1)`. This is a critical bug that's easy to introduce and hard to catch without careful debugging.
- For k from 1 to num_clauses:
  - Generate all combinations of k clauses using `itertools.combinations` or similar
  - **Failure point**: If you start from k=0, you will violate the empty set exclusion rule
  - **DEBUGGING REQUIREMENT**: When generating combinations, ensure you're using clause indices (0-based internally, but remember to convert to 1-based for output). Verify that `combinations(range(num_clauses), k)` generates the correct number of combinations: C(num_clauses, k). If you get fewer combinations than expected, debug your combination generation logic.
- **Failure point**: The enumeration space is 2^M - 1 (excluding empty set), which can be large. You must handle this efficiently but still enumerate all subsets.
- **NICHE KNOWLEDGE (CRITICAL)**: When enumerating subsets, the order in which you generate combinations matters for correctness, even though you'll sort them later. `itertools.combinations` generates combinations in lexicographic order of the input indices. For example, `combinations([0,1,2], 2)` yields `(0,1), (0,2), (1,2)` in that order. This is important because if you're checking subsets in a specific order and stopping early, you might miss the lexicographically smallest minimal set. You must enumerate ALL subsets before selecting the lexicographically smallest minimal set.

**Step 5: Check Logical Equivalence for Each Subset**
- For each subset from Step 4, check if it is logically equivalent to the original formula
- **Niche knowledge**: Two clause sets are logically equivalent if they have the same set of satisfying assignments. This requires checking all 2^N truth assignments.
- Enumerate all 2^N truth assignments
- For each assignment, check if both the original formula and the subset are satisfied by the same assignments
- **Failure point**: If you don't check all assignments, you may incorrectly determine equivalence
- **Debugging requirement**: If a subset is not equivalent, you must reason about why (which assignments differ) to understand the redundancy structure

**Step 6: Check Inclusion-Minimality for Equivalent Subsets**
- For each subset that is equivalent to the original (from Step 5), check if it is inclusion-minimal
- **Niche knowledge**: A clause set is inclusion-minimal if:
  - It is logically equivalent to the original, AND
  - Removing any single clause from it makes it non-equivalent
- For each clause in the subset:
  - Create a new subset with that clause removed
  - Check if this new subset is still equivalent to the original
  - **Failure point**: If any clause can be removed while maintaining equivalence, the set is NOT minimal
- **Debugging requirement**: You must identify which clauses are essential and which are redundant within each subset

**Step 7: Collect All Minimal Sets**
- Collect all subsets that passed both Step 5 (equivalence) and Step 6 (inclusion-minimality)
- **Failure point**: If you stop after finding the first minimal set, you may miss the lexicographically smallest one
- **Failure point**: If you don't check all subsets, you may miss some minimal sets

**Step 8: Find Lexicographically Smallest Minimal Set**
- Among all minimal sets found in Step 7, find the lexicographically smallest
- **Niche knowledge**: Lexicographic comparison works as follows:
  - Compare lists element by element from left to right
  - The first list is smaller if its first differing element is smaller
  - If one list is a prefix of the other, the shorter list is smaller
  - Example: [1] < [1,2] < [1,3] < [2,1] < [2,3]
- **BESPOKE RULE (CRITICAL - EASY TO MISS)**: When comparing minimal sets lexicographically, Python's built-in list comparison is lexicographic, BUT you must ensure the lists contain 1-based indices, not 0-based. If your internal representation uses 0-based indices (e.g., [0,1,2] for clauses 1,2,3), you must convert to 1-based ([1,2,3]) BEFORE lexicographic comparison. Comparing [0,1,2] vs [1,2,3] will give the wrong result because 0 < 1, but the correct comparison should be [1,2,3] vs [2,3,4] (if those are the actual clause indices). This is a critical bug that's easy to introduce.
- **DEBUGGING REQUIREMENT**: Before sorting minimal sets, verify that all sets contain 1-based indices. Add a debug check: `assert all(idx >= 1 for idx in minimal_set)`. If this fails, you forgot to convert from 0-based to 1-based. This is a common mistake that requires careful debugging to catch.
- **BESPOKE RULE (SUBTLE)**: When multiple minimal sets have the same first k elements but differ at position k+1, the set with the smaller (k+1)th element is lexicographically smaller. However, if one set is a proper prefix of another (e.g., [1,2] vs [1,2,3]), the shorter one is always smaller. Python's list comparison handles this correctly, but you must ensure you're comparing sorted lists. **CRITICAL**: The minimal sets must be sorted internally (ascending order) before lexicographic comparison. For example, if you have minimal sets [2,1,3] and [1,2,4], you must first sort them to [1,2,3] and [1,2,4], then compare. Comparing unsorted lists will give incorrect results.
- Sort all minimal sets lexicographically (Python's `sorted()` function does this correctly for lists of integers)
- Select the first (smallest) one
- **Failure point**: If you don't sort correctly, you may select the wrong minimal set
- **BESPOKE RULE (CRITICAL)**: When comparing minimal sets, you must compare the clause indices as they appear in the original file (1-based), not as array indices (0-based). This is easy to miss when implementing lexicographic comparison.

**Step 9: Convert to 1-Based Indices and Sort**
- The minimal set from Step 8 uses 0-based array indices internally
- **BESPOKE RULE (CRITICAL)**: Convert to 1-based indices for output (add 1 to each index)
- Sort the indices in ascending order
- **Failure point**: If you forget to convert to 1-based, all indices will be off by 1
- **Failure point**: If you don't sort, the output format is incorrect

**Step 10: Write Output**
- Write each clause index on its own line
- Ensure the output file is overwritten (not appended)
- **Failure point**: If the file is appended instead of overwritten, old results may remain
- **Failure point**: If you write in the wrong format (e.g., space-separated instead of one per line), the output is incorrect

### Algorithm Requirements (Detailed)

You must implement the following algorithms using only the standard library:

1. **SAT Checking**: To check if a CNF formula is satisfiable (SAT) or unsatisfiable (UNSAT), enumerate all possible truth assignments to the variables. For N variables, there are 2^N possible assignments. For each assignment, check if it satisfies all clauses. If at least one assignment satisfies the formula, it is SAT; otherwise, it is UNSAT.
   - **Niche knowledge**: A clause is satisfied if at least one literal in it is true under the assignment. A formula is satisfied if all clauses are satisfied.
   - **Debugging requirement**: If a formula is UNSAT, you must reason about why (which clauses conflict) to understand the structure.

2. **Logical Equivalence Checking**: Two clause sets are logically equivalent if they have the same set of satisfying assignments. To check equivalence, enumerate all 2^N truth assignments and verify that both clause sets are satisfied by exactly the same assignments.
   - **Niche knowledge**: Logical equivalence is a semantic property - two formulas are equivalent if they have the same truth table, not just if they have the same clauses.
   - **Debugging requirement**: If two sets are not equivalent, identify which assignments differ to understand why.

3. **Inclusion-Minimal Set Detection**: A clause set is inclusion-minimal if:
   - It is logically equivalent to the original formula, AND
   - Removing any single clause from it makes it non-equivalent to the original.
   - **Niche knowledge**: Inclusion-minimality is a set-theoretic property - a minimal set has no proper subset that is also equivalent.
   - To check if a clause subset is inclusion-minimal:
     - First verify it is equivalent to the original (using method #2).
     - Then, for each clause in the subset, check if removing that clause still yields a set equivalent to the original. If any clause can be removed, the set is not minimal.
   - **Debugging requirement**: For each clause in a minimal set, you must verify that removing it breaks equivalence - this requires reasoning about which clauses are essential.

4. **Finding All Minimal Sets**: To find all inclusion-minimal clause sets:
   - Enumerate all possible subsets of clauses (using combinations of clause indices).
   - **IMPORTANT**: Start from subsets of size 1 (k=1). The empty set (k=0) must NEVER be considered, even if it would be logically equivalent to the original formula.
   - For each subset of size k where k ranges from 1 to the total number of clauses, check if it is inclusion-minimal (using method #3).
   - Collect all minimal sets found.
   - **Example**: If you have 3 clauses, enumerate subsets of size 1: [1], [2], [3]; then size 2: [1,2], [1,3], [2,3]; then size 3: [1,2,3]. Do NOT consider the empty set [].
   - Note: When using `itertools.combinations` or similar, iterate over sizes starting from 1: `for k in range(1, num_clauses+1):`

5. **Lexicographic Ordering**: When multiple minimal sets exist, choose the lexicographically smallest one. Lexicographic comparison of two lists of clause indices works as follows:
   - Compare the lists element by element from left to right.
   - The first list is smaller if its first differing element is smaller.
   - If one list is a prefix of the other, the shorter list is smaller.
   - Example: [1,2] < [1,3] < [2,1] < [2,3]
   - In Python, you can sort lists of lists directly; Python's list comparison is lexicographic.
   - **BESPOKE RULE (CRITICAL)**: When comparing, ensure you're comparing 1-based clause indices, not 0-based array indices. This is easy to miss.

6. **UNSAT Handling**: Before searching for minimal sets, first check if the original formula is UNSAT (using method #1). If it is UNSAT, output all clause indices (1 through num_clauses) without any removal.

**Implementation Notes**:
- Use brute-force enumeration of truth assignments (2^N assignments for N variables).
- Use brute-force enumeration of clause subsets (2^M subsets for M clauses, excluding empty set).
- **Critical**: When enumerating clause subsets, start from size 1, not size 0. The empty set must never be considered, regardless of logical equivalence.
- This approach is feasible for the test cases, which use small formulas.
- The `itertools` module (product, combinations) is useful for enumeration.
- **Important**: Your solution must always produce output. If you find no minimal sets (which should not happen if implemented correctly), output at least one clause index. The output file must contain at least one line with a clause index.

### Constraints

- No external SAT libraries are allowed; you must implement your own solver / search using only the standard library.
- No external command-line SAT solvers are allowed (e.g., minisat, glucose, z3 CLI, etc.). Do not install or invoke external SAT solver binaries.
- Find the lexicographically smallest minimal clause set (clause-index subset).
- **Empty clause sets are excluded**: Even if an empty set would be logically equivalent to the original formula (e.g., for formulas containing only tautological clauses), you must output at least one clause index. When enumerating minimal sets, start from subsets of size 1 and never consider the empty set (size 0).
- If the formula is UNSAT, output all clause indices.
- Output must be deterministic (same input always produces same output).

### Output Format Details

- Output one clause index per line, sorted in ascending order.
- If the formula is UNSAT, output all clause indices from 1 to num_clauses, one per line.
- If the formula is SAT, output the lexicographically smallest minimal clause set, with indices sorted ascending.
- Do not output empty lines or extra whitespace.
- Each line should contain exactly one integer (the clause index).
- **BESPOKE RULE (CRITICAL)**: Clause indices must be 1-based (matching DIMACS standard), not 0-based. This is explicitly stated but easy to miss when converting from internal array indices to output.

### Dependencies

- Runtime: Python 3.11+ standard library (already provided by base image).
- No third-party Python packages are required.

The harness will invoke `bash solution.sh --input input.cnf --out /app/result.txt` multiple times with different CNF formulas. Make sure your implementation correctly handles all cases and produces deterministic output.
