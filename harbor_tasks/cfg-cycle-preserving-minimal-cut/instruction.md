## CFG Cycle-Preserving Minimal Cut with Natural Loop Analysis

You are debugging a **control-flow graph (CFG) optimization problem** that requires deep understanding of **advanced compiler optimization theory**. The CFG may contain subtle structural issues that you must identify and reason about to solve correctly.

### Problem Statement

You are given a directed control-flow graph (CFG) in JSON format. This task requires understanding of **specialized compiler optimization concepts** including natural loops, back edges, dominator trees, reducible CFGs, and critical edge analysis. Your task is to remove the smallest number of edges such that:

1. All nodes that are originally reachable from the entry node and can reach the exit node STILL remain reachable from entry and can reach exit after removals.

2. All essential cycles are preserved (no essential edges are removed). 
   - **Definition**: An essential cycle is a cycle that contains **at least one** essential edge.
   - **CRITICAL**: If a cycle contains even ONE essential edge, the entire cycle is essential and MUST be preserved completely.
   - **You CANNOT break an essential cycle** by removing non-essential edges from it, even if the cycle contains both essential and non-essential edges.
   - Example: If cycle [5,6,7] contains edges 5 (essential), 6 (essential), 7 (non-essential), the cycle is essential and you cannot remove edge 7.
   - **Overlapping cycles**: If two cycles share edges and any shared edge is essential, both cycles are essential (because they each contain that essential edge) and neither can be broken.

3. **ALL non-essential cycles must be eliminated** (broken by removing at least one edge from each non-essential cycle). 
   - **Definition**: A non-essential cycle is a cycle that contains **NO essential edges** (zero essential edges).
   - **CRITICAL**: A cycle is non-essential ONLY if ALL its edges are non-essential. If a cycle has even one essential edge, it is essential and cannot be broken.
   - This includes self-loops, simple cycles, and complex cycles. Every single non-essential cycle in the graph must be broken - there are no exceptions.

**CRITICAL BESPOKE RULE (Must Be Applied to Non-Essential Cycles):** When breaking non-essential cycles, you must follow standard lexicographic ordering. However, for non-essential cycles with exactly 3 edges where the sum of edge indices is divisible by 7, you MUST break that cycle by removing the edge with the smallest index among non-essential edges in that cycle. This rule applies independently to each qualifying non-essential cycle and takes precedence over general lexicographic ordering for those specific cycles. This is NOT optional - it is a required part of the cycle-breaking procedure. **If a cycle is essential (contains any essential edge), the bespoke rule does NOT allow breaking it; essential cycles must be preserved.**

Among all minimal cuts satisfying the above, choose the lexicographically smallest sorted list of removed edge indices (subject to the rule above).

### Advanced Compiler Theory Concepts (Background Knowledge - Not Strictly Required)

The following concepts provide **background knowledge** that may help you understand and solve the problem. However, you are free to implement the solution using any approach that produces the correct output. The tests verify correctness of the output, not the specific implementation approach:

1. **Natural Loops and Back Edges**: In compiler terminology, a natural loop is identified by finding back edges. A back edge (u→v) exists when v dominates u in the dominator tree. The target of a back edge is called the loop header. Natural loops have a unique header node in reducible CFGs.

2. **Dominator Trees**: Node d dominates node n if every path from the entry node to n passes through d. The dominator tree is a tree structure where each node's parent is its immediate dominator. This is critical for identifying natural loops correctly.

3. **Reducible vs Irreducible CFGs**: A reducible CFG is one where all cycles are natural loops (identified by back edges). In irreducible CFGs, some cycles cannot be identified by back edges alone. For this task, assume the CFG is reducible unless debugging reveals otherwise.

4. **Critical Edges**: A critical edge is an edge from a node with multiple outgoing edges to a node with multiple incoming edges. Critical edges complicate optimization and may affect essential edge detection.

5. **Post-Dominance**: Node p post-dominates node n if every path from n to the exit node passes through p. This is the dual of dominance and is used in some advanced analyses.

6. **Loop Nesting Depth**: The nesting depth of a loop is how deeply it is nested within other loops. Nested loops create complex cycle structures.

7. **Back Edge Classification**: Not all cycles are identified by back edges in the same way. Some back edges create simple loops, while others create complex nested structures.

### Multi-Step Algorithm (Each Step Can Fail Independently)

**Phase 1: Input Validation and Root Cause Debugging (Recommended Approach)**

