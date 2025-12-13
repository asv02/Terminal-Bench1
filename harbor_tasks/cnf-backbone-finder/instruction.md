# CNF Backbone Finder

Given a Boolean CNF formula in DIMACS format, determine if it is satisfiable. If unsatisfiable, output `"UNSAT"`. If satisfiable, compute and output the backbone of the formula.

The backbone of a satisfiable CNF formula consists of all literals that have the same truth value in every satisfying assignment.

## Requirements

- Script location: `/app/find_backbone.py`
- CLI format: `python /app/find_backbone.py --input <file> --out <file>`
- Empty clauses (clause with only `0`) make the formula unsatisfiable
- The solution must correctly determine satisfiability for all provided inputs
- The solution must correctly identify all backbone literals
- Output must be deterministic (same input always produces same output)
- Solution must complete within the timeout limit

## Output Format

- **Unsatisfiable**: Write exactly `"UNSAT"` followed by exactly one newline (`\n`)
- **Satisfiable with backbone**: Write one literal per line, sorted by absolute value (ascending). Each line contains exactly one integer. No empty lines or trailing spaces.
- **Satisfiable without backbone**: Output file must be empty (zero bytes, no content)
- Variables that never appear in any clause must not appear in the output
- Output format must be exact - byte-level precision required
