# Incremental Log Compaction Canonicalizer (Hard)

You are given an **append-only event log** describing mutations to a key–value
store. The log may contain redundant, canceling, reordered, or partially invalid
events.

Your task is to validate the log and produce the **unique canonical compacted log**
that preserves final state **and** satisfies strict minimality and ordering rules.

This is a debugging + canonicalization task. Greedy or "final-state-only" solutions
will fail.

---

## Input

A single file `/app/input.log`.

Each line is one event:

<timestamp> <op> <key> [value]

- `timestamp` is a non-negative integer (not guaranteed sorted)

- `op` is one of:

  - `SET key value`

  - `DEL key`

- `key` and `value` are ASCII strings without spaces

Example:

3 SET a 10

1 SET a 5

2 DEL a

4 SET b x

---

## Semantics

Events apply in **timestamp order**, not input order.

If two events have the same timestamp, they apply in **input order**.

Rules:

- `SET k v` assigns value `v` to `k`

- `DEL k` removes key `k` if present (no-op otherwise)

---

## Validity Rules

The input log is **VALID** if:

1. All lines parse correctly

2. Timestamps are integers ≥ 0

3. Ops are valid (`SET`, `DEL`)

4. No event references an empty key

5. At least one event exists

If invalid, you must still output the **canonical compacted log** for the valid
prefix up to (but not including) the first invalid line.

---

## Canonical Compacted Log Definition

The canonical compacted log must:

### A. Preserve Final State

Applying the compacted log (from empty store) must result in the **same final key–value state**
as applying the original valid portion of the log.

### B. Be Minimal

The log is minimal if the following rules are applied:

1. No key has more than **one SET** event in the output

2. No `DEL` exists for a key that is never SET
   - **Example**: If input contains `1 DEL x` but `x` is never SET in the valid portion, this DEL must not appear in the output
   - **Example**: If input contains `1 DEL x` and `2 SET x 5`, then `x` was SET, so the DEL may appear if needed for final state

3. **A `SET` immediately followed (in time) by `DEL` for the same key is removed entirely**
   - **Definition**: "Immediately followed" means:
     1. When events are sorted by timestamp, the DEL has timestamp exactly one greater than the SET (ts_DEL = ts_SET + 1)
     2. AND no other events for that same key have timestamps between ts_SET and ts_DEL (i.e., no event for that key exists with timestamp t where ts_SET < t < ts_DEL)
   - **Critical**: This rule applies to ALL immediate SET-DEL pairs. When determining which events to keep for a key, you must check for and remove ALL immediate SET-DEL pairs. If a key has only immediate SET-DEL pairs (and they are all removed), the key does not appear in the output at all.
   - **Example**: If input has `1 SET x 10` followed by `2 DEL x` (consecutive timestamps with no other events for `x` in between), both are removed. Since this is the only event sequence for `x`, the key `x` does not appear in the output at all.
   - **Example**: If input has `1 SET x 10`, `2 DEL x`, `3 SET x 20`:
     - SET at 1 and DEL at 2 are immediate (consecutive timestamps, no other events for `x` between them), so both are removed
     - After removing the immediate pair, only SET at 3 remains, which is needed for the final state (x = 20)
     - Output contains only `0 SET x 20` (timestamp reassigned to 0)
   - **Counter-example**: If input has `1 SET x 10`, `2 SET x 20`, `3 DEL x`, then:
     - SET at 1 and DEL at 3 are NOT consecutive timestamps (3 ≠ 1 + 1), so they are not an immediate pair
     - SET at 2 and DEL at 3 ARE consecutive timestamps (3 = 2 + 1) with no events for `x` between them, so this is an immediate pair and both are removed
     - After removing the immediate pair (SET at 2, DEL at 3), the remaining events for `x` are: SET at 1
     - The final state (computed from ALL original events) has `x` deleted (not in final state)
     - Since the key is not in the final state and we've removed the immediate pair, no events are needed: the key `x` does not appear in the output

