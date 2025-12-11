**PRIMARY DELIVERABLE: Create `/app/resolver.py`**

You must create a Python file named `resolver.py` at the exact path `/app/resolver.py`. This file does not exist - you must create it from scratch. This is the main deliverable and is required for all tests to pass.

Implement a deterministic config/dependency resolver CLI in this file.

**CRITICAL REQUIREMENTS:**
1. **You must CREATE the file `/app/resolver.py`** - this file does not exist and must be created
2. **The file must be named exactly `resolver.py`** (not resolver.py.txt or any variant)
3. **The file must be located at `/app/resolver.py`** (absolute path)
4. **The file must contain working Python code** that implements all functionality below
5. **The code must be executable** and produce the correct output format

**CRITICAL IMPLEMENTATION DETAILS (READ CAREFULLY):**
- **Output format is MANDATORY**: All examples in this instruction show REQUIRED outputs, not suggestions. Your resolver MUST produce the exact outputs shown for the exact inputs given. Tests will fail if outputs do not match byte-for-byte.
- **Invalid dependency type validation is REQUIRED**: During normalization, you MUST validate dependency types. If a dependency element is a dict or list (not a package value), you MUST raise ValueError with message exactly "Invalid dependency type for <package>: <dep>". The resolver MUST exit with code 1 when this error occurs. This is not optional - failing to validate will cause tests to fail.
- **Numeric/bool dependencies**: Coerce to strings (5 → "5", True → "True") during normalization. However, only include coerced dependencies in the dependency graph if they exist as package names in the manifest. Dependencies that don't exist as packages are effectively excluded from scope during reachability computation.
- **Cycle string format**: "a->b->a->a" (WITH repeated start node at end) - the cycle string MUST include the start node at both beginning and end. See exact algorithm below.
- **Error messages**: NO "Error:" prefix. Write exactly: "Unresolvable cycle detected: <cycle>" or "Invalid dependency: Invalid dependency type for <pkg>: <dep>".
- **Exit codes**: Exit 1 on error, 0 on success (not just non-zero).
- **Tie-breaking**: Sort by (bootstrap_index, distance, name) tuple - see detailed algorithm below. Bootstrap index is updated per target (earlier bootstrap targets take priority), and distance is minimum across all bootstrap targets.
- **Distance computation**: BFS (queue/FIFO) from each bootstrap target, take minimum distance per node. When multiple bootstrap targets can reach a node, use the distance from the earliest bootstrap target (lowest index) that reaches it. **CRITICAL**: Use BFS with queue (deque.popleft), NOT DFS with stack (list.pop).
- **Topological ordering**: Must follow the exact algorithm specified below. The output order is deterministic and must match the policy implementation exactly.
- **Deep recursion**: Use sys.setrecursionlimit(10000) or iterative algorithms for 1000+ node graphs.

Requirements
- **File name**: You must CREATE and WRITE a Python file named exactly `resolver.py` at `/app/resolver.py`. This file must contain your implementation. Do not use variants like resolver.py.txt or any other name.
- **Entry point**: The resolver must be executable as `python /app/resolver.py /app/manifest.json`.
- Manifest schema:
  - Top-level `packages`: object mapping package name -> deps (list/str/dict with deps/`dependencies`).
  - Optional `bootstrap_targets` (list of package names). Default: all packages.
  - Optional `protected_edges`: list of `[src, dst]` pairs that must not be removed.
- Output: print install order as newline-separated package names, ending with exactly one trailing newline, no extra whitespace.

**Normalization Rules:**
- String/number/bool deps coerced to strings; empty/None deps ignored.
- Protected edges honored.

**Implementation Details for Normalization:**
- For each package's dependencies:
  - If dependency is None or empty string "", ignore it (skip).
  - If dependency is str/int/float/bool, convert to string using str().
  - If dependency is a list, process each element recursively. **REQUIRED**: During recursive processing, if an element is a dict or list, raise ValueError immediately.
  - If dependency is a dict, look for "deps" or "dependencies" key (both are valid).
  - **REQUIRED VALIDATION**: A dict or list as a dependency element (not as a package value) is invalid. You MUST raise ValueError with message exactly: `"Invalid dependency type for <package>: <dep>"` and exit with code 1. This validation must happen during normalization, not later. Examples of invalid: `[{"key": "value"}]` or `[["nested", "list"]]` as dependency elements. Note: A dict as a package value (e.g., `{"a": {"deps": ["b"]}}`) is valid and should be processed to extract dependencies.

- **Protected Edges Collection:**
  Protected edges can be specified in two places:
  1. **Top-level "protected_edges"**: A list of `[src, dst]` pairs at the manifest root.
  2. **Package dict keys**: Within package dictionaries, keys "protected" or "edges_protected" contain lists of edges.
  
  You must collect protected edges from both locations. Iterate through all packages and check for these keys in package dictionaries.
