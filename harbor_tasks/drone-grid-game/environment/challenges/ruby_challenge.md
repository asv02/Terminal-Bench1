# Ruby Key Challenge: Critical Connections in a Network

## Problem Statement

You are given a network of servers represented as an undirected graph with `n` nodes numbered from `0` to `n-1`. 

A **critical connection** (also known as a **bridge**) is an edge that, if removed, will make some servers unable to reach each other. In other words, removing a bridge will increase the number of connected components in the graph.

Your task is to find all critical connections in the network.

## Input

The network is described in `/app/challenges/ruby_network.txt` with the following format:
- First line: integer `n` (number of nodes)
- Second line: integer `m` (number of edges)
- Next `m` lines: two integers `u v` representing an edge between nodes `u` and `v`

## Output

Write your solution as a Python function in `/app/solutions/ruby_solution.py`:

```python
def find_bridges(n, edges):
    """
    Find all critical connections (bridges) in the network.

    Args:
        n: int - number of nodes (0 to n-1)
        edges: list of [u, v] - undirected edges

    Returns:
        list of [u, v] - list of bridges (order doesn't matter)
    """
    # Your code here
    pass
```

## Example

Input:
```
n = 5
edges = [[0,1], [1,2], [2,0], [1,3], [3,4]]
```

Output:
```
[[1,3], [3,4]]
```

Explanation: Removing edge [1,3] or [3,4] would disconnect the graph.

## Constraints

- 1 ≤ n ≤ 100
- n - 1 ≤ edges.length ≤ 200
- No duplicate edges or self-loops

## Test Cases

Your solution will be tested against 10 hidden test cases including:
- Simple chains and cycles
- Complex graphs with multiple bridges
- Graphs with no bridges
- Edge cases with single nodes

**WARNING: One wrong answer = INSTANT DEATH!**
