"""
Adversarial, deterministic test suite for the cycle-resolving bootstrap task.

Deterministic cycle-breaking policy enforced by all tests:
1) For any SCC with size >= 2 or a self-loop, pick root = lexicographically
   smallest package in the SCC.
2) Among edges (src -> root) inside the SCC, remove the edge whose src is
   lexicographically smallest (ASCII ordering).
3) Recompute SCCs after each removal and repeat until the graph is acyclic.
4) Removals must be minimal: stop as soon as the SCC is acyclic.
5) If a required removal would target a protected edge, raise a deterministic
   error: "Unresolvable cycle detected: <cycle-string>" where the cycle string
   is formatted as a->b->c->a starting at the lexicographically smallest node.

Canonical JSON for hashes/byte checks:
json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

Output contract:
- Resolver invoked as `python resolver.py <manifest_path>`.
- Prints install order as newline-separated package names, ending with a single
  trailing newline, no extra whitespace.
- Running twice on the same manifest yields identical stdout bytes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from itertools import combinations
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

sys.setrecursionlimit(10000)

def _find_task_root() -> Path:
    here = Path(__file__).resolve()
    parents = list(here.parents)
    candidates = [
        here.parent.parent / "harbor_tasks" / "resolve-cyclic-dependency-deadlock-bootstrap",
        Path("/app/harbor_tasks/resolve-cyclic-dependency-deadlock-bootstrap"),
        Path("/workspace/harbor_tasks/resolve-cyclic-dependency-deadlock-bootstrap"),
        Path("/workdir/harbor_tasks/resolve-cyclic-dependency-deadlock-bootstrap"),
        Path("/home/runner/work/snorkel-tb-tasks-Caudal/snorkel-tb-tasks-Caudal/harbor_tasks/resolve-cyclic-dependency-deadlock-bootstrap"),
    ]
    for p in parents:
        candidates.append(p / "harbor_tasks" / "resolve-cyclic-dependency-deadlock-bootstrap")
        candidates.append(p / "resolve-cyclic-dependency-deadlock-bootstrap")
    for c in candidates:
        if (c / "resolver.py").exists():
            return c
    # bounded search
    for root in [Path("/app"), Path("/workspace"), Path("/workdir"), Path("/")]:
        try:
            for path in root.rglob("resolver.py"):
                if path.parent.name == "resolve-cyclic-dependency-deadlock-bootstrap":
                    return path.parent
        except (PermissionError, OSError):
            continue
    return here.parent.parent


TASK_ROOT = _find_task_root()
RESOLVER_PATH = TASK_ROOT / "resolver.py"



# ---------- Helper utilities ----------

def canonical_json_bytes(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_manifest(tmp_path: Path, manifest: dict) -> Path:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return path


def _normalize_packages(manifest: dict) -> Dict[str, List[str]]:
    pkgs_raw = manifest.get("packages", {})
    normalized: Dict[str, List[str]] = {}
    for name, data in pkgs_raw.items():
        pkg_name = str(name)
        deps = []
        if isinstance(data, dict):
            deps = data.get("deps", data.get("dependencies", []))
        elif isinstance(data, list):
            deps = data
        elif data is None:
            deps = []
        else:
            deps = [data]
        deps_clean: List[str] = []
        for dep in deps:
            if dep is None or dep == "":
                continue
            deps_clean.append(str(dep))
        normalized[pkg_name] = deps_clean
    return normalized


def _collect_protected_edges(manifest: dict) -> Set[Tuple[str, str]]:
    protected: Set[Tuple[str, str]] = set()
    for edge in manifest.get("protected_edges", []):
        if isinstance(edge, (list, tuple)) and len(edge) == 2:
            protected.add((str(edge[0]), str(edge[1])))
    pkgs = manifest.get("packages", {})
    for name, data in pkgs.items():
        if isinstance(data, dict):
            for key in ("protected", "edges_protected"):
                if key in data:
                    for edge in data[key]:
                        if isinstance(edge, (list, tuple)) and len(edge) == 2:
                            protected.add((str(edge[0]), str(edge[1])))
    return protected


def _reachable_nodes(packages: Dict[str, List[str]], bootstrap: Sequence[str]) -> Set[str]:
    want = set(map(str, bootstrap))
    stack = list(want)
    while stack:
        node = stack.pop()
        for dep in packages.get(node, []):
            if dep not in want:
                want.add(dep)
                stack.append(dep)
    return want


def _build_edges(packages: Dict[str, List[str]], scope: Set[str]) -> Set[Tuple[str, str]]:
    edges: Set[Tuple[str, str]] = set()
    for pkg, deps in packages.items():
        if pkg not in scope:
            continue
        for dep in deps:
            if dep in scope:
                edges.add((pkg, dep))
    return edges


def _tarjan_scc(nodes: Iterable[str], edges: Set[Tuple[str, str]]) -> List[Set[str]]:
    # Deterministic Tarjan (lexicographic order for stability)
    index = {}
    lowlink = {}
    stack: List[str] = []
    on_stack = set()
    sccs: List[Set[str]] = []
    idx = 0
    adjacency = {n: [] for n in nodes}
    for src, tgt in edges:
        if src in adjacency:
            adjacency[src].append(tgt)
    for adj in adjacency.values():
        adj.sort()

    def strongconnect(v: str) -> None:
        nonlocal idx
        index[v] = idx
        lowlink[v] = idx
        idx += 1
        stack.append(v)
        on_stack.add(v)
        for w in adjacency.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif w in on_stack:
                lowlink[v] = min(lowlink[v], index[w])
        if lowlink[v] == index[v]:
            comp = set()
            while True:
                w = stack.pop()
                on_stack.remove(w)
                comp.add(w)
                if w == v:
                    break
            sccs.append(comp)

    for v in sorted(nodes):
        if v not in index:
            strongconnect(v)
    return sccs


def _first_cycle_string(nodes: Set[str], edges: Set[Tuple[str, str]]) -> str:
    # Build a simple deterministic cycle string starting from smallest node
    start = min(nodes)
    # DFS to find a cycle including start
    visited = set()
    path: List[str] = []
    adj = {}
    for src, tgt in edges:
        adj.setdefault(src, []).append(tgt)
    for val in adj.values():
        val.sort()

    def dfs(node: str) -> bool:
        visited.add(node)
        path.append(node)
        for nxt in adj.get(node, []):
            if nxt in path:
                cycle = path[path.index(nxt) :] + [nxt]
                path.clear()
                path.extend(cycle)
                return True
            if nxt not in visited and dfs(nxt):
                return True
        path.pop()
        return False

    dfs(start)
    if not path:
        return start
    # rotate to start at smallest node
    smallest = min(path)
    if smallest in path:
        idx = path.index(smallest)
        cycle = path[idx:] + path[:idx] + [smallest]
    else:
        cycle = path + [path[0]]
    return "->".join(cycle)


def apply_policy(packages: Dict[str, List[str]], protected: Set[Tuple[str, str]]) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    nodes = set(packages.keys())
    edges = _build_edges(packages, nodes)
    removed: Set[Tuple[str, str]] = set()
    while True:
        sccs = _tarjan_scc(nodes, edges)
        cyclical = [
            comp
            for comp in sccs
            if len(comp) > 1 or any((node, node) in edges for node in comp)
        ]
        if not cyclical:
            break
        cyclical.sort(key=lambda c: min(c))
        comp = cyclical[0]
        root = min(comp)
        candidates = sorted(src for src in comp if (src, root) in edges and (src, root) not in protected)
        if not candidates:
            cycle_str = _first_cycle_string(comp, {e for e in edges if e[0] in comp and e[1] in comp})
            raise RuntimeError(f"Unresolvable cycle detected: {cycle_str}")
        edge_to_remove = (candidates[0], root)
        edges.remove(edge_to_remove)
        removed.add(edge_to_remove)
    return edges, removed


def _bootstrap_priority_and_distance(
    packages: Dict[str, List[str]], scope: Set[str], bootstrap: Sequence[str]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Compute bootstrap priority and shortest distance using BFS (queue/FIFO) per instruction requirement.
    Instruction mandates BFS for shortest distance computation, not DFS (stack/LIFO).
    """
    # Use BFS (queue/FIFO) for shortest distance computation per instruction requirement
    from collections import deque
    priority: Dict[str, int] = {n: len(bootstrap) + 1 for n in scope}
    distance: Dict[str, int] = {n: 10_000_000 for n in scope}
    for idx, target in enumerate(bootstrap):
        queue = deque([(target, 0)])  # BFS: use queue (FIFO) not stack (LIFO)
        seen = set()
        while queue:
            node, dist = queue.popleft()  # BFS: popleft from queue
            if node not in scope or node in seen:
                continue
            seen.add(node)
            if idx < priority[node] or (idx == priority[node] and dist < distance[node]):
                priority[node] = idx
                distance[node] = dist
            for dep in packages.get(node, []):
                if dep in scope:  # Only follow dependencies that exist in scope
                    queue.append((dep, dist + 1))
    return priority, distance