- **CRITICAL**: Numeric and boolean dependencies are COERCED to strings during normalization. However, during scope computation (reachability from bootstrap targets), only dependencies that exist as package names in the manifest are included in the dependency graph. Coerced dependencies like "5" or "True" that don't exist as packages are effectively excluded from the resolution scope.
- Example: If package "a" has dependency [5, True, "b"] and only "b" exists as a package, the normalized dependencies are ["5", "True", "b"], but only "b" will be included in the dependency graph edges and reachability computation.

**Cycle-breaking policy (must be deterministic and minimal):**
1) For any SCC with size >= 2 or a self-loop, pick root = lexicographically smallest node.
2) Remove the edge (src -> root) where src is the lexicographically smallest node in the SCC pointing to root and not protected.
3) Recompute SCCs after each removal; stop removing as soon as the SCC becomes acyclic.
4) If all candidate removals are protected, raise: `Unresolvable cycle detected: a->b->c->a` starting at smallest node.

**Implementation Details for Cycle Breaking:**
- Use strongly connected components (SCCs) to detect cycles. Process nodes in lexicographic order for determinism.
- For each cyclical SCC (size >= 2 or contains self-loop):
  - Root = lexicographically smallest node in the SCC
  - Find all edges (src -> root) where src is in the SCC and edge is not protected
  - Remove the edge from the lexicographically smallest src to root
  - Recompute SCCs and repeat until graph is acyclic
- Error message format: `Unresolvable cycle detected: <cycle-string>` where cycle-string starts at lexicographically smallest node and includes it at the end, e.g., `a->b->a->a` for cycle a->b->a.
- **Cycle String Format:**
  The cycle string must start at the lexicographically smallest node and include it at both the beginning and end. For example, cycle a->b->a should be formatted as "a->b->a->a" (not "a->b->a"). Join nodes with "->" separator.

**Topological order:**
- Stable, deterministic ordering using retained edges; ties broken by bootstrap index, then shortest distance from bootstrap target, then lexicographic name.

**Implementation Details for Topological Ordering:**
- Use Kahn's algorithm (or similar) with retained edges after cycle breaking.
- **EXACT Tie-Breaking Algorithm:**
  For nodes with same indegree (ties), sort by tuple (bootstrap_index, distance, name) in this exact order:
  1. **Bootstrap index** (primary): 
     - Position in bootstrap_targets list (0 for first, 1 for second, etc.).
     - For each node, compute which bootstrap targets can reach it using BFS. Use the index of the EARLIEST bootstrap target (lowest index) that can reach it.
     - Nodes NOT in bootstrap_targets and NOT reachable from any bootstrap target get index = len(bootstrap_targets) (higher than any bootstrap target).
     - Lower index = higher priority.
     - **CRITICAL**: When a node is reachable from multiple bootstrap targets, always use the earliest one's index (even if a later bootstrap target has a shorter path).
  2. **Shortest distance** (secondary):
     - Distance from the bootstrap target that determines the node's bootstrap index.
     - Use BFS (breadth-first search with queue) to compute distances from each bootstrap target.
     - Distance = number of edges traversed (not number of nodes).
     - **CRITICAL**: Process bootstrap targets in order (0, 1, 2, ...). For each node, use the bootstrap_index and distance from the EARLIEST bootstrap target (lowest index) that can reach it. If a node is reachable from multiple bootstrap targets, always use the earliest one's index and distance - do NOT use the minimum distance across all bootstrap targets.
     - Example: If node X is reachable from bootstrap[0] at distance 5, and also from bootstrap[1] at distance 2, use bootstrap_index=0 and distance=5 (earliest bootstrap target wins, not shortest distance).
     - If node is unreachable from all bootstrap targets, use bootstrap_index = len(bootstrap_targets) and distance = large value (e.g., 10,000,000).
     - Lower distance = higher priority, but only when bootstrap indices are equal.
  3. **Lexicographic name** (tertiary):
     - ASCII string comparison using Python's default string ordering.
     - Lexicographically smaller = higher priority.
