# Fix Concurrency Bug: SQLite WAL Counter Service

A small counter service in `/app/app/counter_service.py` (as part of the `app` Python package) is used by multiple worker
processes to record event counts into a SQLite database at `/app/state/counters.db`.

The current implementation is **incorrect under concurrency** and causes:
- lost updates (final count smaller than expected)
- occasional `database is locked` failures
- incorrect behavior when a worker crashes mid-update

Your task is to fix the bug(s) in the application so that it behaves correctly
and deterministically under heavy parallel access.

## What you must do

1. **Package Structure**: The code must be located at `/app/app/counter_service.py` as part of a Python package:
   - Create `/app/app/` directory if needed
   - Place `counter_service.py` in `/app/app/`
   - Create `/app/app/__init__.py` if needed (can be empty or re-export the module)
   - Tests will import using `from app import counter_service`

2. **Database Initialization**: The database file and schema must be initialized:
   - Database file: `/app/state/counters.db` (create the `/app/state/` directory if needed)
   - Table schema: `counters(key TEXT PRIMARY KEY, value INTEGER NOT NULL)`
   - The database file and table must exist before tests run (tests verify this)

3. Fix `/app/app/counter_service.py` so that increments are **atomic** and **durable**.
   Do not change the public interface:
   - `increment(key: str, delta: int = 1) -> None`
   - `get(key: str) -> int`
   - `reset_all() -> None`

4. The service must work with **multiple OS processes** calling `increment()` concurrently.

5. Must tolerate transient contention:
   - Implement bounded retry with jitter-free deterministic backoff.
   - Do not sleep longer than 50ms per retry.
   - Backoff must be deterministic: use fixed sleep intervals, no randomness or jitter.
   - The same contention pattern must produce the same retry behavior.

6. Correctness requirements:
   - No lost updates: final value must equal sum of all successful increments.
   - No negative values: if an increment would make value negative, clamp to 0.
   - `get()` must never throw and must return 0 for unknown keys.
   - Database must remain readable and consistent even if a worker process crashes mid-update.
   - **Counter values must be stored in the SQLite database immediately**: The `increment()` method must write to SQLite and commit the transaction before returning. Values must be immediately readable from SQLite by other processes, even without calling `get()`. Tests verify that values written via `increment()` are immediately visible in the database when queried directly from SQLite.

7. Determinism:
   - No randomness.
   - No time-based logic that changes results.

8. Performance:
   - Must handle 5,000 total increments across 8 processes in < 5 seconds.

## Output / Success Criteria

There is no output file to write.
Success is defined as: **all pytest tests in `/tests/test_outputs.py` pass**.

## Constraints

- You may edit only `/app/app/counter_service.py` (and create necessary package structure).
- You may create the database file and schema as needed (in `/app/state/counters.db`).
- Python standard library only.
- Do not add new files beyond the package structure and database initialization.
- Do not require root privileges.

