# Filesystem Atomic Rename Auditor

You are given a trace log of filesystem operations from a POSIX-like system. Each trace contains filesystem calls (`open`, `write`, `fsync`, `rename`, `close`, `dir_fsync`) executed by multiple processes. Your task is to determine whether each `rename()` operation is atomic and crash-safe.

A rename is crash-safe only if:
- All data written to the file has been durably persisted (via `fsync`) before the rename
- The directory metadata has been durably persisted (via `dir_fsync`) after the rename

---

## Input Format

Text file `/app/trace.log` with one operation per line. Format: `pid:operation:arguments`

Operations:
  - `open`: `path:flags:fd=N` (e.g., `1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3`)
- `write`: `fd=N:size=M` or `fd=N:size=?` if size is unknown
- `fsync`: `fd=N`
- `rename`: `from_path:to_path`
- `close`: `fd=N`
- `dir_fsync`: `directory_path`

Lines starting with `#` are comments. Empty lines are ignored. Process operations in chronological order.

## Solution Requirements

Create `/app/solution.py` with:

```python
def audit_renames(trace_path: str, out_path: str) -> None:
    """Analyze trace log and determine atomicity of rename operations."""
```

Call with `trace_path="/app/trace.log"` and `out_path="/app/results.json"`.

## Output Format

JSON file with schema:

```json
{
  "renames": [
    {
      "from": "/source/path",
      "to": "/target/path",
      "pid": 1,
      "status": "SAFE" | "UNSAFE" | "AMBIGUOUS",
      "reason": "Explanation"
    }
  ]
}
```

**Requirements:**
- Each rename appears exactly once, in trace order
- Exactly 5 fields per rename: `from`, `to`, `pid`, `status`, `reason`
- `reason` must be non-empty
- For UNSAFE/AMBIGUOUS, `reason` must contain required keywords (case-insensitive)

### Status Values

**SAFE**: All conditions satisfied:
- File fsynced before rename (or before first rename if file renamed multiple times)
- No writes after fsync on same file descriptor
- Target directory fsynced AFTER rename
- No cross-process file descriptor leaks
- All writes to the file have known sizes

**UNSAFE**: Reason must contain keywords:
- File not fsynced: "fsync"
- Directory not fsynced: "directory" or "dir"
- Write after fsync: "post-fsync write" OR "write after fsync"
- Cross-process FD: "fd", "descriptor", or "open"
- Wrong FD fsync: "wrong", "different", or "fsync"
- Directory fsync timing: "before", "order", or "after"

**AMBIGUOUS**: Missing information. Reason must contain:
- Missing write size: "size" or "unknown" (when `size=?` for writes to the file being renamed)

## Analysis Requirements

### 1. File Descriptor Tracking

File descriptors point to inodes, not paths. When a file is renamed, all open file descriptors to that file continue referencing the same inode.

- Track `(pid, fd)` → file path mappings
- Update all FD mappings when file is renamed
- Remove mappings on `close`
- File descriptors are process-specific

### 2. File Identity Across Renames

A file remains the same file (same inode) across all renames. Track rename chains to identify the original path.

- If file was fsynced before first rename, it remains fsynced for all subsequent renames
- Follow rename chain backwards to find original path where file was opened

### 3. Write Durability

- File must be fsynced before rename (or before first rename if file renamed multiple times)
- Write after fsync on same file descriptor invalidates durability
- Fsync must be on file descriptor for the file being renamed

### 4. Directory fsync

- Target directory must be fsynced AFTER the rename
- Each rename requires its own directory fsync
- Directory fsync after later rename does not protect earlier renames of same file
- If multiple renames target same directory before single fsync, only first rename (by sequence) is protected

### 5. Cross-Process File Descriptor Leaks

If another process has file descriptor to file being renamed, and that process writes to that FD after the rename, the rename is UNSAFE.

- FD must be opened before rename
- Writes must occur after rename while FD is still valid

### 6. Missing Write Size

If any write to the file being renamed has `size=?`, the rename is AMBIGUOUS. Only writes to the file being renamed are checked - unrelated files don't affect status.

## Priority Order

**CRITICAL**: You must implement sequential checking exactly as described below. This is not optional - the algorithm must follow this exact pattern.

### Algorithm for Checking Each Rename

For each rename operation, execute this algorithm:

```
1. Check condition #1 (Missing write size)
   - If condition applies → Return AMBIGUOUS, STOP
   - If condition does NOT apply → Continue to step 2

2. Check condition #2 (Cross-process FD leak)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 3

3. Check condition #3 (File not fsynced)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 4

4. Check condition #4 (Write after fsync)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 5

5. Check condition #5 (Wrong FD fsync)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 6

6. Check condition #6 (Directory fsync timing)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 7

7. Check condition #7 (Directory not fsynced)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Continue to step 8

8. Check condition #8 (Multiple renames to same directory)
   - If condition applies → Return UNSAFE, STOP
   - If condition does NOT apply → Return SAFE
```