- **Topological Ordering:**
  Use a topological sort algorithm (e.g., Kahn's algorithm) with the retained edges after cycle breaking. The ordering is determined by the retained edges: if package A depends on B (edge A->B exists in retained edges), then B must appear before A in the output. When multiple nodes are ready (indegree = 0), break ties by sorting by (bootstrap_index, distance, name) tuple. Always maintain the ready queue sorted by this tuple before selecting the next node to process.

**REQUIRED OUTPUT FORMATS (NOT JUST EXAMPLES - THESE ARE MANDATORY):**
- **CRITICAL**: The following examples show REQUIRED outputs. Your resolver MUST produce these exact outputs for these exact inputs. Tests will fail if outputs do not match exactly. The ordering is determined by the retained edges after cycle breaking: if A depends on B (edge A->B in retained edges), then B must come before A in the output.
- For manifest `{"packages": {"a": ["b"], "b": ["a"]}, "bootstrap_targets": ["a"]}`:
  - The cycle `a->b->a` must be broken by removing edge `b->a` (since `b` is lexicographically smallest source pointing to root `a`).
  - After removal, the retained edge is `a->b` (a depends on b). This means b has no dependencies and must be installed first, then a.
  - **REQUIRED OUTPUT**: Exactly `b\na\n` (b first, then a, then exactly one newline). Output "a\nb\n" is WRONG and will fail tests. This is NOT an example - it is the REQUIRED output format.
  - The output must be exactly these bytes: `b'\x62\n\x61\n'` (b, newline, a, newline).
- For manifest `{"packages": {"a": ["b"], "b": ["c"], "c": ["a"]}, "bootstrap_targets": ["a"]}`:
  - The cycle `a->b->c->a` must be broken by removing edge `c->a` (since `c` is lexicographically smallest source pointing to root `a`).
  - Output order is deterministic based on retained edges and tie-breaking rules (see detailed algorithm below).
- **GENERAL RULE**: All outputs must be deterministic - identical inputs must produce identical outputs byte-for-byte. The exact output format is: package names separated by newlines, ending with exactly one trailing newline, no extra whitespace.


Deliverables
- **MANDATORY: You must CREATE and IMPLEMENT a Python file named `resolver.py` at `/app/resolver.py`**. This file must contain working Python code that implements all the requirements above. Write the code yourself - this file does not exist and must be created.
- The `resolver.py` file must implement:
  - **Command-line interface**: Accept one argument (manifest.json path). Usage: `python /app/resolver.py /app/manifest.json`. Exit with code 0 on success, 1 on error. Write errors to stderr.
  - **Manifest loading**: Read JSON from file path, parse packages, bootstrap_targets (default: all packages), protected_edges.
    - **CRITICAL**: Extract protected edges from both top-level "protected_edges" AND from package dicts with "protected" or "edges_protected" keys.
  - **Package normalization**: 
    - Coerce str/int/float/bool to strings, ignore None/empty, handle list/dict formats.
    - **REQUIRED**: Validate dependency types during normalization. If a dependency element is a dict or list (not a package value), raise ValueError with exact message "Invalid dependency type for <package>: <dep>" and exit with code 1. This validation is mandatory - the resolver must not proceed with invalid dependency types.
  - **Scope computation**: Only include packages reachable from bootstrap_targets (transitive closure).
  - **Cycle detection**: Use SCC algorithm to find strongly connected components. Process nodes in sorted order for determinism.
  - **Cycle-breaking policy**: Iteratively remove edges per policy until graph is acyclic. Track removed edges.
  - **Topological ordering**: 
    - Use a topological sort algorithm (e.g., Kahn's algorithm) with retained edges after cycle breaking.
    - Compute bootstrap index (position in bootstrap_targets list) and shortest distance from each bootstrap target using BFS.
    - Sort ready nodes by tuple (bootstrap_index, distance, name) before each selection.
    - Process nodes in sorted order, re-sorting after each node is processed.
    - **CRITICAL**: Output must be deterministic - identical inputs must produce identical outputs.
  - **Error handling (EXACT FORMATS REQUIRED):**
    - For unresolvable cycles: Raise RuntimeError with message exactly "Unresolvable cycle detected: <cycle-string>" (NO "Error:" prefix, NO extra text).
    - For invalid dependency types: Raise ValueError with message exactly "Invalid dependency type for <package>: <dep>" (where <package> is package name, <dep> is the invalid dependency value).
    - In main() function, catch exceptions and write to stderr:
      ```python
      try:
          # ... resolver logic ...
      except ValueError as e:
          sys.stderr.write(f"Invalid dependency: {e}\n")
          return 1
      except RuntimeError as e:
          sys.stderr.write(str(e) + "\n")  # NO "Error:" prefix, just the message
          return 1
      ```
    - **CRITICAL**: Error messages must NOT have "Error:" prefix. Write exactly the exception message.
    - Exit with code 1 on any error, 0 on success.
  - **Output**: Print package names one per line, ending with exactly one newline. Use sys.stdout.buffer.write() for binary output (bytes, not text).
  - **Deep recursion handling**: 
    - Use iterative algorithms (BFS/DFS with explicit stack) or set sys.setrecursionlimit(10000) at the start of the file.
    - Ensure algorithms handle graphs with 1000+ nodes without stack overflow.
    - For SCC detection, use iterative Tarjan's algorithm or equivalent iterative approach.
- Solution script must actually run the resolver (see tests).
