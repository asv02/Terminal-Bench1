from __future__ import annotations

from pathlib import Path
import importlib.util
import inspect
import random


# ---------- Reference helpers ----------

def is_good_subarray(arr, left, right):
    """Return True if subarray arr[left:right+1] has no strict local maximum."""
    if right - left + 1 < 3:
        return True
    for i in range(left + 1, right):
        if arr[i] > arr[i - 1] and arr[i] > arr[i + 1]:
            return False
    return True


def brute_count(arr):
    """O(n^3) brute-force count of good subarrays. Only for small tests."""
    n = len(arr)
    total = 0
    for left in range(n):
        for right in range(left, n):
            if is_good_subarray(arr, left, right):
                total += 1
    return total


def solve_reference(arr):
    """
    O(n) reference solution mirroring the intended two-pointer invariant.

    Maintains a sliding window [left, right] with no internal peak. When a new
    peak emerges at mid=right-1, the earliest allowed start is updated with the
    maximum forbidden index ever seen.
    """
    n = len(arr)
    if n == 0:
        return 0

    left = 0
    last_forbid = -1
    ans = 0

    for right in range(n):
        if right >= 2:
            mid = right - 1
            if arr[mid] > arr[mid - 1] and arr[mid] > arr[right]:
                last_forbid = max(last_forbid, right - 2)
        if last_forbid >= 0 and left <= last_forbid:
            left = last_forbid + 1
        ans += right - left + 1
    return ans


# ---------- Loading helpers ----------

def _load_participant_module():
    spec = importlib.util.spec_from_file_location("solve_solution", "/app/solution.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _module_and_solve():
    module = _load_participant_module()
    assert hasattr(module, "solve"), "solve function missing"
    solve = module.solve
    assert callable(solve), "solve must be callable"
    return module, solve


# ---------- Tests ----------

def test_contract_and_signature():
    """Ensure solution file exists, exposes solve, and respects signature and return type."""
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "Solution file /app/solution.py does not exist"

    module, solve = _module_and_solve()
    sig = inspect.signature(solve)
    params = list(sig.parameters.values())
    assert len(params) == 1, "solve must take exactly one positional parameter"
    assert params[0].default is inspect._empty, "parameter must not have default value"
    assert params[0].kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)

    # Adversarial smoke tests with edge cases that break naive implementations
    adversarial_samples = [
        [1, 3, 2, 2, 3, 1],  # basic
        [1, 2, 10, 2, 3, 4, 5],  # critical: peak at 2 forbids starts <= 0, must use > not >=
        [1, 10, 1, 2, 10, 2, 3],  # multiple peaks requiring max tracking
        [1, 2, 1, 10, 1, 2, 1, 5, 1, 2, 3, 4, 5],  # non-monotonic forbidden indices
        [5, 5, 5, 5, 5],  # all equal - no peaks
        [1, 100, 1, 1, 1, 1, 100, 1, 1, 1, 1, 1, 1, 100, 1],  # sparse peaks with gaps
    ]
    for sample in adversarial_samples:
        snapshot = list(sample)
        out = solve(sample)
        assert isinstance(out, int), "solve must return an int"
        assert sample == snapshot, "solve must not mutate input"
        assert out == brute_count(sample), f"smoke run failed on {sample}: expected {brute_count(sample)}, got {out}"


def test_purity_and_repeated_calls_with_aliases():
    """
    Verify determinism, purity, and lack of alias-based caching.
    Uses adversarial array mixing negatives, huge ints, dense peaks, and patterns
    that break implementations using >= instead of > or not tracking max forbidden.
    """
    random.seed(1337)
    module, solve = _module_and_solve()

    # Create complex adversarial pattern with strategic peak placement
    arr = []
    for i in range(500):
        if i % 13 == 5:
            arr.append(10**9 + i)  # gigantic peaks at strategic positions
        elif i % 17 == 8:
            arr.append(-10**6 + i)  # negative baselines
        elif i % 7 == 3 and i > 0 and i < 499:
            arr.append(10**8)  # additional dense peaks
        else:
            arr.append(42)
    
    # Inject critical pattern: peaks that create non-monotonic forbidden indices
    for i in range(50, 450, 50):
        if i + 1 < len(arr):
            arr[i] = 10**9
            arr[i-1] = 1
            arr[i+1] = 1

    snapshot = list(arr)
    alias = arr
    view = arr[:]
    deep_copy = [x for x in arr]

    first = solve(arr)
    second = solve(alias)
    third = solve(view)
    fourth = solve(deep_copy)
    fifth = solve(arr)  # repeated call on same object

    assert arr == snapshot, "input mutated between calls"
    assert alias is arr, "aliases must refer to same object"
    assert first == second == third == fourth == fifth, "results must be deterministic and alias-safe"
    assert first == solve_reference(arr), f"result must match reference: expected {solve_reference(arr)}, got {first}"


