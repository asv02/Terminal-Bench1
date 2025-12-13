# Semantic Version Lockfile Canonicalizer

## Task Description

You are tasked with implementing a lockfile canonicalizer that validates and normalizes dependency lockfiles using semantic versioning (semver) rules. The canonicalizer must parse a lockfile format, resolve dependencies according to semver constraints, and output a canonical (sorted and deterministically formatted) lockfile.

## Required Implementation

Create a file `/app/solution.py` with a function `canonicalize(input_path: str, output_path: str) -> None` that:

1. Reads a lockfile from `input_path`
2. Parses and validates the dependency information
3. Resolves dependencies according to semver rules
4. Writes a canonicalized lockfile to `output_path`

### Function Signature

```python
def canonicalize(input_path: str, output_path: str) -> None:
    """
    Canonicalize a lockfile.
    
    Args:
        input_path: Path to input lockfile
        output_path: Path where canonicalized lockfile should be written
    """
    pass
```

## Input Format

The input file contains two sections:

1. **UNIVERSE section**: Defines all available package versions and their dependencies
2. **LOCK section**: Defines the current lockfile state (may be incomplete or invalid)

### UNIVERSE Format

```
UNIVERSE
package@version:
  dependency1 range1
  dependency2 range2

package@version:
  dependency3 range3
```

- Each package version is specified as `package@version` followed by a colon
- Dependencies are listed on subsequent lines, indented with exactly 2 spaces
- Each dependency line has format: `dependency_package version_range`
- Multiple dependency lines for the same package are combined with AND logic
- Blank lines separate package blocks

### LOCK Format

```
LOCK
package@version
  dependency@version
    transitive_dependency@version
```

- Packages are listed as `package@version` (not indented)
- Direct dependencies are indented with 2 spaces
- Transitive dependencies are indented with 4 spaces (2 spaces per level)
- The root package is the one not referenced as a dependency by any other package

## Output Format

The output must be a canonicalized lockfile with:

1. **Sorted packages**: ALL packages (including the root package) must appear at the top level, sorted lexicographically by package name, then by version
2. **Tree structure**: Dependencies are shown as an indented tree (2 spaces per level) beneath their parent package
3. **Deterministic formatting**: Same input always produces identical output
4. **Complete transitive closure**: All required dependencies must be included
5. **No duplicates**: Each `package@version` appears exactly ONCE in the entire output

**CRITICAL Formatting Rules - Read Carefully:**

- **Each package@version appears EXACTLY ONCE in the output** - never duplicated
- When formatting the output:
  1. Sort all packages by (package_name, version) lexicographically
  2. For each package in sorted order, output it at top level (no indentation) with its dependency tree indented below
  3. When building the dependency tree, if a dependency has already been output at top level, DO NOT output it again in the tree - skip it to avoid duplicates
  4. The tree structure shows relationships, but packages only appear once at top level
- The root package is NOT special - it appears in the sorted list like any other package
- Top-level packages (those with no indentation) must be sorted lexicographically by (package_name, version)

**Formatting Algorithm (Step-by-Step):**
```
1. Resolve all dependencies to get the complete set of packages: {a@1.0.0, b@1.0.0, root@1.0.0}
2. Sort all packages by (package_name, version) lexicographically: [a@1.0.0, b@1.0.0, root@1.0.0]
3. Initialize an empty set "formatted" to track which packages have been output
4. For each package in sorted order:
   a. If package is NOT in "formatted":
      - Add it to "formatted"
      - Output it at top level (no indentation): "a@1.0.0"
      - For each of its dependencies:
        * If dependency is NOT in "formatted":
          - Add it to "formatted"
          - Output it indented (2 spaces): "  b@1.0.0"
          - Recursively output its dependencies with more indentation
        * If dependency IS in "formatted":
          - SKIP it (don't output it again)
   b. If package IS in "formatted":
      - SKIP it (already output)
```

**Example walkthrough:**
- Packages: `{a@1.0.0, b@1.0.0, root@1.0.0}`, sorted: `[a@1.0.0, b@1.0.0, root@1.0.0]`
- Process `a@1.0.0` (first in sorted order):
  - Not in formatted, so output "a@1.0.0" at top level (indent=0), add to formatted
  - `a@1.0.0` depends on `b@1.0.0`, which is not in formatted, so output "  b@1.0.0" indented (indent=1), add to formatted
- Process `b@1.0.0` (second in sorted order):
  - Already in formatted (was output as dependency of a@1.0.0), so SKIP - don't output again
- Process `root@1.0.0` (third in sorted order):
  - Not in formatted, so output "root@1.0.0" at top level (indent=0), add to formatted
  - `root@1.0.0` depends on `a@1.0.0`, which IS in formatted, so SKIP - don't show it again
- Final output:
```
a@1.0.0
  b@1.0.0
root@1.0.0
```

