# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from pathlib import Path
import importlib.util


def load():
    p = Path("/app/solution.py")
    spec = importlib.util.spec_from_file_location("s", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.solve


def test_linearizable_simple():
    """Simple linearizable history."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 READ 1",
    ]
    assert solve(lines) == "NONE"


def test_simple_violation():
    """Read observes impossible value."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 READ 0",
    ]
    assert solve(lines) == "R=2@1 <- W=1@0"


def test_concurrent_writes_latest_chosen():
    """Latest conflicting write must be selected."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 WRITE 2",
        "2 3 READ 1",
    ]
    assert solve(lines) == "R=3@2 <- W=2@1"


def test_real_time_order_violation():
    """Real-time ordering forbids linearization."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 READ 1",
        "2 3 WRITE 2",
        "3 4 READ 1",
    ]
    assert solve(lines) == "R=4@3 <- W=1@0"


def test_multiple_reads_choose_earliest():
    """Earliest violating READ chosen."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 READ 0",
        "2 3 READ 0",
    ]
    assert solve(lines) == "R=2@1 <- W=1@0"


def test_same_time_concurrent():
    """Concurrent operations allow reordering."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "0 2 READ 0",
    ]
    assert solve(lines) == "NONE"


def test_invalid_read_cutoff():
    """Invalid read value cuts off history."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 READ 999",  # invalid
        "2 3 READ 0",
    ]
    assert solve(lines) == "NONE"


def test_value_reuse_confusion():
    """Multiple writes of same value."""
    solve = load()
    lines = [
        "0 1 WRITE 1",
        "1 2 WRITE 1",
        "2 3 READ 1",
        "3 4 READ 0",
    ]
    assert solve(lines) == "R=4@3 <- W=2@1"


def test_large_stability():
    """Deterministic under large history."""
    solve = load()
    lines = ["0 1 WRITE 1"]
    for i in range(2, 1000):
        lines.append(f"{i} {i} READ 1")
    assert solve(lines) == "NONE"