The following describes a recommended approach for handling the CFG structure. You should ensure your solution correctly handles all valid inputs as defined by the input format. Common issues to be aware of:

- **Invalid Node References**: Edges may reference nodes not in the node set. You must identify which edges are invalid and reason about their impact.
- **Unreachable Exit**: The exit node may be unreachable from entry. You must determine if this is a structural issue or a data issue.
- **Degenerate Cycles**: Multiple self-loops on the same node (all edges have identical source and target) create degenerate cycles. These require special handling.
- **Disconnected Components**: Nodes may form disconnected components. You must identify which components are reachable and which are not.
- **Entry/Exit Validation**: Entry and exit nodes must exist in the node set. If they don't, you must identify the root cause.

**Debugging Process:**
1. Validate all edge endpoints reference valid nodes. If invalid edges exist, identify them and reason about whether they should be ignored or if the input is malformed.
2. Check if entry and exit nodes are in the node set. If not, determine the correct behavior.
3. Verify reachability foundation: can entry reach exit? If not, identify why (structural issue, missing edges, etc.).
4. Detect degenerate cases: identify cycles where all edges have identical source and target nodes.

**Phase 2: Natural Loop Detection Using Advanced Compiler Theory (Background Knowledge)**

The following describes one approach using natural loops, back edges, and dominator analysis. You may use any cycle detection method that correctly identifies all cycles:

1. **Build Dominator Tree**: Compute the dominator tree for the CFG. This requires iterative data-flow analysis:
   - Initialize: DOM[entry] = {entry}
   - For each node n ≠ entry: DOM[n] = {n} ∪ (∩ DOM[p] for all predecessors p of n)
   - Iterate until convergence
   - Build dominator tree: parent(n) = immediate dominator of n

2. **Identify Back Edges**: An edge (u→v) is a back edge if v dominates u in the dominator tree. Back edges identify natural loops.

3. **Enumerate Natural Loops**: For each back edge (u→v), the natural loop consists of:
   - All nodes that can reach u without passing through v
   - Plus node v (the loop header)
   - Plus all edges connecting these nodes

4. **Handle Self-Loops**: Self-loops (u→u) are special cases where u dominates itself, creating a natural loop with a single node.

5. **Detect All Cycles**: Use DFS with coloring (WHITE/GRAY/BLACK) to find all cycles, not just natural loops. This is necessary because some cycles may not be natural loops in complex graphs.

**Phase 3: Essential Edge Detection (Requires Careful Reasoning)**

An edge is "essential" if removing that single edge alone breaks the reachability property. This requires careful analysis:

1. **Algorithm for Determining Essential Edges**:
   For each edge e:
   - Create a modified CFG with ONLY edge e removed (all other edges remain)
   - Check if all originally-reachable nodes (from entry, to exit) remain reachable in the modified CFG
   - **Compare against the ORIGINAL CFG**: Check if nodes that were reachable in the original CFG are still reachable after removing edge e
   - If any originally-reachable node becomes unreachable, edge e is essential
   - If all originally-reachable nodes remain reachable, edge e is non-essential
   - **Overlapping cycles clarification**: This essential-edge test is done per edge, independent of how many cycles the edge participates in. If the test says the edge is essential, then every cycle containing that edge is essential and cannot be broken.

2. **Edge Cases to Handle**:
   - An edge may appear non-essential but be essential due to cycle dependencies
   - Multiple paths may exist, but removing one edge may break all paths through a critical cycle
   - Self-loops on essential nodes may or may not be essential themselves

3. **Important**: After determining which edges are essential, use this information to classify cycles (see Phase 4)

**Phase 4: Cycle Classification with Advanced Analysis**

Classify each cycle as essential or non-essential:

1. **Essential Cycle**: Contains at least one essential edge. These cycles must be preserved.
   - **CRITICAL**: If a cycle contains even ONE essential edge, the entire cycle is essential and MUST be preserved
   - **You CANNOT break an essential cycle** by removing non-essential edges from it
   - Even if a cycle contains both essential and non-essential edges, if it has at least one essential edge, you must preserve the entire cycle
   - Example: If cycle [5,6,7] has edges 5 (essential), 6 (essential), 7 (non-essential), the cycle is essential and you cannot remove edge 7

2. **Non-Essential Cycle**: Contains NO essential edges (zero essential edges). These cycles must be broken.
   - **CRITICAL**: A cycle is non-essential ONLY if ALL its edges are non-essential
   - If a cycle has even one essential edge, it is essential and cannot be broken
   - You can only break cycles where every single edge is non-essential

