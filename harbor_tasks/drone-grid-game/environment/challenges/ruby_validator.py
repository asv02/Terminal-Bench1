#!/usr/bin/env python3
"""
Validator for Ruby Key Challenge - Graph Bridges
Tests the solution against hidden test cases
"""

import sys
from pathlib import Path

def find_bridges_tarjan(n, edges):
    """Reference solution using Tarjan's algorithm for finding bridges."""
    from collections import defaultdict

    graph = defaultdict(list)
    for u, v in edges:
        graph[u].append(v)
        graph[v].append(u)

    visited = [False] * n
    disc = [0] * n
    low = [0] * n
    parent = [-1] * n
    bridges = []
    timer = [0]

    def dfs(u):
        visited[u] = True
        disc[u] = low[u] = timer[0]
        timer[0] += 1

        for v in graph[u]:
            if not visited[v]:
                parent[v] = u
                dfs(v)
                low[u] = min(low[u], low[v])

                # Check if edge u-v is a bridge
                if low[v] > disc[u]:
                    bridges.append(sorted([u, v]))
            elif v != parent[u]:
                low[u] = min(low[u], disc[v])

    for i in range(n):
        if not visited[i]:
            dfs(i)

    return sorted([sorted(b) for b in bridges])

# Test cases
TEST_CASES = [
    # Test 1: Simple chain
    {
        'n': 4,
        'edges': [[0,1], [1,2], [2,3]],
        'expected': [[0,1], [1,2], [2,3]]
    },
    # Test 2: Cycle with bridge
    {
        'n': 5,
        'edges': [[0,1], [1,2], [2,0], [1,3], [3,4]],
        'expected': [[1,3], [3,4]]
    },
    # Test 3: No bridges (complete cycle)
    {
        'n': 4,
        'edges': [[0,1], [1,2], [2,3], [3,0]],
        'expected': []
    },
    # Test 4: Multiple components
    {
        'n': 6,
        'edges': [[0,1], [1,2], [2,0], [3,4], [4,5]],
        'expected': [[3,4], [4,5]]
    },
    # Test 5: Complex graph
    {
        'n': 7,
        'edges': [[0,1], [1,2], [2,0], [1,3], [3,4], [3,5], [4,5], [5,6]],
        'expected': [[1,3], [5,6]]
    },
    # Test 6: Star graph (all bridges)
    {
        'n': 5,
        'edges': [[0,1], [0,2], [0,3], [0,4]],
        'expected': [[0,1], [0,2], [0,3], [0,4]]
    },
    # Test 7: Two cycles connected
    {
        'n': 6,
        'edges': [[0,1], [1,2], [2,0], [2,3], [3,4], [4,5], [5,3]],
        'expected': [[2,3]]
    },
    # Test 8: Single edge
    {
        'n': 2,
        'edges': [[0,1]],
        'expected': [[0,1]]
    },
    # Test 9: Larger graph
    {
        'n': 8,
        'edges': [[0,1], [0,2], [1,2], [2,3], [3,4], [4,5], [5,6], [6,7], [7,4]],
        'expected': [[2,3], [3,4]]
    },
    # Test 10: No edges
    {
        'n': 3,
        'edges': [],
        'expected': []
    }
]

def main():
    if len(sys.argv) < 2:
        print("Usage: python ruby_validator.py <solution_file>")
        sys.exit(1)

    solution_file = Path(sys.argv[1])

    if not solution_file.exists():
        print(f"Solution file not found: {solution_file}")
        sys.exit(1)

    # Import the solution
    import importlib.util
    spec = importlib.util.spec_from_file_location("solution", solution_file)
    solution_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solution_module)

    if not hasattr(solution_module, 'find_bridges'):
        print("Error: solution must define function 'find_bridges(n, edges)'")
        sys.exit(1)

    find_bridges = solution_module.find_bridges

    # Run all test cases
    passed = 0
    for i, test in enumerate(TEST_CASES, 1):
        n = test['n']
        edges = test['edges']
        expected = sorted([sorted(b) for b in test['expected']])

        try:
            result = find_bridges(n, edges)
            result_sorted = sorted([sorted(b) for b in result])

            if result_sorted == expected:
                passed += 1
            else:
                print(f"Test {i} FAILED")
                print(f"  Input: n={n}, edges={edges}")
                print(f"  Expected: {expected}")
                print(f"  Got: {result_sorted}")
                sys.exit(1)
        except Exception as e:
            print(f"Test {i} CRASHED: {e}")
            sys.exit(1)

    print(f"✅ All {len(TEST_CASES)} test cases passed!")
    sys.exit(0)

if __name__ == '__main__':
    main()