**Key Points:**
- You MUST check conditions in numerical order (1, then 2, then 3, etc.)
- You MUST stop immediately when a condition applies - do not check any later conditions
- You MUST only check the next condition if the current one does NOT apply
- Do NOT check all conditions and then pick one - check sequentially and stop at first match
- Even if multiple conditions could apply, only report the first one in priority order

### Priority Conditions with Explicit "Applies" Definitions

1. **Missing write size** → AMBIGUOUS
   - **Applies if**: Any write operation to the file being renamed (on any FD that wrote to this file) has `size=?`
   - **Does NOT apply if**: All writes to the file have known sizes

2. **Cross-process FD leak** → UNSAFE
   - **Applies if**: Another process (different PID) has a file descriptor open to the file being renamed, AND that process writes to that FD AFTER the rename occurs, AND the FD was opened BEFORE the rename
   - **Does NOT apply if**: No other process writes after rename, or FD was opened after rename, or no writes occur after rename

3. **File not fsynced** → UNSAFE
   - **Applies if**: The file was NEVER fsynced before ANY rename of this file (follow rename chain backwards to original path, check if any FD to that path was fsynced before the first rename)
   - **Does NOT apply if**: The file was fsynced before its first rename (for subsequent renames, if file was fsynced before first rename, this condition does NOT apply - continue to check #4)

4. **Write after fsync** → UNSAFE
   - **Applies if**: On the SAME file descriptor that was used for the file being renamed, there was a write operation AFTER an fsync operation on that same FD (the write can occur before or after the rename, but must be on the same FD after an fsync)
   - **Does NOT apply if**: No writes occur after fsync on the same FD, or writes occur on different FDs

5. **Wrong FD fsync** → UNSAFE
   - **Applies if**: An fsync was performed on a file descriptor that does NOT correspond to the file being renamed (fsync on different file)
   - **Does NOT apply if**: No fsync occurred, or fsync was on correct FD

6. **Directory fsync timing** → UNSAFE
   - **Applies if**: A directory fsync on the target directory occurred BEFORE the rename (earlier in trace)
   - **Does NOT apply if**: No directory fsync, or directory fsync occurs after rename

7. **Directory not fsynced** → UNSAFE
   - **Applies if**: No directory fsync occurred on the target directory AFTER the rename
   - **Does NOT apply if**: Directory fsync occurred after the rename

8. **Multiple renames to same directory** → UNSAFE
   - **Applies if**: Multiple renames target the same directory before a single directory fsync, AND this rename is NOT the first one (by sequence number in trace)
   - **Does NOT apply if**: This is the first rename to the directory, or only one rename targets the directory

### Example: Sequential Checking

Consider this trace:
```
1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:write:fd=3:size=50
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
# No directory fsync
```

For the rename operation:
- Condition #1 (Missing write size): Does NOT apply (all writes have known sizes)
- Condition #2 (Cross-process FD leak): Does NOT apply (no other process)
- Condition #3 (File not fsynced): Does NOT apply (file was fsynced before rename)
- Condition #4 (Write after fsync): **APPLIES** (write on fd=3 after fsync on fd=3)
  - **STOP HERE** - Return UNSAFE with reason containing "write after fsync"
- **DO NOT CHECK** conditions #5, #6, #7, #8

**Correct behavior**: Check conditions 1→2→3→4 sequentially. When #4 applies, return UNSAFE and STOP. Never check #7.

**Incorrect behavior**: 
- Checking condition #7 before #4
- Checking all conditions and then picking one
- Reporting "directory not fsynced" when "write after fsync" applies

### Special Rules

- **File fsync persistence**: If file was fsynced before first rename, it remains fsynced for all subsequent renames. For subsequent renames, skip check #3 and continue to check #4.
- **Directory fsync per rename**: Each rename needs its own directory fsync. A directory fsync after later rename does not protect earlier renames.

## Critical Requirements

1. Process operations in chronological order
2. File descriptors point to inodes, not paths
3. Track file identity across renames
4. **Sequential Priority Checking**: For each rename, check conditions 1-8 in exact numerical order. For each condition: (a) check if it applies, (b) if YES → assign status and STOP immediately, (c) if NO → continue to next condition. Never check later conditions if an earlier one applies. Never check all conditions and pick one - must check sequentially and stop at first match.
5. Only writes to file being renamed affect missing size check
6. Cross-process checks before directory fsync checks
7. File fsync status persists across renames
8. Each rename needs its own directory fsync
9. Multiple renames to same directory: only first is protected
10. Output must match exact JSON schema with all fields