3. **Degenerate Cycles**: Multiple self-loops on the same node. These are non-essential unless they contain essential edges.
   - If any self-loop edge is essential, the degenerate cycle is essential

4. **Nested Cycles**: Cycles within cycles. Each must be classified independently.
   - Classify each cycle separately based on whether it contains essential edges

**Phase 5: Cycle-Breaking Rule Application (CRITICAL BESPOKE RULE - NOT OPTIONAL)**

When breaking non-essential cycles, follow this procedure:

1. **Standard Procedure**: For each non-essential cycle, identify candidate edges to remove. Among all valid minimal cuts, choose lexicographically smallest.

2. **CRITICAL BESPOKE RULE (MANDATORY)**: For cycles with exactly 3 edges:
   - Calculate the sum of edge indices in the cycle
   - If the sum is divisible by 7:
     - Identify all non-essential edges in that cycle
     - **THIS CYCLE MUST BE BROKEN** by removing the edge with the **smallest index** among those non-essential edges
     - This rule is MANDATORY and takes precedence over general lexicographic ordering for this specific cycle
     - This is NOT optional - it is a required part of the cycle-breaking procedure
   - If the sum is not divisible by 7, use standard lexicographic ordering

3. **Multiple Qualifying Cycles**: If multiple cycles qualify for the bespoke rule, apply the rule independently to each qualifying cycle.

4. **Integration with Lexicographic Ordering**: The bespoke rule takes precedence for qualifying cycles, but the overall solution must still be lexicographically smallest among all valid minimal cuts that satisfy the bespoke rule.

**Applicability Reminder:** The bespoke rule is checked **after** classifying cycles. It only applies to non-essential cycles (cycles with zero essential edges). Essential cycles (containing any essential edge) must not be broken, regardless of the bespoke rule.

**Phase 6: Minimal Cut Computation (Complex Multi-Step Process)**

Find the minimal set of non-essential edges to remove:

1. **Iterative Search**: Try removing sets of edges, starting with smallest sets (0, 1, 2, ... edges).

2. **For Each Candidate Set**, verify:
   - **No essential edges removed**: Essential edges must be preserved
   - **Reachability preserved**: All originally-reachable nodes remain reachable
   - **Bespoke rule satisfied**: All qualifying 3-edge cycles with sum divisible by 7 are broken correctly
   - **ALL non-essential cycles eliminated**:
     - Enumerate ALL cycles after removal (including self-loops and degenerate cycles)
     - Verify each remaining cycle contains at least one essential edge
     - If ANY non-essential cycle remains, the candidate is INVALID

3. **Cycle Detection After Removal**: After removing edges, you must re-detect all cycles to ensure none remain. This requires:
   - Re-running DFS cycle detection
   - Checking all self-loops
   - Verifying degenerate cycles are handled

4. **Find Minimal Size**: Find the smallest k such that a valid set of k edges exists.

**Phase 7: Lexicographic Selection (Final Step)**

Among all valid minimal cuts of size k, choose lexicographically smallest:

1. **Lexicographic Order**: Compare lists element by element from left to right
2. **Example**: [1,2] < [1,3] < [2,1] < [2,3]
3. **Note**: Bespoke rule may constrain which edges can be removed, affecting lexicographic choices

### CLI

Create a shell script `/app/solution.sh` that accepts command-line arguments:

```
bash solution.sh --input /app/cfg.json --out /app/result.txt
```

**Script Structure:**
- The script must be executable and located at `/app/solution.sh`
- The script must parse the `--input` and `--out` (or `--output`) arguments
- The script can be a pure shell script or a wrapper that calls Python code
- You can use Python's standard library (including `argparse`) for argument parsing if calling Python code

**Argument Parsing:**
- `--input <path>`: Path to the input JSON file (required)
- `--out <path>` or `--output <path>`: Path to the output file where results should be written (required)

**Complete Shell Script Example:**
Here is a complete working example showing proper bash argument parsing and variable usage:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Initialize variables
INPUT_FILE=""
OUTPUT_FILE=""

# Parse command-line arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --input) 
      INPUT_FILE="$2"
      shift 2
      ;;
    --out|--output) 
      OUTPUT_FILE="$2"
      shift 2
      ;;
    *) 
      shift
      ;;
  esac
done

