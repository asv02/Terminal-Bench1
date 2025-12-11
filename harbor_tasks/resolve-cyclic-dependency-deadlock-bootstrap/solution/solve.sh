#!/bin/bash
# Oracle solution: run resolver.py on the provided manifest and persist stdout
# to /app/resolved_order.txt so tests can confirm the agent actually ran.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Generate resolver.py from embedded solution code
RESOLVER="/app/resolver.py"
mkdir -p /app
cat > "$RESOLVER" <<'PY'
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set, Tuple

sys.setrecursionlimit(10000)


def load_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_packages(manifest: dict) -> Dict[str, List[str]]:
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
            if isinstance(dep, (str, int, float, bool)):
                deps_clean.append(str(dep))
            else:
                raise ValueError(f"Invalid dependency type for {pkg_name}: {dep}")
        normalized[pkg_name] = deps_clean
    return normalized


def collect_protected_edges(manifest: dict) -> Set[Tuple[str, str]]:
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


def reachable_nodes(packages: Dict[str, List[str]], bootstrap: Sequence[str]) -> Set[str]:
    want = set(map(str, bootstrap))
    stack = list(want)
    while stack:
        node = stack.pop()
        for dep in packages.get(node, []):
            if dep not in want:
                want.add(dep)
                stack.append(dep)
    return want


def build_edges(packages: Dict[str, List[str]], scope: Set[str]) -> Set[Tuple[str, str]]:
    edges: Set[Tuple[str, str]] = set()
    for pkg, deps in packages.items():
        if pkg not in scope:
            continue
        for dep in deps:
            if dep in scope:
                edges.add((pkg, dep))
    return edges


def tarjan_scc(nodes: Iterable[str], edges: Set[Tuple[str, str]]) -> List[Set[str]]:
    index: Dict[str, int] = {}
    lowlink: Dict[str, int] = {}
    stack: List[str] = []
    on_stack: Set[str] = set()
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


def first_cycle_string(nodes: Set[str], edges: Set[Tuple[str, str]]) -> str:
    start = min(nodes)
    visited = set()
    path: List[str] = []
    adj: Dict[str, List[str]] = {}
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
    smallest = min(path)
    idx = path.index(smallest)
    cycle = path[idx:] + path[:idx] + [smallest]
    return "->".join(cycle)


def apply_policy(packages: Dict[str, List[str]], protected: Set[Tuple[str, str]]) -> Tuple[Set[Tuple[str, str]], Set[Tuple[str, str]]]:
    nodes = set(packages.keys())
    edges = build_edges(packages, nodes)
    removed: Set[Tuple[str, str]] = set()
    while True:
        sccs = tarjan_scc(nodes, edges)
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
            cycle_str = first_cycle_string(comp, {e for e in edges if e[0] in comp and e[1] in comp})
            raise RuntimeError(f"Unresolvable cycle detected: {cycle_str}")
        edge_to_remove = (candidates[0], root)
        edges.remove(edge_to_remove)
        removed.add(edge_to_remove)
    return edges, removed


def _bootstrap_priority_and_distance(
    packages: Dict[str, List[str]], scope: Set[str], bootstrap: Sequence[str]
) -> Tuple[Dict[str, int], Dict[str, int]]:
    priority: Dict[str, int] = {n: len(bootstrap) + 1 for n in scope}
    distance: Dict[str, int] = {n: 10_000_000 for n in scope}
    for idx, target in enumerate(bootstrap):
        stack = [(target, 0)]
        seen = set()
        while stack:
            node, dist = stack.pop()
            if node not in scope or node in seen:
                continue
            seen.add(node)
            if idx < priority[node] or (idx == priority[node] and dist < distance[node]):
                priority[node] = idx
                distance[node] = dist
            for dep in packages.get(node, []):
                stack.append((dep, dist + 1))
    return priority, distance


def topo_order(
    packages: Dict[str, List[str]],
    retained_edges: Set[Tuple[str, str]],
    scope: Set[str],
    bootstrap: Sequence[str],
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
        raise RuntimeError("Topological sort failed; graph still cyclic.")
    return order


def resolve(manifest: dict) -> bytes:
    packages = normalize_packages(manifest)
    bootstrap = [str(x) for x in manifest.get("bootstrap_targets", manifest.get("bootstrap", packages.keys()))]
    scope = reachable_nodes(packages, bootstrap) or set(packages.keys())
    packages = {k: v for k, v in packages.items() if k in scope}
    protected = collect_protected_edges(manifest)
    retained, _removed = apply_policy(packages, protected)
    order = topo_order(packages, retained, set(packages.keys()), bootstrap)
    return ("\n".join(order) + "\n").encode("utf-8")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        sys.stderr.write("Usage: python /app/resolver.py /app/manifest.json\n")
        return 1
    manifest_path = Path(argv[1])
    try:
        manifest = load_manifest(manifest_path)
        out = resolve(manifest)
        sys.stdout.buffer.write(out)
    except ValueError as e:
        sys.stderr.write(f"Invalid dependency: {e}\n")
        return 1
    except RuntimeError as e:
        sys.stderr.write(str(e) + "\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
PY

MANIFEST="${1:-/app/manifest.json}"

# Copy resolver.py to task directory so tests can find it
# $ROOT is the task root directory (parent of solution/)
cp "$RESOLVER" "$ROOT/resolver.py"

# If no manifest is provided by the harness, synthesize the minimal
# two-node cycle manifest used in the tests so the oracle always runs.
if [[ ! -f "$MANIFEST" ]]; then
  mkdir -p "$(dirname "$MANIFEST")"
  cat > "$MANIFEST" <<'JSON'
{
  "packages": {"a": ["b"], "b": ["a"]},
  "bootstrap_targets": ["a"]
}
JSON
fi

python "$RESOLVER" "$MANIFEST" > /app/resolved_order.txt