4. If a key is SET multiple times (after removing immediate pairs), only the **last effective SET** remains

**Algorithm for determining minimal events for each key:**

For each key, follow these steps:

1. **Group all events for this key** and sort them by timestamp (then input order for ties)

2. **Identify and mark all immediate SET-DEL pairs for removal:**
   - For each SET event at timestamp `t`, check if there's a DEL event at timestamp `t+1` for the same key
   - If yes, and there are no other events for this key between `t` and `t+1`, mark both the SET and DEL for removal
   - Repeat this check for all SET events (there may be multiple immediate pairs)

3. **Remove all marked immediate pairs** from consideration

4. **Determine final state** from ALL original events (before removal)

5. **Select events to keep:**
   - If the key is in the final state: keep only the last SET (from remaining events after step 3) that sets the key to its final value
   - If the key is NOT in the final state:
     - If the key was never SET (in original events), keep nothing
     - If the key was SET but deleted, and all SET-DEL pairs were immediate (and removed), keep nothing
     - Otherwise, if there are non-immediate events needed, keep them (but typically if key is not in final state and immediate pairs are removed, nothing remains)

6. **Result**: If no events are kept for a key, the key does not appear in the output at all

### C. Canonical Ordering (CRITICAL)

Events must be ordered using the following **hierarchical rules**, applied in order:

1. **Primary**: increasing timestamp

2. **Secondary**: `DEL` before `SET` **if timestamps are equal**
   - This rule **overrides** input order when timestamps are equal
   - Example: If input has `5 SET a 10` followed by `5 DEL a`, the output must have `DEL a` before `SET a` at timestamp 5

3. **Tertiary**: ASCII order of key (applied when timestamps and operation types are equal)

4. **Quaternary**: original input order (stable tie-break, applied only when timestamps, operation types, and keys are all equal)

**Important**: These rules are applied hierarchically. The secondary rule takes precedence over the quaternary rule. The quaternary rule only applies when all previous rules result in a tie (same timestamp, same operation type, same key).

### D. Canonical Timestamp Assignment (BESPOKE RULE)

Timestamps in the output **must be reassigned**:

- For each remaining event, assign timestamps starting from `0`

- Preserve relative order only

- This rule is extremely easy to miss and is explicitly tested

### E. Canonical Formatting

- One event per line

- Exactly one space between tokens

- Each line must end with a newline character (`\n`) - this includes ALL lines, including the last line in the file (following Unix text file conventions)

- No extra whitespace

---

## Output

**You MUST create the file `/app/output.log`** and write the canonical compacted log to it.

**Important**: The output file MUST be created even if there are no events to output (in which case it should be empty, but still created).

**⚠️ CRITICAL FORMATTING REQUIREMENT ⚠️**

**You MUST include a newline character (`\n`) at the end of EVERY line you write, including the last line.** This is a Unix text file requirement and is strictly enforced by the tests. Common mistakes:
- Writing `f.write("0 SET a 10")` without `\n` → **WRONG**
- Writing `print("0 SET a 10", end="")` → **WRONG**  
- Writing `echo -n "0 SET a 10"` → **WRONG**

**Correct examples:**
- Python: `f.write(f"{timestamp} {op} {key} {value}\n")` (note the `\n` at the end)
- Python: `print(f"{timestamp} {op} {key} {value}", file=f)` (print automatically adds newline)
- Shell: `echo "0 SET a 10" >> /app/output.log` (echo automatically adds newline)
- Other languages: ensure each line written ends with `\n`, including the final line

The output file must be a proper Unix text file where every line (including the last) terminates with a newline character.

**Output content rules:**
- If input was fully valid: compact the entire log
- If input becomes invalid at line N: compact only lines `[1..N-1]` (the valid prefix)
- If there are no valid events: create an empty file (but still create `/app/output.log`)
