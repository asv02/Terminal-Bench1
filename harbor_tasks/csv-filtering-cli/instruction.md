Create an executable Python script at /app/csvfilter.py.

This script must implement a CLI tool that filters CSV rows using a rule
specification provided as a JSON or YAML file.

All validation is performed strictly via file-content and CLI behavior.
No networking, no external libraries, and no internet access are allowed.

──────────────────────────────────────────────────────────────────────────────
REQUIREMENTS
──────────────────────────────────────────────────────────────────────────────

1. CLI BEHAVIOR
  The tool must accept the following arguments (all must be absolute paths):
    --input /app/input.csv
    --spec  /app/spec.json
    --out-csv /app/output/matches.csv
    --out-summary /app/output/summary.json

  • --input and --spec are REQUIRED.  
  • --out-csv defaults to:      /app/output/matches.csv  
  • --out-summary defaults to:  /app/output/summary.json  
  • All paths MUST be absolute (beginning with /app/).

  Exit codes:
    0 → all rows accepted  
    2 → one or more rows rejected  
    3 → usage errors, bad arguments, unreadable input/spec, malformed spec

2. SPEC PARSING
  The spec file must support:
    • JSON (full JSON)  
    • A minimal YAML subset (indentation-based maps/lists; no external libs)

  Behavior on YAML:
    • Only a simple mapping/list/scalar subset is required.
    • If JSON parsing fails, attempt YAML parse.

  If parsing fails ⇒ exit code 3.

3. CSV READING REQUIREMENTS
  The script must:
    • Read CSV using UTF-8 or UTF-8-SIG.  
    • Properly trim newline and whitespace around values.  
    • Support extra columns not listed in the header.  
    • Preserve header order exactly as provided in the input CSV.  
    • Handle missing columns safely (treat missing entries as empty strings).  

4. RULE ENGINE
  The spec describes a tree of rules using:
    AND / OR / NOT operators  
    regex, number-range, and date-range leaf rules

  LEAF RULES:

  type: regex
    keys:
      id: string (required)
      column: string (required)
      pattern: regex (required)
    Behavior:
      Must test regex search on the field value.

  type: number
    keys:
      id: string
      column: string
      min: numeric (optional)
      max: numeric (optional)
    Behavior:
      Convert field to float; fail if conversion fails.

  type: date
    keys:
      id: string
      column: string
      fmt: datetime format string (required)
      from: date string in same fmt (optional)
      to:   date string in same fmt (optional)
    Behavior:
      Parse using the provided fmt. Fail if parsing fails.

  LOGICAL OPERATORS:
    AND  → all children rules must be true  
    OR   → at least one child must be true  
    NOT  → invert the result of exactly one child

  Failure attribution rules:
    • Every LEAF rule has an "id".  
    • A leaf contributes to per_rule_rejects only when that leaf itself
      evaluates to False.  
    • For OR: only if the *entire OR* evaluates False do we aggregate the
      failing leaf IDs from all children.  
    • For NOT: if NOT makes the row fail, DO NOT attribute any leaf failures.

5. REQUIRED OUTPUTS
  The script must output:

  (A) CSV:
      Write only accepted rows to --out-csv.
      Must include header (preserved exactly as input).
      Order of rows must match original input order.

  (B) JSON summary at --out-summary containing exactly:
      {
        "total_rows": <int>,
        "accepted": <int>,
        "rejected": <int>,
        "acceptance_rate": <float>,    # accepted/total between 0 and 1
        "per_rule_rejects": { "<id>": <int>, ... }
      }

      IMPORTANT CLARIFICATIONS (per reviewer request):

      • The per_rule_rejects dictionary MUST contain **every leaf rule ID**
        present anywhere in the spec tree.

      • All leaf rule IDs MUST be present, even when their reject count = 0.

      • The *initial* state of per_rule_rejects must therefore be:
              { <leaf_id>: 0 for every leaf in the spec }

6. ERROR HANDLING
  The script MUST return exit code 3 on any of these:
    • Missing required CLI arguments  
    • Non-absolute paths  
    • Input CSV does not exist  
    • Spec file does not exist  
    • JSON/YAML parse errors  
    • Invalid spec structure  
    • Unreadable CSV  

7. FILE CREATION REQUIREMENTS
  The /app directory must contain:
    • /app/csvfilter.py       (executable)
    • No other required files.

  The script must create directories for output paths automatically if needed.

──────────────────────────────────────────────────────────────────────────────
SUMMARY OF REQUIRED FORMATS
──────────────────────────────────────────────────────────────────────────────

• Spec: JSON or tiny-YAML defining AND/OR/NOT plus leaf rules
• Per-rule-rejects: all leaf IDs, even zeros
• Output CSV: preserves header order
• Acceptance rate = accepted/total
• Exit codes: 0, 2, 3 as defined
• Only absolute paths allowed in all CLI usage