**Key observation**: `b@1.0.0` appears ONLY as an indented dependency of `a@1.0.0`, not at top level, because it was output as a dependency before its turn in the sorted list. This is correct - each package appears exactly once.

**Important**: The example walkthrough above shows the CORRECT output format. Each package@version appears exactly once. The `b@1.0.0` that appears indented under `a@1.0.0` is the ONLY occurrence of `b@1.0.0` in the output - it does NOT appear again at top level because it was already output as a dependency.

**Key point**: When a package is output as a dependency (indented), it is added to the "formatted" set. When the algorithm later processes that same package in the sorted list, it sees it's already formatted and SKIPS it, so it doesn't appear again at top level.

## Semantic Versioning Rules

### Version Format

Semantic versions follow the format: `MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]`
- Examples: `1.2.3`, `1.2.3-alpha`, `1.2.3+20240101`

### Version Ranges

The canonicalizer must support these range formats:

1. **Exact version**: `1.2.3` or `=1.2.3`
2. **Comparison operators**: `>=1.2.3`, `>1.2.3`, `<=2.0.0`, `<2.0.0`
3. **Caret range**: `^1.2.3`
   - `^1.2.3` means `>=1.2.3 <2.0.0`
   - `^0.2.3` means `>=0.2.3 <0.3.0` (special case for 0.x.y)
   - `^0.0.3` means `>=0.0.3 <0.0.4`
4. **Tilde range**: `~1.2.3` means `>=1.2.3 <1.3.0`
5. **Wildcard**: `1.*` means any version with major=1, `1.2.*` means any version with major=1 and minor=2
6. **Hyphen range**: `1.2.3 - 2.3.4` means `>=1.2.3 <=2.3.4` (inclusive on both ends)
7. **Multiple ranges**: `>=1.2.3, <2.0.0` (comma-separated, combined with AND logic)

### Prerelease Handling

- **Prereleases are forbidden by default**: Unless the range explicitly allows prereleases (e.g., ends with `-0`), only stable versions should be selected
- If a range like `>=1.2.3 <2.0.0` has only prerelease versions available but also an older stable version that satisfies, choose the older stable version
- Prerelease versions are only considered when explicitly allowed in the range specification

### Dependency Resolution Rules

1. **Transitive closure**: All dependencies of dependencies must be included in the output
2. **Version selection**: When multiple versions satisfy a range:
   - Prefer stable versions over prerelease versions
   - When closures have the same size, prefer solutions that minimize the total number of packages
   - When multiple minimal closures exist, break ties by comparing (package_name, version) tuples lexicographically
3. **Validation and Correction**: The lockfile must match the declared dependencies in the UNIVERSE:
   - If `a@1.0.0` declares `b ^2.1.0`, the lockfile must use a version of `b` that satisfies `^2.1.0`
   - Even if a different version of `b` satisfies the root package's constraints, it must match the exact declared dependency
   - **Invalid lockfile entries must be corrected**: If the LOCK section specifies a dependency version that doesn't satisfy the UNIVERSE constraints, the canonicalizer must override it and select a valid version that satisfies the constraints
   - Example: If `a@1.0.0` requires `b ^2.1.0` but the lockfile has `b@2.0.0`, the output must use `b@2.1.0` (or another version satisfying `^2.1.0`) instead