def test_strict_peak_definition_edge_cases():
    """
    Enforce strict '>' on both neighbors, plateaus are NOT peaks, and borders never peak.
    Includes adversarial cases that break implementations using >= or treating plateaus as peaks.
    """
    _, solve = _module_and_solve()
    cases = [
        [5, 5, 5, 5],  # all equal
        [1, 9, 9, 1],  # plateau in middle
        [2, 2, 3, 3, 2, 2],  # multiple plateaus
        [7, 7, 6, 6, 7, 7],  # valley plateaus
        [1, 4, 4, 4, 2, 2, 4, 4, 1],  # complex plateaus
        [9, 1, 9, 1, 9, 1, 9],  # alternating peaks
        [100, 1, 2, 3, 4, 100],  # high boundaries
        [50, 1, 50, 1, 50],  # alternating pattern
        # Critical adversarial cases
        [1, 2, 2, 2, 1, 2, 2, 2, 1],  # plateaus that look like peaks
        [3, 3, 3, 4, 4, 3, 3, 3, 2, 2, 2],  # wide plateaus with small bumps
        [10, 10, 1, 2, 3, 4, 10, 10],  # boundary plateaus
        [1, 5, 5, 5, 1, 5, 5, 5, 1],  # repeated plateau pattern
        [2, 2, 9, 2, 2, 2, 8, 8, 2, 7, 7, 7, 2],  # mixed plateaus and peaks
        [100, 100, 1, 2, 3, 100, 100],  # high boundary plateaus
        [1, 1, 1, 10, 10, 10, 1, 1, 1],  # plateau separated by lows
        [5, 5, 1, 5, 5, 1, 5, 5],  # alternating plateaus
        [9, 9, 1, 9, 9, 2, 9, 9, 1],  # plateaus with varying valleys
    ]
    for arr in cases:
        expected = brute_count(arr)
        got = solve(arr)
        assert got == expected, f"strict peak rule failed on {arr}: expected {expected}, got {got}"


