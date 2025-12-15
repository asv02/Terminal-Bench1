# Graph Cycle Detector with Path Reconstruction

Create an executable Python script at `/app/cycle_detector.py` that detects cycles in directed graphs and reconstructs the exact cycle paths.

## Requirements

### 1. Input Format
The script must read from `/app/input.json` containing:
```json
{
  "nodes": ["A", "B", "C", "D"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C"},
    {"from": "C", "to": "A"},
    {"from": "D", "to": "A"}
  ],
  "detect_all_cycles": false,
  "min_cycle_length": 2,
  "ignore_self_loops": false
}
```

**Fields:**
- `nodes`: List of node identifiers (strings)
- `edges`: List of directed edges with `from` and `to` fields
- `detect_all_cycles`: If `true`, find all simple cycles; if `false`, find first cycle only
- `min_cycle_length`: Minimum cycle length to report (default: 2)
- `ignore_self_loops`: If `true`, ignore edges from a node to itself

### 2. Output Format
Write to `/app/output.json`:
```json
{
  "has_cycle": true,
  "cycles": [
    {
      "path": ["A", "B", "C", "A"],
      "length": 3,
      "nodes_involved": ["A", "B", "C"]
    }
  ],
  "total_cycles_found": 1,
  "graph_stats": {
    "node_count": 4,
    "edge_count": 4,
    "is_strongly_connected": false,
    "has_self_loops": false
  }
}
```

**Fields:**
- `has_cycle`: Boolean indicating if any cycle exists
- `cycles`: Array of cycle objects, each containing:
  - `path`: Ordered list of nodes forming the cycle (first and last node are the same)
  - `length`: Number of edges in the cycle
  - `nodes_involved`: Unique nodes in the cycle (excluding the repeated start/end node)
- `total_cycles_found`: Total number of cycles detected
- `graph_stats`: Statistics about the graph structure

### 3. Cycle Detection Rules

**Simple Cycles:**
- A cycle must return to the starting node
- No node (except start/end) should appear more than once in the path
- Path must have at least `min_cycle_length` edges

**Self-loops:**
- Edge from node to itself (e.g., A → A)
- Counted as cycle of length 1 unless `ignore_self_loops` is `true`

**All Cycles Mode:**
- When `detect_all_cycles` is `true`, find all simple cycles
- Use efficient algorithm (e.g., Johnson's algorithm or Tarjan's)
- Cycles should be reported in lexicographically sorted order by their canonical form
- Canonical form: rotate cycle to start with lexicographically smallest node

**First Cycle Mode:**
- When `detect_all_cycles` is `false`, return immediately after finding first cycle
- Use DFS-based detection for efficiency

### 4. Graph Statistics

**is_strongly_connected:**
- `true` if there's a path from every node to every other node
- For an empty graph (0 nodes), return `false` (no nodes means no connectivity)
- For a single node with no edges, return `true` (trivially connected to itself)
- Use Kosaraju's or Tarjan's algorithm for multi-node graphs

**has_self_loops:**
- `true` if any node has an edge to itself

### 5. Edge Cases
- Empty graph (no nodes) should return `has_cycle: false` and `is_strongly_connected: false`
- Single node with no edges should return `has_cycle: false` and `is_strongly_connected: true`
- Disconnected graph components should all be checked
- Duplicate edges should be treated as single edge
- Invalid node references in edges should result in error
- Missing required fields should result in error

### 6. Error Handling
On error, write to `/app/output.json`:
```json
{
  "has_cycle": false,
  "error": "Description of error"
}
```

### 7. Exit Codes
- `0`: Success (cycle found or not found, but no errors)
- `1`: Error in processing (malformed input, missing files, invalid graph)

## Examples

### Example 1: Simple Triangle Cycle
**Input:**
```json
{
  "nodes": ["A", "B", "C"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "C"},
    {"from": "C", "to": "A"}
  ],
  "detect_all_cycles": false,
  "min_cycle_length": 2
}
```
**Output:**
```json
{
  "has_cycle": true,
  "cycles": [
    {
      "path": ["A", "B", "C", "A"],
      "length": 3,
      "nodes_involved": ["A", "B", "C"]
    }
  ],
  "total_cycles_found": 1,
  "graph_stats": {
    "node_count": 3,
    "edge_count": 3,
    "is_strongly_connected": true,
    "has_self_loops": false
  }
}
```

### Example 2: No Cycle (DAG)
**Input:**
```json
{
  "nodes": ["A", "B", "C", "D"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "A", "to": "C"},
    {"from": "B", "to": "D"},
    {"from": "C", "to": "D"}
  ],
  "detect_all_cycles": false
}
```
**Output:**
```json
{
  "has_cycle": false,
  "cycles": [],
  "total_cycles_found": 0,
  "graph_stats": {
    "node_count": 4,
    "edge_count": 4,
    "is_strongly_connected": false,
    "has_self_loops": false
  }
}
```

### Example 3: Multiple Cycles
**Input:**
```json
{
  "nodes": ["A", "B", "C", "D"],
  "edges": [
    {"from": "A", "to": "B"},
    {"from": "B", "to": "A"},
    {"from": "C", "to": "D"},
    {"from": "D", "to": "C"}
  ],
  "detect_all_cycles": true,
  "min_cycle_length": 2
}
```
**Output:**
```json
{
  "has_cycle": true,
  "cycles": [
    {
      "path": ["A", "B", "A"],
      "length": 2,
      "nodes_involved": ["A", "B"]
    },
    {
      "path": ["C", "D", "C"],
      "length": 2,
      "nodes_involved": ["C", "D"]
    }
  ],
  "total_cycles_found": 2,
  "graph_stats": {
    "node_count": 4,
    "edge_count": 4,
    "is_strongly_connected": false,
    "has_self_loops": false
  }
}
```

### Example 4: Self-Loop Handling
**Input:**
```json
{
  "nodes": ["A", "B"],
  "edges": [
    {"from": "A", "to": "A"},
    {"from": "A", "to": "B"}
  ],
  "detect_all_cycles": true,
  "ignore_self_loops": false
}
```
**Output:**
```json
{
  "has_cycle": true,
  "cycles": [
    {
      "path": ["A", "A"],
      "length": 1,
      "nodes_involved": ["A"]
    }
  ],
  "total_cycles_found": 1,
  "graph_stats": {
    "node_count": 2,
    "edge_count": 2,
    "is_strongly_connected": false,
    "has_self_loops": true
  }
}
```

## Implementation Notes
- Use efficient algorithms: DFS for single cycle, Johnson's algorithm for all cycles
- Handle graphs up to 1,000 nodes and 10,000 edges efficiently
- Time complexity should be O(V + E) for single cycle detection
- For all cycles, use O((V + E)(C + 1)) where C is the number of cycles
- Properly handle strongly connected components
- Ensure cycle paths are correctly reconstructed with exact node order