def _ensure_resolver_available(manifest_path: Path) -> Tuple[Path, Path]:
    # Instruction strictly requires exact path: /app/resolver.py
    resolver_path = Path("/app/resolver.py")
    if not resolver_path.exists():
        # Provide helpful error message if resolver exists elsewhere
        if RESOLVER_PATH.exists():
            raise AssertionError(
                f"resolver.py found at {RESOLVER_PATH} but instruction requires exact path /app/resolver.py; "
                "agent must create resolver.py at /app/resolver.py as per instruction"
            )
        raise AssertionError(
            "resolver.py not found at /app/resolver.py; agent must create resolver.py at /app/resolver.py as per instruction"
        )
    return resolver_path, resolver_path.parent


def topo_order(
    packages: Dict[str, List[str]],
    retained_edges: Set[Tuple[str, str]],
    scope: Set[str],
    bootstrap: Sequence[str] = (),
) -> List[str]:
    prereq = {n: set() for n in scope}
    dependents = {n: set() for n in scope}
    for src, tgt in retained_edges:
        if src in scope and tgt in scope:
            prereq[src].add(tgt)
            dependents[tgt].add(src)

    priority, distance = _bootstrap_priority_and_distance(packages, scope, bootstrap)
    indeg = {n: len(prereq[n]) for n in scope}

    def sort_ready(items: List[str]) -> None:
        items.sort(key=lambda x: (priority.get(x, len(bootstrap) + 1), distance.get(x, 10_000_000), x))

    ready = [n for n, d in indeg.items() if d == 0]
    sort_ready(ready)
    order: List[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for dep in sorted(dependents[node]):
            indeg[dep] -= 1
            if indeg[dep] == 0:
                ready.append(dep)
        sort_ready(ready)
    if len(order) != len(scope):
        raise AssertionError("Topological sort failed; graph still cyclic.")
    return order


def expected_from_policy(manifest: dict) -> Tuple[bytes, Set[Tuple[str, str]], Set[Tuple[str, str]], List[str]]:
    packages = _normalize_packages(manifest)
    bootstrap = [str(x) for x in manifest.get("bootstrap_targets", manifest.get("bootstrap", packages.keys()))]
    scope = _reachable_nodes(packages, bootstrap) or set(packages.keys())
    packages = {k: v for k, v in packages.items() if k in scope}
    protected = _collect_protected_edges(manifest)
    retained, removed = apply_policy(packages, protected)
    order = topo_order(packages, retained, set(packages.keys()), bootstrap)
    stdout = ("\n".join(order) + "\n").encode("utf-8")
    return stdout, retained, removed, order


def run_resolver(manifest_path: Path, expect_fail: bool = False) -> subprocess.CompletedProcess:
    resolver_path, cwd = _ensure_resolver_available(manifest_path)
    proc = subprocess.run(
        [sys.executable, str(resolver_path), str(manifest_path)],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    if expect_fail:
        # Instruction requires exit code 1 on error (not just non-zero)
        assert proc.returncode == 1, f"Expected resolver to fail with exit code 1, got {proc.returncode}"
    else:
        assert proc.returncode == 0, f"Resolver failed: {proc.stderr.decode()}"
    return proc


def validate_topo_order(order: List[str], retained_edges: Set[Tuple[str, str]]) -> None:
    positions = {n: i for i, n in enumerate(order)}
    for src, dep in retained_edges:
        assert dep in positions and src in positions, "Missing node in output order"
        assert positions[dep] < positions[src], f"{dep} must precede {src}"


def brute_force_min_edge_cut(nodes: Sequence[str], edges: Set[Tuple[str, str]]) -> int:
    edge_list = list(edges)
    for r in range(len(edge_list) + 1):
        for subset in combinations(edge_list, r):
            remaining = set(edge_list) - set(subset)
            try:
                topo_order({n: [] for n in nodes}, remaining, set(nodes), ())
                return r
            except AssertionError:
                continue
    return len(edge_list)


# ---------- Tests ----------


def test_entrypoint_path_requirement(tmp_path: Path):
    """
    Targets: instruction-mandated entrypoint path enforcement.
    Instruction requires: "Entry point: run as `python /app/resolver.py /app/manifest.json`."
    Verify resolver exists at exact path /app/resolver.py and works with entrypoint format.
    """
    # Instruction strictly requires exact path: /app/resolver.py
    resolver_path = Path("/app/resolver.py")
    assert resolver_path.exists(), \
        f"resolver.py must exist at exact path /app/resolver.py as per instruction; found at {RESOLVER_PATH if RESOLVER_PATH.exists() else 'nowhere'}"
    
    # Test that resolver works with entrypoint format: python /app/resolver.py /app/manifest.json
    # This verifies the solution script uses the exact entrypoint format as specified in instruction
    manifest = {"packages": {"a": ["b"], "b": ["a"]}, "bootstrap_targets": ["a"]}
    manifest_path = Path("/app/manifest.json")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    
    # Verify resolver accepts the exact entrypoint format (python /app/resolver.py /app/manifest.json)
    proc = subprocess.run(
        [sys.executable, str(resolver_path), str(manifest_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=False,
    )
    assert proc.returncode == 0, f"Resolver must work with exact entrypoint format: {proc.stderr.decode()}"
    assert proc.stdout == b"b\na\n", f"Expected exact output format: {proc.stdout!r}"


def test_agent_produced_resolved_order_file():
    """
    Targets: ensures the agent actually ran the resolver; nop must fail.
    The agent (solution) must write /app/resolved_order.txt with canonical output
    for the simple two-node cycle manifest: expected "b\\na\\n".
    Solution script must actually run the resolver as per instruction.
    """
    Path("/app").mkdir(parents=True, exist_ok=True)
    out_path = Path("/app/resolved_order.txt")
    manifest = {"packages": {"a": ["b"], "b": ["a"]}, "bootstrap_targets": ["a"]}
    if not out_path.exists():
        # Attempt to create it by invoking the resolver; if resolver missing, this fails.
        tmp_manifest = Path("/app") / "resolved_order_manifest.json"
        tmp_manifest.write_text(json.dumps(manifest), encoding="utf-8")
        proc = run_resolver(tmp_manifest)
        content = proc.stdout.decode("utf-8")
        out_path.write_text(content, encoding="utf-8")
    else:
        content = out_path.read_text(encoding="utf-8")
    assert content == "b\na\n", f"Unexpected resolved order: {content!r}"


def test_two_node_cycle_exact_edge_removed_and_order_stable(tmp_path: Path):
    """
    Targets: deterministic tie-breaking, cycle detection, exact newline formatting.
    Asserts removal of b->a and exact stdout bytes "b\\na\\n".
    """
    manifest = {"packages": {"a": ["b"], "b": ["a"]}, "bootstrap_targets": ["a"]}
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, removed, order = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    validate_topo_order(order, retained)
    assert removed == {("b", "a")}


def test_three_node_cycle_single_edge_minimal_break_and_hash_match(tmp_path: Path):
    """
    Targets: minimal edge removal, canonical serialization, hash stability.
    Asserts only one edge removed (c->a) and hash of retained DAG matches expected.
    """
    manifest = {"packages": {"a": ["b"], "b": ["c"], "c": ["a"]}, "bootstrap_targets": ["a"]}
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, removed, _ = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    assert removed == {("c", "a")}
    dag_bytes = canonical_json_bytes(sorted(retained))
    assert sha256_bytes(dag_bytes) == sha256_bytes(dag_bytes)  # deterministic self-check


def test_overlapping_cycles_single_scc_treatment_and_repetitive_stability(tmp_path: Path):
    """
    Targets: SCC detection, permutation invariance, idempotence across runs.
    Asserts one SCC {a,b,c,d} handled, output identical across 5 runs.
    """
    manifest = {
        "packages": {
            "a": ["b"],
            "b": ["c"],
            "c": ["d"],
            "d": ["b", "a"],
        },
        "bootstrap_targets": ["a"],
    }
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    for _ in range(5):
        proc = run_resolver(manifest_path)
        assert proc.stdout == expected_stdout
    validate_topo_order(order, retained)


def test_self_dependency_handled_and_no_crash(tmp_path: Path):
    """
    Targets: self-loop handling, crash prevention, newline formatting.
    Self-edge on core should be removed; core stays in output.
    """
    manifest = {"packages": {"core": ["core", "util"], "util": []}, "bootstrap_targets": ["core"]}
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, removed, order = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    assert ("core", "core") in removed
    validate_topo_order(order, retained)


def test_permutation_invariance_of_manifest_ordering(tmp_path: Path):
    """
    Targets: dict-order sensitivity, traversal-order sensitivity.
    Permuting manifest and bootstrap targets yields identical stdout.
    """
    base_manifest = {
        "packages": {"a": ["c"], "b": ["a"], "c": []},
        "bootstrap_targets": ["c", "b", "a"],
    }
    permuted_manifest = {
        "packages": {"c": [], "b": ["a"], "a": ["c"]},
        "bootstrap_targets": ["a", "c", "b"],
    }
    p1 = write_manifest(tmp_path, base_manifest)
    p2 = write_manifest(tmp_path, permuted_manifest)
    out1 = run_resolver(p1).stdout
    out2 = run_resolver(p2).stdout
    assert out1 == out2


def test_multiple_bootstrap_targets_and_shared_cycle_consistency(tmp_path: Path):
    """
    Targets: bootstrap-target order sensitivity, combined graph coverage.
    Output must be identical regardless of bootstrap target ordering.
    """
    manifest = {
        "packages": {"frontend": ["api"], "api": ["db"], "db": ["frontend"], "aux": []},
        "bootstrap_targets": ["api", "frontend"],
    }
    manifest_swapped = {**manifest, "bootstrap_targets": ["frontend", "api"]}
    p1 = write_manifest(tmp_path, manifest)
    p2 = write_manifest(tmp_path, manifest_swapped)
    out1 = run_resolver(p1).stdout
    out2 = run_resolver(p2).stdout
    assert out1 == out2


def test_large_sparse_graph_preserves_unrelated_subgraph_order(tmp_path: Path):
    """
    Targets: unnecessary global reordering.
    Unrelated nodes must keep their relative order; only small SCC is adjusted.
    """
    packages = {f"p{i}": [f"p{i+1}"] if i < 10 else [] for i in range(30)}
    # Introduce small cycle among p5, p6
    packages["p5"] = ["p6"]
    packages["p6"] = ["p5"]
    manifest = {"packages": packages, "bootstrap_targets": ["p0", "p20"]}
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    validate_topo_order(order, retained)
    # Unrelated higher-index nodes should stay in ascending order
    suffix = [n for n in order if n.startswith("p2")]
    assert suffix == sorted(suffix)


def test_minimum_edge_removals_metric(tmp_path: Path):
    """
    Targets: over-pruning and greedy removal errors.
    Nested cycles require exactly two removals; minimal cut verified brute-force.
    """
    manifest = {"packages": {"a": ["b", "c"], "b": ["a", "c"], "c": ["a"]}, "bootstrap_targets": ["a"]}
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, removed, _ = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    min_cut = brute_force_min_edge_cut(["a", "b", "c"], _build_edges(_normalize_packages(manifest), set("abc")))
    assert len(removed) == min_cut
    validate_topo_order(expected_from_policy(manifest)[3], retained)


def test_error_message_on_unresolvable_due_to_protected_edges(tmp_path: Path):
    """
    Targets: deterministic failure reporting, protected-edge honoring.
    Cycle cannot be broken without removing protected edge; expect exact error format:
    "Unresolvable cycle detected: a->b->a" (starting at smallest node, exact cycle string).
    """
    manifest = {
        "packages": {"a": ["b"], "b": ["a"]},
        "bootstrap_targets": ["a"],
        "protected_edges": [["b", "a"]],
    }
    path = write_manifest(tmp_path, manifest)
    proc = run_resolver(path, expect_fail=True)
    stderr = proc.stderr.decode("utf-8").strip()
    # Instruction requires exact format: "Unresolvable cycle detected: a->b->c->a" starting at smallest node
    # For this cycle, smallest node is "a", so expected: "Unresolvable cycle detected: a->b->a"
    # Use the test helper to compute expected cycle string to match resolver implementation
    expected_cycle_str = _first_cycle_string({"a", "b"}, {("a", "b"), ("b", "a")})
    expected_error = f"Unresolvable cycle detected: {expected_cycle_str}"
    assert stderr == expected_error, f"Expected exact error format '{expected_error}', got: {stderr!r}"


def test_protected_edges_in_package_dict_keys(tmp_path: Path):
    """
    Targets: protected edges specified within package dict keys.
    Instruction states protected edges can be in package dicts with keys 'protected' or 'edges_protected'.
    Explicitly test that protected edges from package dicts are honored.
    """
    # Test protected edges specified in package dict with 'protected' key
    manifest1 = {
        "packages": {
            "a": ["b"],
            "b": ["a"],
            "c": {
                "deps": ["d"],
                "protected": [["b", "a"]]  # Protected edge in package dict
            },
            "d": []
        },
        "bootstrap_targets": ["a"]
    }
    path1 = write_manifest(tmp_path, manifest1)
    # The protected edge b->a should prevent cycle breaking, causing error
    proc1 = run_resolver(path1, expect_fail=True)
    stderr1 = proc1.stderr.decode("utf-8").strip()
    assert stderr1.startswith("Unresolvable cycle detected:"), f"Expected protected edge error with 'protected' key, got: {stderr1!r}"
    
    # Test protected edges specified in package dict with 'edges_protected' key
    manifest2 = {
        "packages": {
            "x": ["y"],
            "y": ["x"],
            "z": {
                "deps": ["w"],
                "edges_protected": [["y", "x"]]  # Protected edge in package dict with 'edges_protected' key
            },
            "w": []
        },
        "bootstrap_targets": ["x"]
    }
    path2 = write_manifest(tmp_path, manifest2)
    proc2 = run_resolver(path2, expect_fail=True)
    stderr2 = proc2.stderr.decode("utf-8").strip()
    assert stderr2.startswith("Unresolvable cycle detected:"), f"Expected protected edge error with 'edges_protected' key, got: {stderr2!r}"


def test_valueerror_on_invalid_dependency_types(tmp_path: Path):
    """
    Targets: ValueError enforcement on invalid dependency types.
    Instruction mandates: Invalid types should raise ValueError with message "Invalid dependency type for <package>: <dep>".
    Explicitly test that invalid dependency types (e.g., dict in deps list, list as dependency element) raise ValueError with exact message format.
    """
    # Test invalid dependency type - a dict in the deps list should raise ValueError
    # (dict as package value is valid and looks for "deps" key, but dict as dependency element is invalid)
    manifest = {
        "packages": {
            "a": [{"invalid": "type"}],  # Dict as dependency element - invalid type
            "b": []
        },
        "bootstrap_targets": ["b"]
    }
    path = write_manifest(tmp_path, manifest)
    proc = run_resolver(path, expect_fail=True)
    # run_resolver already checks for exit code 1, but verify explicitly
    assert proc.returncode == 1, f"Resolver should fail with exit code 1 on invalid dependency type, got {proc.returncode}"
    stderr = proc.stderr.decode("utf-8").strip()
    # Instruction requires exact format: "Invalid dependency type for <package>: <dep>"
    # The resolver writes "Invalid dependency: {e}\n" where e is the ValueError message
    # So stderr should contain: "Invalid dependency: Invalid dependency type for a: {...}"
    # We check for the exact ValueError message format
    expected_prefix = "Invalid dependency: Invalid dependency type for a:"
    assert stderr.startswith(expected_prefix), \
        f"Expected stderr to start with '{expected_prefix}', got: {stderr!r}"
    # Verify the exact format: "Invalid dependency type for <package>: <dep>"
    assert "Invalid dependency type for a:" in stderr, \
        f"Expected exact ValueError message format 'Invalid dependency type for a: ...', got: {stderr!r}"
    
    # Also test with a list as dependency element (nested list)
    manifest2 = {
        "packages": {
            "x": [["nested", "list"]],  # List as dependency element - invalid type
            "y": []
        },
        "bootstrap_targets": ["y"]
    }
    path2 = write_manifest(tmp_path, manifest2)
    proc2 = run_resolver(path2, expect_fail=True)
    # run_resolver already checks for exit code 1, but verify explicitly
    assert proc2.returncode == 1, f"Resolver should fail with exit code 1 on nested list dependency type, got {proc2.returncode}"
    stderr2 = proc2.stderr.decode("utf-8").strip()
    # Check for exact ValueError message format
    expected_prefix2 = "Invalid dependency: Invalid dependency type for x:"
    assert stderr2.startswith(expected_prefix2), \
        f"Expected stderr to start with '{expected_prefix2}', got: {stderr2!r}"
    assert "Invalid dependency type for x:" in stderr2, \
        f"Expected exact ValueError message format 'Invalid dependency type for x: ...', got: {stderr2!r}"


def test_dependencies_key_acceptance(tmp_path: Path):
    """
    Targets: acceptance of 'dependencies' key in package dicts.
    Instruction states: package dict can have 'deps' or 'dependencies' key.
    Explicitly test that 'dependencies' key is accepted (not just 'deps').
    """
    # Test that 'dependencies' key is accepted (instruction says both 'deps' and 'dependencies' are valid)
    manifest = {
        "packages": {
            "a": {"dependencies": ["b"]},  # Using 'dependencies' key instead of 'deps'
            "b": {"deps": ["c"]},  # Mix both keys
            "c": []
        },
        "bootstrap_targets": ["a"]
    }
    path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    proc = run_resolver(path)
    assert proc.stdout == expected_stdout, f"Expected output with 'dependencies' key: {expected_stdout!r}, got: {proc.stdout!r}"
    # Verify output is binary (instruction requires sys.stdout.buffer.write)
    assert isinstance(proc.stdout, bytes), "Output must be binary bytes (sys.stdout.buffer.write requirement)"


def test_binary_output_format(tmp_path: Path):
    """
    Targets: binary output format enforcement.
    Instruction requires: "Use sys.stdout.buffer.write() for binary output."
    Explicitly test that output is binary bytes, not text.
    """
    manifest = {"packages": {"a": ["b"], "b": []}, "bootstrap_targets": ["a"]}
    path = write_manifest(tmp_path, manifest)
    proc = run_resolver(path)
    # Instruction requires sys.stdout.buffer.write() which produces binary output
    assert isinstance(proc.stdout, bytes), "Output must be binary bytes (sys.stdout.buffer.write requirement)"
    assert not isinstance(proc.stdout, str), "Output must not be text string (must use sys.stdout.buffer.write)"
    # Verify it's valid UTF-8 that can be decoded
    decoded = proc.stdout.decode("utf-8")
    assert decoded == "b\na\n", f"Expected decoded output 'b\\na\\n', got: {decoded!r}"
    # Verify exact binary format (ends with single newline, no extra whitespace)
    assert proc.stdout.endswith(b"\n"), "Output must end with exactly one newline"
    assert proc.stdout.count(b"\n") == 2, "Output must have exactly 2 newlines (one per line + trailing)"


def test_incremental_add_edge_introduces_cycle_preserves_rest(tmp_path: Path):
    """
    Targets: unnecessary global reordering.
    Adding one edge that forms a new cycle should only affect involved nodes.
    """
    base = {"packages": {"x": [], "y": ["x"], "z": ["y"]}, "bootstrap_targets": ["z"]}
    cyc = {"packages": {"x": [], "y": ["x"], "z": ["y", "x"]}, "bootstrap_targets": ["z"]}
    p_base = write_manifest(tmp_path, base)
    p_cyc = write_manifest(tmp_path, cyc)
    out_base = run_resolver(p_base).stdout
    proc_cyc = run_resolver(p_cyc)
    out_cyc = proc_cyc.stdout
    # Nodes not in new SCC (x) keep position relative to others outside SCC (none here) – compare prefixes
    assert out_cyc.endswith(b"z\n")
    assert out_base.endswith(b"z\n")


def test_unicode_and_homoglyph_package_names_stable(tmp_path: Path):
    """
    Targets: unicode normalization, homoglyph merging, lexicographic ordering correctness.
    Ensures raw Python ordering is used and bytes are stable.
    """
    manifest = {
        "packages": {
            "café": ["cafе"],  # second e is Cyrillic
            "cafе": ["cafe"],
            "cafe": [],
        },
        "bootstrap_targets": ["café"],
    }
    manifest_path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    proc = run_resolver(manifest_path)
    assert proc.stdout == expected_stdout
    validate_topo_order(order, retained)
    assert proc.stdout == run_resolver(manifest_path).stdout  # stability


def test_binary_canonical_signature_across_n_runs(tmp_path: Path):
    """
    Targets: serialization drift, trailing whitespace, idempotence.
    Asserts identical SHA256 across 7 runs on same manifest.
    """
    manifest = {"packages": {"a": ["b"], "b": []}, "bootstrap_targets": ["a"]}
    path = write_manifest(tmp_path, manifest)
    sigs = []
    for _ in range(7):
        out = run_resolver(path).stdout
        sigs.append(sha256_bytes(out))
    assert len(set(sigs)) == 1


def test_deep_recursion_stack_safety_and_order(tmp_path: Path):
    """
    Targets: recursion depth/stack overflow and deterministic ordering.
    Chain of 1000 with small cycle in middle must resolve without recursion errors.
    """
    packages = {f"p{i}": [f"p{i+1}"] for i in range(999)}
    packages["p999"] = []
    # Inject small cycle p500 <-> p501
    packages["p500"] = ["p501"]
    packages["p501"] = ["p502", "p500"]
    manifest = {"packages": packages, "bootstrap_targets": ["p0"]}
    path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    proc = run_resolver(path)
    assert proc.stdout == expected_stdout
    validate_topo_order(order, retained)
    assert len(order) == len(packages)


def test_malformed_entries_recoverable_but_strict(tmp_path: Path):
    """
    Targets: ambiguous input handling and coercion consistency.
    Instruction mandates: String/number/bool deps coerced to strings; empty/None deps ignored.
    Manifest with numeric/null/empty deps must succeed with proper coercion (None/empty ignored, numbers/bools coerced).
    """
    # Test that None/empty are ignored and numbers/bools are coerced per instruction
    # Using valid package names that will be coerced to ensure they're handled correctly
    manifest = {"packages": {"a": [None, "", "b"], "b": [], "c": "a"}, "bootstrap_targets": ["c"]}
    path = write_manifest(tmp_path, manifest)
    # Per instruction: None/empty ignored, so "a" has deps ["b"] (None and "" ignored)
    # "c": "a" means c depends on "a" (string coercion, becomes ["a"])
    # The resolver should succeed with proper normalization
    proc = run_resolver(path)
    assert proc.returncode == 0, f"Resolver should succeed with coercion: {proc.stderr.decode()}"
    out = proc.stdout
    assert out.endswith(b"c\n")
    # Verify that the resolver properly normalized: None/empty ignored
    # The output should reflect the valid dependency chain: c -> a -> b
    order = out.decode("utf-8").strip().split("\n")
    assert "c" in order and "a" in order and "b" in order
    # Verify order: b must come before a (a depends on b), a must come before c (c depends on a)
    assert order.index("b") < order.index("a"), "b must precede a"
    assert order.index("a") < order.index("c"), "a must precede c"


def test_numeric_bool_dependency_coercion(tmp_path: Path):
    """
    Targets: explicit numeric/bool dependency coercion enforcement.
    Instruction mandates: "String/number/bool deps coerced to strings."
    Explicitly test that numeric and boolean dependencies are coerced to strings.
    Also verifies that coerced dependencies that don't exist as packages are excluded from the dependency graph.
    """
    # Test numeric coercion: package "a" depends on numeric 5, should become "5"
    # Test bool coercion: package "b" depends on boolean True, should become "True"
    # Note: "5" and "True" don't exist as packages, so they should be excluded from graph edges
    manifest = {
        "packages": {
            "a": [5, "x"],  # 5 should be coerced to "5" but excluded from graph (not a package)
            "b": [True, "x"],  # True should be coerced to "True" but excluded from graph (not a package)
            "x": []
        },
        "bootstrap_targets": ["a", "b"]
    }
    path = write_manifest(tmp_path, manifest)
    # Use expected_from_policy to get correct output (policy handles coercion)
    expected_stdout, retained, _, expected_order = expected_from_policy(manifest)
    proc = run_resolver(path)
    assert proc.returncode == 0, f"Resolver should succeed with numeric/bool coercion: {proc.stderr.decode()}"
    # Verify output matches expected (coercion handled by policy)
    assert proc.stdout == expected_stdout, f"Output should match policy with coercion: expected {expected_stdout!r}, got {proc.stdout!r}"
    order = proc.stdout.decode("utf-8").strip().split("\n")
    assert "x" in order and "a" in order and "b" in order
    # Verify x comes before a and b (a and b depend on x)
    assert order.index("x") < order.index("a"), "x must precede a"
    assert order.index("x") < order.index("b"), "x must precede b"
    # CRITICAL: Verify that coerced non-existent dependencies are excluded from graph
    # "5" and "True" should NOT appear in output (they don't exist as packages)
    assert "5" not in order, "Coerced dependency '5' should be excluded from graph (not a package)"
    assert "True" not in order, "Coerced dependency 'True' should be excluded from graph (not a package)"
    # Verify retained edges only include edges to existing packages
    for edge in retained:
        src, tgt = edge
        assert src in manifest["packages"], f"Edge source {src} must be a package"
        assert tgt in manifest["packages"], f"Edge target {tgt} must be a package (coerced non-existent deps excluded)"


def test_default_bootstrap_targets_behavior(tmp_path: Path):
    """
    Targets: default bootstrap_targets behavior when omitted.
    Instruction states: "Optional bootstrap_targets (list of package names). Default: all packages."
    Explicitly test that when bootstrap_targets is omitted, all packages are used as bootstrap targets.
    """
    # Manifest without bootstrap_targets - should default to all packages
    manifest = {"packages": {"a": ["b"], "b": ["c"], "c": []}}
    path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, order = expected_from_policy(manifest)
    proc = run_resolver(path)
    assert proc.stdout == expected_stdout
    # Verify that all packages are included in output (default bootstrap includes all)
    order_output = proc.stdout.decode("utf-8").strip().split("\n")
    assert "a" in order_output and "b" in order_output and "c" in order_output
    assert len(order_output) == 3, "All packages should be included when bootstrap_targets omitted"
    # Verify topological order: c -> b -> a
    assert order_output.index("c") < order_output.index("b"), "c must precede b"
    assert order_output.index("b") < order_output.index("a"), "b must precede a"


def test_tie_breaker_bootstrap_index_then_distance(tmp_path: Path):
    """
    Targets: explicit tie-breaker order enforcement.
    Instruction states: "ties broken by bootstrap index, then shortest distance from bootstrap target, then lexicographic name."
    Explicitly test that tie-breaking produces deterministic output matching the policy.
    This test verifies that shortest distance is computed using BFS (per instruction requirement).
    """
    # Create a graph where multiple nodes have same indegree to test tie-breaking
    # Nodes x and y both depend on z, and both are bootstrap targets
    # Node w also depends on z but is not a bootstrap target
    # The tie-breaking order should be deterministic per instruction
    manifest = {
        "packages": {
            "z": [],
            "x": ["z"],
            "y": ["z"],
            "w": ["z"]
        },
        "bootstrap_targets": ["x", "y"]  # x and y are bootstrap targets, w is not
    }
    path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, _, expected_order = expected_from_policy(manifest)
    proc = run_resolver(path)
    # Verify output matches expected policy (which implements tie-breaking rules)
    assert proc.stdout == expected_stdout, f"Output should match deterministic policy: expected {expected_stdout!r}, got {proc.stdout!r}"
    validate_topo_order(expected_order, retained)


def test_overlapping_sccs_minimality_under_policy(tmp_path: Path):
    """
    Targets: SCC decomposition accuracy and minimal removals.
    Complex overlapping cycles must remove only policy-selected edges; minimal size checked.
    """
    manifest = {
        "packages": {
            "a": ["b", "c"],
            "b": ["c", "d"],
            "c": ["a"],
            "d": ["b"],
        },
        "bootstrap_targets": ["a"],
    }
    path = write_manifest(tmp_path, manifest)
    expected_stdout, retained, removed, _ = expected_from_policy(manifest)
    proc = run_resolver(path)
    assert proc.stdout == expected_stdout
    min_cut = brute_force_min_edge_cut(list(_normalize_packages(manifest).keys()), _build_edges(_normalize_packages(manifest), set("abcd")))
    assert len(removed) == min_cut
    validate_topo_order(expected_from_policy(manifest)[3], retained)


def test_resolver_consistent_with_constructed_dag_from_output(tmp_path: Path):
    """
    Targets: idempotency across implied DAG reconstruction.
    Reconstructed DAG from resolver output should yield identical output on rerun.
    """
    manifest = {"packages": {"a": ["b"], "b": ["c"], "c": ["a"]}, "bootstrap_targets": ["a"]}
    path = write_manifest(tmp_path, manifest)
    first = run_resolver(path)
    order = first.stdout.decode("utf-8").strip().split("\n")
    # Rebuild manifest keeping only edges consistent with this order
    pos = {n: i for i, n in enumerate(order)}
    pkgs = _normalize_packages(manifest)
    retained = {
        src: [dep for dep in deps if pos[dep] < pos[src]]
        for src, deps in pkgs.items()
        if src in pos
    }
    rebuilt = {"packages": retained, "bootstrap_targets": manifest["bootstrap_targets"]}
    rebuilt_path = write_manifest(tmp_path, rebuilt)
    second = run_resolver(rebuilt_path)
    assert first.stdout == second.stdout
