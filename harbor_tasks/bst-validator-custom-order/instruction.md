# Binary Search Tree Validator with Custom Ordering

Create an executable Python script at `/app/bst_validator.py` that validates whether a given binary tree is a valid Binary Search Tree (BST) according to custom ordering rules.

## Requirements

### 1. Input Format
The script must read from `/app/input.json` containing:
```json
{
  "tree": [10, 5, 15, null, null, 12, 20],
  "comparator": "asc",
  "allow_duplicates": false,
  "exceptions": []
}
```

**Fields:**
- `tree`: Array representation of binary tree (level-order traversal, `null` for missing nodes)
- `comparator`: Either `"asc"` (ascending: left < parent < right) or `"desc"` (descending: left > parent > right)
- `allow_duplicates`: Boolean, if `true` allows duplicate values in the tree
- `exceptions`: Optional list of node indices (0-based) that are exempt from BST validation

### 2. Output Format
Write to `/app/output.json`:
```json
{
  "valid": true,
  "violations": [],
  "node_count": 7,
  "max_depth": 3
}
```

**Fields:**
- `valid`: Boolean indicating if tree is a valid BST
- `violations`: Array of violation descriptions (empty if valid)
- `node_count`: Total number of non-null nodes
- `max_depth`: Maximum depth of the tree (root is depth 1)

### 3. Validation Rules

**For ascending order (`"asc"`):**
- All nodes in left subtree must be **strictly less than** parent
- All nodes in right subtree must be **strictly greater than** parent
- Duplicates are invalid unless `allow_duplicates` is `true`

**For descending order (`"desc"`):**
- All nodes in left subtree must be **strictly greater than** parent
- All nodes in right subtree must be **strictly less than** parent
- Duplicates are invalid unless `allow_duplicates` is `true`

**Exception nodes:**
- Nodes at specified indices (0-based level-order) skip BST validation
- Their subtrees are still validated normally
- Exception nodes still count toward node_count and max_depth

### 4. Edge Cases
- Empty tree (`[]`) is valid
- Single node is always valid
- Tree with only `null` values is treated as empty
- Malformed JSON should result in error output
- Missing required fields should result in error output

### 5. Error Handling
On error, write to `/app/output.json`:
```json
{
  "valid": false,
  "error": "Description of error"
}
```

### 6. Exit Codes
- `0`: Success (valid or invalid tree, but no errors)
- `1`: Error in processing (malformed input, missing files, etc.)

## Examples

### Example 1: Valid Ascending BST
**Input:**
```json
{
  "tree": [10, 5, 15, 2, 7, 12, 20],
  "comparator": "asc",
  "allow_duplicates": false
}
```
**Output:**
```json
{
  "valid": true,
  "violations": [],
  "node_count": 7,
  "max_depth": 3
}
```

### Example 2: Invalid BST
**Input:**
```json
{
  "tree": [10, 5, 15, 2, 12, 11, 20],
  "comparator": "asc",
  "allow_duplicates": false
}
```
**Output:**
```json
{
  "valid": false,
  "violations": ["Node at index 4 (value=12) violates BST property: must be < 10"],
  "node_count": 7,
  "max_depth": 3
}
```

### Example 3: With Exceptions
**Input:**
```json
{
  "tree": [10, 5, 15, 2, 12, 11, 20],
  "comparator": "asc",
  "allow_duplicates": false,
  "exceptions": [4]
}
```
**Output:**
```json
{
  "valid": true,
  "violations": [],
  "node_count": 7,
  "max_depth": 3
}
```

## Implementation Notes
- Use O(n) time complexity for validation
- Handle trees up to 100,000 nodes efficiently
- Properly handle integer overflow cases
- Validate the entire tree structure, not just immediate children
