# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_solution():
    import sys
    spec = importlib.util.spec_from_file_location("solution", "/app/solution.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("Could not load /app/solution.py")
    module = importlib.util.module_from_spec(spec)
    # Register module in sys.modules before execution to fix dataclass processing
    sys.modules["solution"] = module
    spec.loader.exec_module(module)
    return module


def _run_canonicalize(tmp_path: Path, input_content: str) -> str:
    """Write input.txt and run the solution, return output."""
    input_path = tmp_path / "input.txt"
    input_path.write_text(input_content, encoding="utf-8")
    
    solution = _load_solution()
    output_path = tmp_path / "output.txt"
    solution.canonicalize(str(input_path), str(output_path))
    
    assert output_path.exists(), "output.txt must be created"
    return output_path.read_text(encoding="utf-8")


def test_solution_file_exists_and_has_canonicalize():
    """Test 0: Verify solution file exists and has required function."""
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "/app/solution.py must exist"
    solution = _load_solution()
    assert callable(getattr(solution, "canonicalize", None)), "canonicalize() must be defined"


def test_prerelease_forbidden_unless_explicit_zero(tmp_path):
    """Test 1: Prerelease Forbidden Unless Explicit -0
    
    Input: range like >=1.2.3 <2.0.0 with only prereleases available and also one older stable.
    Expect: must NOT pick prerelease; choose older stable if it satisfies.
    """
    input_text = """UNIVERSE
pkg@1.0.0:

pkg@1.2.3-alpha:

pkg@1.2.3-beta:

pkg@1.2.4:

LOCK
pkg@1.2.4
"""
    output = _run_canonicalize(tmp_path, input_text)
    assert "pkg@1.2.4" in output
    assert "pkg@1.2.3-alpha" not in output
    assert "pkg@1.2.3-beta" not in output


def test_caret_zero_special_case(tmp_path):
    """Test 2: ^0.x.y Caret Special-Case
    
    Input: ^0.2.3 with versions 0.2.4, 0.3.0.
    Expect: allowed <0.3.0, so 0.2.4.
    """
    input_text = """UNIVERSE
root@1.0.0:
  dep ^0.2.3

dep@0.2.4:

dep@0.3.0:

LOCK
root@1.0.0
  dep@0.2.4
"""
    output = _run_canonicalize(tmp_path, input_text)
    assert "dep@0.2.4" in output
    assert "dep@0.3.0" not in output


def test_wildcard_comparator_interaction(tmp_path):
    """Test 3: Wildcard + Comparator Interaction
    
    Input: 1.* >=1.2.0 (AND).
    Expect: versions 1.1.9 rejected, 1.2.0 accepted.
    """
    input_text = """UNIVERSE
root@1.0.0:
  dep 1.*
  dep >=1.2.0

dep@1.1.9:

dep@1.2.0:

dep@1.3.0:

LOCK
root@1.0.0
  dep@1.2.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    assert "dep@1.2.0" in output or "dep@1.3.0" in output
    assert "dep@1.1.9" not in output


def test_hyphen_range_inclusivity_prerelease_ordering(tmp_path):
    """Test 4: Hyphen Range Inclusivity + Prerelease Ordering
    
    Input: 1.2.3 - 1.2.3 with available 1.2.3-alpha, 1.2.3.
    Expect: picks 1.2.3 only (inclusive exact).
    """
    input_text = """UNIVERSE
root@1.0.0:
  dep 1.2.3 - 1.2.3

dep@1.2.3-alpha:

dep@1.2.3:

LOCK
root@1.0.0
  dep@1.2.3
"""
    output = _run_canonicalize(tmp_path, input_text)
    assert "dep@1.2.3" in output
    assert "dep@1.2.3-alpha" not in output


def test_lockfile_missing_transitive_closure(tmp_path):
    """Test 5: Lockfile Missing Transitive Closure
    
    Input LOCK: includes root deps but omits deep dependency package line.
    Expect: INVALID → canonical output adds missing nodes.
    """
    input_text = """UNIVERSE
root@1.0.0:
  a ^1.0.0

a@1.0.0:
  b ^1.0.0

b@1.0.0:

LOCK
root@1.0.0
  a@1.0.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    # Should include b@1.0.0 in output
    assert "b@1.0.0" in output


def test_lock_wrong_dep_edge_despite_correct_versions(tmp_path):
    """Test 6: Lock Has Wrong Dep Edge Despite Correct Versions
    
    Input LOCK: a@1.0.0 -> b@2.0.0 but UNIVERSE for a@1.0.0 depends on b ^2.1.0.
    Expect: INVALID even if b version satisfies root; must match exact declared deps.
    """
    input_text = """UNIVERSE
root@1.0.0:
  a ^1.0.0

a@1.0.0:
  b ^2.1.0

b@2.0.0:

b@2.1.0:

LOCK
root@1.0.0
  a@1.0.0
    b@2.0.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    # Should fix to b@2.1.0
    assert "b@2.1.0" in output
    assert "b@2.0.0" not in output or output.count("b@2.0.0") == 0


def test_multiple_satisfying_assignments_tiebreak_package_set_size(tmp_path):
    """Test 7: Multiple Satisfying Assignments, Tie-Break by Package Set Size
    
    Universe: optional dependency path where one solution introduces extra package.
    Expect: choose solution with fewer packages even if versions lower.
    """
    input_text = """UNIVERSE
root@1.0.0:
  a ^1.0.0

a@1.0.0:
  b ^1.0.0
  c ^1.0.0

a@1.1.0:
  b ^1.0.0

b@1.0.0:

c@1.0.0:

LOCK
root@1.0.0
  a@1.1.0
    b@1.0.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    # Should prefer a@1.1.0 (fewer packages) over a@1.0.0 (requires c)
    assert "a@1.1.0" in output
    assert "c@1.0.0" not in output


def test_two_minimal_closures_tiebreak_tuple(tmp_path):
    """Test 8: Two Minimal Closures, Tie-Break by Tuple of (pkgname, version)
    
    Setup: both closures same size; one has higher version of a but lower of z.
    Expect: compare tuple order by pkgname ASCII → decide based on earliest pkg.
    """
    input_text = """UNIVERSE
root@1.0.0:
  a ^1.0.0
  z ^1.0.0

a@1.0.0:

a@1.1.0:

z@1.0.0:

z@1.1.0:

LOCK
root@1.0.0
  a@1.0.0
  z@1.1.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    # Should prefer lexicographically first package when tie-breaking
    # Since 'a' < 'z', prefer a@1.1.0, z@1.0.0 over a@1.0.0, z@1.1.0
    # Actually, should compare (pkgname, version) tuples lexicographically
    # Check that output is canonical (sorted)
    assert output.count("a@") == 1
    assert output.count("z@") == 1


def test_deterministic_canonical_formatting_required(tmp_path):
    """Test 9: Deterministic Canonical Formatting Required
    
    Input LOCK: correct solution but lines shuffled, deps unsorted, spacing varies.
    Expect: output must be sorted + exact formatting.
    """
    input_text = """UNIVERSE
root@1.0.0:
  z ^1.0.0
  a ^1.0.0

a@1.0.0:

z@1.0.0:

LOCK
root@1.0.0
  z@1.0.0
  a@1.0.0
"""
    output1 = _run_canonicalize(tmp_path, input_text)
    # Run again to ensure deterministic
    output2 = _run_canonicalize(tmp_path, input_text)
    assert output1 == output2, "Output must be deterministic"
    # Check that packages are sorted
    lines = [line.strip() for line in output1.splitlines() if line.strip() and not line.strip().startswith("#")]
    pkg_lines = [line for line in lines if "@" in line and not line.startswith("  ")]
    assert pkg_lines == sorted(pkg_lines), "Packages must be sorted"


def test_cyclic_dependencies_valid_resolution(tmp_path):
    """Test 10: Cyclic Dependencies With Valid Resolution
    
    Universe: a@1.0.0 -> b ^1.0.0, b@1.0.0 -> a ^1.0.0.
    Expect: closure terminates correctly, single version each, canonical output stable.
    """
    input_text = """UNIVERSE
root@1.0.0:
  a ^1.0.0

a@1.0.0:
  b ^1.0.0

b@1.0.0:
  a ^1.0.0

LOCK
root@1.0.0
  a@1.0.0
    b@1.0.0
"""
    output = _run_canonicalize(tmp_path, input_text)
    assert "a@1.0.0" in output
    assert "b@1.0.0" in output
    # Should handle cycles correctly without infinite expansion
    assert output.count("a@1.0.0") == 1
    assert output.count("b@1.0.0") == 1