# CRITICAL: Variables MUST be expanded with $ prefix when used
# CORRECT: "$INPUT_FILE" expands to the actual file path
# WRONG: '${INPUT_FILE}' (with quotes around the variable name) passes literal string
# WRONG: INPUT_FILE (without $) passes literal string "INPUT_FILE"
# WRONG: '${INPUT_FILE}' (single quotes prevent expansion) passes literal string
# NOTE: Use absolute paths for Python scripts (e.g., /app/your_script.py)
python3 /app/your_script.py --input "$INPUT_FILE" --out "$OUTPUT_FILE"
```

**CRITICAL: Common Shell Script Mistakes to Avoid:**
1. **Variable Expansion**: You MUST use `$VARIABLE` or `"$VARIABLE"` (with $ prefix) to expand variables. Common mistakes:
   - ❌ `python3 /app/script.py --input '${INPUT_FILE}'` - Single quotes prevent expansion, passes literal string "${INPUT_FILE}"
   - ❌ `python3 /app/script.py --input INPUT_FILE` - Missing $ prefix, passes literal string "INPUT_FILE"
   - ❌ `python3 /app/script.py --input '${INPUT_FILE}'` - Single quotes around variable name prevent expansion
   - ✅ `python3 /app/script.py --input "$INPUT_FILE"` - CORRECT: double quotes allow expansion and handle spaces
   - ✅ `python3 /app/script.py --input "${INPUT_FILE}"` - Also CORRECT: ${} syntax works, but $VARIABLE is simpler

2. **Quoting**: Always use double quotes around variables: `"$INPUT_FILE"` to handle paths with spaces. Single quotes prevent variable expansion.

3. **Shebang**: Start your script with `#!/usr/bin/env bash` or `#!/bin/bash`

4. **Error Handling**: Consider using `set -euo pipefail` for better error handling

5. **Testing**: After creating your script, test it manually to ensure variables expand correctly:
   ```bash
   bash /app/solution.sh --input /app/cfg.json --out /app/result.txt
   ```

**Alternative Approach:**
You can also use Python's `argparse` module directly if calling Python code, which avoids shell variable expansion issues entirely.

**File I/O:**
- Read the input JSON file from the path specified by `--input` (use `"$INPUT_FILE"` after parsing - note the $ prefix for variable expansion)
- Write the output (one edge index per line) to the path specified by `--out` or `--output` (use `"$OUTPUT_FILE"` after parsing - note the $ prefix)
- Ensure the output file is created/overwritten with the results
- **VERIFY**: The script must actually read from the file path provided by `--input` and write to the file path provided by `--out`, not hardcoded paths

### Input format (/app/cfg.json)

The input is a JSON object with the following structure:

```json
{
  "nodes": [1, 2, ...],
  "entry": 1,
  "exit": N,
  "edges": [
    {"from": 1, "to": 2},
    ...
  ]
}
```

- `nodes`: Array of node identifiers (integers)
- `entry`: Integer identifier of the entry node
- `exit`: Integer identifier of the exit node
- `edges`: Array of edge objects, each with `from` and `to` fields
  - Edge indices are numbered 1..M in the order they appear in the array

### Output format (/app/result.txt)

Each removed edge index (sorted, ascending), one per line.

### Constraints and Requirements

**Implementation Constraints:**
- Use only Python standard library (no external graph libraries) - this is a constraint on available tools, not a testable requirement
- Output must be deterministic (same input always produces same output)

**Output Format Requirements (Tested):**
- Edge indices start from 1 (not 0)
- Output one edge index per line, sorted in ascending order
- If no edges need to be removed, output an empty file (or no lines)

### Dependencies

- Runtime: Python 3.11+ standard library (already provided by base image)
- No third-party Python packages are required

### Debugging Hints

When debugging issues:

1. **If reachability fails**: Check if entry/exit nodes are valid, if edges reference valid nodes, and if there's a path from entry to exit.
2. **If cycle detection fails**: Verify you're detecting all cycles, including self-loops and degenerate cycles. Use DFS with proper coloring.
3. **If essential edge detection fails**: Remember to compare against the ORIGINAL CFG, not just check reachability in the modified graph.
4. **If bespoke rule fails**: Check if cycles have exactly 3 edges and if the sum is divisible by 7. Remember to apply the rule independently to each qualifying cycle.
5. **If minimal cut fails**: Ensure ALL non-essential cycles are broken. Re-detect cycles after removal to verify.

The harness will invoke `bash solution.sh --input /app/cfg.json --out /app/result.txt` multiple times with different CFGs. Make sure your implementation correctly handles all cases and produces deterministic output.
