#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.


set -euo pipefail
cd /app

# Ensure package layout and DB directory exist.
mkdir -p /app/app
mkdir -p /app/state

# Apply fix: use atomic UPSERT with proper transaction boundaries,
# enable WAL, and bounded deterministic retry.
# (This is written as a here-doc overwrite for determinism.)
cat > /app/app/counter_service.py <<'PY'
import sqlite3
import time
from pathlib import Path

DB_PATH = Path("/app/state/counters.db")

# Deterministic retry settings (no randomness).
_MAX_RETRIES = 200  # Increased for heavy contention and EXCLUSIVE locks
_BASE_SLEEP = 0.001  # 1ms - very fast retries for transient locks
_MAX_SLEEP = 0.01   # 10ms - keep sleeps short
_TOTAL_BUDGET = 2.0 # Increased to 2s to handle heavy contention


def _connect():
    # timeout=0 so we handle busy ourselves deterministically
    con = sqlite3.connect(DB_PATH, timeout=0.0, isolation_level=None)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    con.execute("PRAGMA foreign_keys=ON")
    return con


def reset_all() -> None:
    con = _connect()
    try:
        con.execute("BEGIN IMMEDIATE")
        con.execute("DELETE FROM counters")
        con.execute("COMMIT")
    except Exception:
        try:
            con.execute("ROLLBACK")
        except Exception:
            pass
        raise
    finally:
        con.close()


def get(key: str) -> int:
    con = _connect()
    try:
        row = con.execute("SELECT value FROM counters WHERE key = ?", (key,)).fetchone()
        if not row:
            return 0
        v = row[0]
        return int(v) if v is not None and v > 0 else 0
    except Exception:
        # Must never throw per spec
        return 0
    finally:
        con.close()


def increment(key: str, delta: int = 1) -> None:
    # Atomic and durable under contention:
    # single-statement UPSERT with clamp using CASE ensures no lost updates.
    t_start = time.time()
    
    for attempt in range(_MAX_RETRIES + 1):
        con = None
        try:
            con = _connect()
            # IMMEDIATE to acquire write lock early and avoid long implicit waits.
            con.execute("BEGIN IMMEDIATE")
            # Use original delta in UPDATE clause to properly handle negative values
            # For INSERT: clamp initial value to 0 if negative
            # For UPDATE: add original delta and clamp result to 0 if negative
            con.execute(
                """
                INSERT INTO counters(key, value)
                VALUES(?, CASE WHEN ? < 0 THEN 0 ELSE ? END)
                ON CONFLICT(key) DO UPDATE SET
                  value = CASE
                    WHEN counters.value + ? < 0 THEN 0
                    ELSE counters.value + ?
                  END
                """,
                (key, delta, delta, delta, delta),
            )
            con.execute("COMMIT")
            if con:
                con.close()
            return
        except sqlite3.OperationalError as e:
            # Handle lock contention with bounded deterministic retry.
            if con:
                try:
                    con.execute("ROLLBACK")
                except Exception:
                    pass
                try:
                    con.close()
                except Exception:
                    pass
            msg = str(e).lower()
            if "locked" in msg or "busy" in msg:
                elapsed = time.time() - t_start
                if elapsed > _TOTAL_BUDGET:
                    # Surface as error; tests expect bounded retry to succeed
                    # in their scenario, but this prevents infinite loops.
                    raise
                # Use very small fixed sleep for fast retries
                # This ensures we retry quickly when locks are released
                time.sleep(_BASE_SLEEP)
                continue
            raise
        except Exception:
            if con:
                try:
                    con.close()
                except Exception:
                    pass
            raise
PY

# Make `from app import counter_service` work by creating a proper package.
cat > /app/app/__init__.py <<'PY'
from . import counter_service  # re-export submodule for convenience
PY

# Ensure /app is in Python path for tests (persists across shell sessions)
python - <<'PY'
import site
import sys
from pathlib import Path

# Add /app to Python path via .pth file so it persists for pytest
app_path = Path("/app")
if str(app_path) not in sys.path:
    # Find site-packages directory
    site_packages = Path(site.getsitepackages()[0])
    pth_file = site_packages / "app_path.pth"
    pth_file.write_text(str(app_path) + "\n")
    # Also add to current session
    sys.path.insert(0, str(app_path))
PY

# Initialize the SQLite database file and schema expected by the tests.
python - <<'PY'
from pathlib import Path
import sqlite3

db_path = Path("/app/state/counters.db")
db_path.parent.mkdir(parents=True, exist_ok=True)

con = sqlite3.connect(db_path)
try:
    con.execute("PRAGMA journal_mode=WAL")
    con.execute(
        "CREATE TABLE IF NOT EXISTS counters (key TEXT PRIMARY KEY, value INTEGER NOT NULL)"
    )
    con.commit()
finally:
    con.close()
PY
