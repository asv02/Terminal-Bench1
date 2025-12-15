# Happens-Before Data Race Finder (Vector Clocks)

Goal: given an execution trace of a concurrent program, report the unique earliest HB data race (canonical choice). Deterministic behavior is mandatory; no randomness or reliance on unspecified ordering is allowed.

## Input
- You receive a Python list of raw strings (may include comments).
- Implement `/app/solution.py` with:
```py
def solve(lines: list[str]) -> str:
    ...
```
- Event formats (tokens separated by single ASCII spaces, no tabs, no extra whitespace):
  - Thread lifecycle: `T <tid> START <child_tid>`, `T <tid> JOIN <child_tid>`
  - Locking (re-entrant per thread): `L <tid> ACQ <lock>`, `L <tid> REL <lock>`
  - Shared memory: `R <tid> <var>`, `W <tid> <var>`
- Identifiers: `<tid>`/`<child_tid>` are non-negative ints; `<lock>` and `<var>` match `[A-Za-z0-9_]+`.
- Lines starting with `#` are comments and ignored (do not consume event indices and cannot be invalid).
- Any non-comment line that fails all formats is invalid (triggers cutoff below).

## Semantics (HB and validity)
- Per-thread order: total within a thread; every event of a thread must advance that thread’s clock.
- Locks: `ACQ` increments re-entrance count if already held by same thread. Only when a `REL` drops the count to 0 is the lock released; that `REL` HB the *next* `ACQ` by another thread (not by the holder re-acquiring). `REL` while count is 0 or while not owning the lock is invalid. Nested re-entrant acquisitions do not create extra HB edges; only the transition from held→free→next-holder does.
- Fork: `T t START c` HB the first valid event of child `c`. Starting an already-started `c` is invalid. A child with no events still “exists” and can be joined if started.
- Join: The last valid event of child `c` HB `T t JOIN c`. If child `c` has any events remaining after the current point in the valid prefix (i.e., the child has not ended yet), the JOIN is invalid. Joining a never-started child is invalid.
- Thread end: a thread is considered ended when it has no further events in the valid prefix (after the cutoff logic). JOIN validity depends on this notion of “future events”.

## Validity cutoff (strict)
- Process lines top to bottom, skipping comments.
- On the first invalid event, stop immediately; exclude that invalid event and all following lines from the trace. Only the prefix before the first invalid event is “valid”.
- Invalid events include (but are not limited to): `REL` on an unheld lock or with underflow; `JOIN` of a never-started child; `JOIN` while the child still has future events in the would-be prefix; `START` of an already-started child id; any non-comment line that fails the exact formats. No recovery after cutoff.

## Data race
- Pair `(e_i, e_j)` on the same `<var>`, at least one is `W`, from different threads, and neither HB the other (they are concurrent under HB on the valid prefix).

## Output (canonical)
- No race in valid prefix: return `"NONE"`.
- Race: return `"<i> <j> <var>"` where `i < j` are 1-based indices over non-comment events of the valid prefix.
- Canonical selection over all races in the valid prefix: smallest `j`; then smallest `i`; then lexicographically smallest `<var>`. This tie-break order is strict.

## Constraints / notes
- Up to 200,000 non-comment lines; up to 10,000 threads.
- Efficiency required: use vector clocks or equivalent HB; naive `O(n^2)` will time out.
- Standard library only. Deterministic behavior required; output must match exactly (spacing included).
- Thread “end” is defined by the valid prefix; used for JOIN validity and cutoff decisions.
- Vector clocks (or equivalent HB) must merge correctly on lock handoff, START/ JOIN edges, and per-thread steps; missing merges will alter race ordering and fail canonical selection.
- Re-entrance counts must be tracked per-thread per-lock; incorrect underflow/ownership detection invalidates the prefix and changes the race set.
- The cutoff can remove suffix synchronization edges; implementations that continue processing after an invalid event will produce spurious races and fail.