def test_max_forbidden_tracking_and_update_order():
    """
    CRITICAL: Detect (1) using last peak instead of max forbidden, (2) counting before updating,
    (3) using >= instead of >, (4) resetting forbidden index incorrectly.
    Patterns escalate constraints non-monotonically and force left jumps.
    These patterns will break implementations that don't track MAXIMUM forbidden index.
    """
    _, solve = _module_and_solve()
    patterns = [
        # Critical: peak at 2 forbids starts <= 0, peak at 6 forbids starts <= 4
        # Must track max(0, 4) = 4, requiring start > 4
        [1, 2, 10, 2, 3, 4, 20, 4, 5, 6, 7, 8, 9, 10, 11],
        # Critical: peak at 1 forbids starts <= -1, peak at 4 forbids starts <= 2
        # Must track max(-1, 2) = 2, requiring start > 2
        [1, 10, 1, 2, 10, 2, 3, 4, 5, 6, 7, 8, 9],
        # CRITICAL: Earlier peak (index 3) has smaller constraint, later (index 7) has larger
        # Must track max(1, 5) = 5, not just 5
        [1, 2, 1, 10, 1, 2, 1, 5, 1, 2, 3, 4, 5, 6, 7, 8, 9],
        # Dense peaks requiring careful max tracking
        [1, 10, 1, 2, 10, 2, 3, 10, 3, 4, 10, 4, 5, 10, 5],
        # CRITICAL: Non-monotonic forbidden indices - earlier peak has larger constraint
        # Peak at 3 forbids starts <= 1, peak at 7 forbids starts <= 5
        # At position 14, must use max(1, 5) = 5
        [1, 2, 1, 10, 1, 2, 1, 5, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
        # Pattern where update order matters: must update BEFORE counting
        [1, 10, 1, 2, 10, 2, 3, 4, 5],
        # Multiple peaks with varying constraints
        [1, 5, 1, 2, 10, 2, 3, 3, 1, 4, 15, 4, 5, 5, 1],
        # Sparse peaks creating non-monotonic forbidden regions
        [1, 10, 1, 1, 1, 1, 10, 1, 1, 1, 1, 1, 1, 10, 1],
        # CRITICAL: Pattern that breaks >= vs > bug
        # Peak at 2 forbids starts <= 0, at position 6 must use start > 0 (not >= 0)
        [1, 2, 10, 2, 3, 4, 5, 6, 7, 8],
        # Long sequence with early constraint that must persist
        [1, 2, 10, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
    ]
    for arr in patterns:
        expect = brute_count(arr)
        got = solve(arr)
        assert got == expect, f"forbidden tracking/update order mismatch for {arr}: expected {expect}, got {got}"


def test_state_leakage_after_in_place_mutations():
    """
    Ensure solver does not cache length/data: mutate list in place between calls.
    Tests multiple mutation patterns to catch state leakage.
    """
    _, solve = _module_and_solve()
    base = [1, 10, 1, 2, 3, 10, 2, 1, 4, 5]
    first = solve(base)
    assert first == solve_reference(base), f"initial call failed: expected {solve_reference(base)}, got {first}"

    # Test 1: Destructive reverse and extend
    base[:] = base[::-1]
    base.extend([99, 1, 1, 99])
    second = solve(base)
    assert second == solve_reference(base), f"reverse+extend mutation failed: expected {solve_reference(base)}, got {second}"
    assert second != first, "meaningful mutation should change result"

    # Test 2: Slice replacement creating new peaks
    base[:5] = [100, 1, 100, 1, 100]
    third = solve(base)
    assert third == solve_reference(base), f"slice replacement failed: expected {solve_reference(base)}, got {third}"

    # Test 3: Insertion in middle
    base.insert(7, 200)
    base.insert(8, 1)
    base.insert(9, 200)
    fourth = solve(base)
    assert fourth == solve_reference(base), f"insertion mutation failed: expected {solve_reference(base)}, got {fourth}"

    # Test 4: Multiple mutations
    base.pop()
    base.pop(0)
    base.append(50)
    base.insert(0, 50)
    fifth = solve(base)
    assert fifth == solve_reference(base), f"multiple mutations failed: expected {solve_reference(base)}, got {fifth}"


def test_random_small_fuzz_against_bruteforce():
    """
    Deterministic fuzz with mirrored overlays, strategic peak placement, and adversarial patterns
    to break asymmetric or heuristic logic. Increased iterations and complexity.
    """
    random.seed(424242)
    module, solve = _module_and_solve()

    for trial in range(800):  # Doubled iterations
        n = random.randint(1, 35)  # Increased max size
        pattern_type = random.random()
        
        if pattern_type < 0.2:
            # Dense peak pattern - every other position is peak
            arr = []
            for i in range(n):
                if i % 2 == 1 and i > 0 and i < n - 1:
                    arr.append(random.randint(50, 200))
                else:
                    arr.append(random.randint(-5, 30))
        elif pattern_type < 0.4:
            # Strategic peak placement creating overlapping constraints
            base = [random.randint(-5, 30) for _ in range(n)]
            for i in range(2, n - 2, 3):
                base[i] = random.randint(50, 200)
                base[i-1] = random.randint(-3, 5)
                base[i+1] = random.randint(-3, 5)
            arr = base
        elif pattern_type < 0.6:
            # Alternating pattern with peaks
            arr = [random.randint(1, 5) if i % 2 == 0 else random.randint(50, 200) for i in range(n)]
        elif pattern_type < 0.8:
            # Random with high peak probability
            arr = []
            for i in range(n):
                if i > 0 and i < n - 1 and random.random() < 0.4:
                    arr.append(random.randint(50, 200))
                else:
                    arr.append(random.randint(-5, 30))
        else:
            # Structured spikes and flats
            base = [random.randint(-5, 30) for _ in range(n)]
            for i in range(1, n - 1, 3):
                base[i] = random.randint(50, 200)
                base[i - 1] = random.randint(-3, 5)
                base[i + 1] = random.randint(-3, 5)
            if random.random() < 0.5:
                arr = base + base[::-1]  # palindrome overlay
            else:
                arr = base
        
        expect = brute_count(arr)
        got = solve(arr)
        assert got == expect, f"fuzz mismatch on trial {trial}, array {arr}: expected {expect}, got {got}"


def test_compound_boundary_and_plateau_patterns():
    """
    Mix boundaries, wide plateaus, alternating highs, and interior traps.
    Uses brute force because lengths stay modest. Includes adversarial cases that break
    implementations not handling plateaus correctly or treating boundaries as peaks.
    """
    _, solve = _module_and_solve()
    cases = [
        [20, 1, 1, 1, 5, 5, 1, 1, 1, 20],
        [10, 10, 1, 2, 3, 4, 10, 10],
        [1, 1, 2, 2, 1, 1, 2, 2, 3, 3, 1, 1, 2, 2],
        [2, 2, 2, 9, 9, 2, 2, 2, 8, 8, 2, 2, 7, 7, 7, 2, 2, 6, 6, 2],
        [5, 5, 5, 1, 5, 5, 5, 1, 5, 5, 5],
        [30, 1, 2, 30, 2, 1, 30],
        # Additional adversarial cases
        [100, 100, 1, 2, 3, 4, 5, 100, 100],
        [1, 1, 1, 10, 10, 10, 1, 1, 1, 20, 20, 20, 1, 1, 1],
        [50, 1, 1, 50, 2, 2, 50, 3, 3, 50],
        [9, 9, 1, 9, 9, 2, 9, 9, 3, 9, 9],
        [2, 2, 2, 2, 9, 9, 9, 2, 2, 2, 2],
        [10, 10, 1, 1, 1, 10, 10, 2, 2, 2, 10, 10],
        [1, 5, 5, 5, 1, 6, 6, 6, 1, 7, 7, 7, 1],
        [100, 1, 1, 1, 100, 2, 2, 2, 100, 3, 3, 3, 100],
        [5, 5, 1, 5, 5, 2, 5, 5, 3, 5, 5],
    ]
    for arr in cases:
        expected = brute_count(arr)
        got = solve(arr)
        assert got == expected, f"boundary/plateau mismatch for {arr}: expected {expected}, got {got}"


def test_extreme_values_and_equivalence_variants():
    """
    Stress comparisons with huge magnitude differences, negative values, and ensure symmetry
    under transforms. Includes patterns that break implementations with integer overflow issues
    or incorrect comparison logic.
    """
    _, solve = _module_and_solve()
    base = [10**12, -10**12, 10**12, -10**12, 0, 10**12]
    variants = [
        base,
        base[::-1],
        [base[0]] + base + [base[0]],
        [x // 2 for x in base],
        # Additional extreme cases
        [10**15, 1, 10**15, 1, 10**15],
        [-10**15, 1, -10**15, 1, -10**15],
        [10**18, -10**18, 10**18, -10**18],
        [1, 10**20, 1, 10**20, 1],
        [10**20, 1, 2, 3, 4, 10**20],
        [1, 2, 3, 10**25, 3, 2, 1],
        # Mixed extreme and normal
        [10**12, 1, 2, 10**12, 2, 1, 10**12],
        [1, 10**15, 1, 1, 1, 10**15, 1],
    ]
    for arr in variants:
        expect = brute_count(arr)
        got = solve(arr)
        assert got == expect, f"extreme value handling failed for {arr}: expected {expect}, got {got}"


def test_large_deterministic_reference():
    """
    Enforce near-linear performance and correct sliding window on a large but deterministic array.
    Size chosen to be heavy for O(n^2) but safe for O(n). Includes complex peak patterns that
    require careful max forbidden tracking and correct update order.
    """
    random.seed(2025)
    _, solve = _module_and_solve()

    n = 500_000  # Doubled size
    arr = []
    for i in range(n):
        if 0 < i < n - 1 and (i % 11 == 3 or i % 17 == 5 or i % 19 == 7):
            arr.append(random.randint(2000, 8000))
        else:
            arr.append(random.randint(1, 500))
    
    # Inject structured clusters creating overlapping constraints
    for start in range(500, n - 500, 3000):  # More frequent clusters
        for off in (0, 1, 2, 3):  # More peaks per cluster
            idx = start + off * 7
            if idx > 0 and idx < n - 1:
                arr[idx] = 10_000
                arr[idx - 1] = 1
                arr[idx + 1] = 1
    
    # Add dense peak regions that create non-monotonic forbidden indices
    for cluster in range(1000, n - 1000, 8000):
        for offset in [0, 1, 2]:
            idx = cluster + offset * 100
            if idx > 0 and idx < n - 1:
                arr[idx] = random.randint(8000, 10000)
                arr[idx-1] = random.randint(1, 10)
                arr[idx+1] = random.randint(1, 10)
    
    # Add strategic peaks that require max tracking
    for i in range(2000, n - 2000, 10000):
        if i > 0 and i < n - 1:
            arr[i] = 15_000
            arr[i-1] = 1
            arr[i+1] = 1

    expect = solve_reference(arr)
    got = solve(arr)
    assert got == expect, f"large deterministic reference mismatch: expected {expect}, got {got}"


def test_recursive_mutation_resistance_and_alias_slices():
    """
    Catch solvers that store global state or reuse stale prefixes.
    Mutate the list via slice assignment, insertion, deletion between calls.
    Tests multiple mutation patterns to ensure no state leakage.
    """
    _, solve = _module_and_solve()
    arr = [1, 9, 1, 2, 9, 2, 3, 9, 3, 4]
    expect1 = solve_reference(arr)
    got1 = solve(arr)
    assert got1 == expect1, f"initial call failed: expected {expect1}, got {got1}"

    # Test 1: Slice replacement
    arr[:4] = [5, 5, 5, 5]
    arr[-4:] = [7, 1, 7, 1]
    expect2 = solve_reference(arr)
    got2 = solve(arr)
    assert got2 == expect2, f"slice mutation failed: expected {expect2}, got {got2}"
    assert expect1 != expect2, "mutation should change count"

    # Test 2: Insert creating new peaks
    arr.insert(5, 100)
    arr.insert(6, 1)
    arr.insert(7, 100)
    expect3 = solve_reference(arr)
    got3 = solve(arr)
    assert got3 == expect3, f"insertion mutation failed: expected {expect3}, got {got3}"

    # Test 3: Delete and replace
    del arr[2:5]
    arr[3:5] = [200, 1, 200]
    expect4 = solve_reference(arr)
    got4 = solve(arr)
    assert got4 == expect4, f"delete+replace mutation failed: expected {expect4}, got {got4}"

    # Test 4: Multiple operations
    arr.pop(0)
    arr.append(50)
    arr[1:3] = [300, 1]
    expect5 = solve_reference(arr)
    got5 = solve(arr)
    assert got5 == expect5, f"multiple mutations failed: expected {expect5}, got {got5}"


def test_long_sawtooth_and_sparse_peaks():
    """
    Blend sparse and dense peaks with wide flats to expose off-by-one errors,
    incorrect boundary handling, and max forbidden tracking bugs.
    """
    _, solve = _module_and_solve()
    arr = []
    # Create complex sawtooth pattern with varying densities
    for i in range(400):  # Increased length
        if i % 6 == 0:
            arr.append(100)
        elif i % 6 == 3:
            arr.append(1)
        elif i % 10 == 7:
            arr.append(200)
        elif i % 13 == 5:
            arr.append(300)  # Additional peak pattern
        else:
            arr.append(5)
    
    # Inject strategic peaks creating non-monotonic constraints
    for i in range(50, 350, 50):
        if i > 0 and i < len(arr) - 1:
            arr[i] = 500
            arr[i-1] = 1
            arr[i+1] = 1
    
    expect = solve_reference(arr)
    got = solve(arr)
    assert got == expect, f"sawtooth pattern failed: expected {expect}, got {got}"


def test_small_exhaustive_smoke_set():
    """Exhaustive adversarial minis checked by brute force. Includes critical edge cases
    that break common LLM mistakes: >= vs >, max tracking, update order, plateau handling."""
    _, solve = _module_and_solve()
    examples = [
        [1],
        [1, 2],
        [1, 3, 2],  # basic peak
        [1, 2, 3],  # increasing
        [3, 2, 1],  # decreasing
        [1, 2, 1],  # valley
        [1, 3, 5, 4, 2],  # multiple peaks
        [3, 1, 2, 4],  # peak at start
        [1, 10, 2, 10, 3, 10, 4],  # multiple peaks
        [3, 3, 2, 3, 3, 4, 3, 3, 2, 3, 3],  # plateaus
        # Critical adversarial cases
        [1, 2, 10, 2, 3, 4, 5],  # CRITICAL: peak at 2, tests >= vs > bug
        [1, 10, 1, 2, 10, 2, 3],  # CRITICAL: multiple peaks, tests max tracking
        [1, 2, 1, 10, 1, 2, 1, 5, 1, 2, 3],  # CRITICAL: non-monotonic forbidden
        [5, 5, 5, 5, 5],  # all equal
        [1, 1, 1, 1, 1],  # all equal small
        [100, 1, 2, 3, 4, 100],  # high boundaries
        [1, 100, 1, 1, 1, 1, 100, 1],  # sparse peaks
        [1, 10, 1, 10, 1, 10, 1],  # dense peaks
        [2, 2, 2, 2, 2],  # plateau
        [1, 2, 2, 2, 1],  # plateau in middle
        [10, 10, 1, 10, 10],  # boundary plateaus
        [1, 5, 1, 6, 1, 7, 1],  # increasing peaks
        [7, 1, 6, 1, 5, 1, 4],  # decreasing peaks
    ]
    for arr in examples:
        expected = brute_count(arr)
        got = solve(arr)
        assert got == expected, f"exhaustive mini failed for {arr}: expected {expected}, got {got}"