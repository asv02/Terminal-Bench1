# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal


"""
Tests for sqlite-wal-counter-racefix.

These tests verify correctness under multi-process contention and durability.
They intentionally use multiple processes to expose lost updates and locking bugs.
"""

import os
import sys
import sqlite3
import time
from multiprocessing import Process, Queue
from pathlib import Path

# Ensure /app is in Python path so we can import the app package
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

DB_PATH = Path("/app/state/counters.db")


def _worker_inc(key: str, n: int, delta: int, q: Queue):
    """Worker performs n increments and reports any exception as a string."""
    try:
        from app import counter_service as cs  # must exist

        for _ in range(n):
            cs.increment(key, delta)
        q.put(None)
    except Exception as e:
        q.put(repr(e))


def _worker_crashy(key: str, n: int, q: Queue):
    """
    Worker that increments and then exits abruptly.
    This simulates a process crash during contention.
    """
    from app import counter_service as cs

    for i in range(n):
        cs.increment(key, 1)
        if i == n // 2:
            os._exit(137)  # abrupt exit (no finally)


def test_db_exists_and_schema():
    """Database file must exist and contain required counters table schema."""
    assert DB_PATH.exists(), "Expected /app/state/counters.db to exist"
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='counters'"
        ).fetchall()
        assert rows, "Missing counters table"
        cols = con.execute("PRAGMA table_info(counters)").fetchall()
        colnames = [c[1] for c in cols]
        assert colnames == ["key", "value"], f"Unexpected columns: {colnames}"
    finally:
        con.close()


def test_counters_stored_in_sqlite():
    """
    Verify that counter values are actually stored in SQLite database.
    This prevents cheating by using files/multiprocessing instead of SQLite.
    """
    from app import counter_service as cs

    cs.reset_all()

    # Perform operations via the API
    cs.increment("verify", 5)
    cs.increment("verify", 3)
    cs.increment("other", 10)

    # Verify via API
    assert cs.get("verify") == 8
    assert cs.get("other") == 10

    # Directly query SQLite to ensure values are actually stored there
    con = sqlite3.connect(DB_PATH)
    try:
        rows = con.execute(
            "SELECT key, value FROM counters ORDER BY key"
        ).fetchall()
        
        # Convert to dict for easier checking
        db_values = {row[0]: row[1] for row in rows}
        
        # Verify the values match what's in the database
        assert db_values["verify"] == 8, f"Expected verify=8 in DB, got {db_values.get('verify')}"
        assert db_values["other"] == 10, f"Expected other=10 in DB, got {db_values.get('other')}"
        
        # Verify API and DB are in sync
        assert cs.get("verify") == db_values["verify"], "API and DB values must match"
        assert cs.get("other") == db_values["other"], "API and DB values must match"
    finally:
        con.close()


def test_increment_persists_immediately():
    """
    Anti-cheating: increment() must write to SQLite immediately, not defer until get().
    This test verifies that after increment() returns, the value is immediately
    readable from SQLite in a separate connection without calling get().
    """
    from app import counter_service as cs

    cs.reset_all()

    # Call increment() but do NOT call get() yet
    cs.increment("immediate", 42)
    cs.increment("immediate", 8)
    cs.increment("another", 100)

    # Open a fresh SQLite connection and read directly (bypassing the API)
    # This ensures increment() actually wrote to SQLite, not just cached in memory
    con = sqlite3.connect(DB_PATH)
    try:
        # Use a separate connection to ensure we're not reading from a cache
        rows = con.execute(
            "SELECT key, value FROM counters ORDER BY key"
        ).fetchall()
        
        db_values = {row[0]: row[1] for row in rows}
        
        # Verify values are in the database immediately after increment()
        assert "immediate" in db_values, "increment() must write to SQLite immediately"
        assert db_values["immediate"] == 50, f"Expected immediate=50, got {db_values.get('immediate')}"
        assert "another" in db_values, "increment() must write to SQLite immediately"
        assert db_values["another"] == 100, f"Expected another=100, got {db_values.get('another')}"
    finally:
        con.close()