4. **Cyclic dependencies**: Must be handled correctly without infinite expansion:
   - Each `package@version` appears exactly ONCE in the entire output
   - When formatting the dependency tree:
     * Output each package at top level in sorted order
     * When showing a package's dependencies, only show dependencies that haven't been output yet at top level
     * If a dependency was already output at top level, skip it in the tree (don't show it again)
   - This ensures cycles don't cause infinite loops or duplicate output
   - The tree structure shows dependency relationships, but each package@version appears only once at the top level in the sorted list

### Tie-Breaking Rules

When multiple valid resolutions exist:

1. **Minimize package set size**: Prefer solutions that introduce fewer total packages
2. **Lexicographic tie-breaking for same-size closures**: When multiple resolutions have the same closure size (same number of packages), use the following precise tie-breaking algorithm:
   
   **Algorithm for tie-breaking:**
   - When you have multiple packages that need version selection and all have the same closure size:
     1. Sort all packages that need version selection by package name lexicographically (ASCII order)
     2. For the lexicographically FIRST package, prefer the HIGHER version that still allows all other packages to be resolved
     3. Once the first package's version is chosen, resolve remaining packages in order, preferring higher versions
   
   **Concrete example with step-by-step:**
   - Input: Root depends on both `a ^1.0.0` and `z ^1.0.0`
   - Available versions: `a@1.0.0`, `a@1.1.0`, `z@1.0.0`, `z@1.1.0`
   - Both `a@1.0.0` and `a@1.1.0` satisfy `^1.0.0`, same for `z`
   - Both closures have the same size (1 package each - no dependencies)
   - **Step 1**: Sort packages by name: `['a', 'z']` (a comes before z)
   - **Step 2**: For the first package `a`, prefer higher version: choose `a@1.1.0` over `a@1.0.0`
   - **Step 3**: For the next package `z`, both versions work, but since `a` already got the higher version, choose `z@1.0.0`
   - **Result**: `{a@1.1.0, z@1.0.0}` is preferred over `{a@1.0.0, z@1.1.0}`
   
   **Key principle**: When closures are equal size, resolve packages in lexicographic order by name, and for each package, prefer the higher version that still allows all remaining packages to be resolved.

## Canonical Formatting Requirements

1. **Deterministic output**: Running the canonicalizer multiple times on the same input must produce identical output (byte-for-byte identical)

2. **Sorted packages**: Packages are processed in sorted order (lexicographically by package name, then by version), but they may appear at different indentation levels:
   - Packages are processed in sorted order: `[a@1.0.0, b@1.0.0, root@1.0.0]`
   - When a package is processed, if it hasn't been output yet, it's output at the current indentation level
   - If a package appears as a dependency (indented) before it's processed in sorted order, it's already marked as formatted and skipped when its turn comes
   - **Test requirement**: The test checks that all top-level lines (those not starting with spaces) are sorted lexicographically

3. **Consistent indentation**: Use exactly 2 spaces per indentation level for dependencies

4. **No duplicate packages - CRITICAL**: Each `package@version` combination appears exactly ONCE in the entire output
   - A package may appear at top level (no indentation) OR as an indented dependency, but never both
   - If a package is output as a dependency first (indented), it's marked as formatted and won't appear again at top level
   - If a package is output at top level first, it won't appear again as a dependency in other trees
   - This ensures no package@version appears twice, even in cyclic dependencies

5. **Tree structure**: Dependencies are shown indented below their parent:
   - When outputting a package's dependency tree, only show dependencies that haven't been output yet
   - If a dependency was already output (either at top level or in another tree), skip it
   - The tree structure shows relationships, but each package@version appears only once in the entire output

## Examples

### Example 1: Basic Resolution

**Input:**
```
UNIVERSE
root@1.0.0:
  dep ^1.0.0

dep@1.0.0:

dep@1.1.0:

LOCK
root@1.0.0
```

**Expected Output:**
```
dep@1.0.0
root@1.0.0
  dep@1.0.0
```

### Example 2: Prerelease Handling

**Input:**
```
UNIVERSE
pkg@1.0.0:

pkg@1.2.3-alpha:

pkg@1.2.4:

LOCK
pkg@1.2.4
```

**Expected Output:**
```
pkg@1.2.4
```

Note: `1.2.3-alpha` is not selected because prereleases are forbidden unless explicitly allowed.

### Example 3: Transitive Dependencies

**Input:**
```
UNIVERSE
root@1.0.0:
  a ^1.0.0

a@1.0.0:
  b ^1.0.0

b@1.0.0:

LOCK
root@1.0.0
  a@1.0.0
```

**Expected Output:**
```
a@1.0.0
  b@1.0.0
b@1.0.0
root@1.0.0
  a@1.0.0
```

Note: `b@1.0.0` must be included even though it wasn't in the original LOCK section.

### Example 4: Invalid Lockfile Correction

**Input:**
```
UNIVERSE
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
```

**Expected Output:**
```
a@1.0.0
  b@2.1.0
b@2.1.0
root@1.0.0
  a@1.0.0
```

Note: The lockfile specified `b@2.0.0`, but `a@1.0.0` requires `b ^2.1.0`, so the output must use `b@2.1.0` instead.

### Example 5: Cyclic Dependencies

**Input:**
```
UNIVERSE
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
```

**Expected Output:**
```
a@1.0.0
  b@1.0.0
b@1.0.0
root@1.0.0
  a@1.0.0
```

**Explanation:**
- All packages sorted: `a@1.0.0`, `b@1.0.0`, `root@1.0.0`
- `a@1.0.0` appears first (sorted), with `b@1.0.0` shown as its dependency (indented)
- `b@1.0.0` appears next at top level. It depends on `a@1.0.0`, but `a@1.0.0` was already output, so it's NOT shown again in `b@1.0.0`'s tree
- `root@1.0.0` appears last, with `a@1.0.0` shown as its dependency. `b@1.0.0` is NOT shown again because it was already output at top level

**Critical point**: Each package@version appears exactly ONCE in the output. The tree structure shows relationships, but once a package is output at top level, it's never shown again, even if other packages depend on it.

## Implementation Notes

- The solution must handle edge cases including cyclic dependencies, missing transitive closures, and invalid lockfile entries
- Invalid lockfile entries that don't match UNIVERSE constraints must be corrected automatically
- Version comparison must correctly handle prerelease versions (stable > prerelease)
- The output must be deterministic and properly sorted - all packages at top level, sorted lexicographically
- All dependency constraints must be satisfied according to semver rules
- When multiple valid resolutions exist with the same closure size, prefer higher versions for lexicographically earlier packages
