# Linearizability Violation – Minimal Canonical Witness (Hard)

You are given a concurrent execution history of a **single shared register**
supporting atomic `READ` and `WRITE` operations.

Your task is to detect whether the history is **linearizable**.
If it is not, you must extract the **canonical minimal violation witness**.

This is a classic research-grade debugging problem.
Greedy checks, local reasoning, or partial ordering mistakes will fail.

---

## Input

Implement:

```python
def solve(lines: list[str]) -> str:
```

Place your implementation in `solution.py` at the repository root (the tests load `/app/solution.py`) and expose the `solve` function with the signature shown above.


Each non-comment line is an event:

<time> <tid> <op> <value>


<time>: integer timestamp (monotonic but not contiguous)

<tid>: thread id (non-negative integer)

<op>: READ or WRITE

<value>:

For WRITE: the value written

For READ: the value observed

Lines starting with # are comments and must be ignored.

Register Semantics

Initial value of the register is 0

Writes overwrite previous value

Reads must observe the value of the most recent linearized write

Each operation is atomic but overlaps in time

Real-time order must be respected:

If op A ends before op B begins, A must appear before B in the linearization

History Model

Each operation consists of:

invocation at its timestamp

response at the same timestamp (atomic, but ordering is partial)

Operations from different threads at the same timestamp are concurrent.

Invalid History Cutoff Rule (CRITICAL)

Stop processing immediately if any invalid event occurs.
Ignore that event and everything after it.

Invalid events:

Malformed line

READ observing a value that was never written

Negative values

After cutoff, decide linearizability using only the prefix processed so far. A cutoff that removes later synchronization edges can mask potential races; continuing past an invalid event will be considered incorrect.

Linearizability Definition

A history is linearizable if there exists a total order of operations such that:

The order respects real-time precedence

Each READ returns the value of the most recent WRITE before it

Violation Witness

If the history is NOT linearizable, output:

R=<rid>@<tR> <- W=<wid>@<tW>


Meaning:

READ by thread rid at time tR

Observed a value written by WRITE of thread wid at time tW

But no valid linearization can justify this observation

Canonical Witness Selection (EXTREMELY IMPORTANT)

If multiple violations exist:

Choose the READ with the earliest timestamp

If tie, choose the READ with the smallest thread id

For that chosen READ, you must now choose **one WRITE** to report as the witness source:

- The **general rule** is: choose the **latest conflicting WRITE** – the most recent WRITE whose existence makes the observed value at that READ impossible to justify in any linearization that respects real-time order. This WRITE may differ from the value returned by the READ (e.g., a newer WRITE of a different value that must precede the READ in any linearization), or it may even write the **same value** but still conflict due to ordering constraints.

- **Special real‑time “stale read” case (observed‑write reported):** sometimes respecting real-time order forces a later WRITE to remain *after* an earlier READ, so that a subsequent READ that returns the earlier value becomes impossible, even though that later WRITE exists. In this specific shape, you must report the **stale WRITE whose value was actually returned by the violating READ**, not the later WRITE that blocks it.

Example (real-time order forces a stale read; we report the observed write):

0 1 WRITE 1
1 2 READ 1
2 3 WRITE 2
3 4 READ 1

Here any linearization respecting real-time must put `WRITE 2` before the second `READ 1`, so that READ cannot keep seeing the old value `1`. The canonical witness is therefore the stale observed write:

Witness: `R=4@3 <- W=1@0`

Example (latest conflicting write uses a different value and is reported):

0 1 WRITE 1
1 2 WRITE 2
2 3 READ 1

Here the READ observes value `1` from the first write, but the presence of the later WRITE of `2` makes that observation impossible in any valid linearization. The witness is the **latest conflicting write** (not the observed one):

Witness: `R=3@2 <- W=2@1`

Example (latest conflicting write reuses the same value but is still reported):

0 1 WRITE 1
1 2 WRITE 1
2 3 READ 1
3 4 READ 0

The history is not linearizable because of the final READ of `0`. The latest conflicting WRITE is `W=2@1` (which wrote `1`), even though the violating READ returns `0`. The canonical witness is:

Witness: `R=4@3 <- W=2@1`

Output exactly one witness

Output

If the history is linearizable:

NONE


Otherwise, output exactly one line as described above.

Performance and robustness requirements

- Your algorithm must handle histories with at least 1,000 events (the tests include such a case) without exceeding recursion limits or timing out. Exponential-time search that works only for tiny inputs is insufficient.
- Avoid unbounded recursion for reachability/ordering checks; use iterative approaches or explicitly managed stacks/queues to remain stack-safe.
- Aim for polynomial-time behavior (e.g., O(n^2) or better) over the number of events; naive factorial/branch-and-bound over all linearizations will fail.