def test_cross_process_persistence():
    """
    Anti-cheating: Values written by increment() must be immediately visible
    to other processes reading directly from SQLite (not through the API).
    This prevents cheating by deferring persistence until get() is called.
    """
    from app import counter_service as cs

    cs.reset_all()

    def writer_process(q: Queue):
        """Writer process that calls increment() and signals completion."""
        try:
            from app import counter_service as cs_writer
            cs_writer.increment("crossproc", 77)
            cs_writer.increment("crossproc", 23)
            q.put("done")
        except Exception as e:
            q.put(f"error: {repr(e)}")

    def reader_process(q: Queue):
        """Reader process that reads directly from SQLite without using the API."""
        # Wait a bit for writer to complete
        time.sleep(0.1)
        try:
            # Read directly from SQLite, bypassing the counter_service API
            con = sqlite3.connect(DB_PATH)
            try:
                row = con.execute(
                    "SELECT value FROM counters WHERE key = ?", ("crossproc",)
                ).fetchone()
                if row:
                    q.put(f"value:{row[0]}")
                else:
                    q.put("not_found")
            finally:
                con.close()
        except Exception as e:
            q.put(f"error: {repr(e)}")

    # Start writer process
    writer_q = Queue()
    writer_p = Process(target=writer_process, args=(writer_q,))
    writer_p.start()

    # Wait for writer to signal completion
    writer_result = writer_q.get(timeout=5)
    assert writer_result == "done", f"Writer failed: {writer_result}"

    # Start reader process that reads directly from SQLite
    reader_q = Queue()
    reader_p = Process(target=reader_process, args=(reader_q,))
    reader_p.start()

    # Get result from reader
    reader_result = reader_q.get(timeout=5)
    assert reader_result.startswith("value:"), f"Reader should find value, got: {reader_result}"
    value = int(reader_result.split(":")[1])
    assert value == 100, f"Expected crossproc=100 in DB, got {value}"

    # Clean up
    writer_p.join(timeout=5)
    reader_p.join(timeout=5)
    assert writer_p.exitcode == 0, "Writer process should exit cleanly"
    assert reader_p.exitcode == 0, "Reader process should exit cleanly"


def test_atomic_no_lost_updates_under_multiprocess():
    """Concurrent increments across processes must not lose updates."""
    from app import counter_service as cs

    cs.reset_all()

    procs = []
    q = Queue()
    # 8 processes * 500 increments = 4000 total increments
    for _ in range(8):
        p = Process(target=_worker_inc, args=("hits", 500, 1, q))
        p.start()
        procs.append(p)

    errs = []
    for _ in procs:
        err = q.get(timeout=20)
        if err:
            errs.append(err)

    for p in procs:
        p.join(timeout=10)
        assert p.exitcode == 0, f"worker exitcode={p.exitcode}"

    assert not errs, f"worker errors: {errs}"
    assert cs.get("hits") == 4000


def test_negative_clamp_to_zero():
    """If decrement would go negative, value must clamp to 0."""
    from app import counter_service as cs

    cs.reset_all()
    cs.increment("k", 3)
    cs.increment("k", -10)  # should clamp
    assert cs.get("k") == 0


def test_unknown_key_returns_zero_no_throw():
    """get() must return 0 for unknown keys and never throw."""
    from app import counter_service as cs

    cs.reset_all()
    assert cs.get("missing") == 0


def test_durability_after_crashy_worker():
    """
    Abrupt worker exit must not corrupt DB and must not lose completed increments.
    We accept that increments after the crash point do not occur, but increments
    performed before crash must persist.
    """
    from app import counter_service as cs

    cs.reset_all()

    q = Queue()
    p = Process(target=_worker_crashy, args=("crash", 200, q))
    p.start()
    p.join(timeout=10)
    assert p.exitcode != 0, "crashy worker should exit non-zero"

    # DB must still be readable and count must be >= 100 (halfway point),
    # and <= 200 (cannot exceed attempted increments).
    val = cs.get("crash")
    assert 100 <= val <= 200


def test_performance_budget():
    """Total 5000 increments across 8 processes must finish reasonably quickly (<5s)."""
    from app import counter_service as cs

    cs.reset_all()

    t0 = time.time()
    q = Queue()
    procs = []
    # 8*625 = 5000
    for _ in range(8):
        p = Process(target=_worker_inc, args=("perf", 625, 1, q))
        p.start()
        procs.append(p)

    for _ in procs:
        err = q.get(timeout=30)
        assert err is None, f"worker error: {err}"

    for p in procs:
        p.join(timeout=20)
        assert p.exitcode == 0

    dt = time.time() - t0
    assert dt < 5.0, f"too slow: {dt:.3f}s"
    assert cs.get("perf") == 5000
