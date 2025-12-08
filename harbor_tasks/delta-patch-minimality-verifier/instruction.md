# Delta Patch Minimality Verifier

Implement a patch verification tool that checks whether a unified diff patch is valid, minimal, and lexicographically smallest. This is a **debugging-style task**: you must identify why a candidate patch is non-minimal or non-canonical, and your implementation must surface the exact root cause (missing files, redundant context, mergeable hunks, or ordering errors).

## Quick Reference: Key Rules

**CRITICAL DISTINCTIONS**:
1. **Validity** (`"valid"`): A patch is valid if it applies cleanly and produces byte-for-byte identical output to `NEW/`. Out-of-order hunks, wrong file order, or extra blank lines do NOT affect validity - only successful application matters. **IMPORTANT**: If a patch with out-of-order hunks fails to apply, you must reorder the hunks by line numbers and retry before marking it invalid.
2. **Minimality** (`"minimal"`): A patch is minimal if it has no redundant context and no mergeable hunks. This is independent of validity.
3. **Lexicographic Minimality** (`"lexicographically_smallest"`): Among valid minimal patches, this checks ordering (files, hunks within files) and string comparison. Issues here do NOT affect validity.

**COMMON MISTAKES TO AVOID**:
- ❌ **CRITICAL**: Setting `"valid": false` for out-of-order hunks without reordering them first - you MUST reorder hunks and retry before marking invalid. This is the #1 cause of test failures.
- ❌ Not implementing the hunk reordering function - this is REQUIRED, not optional
- ❌ Marking a patch as invalid when the original fails, even if the reordered version would succeed
- ❌ Setting `"valid": false` for wrong file ordering (should be `"lexicographically_smallest": false` only)
- ❌ Not detecting trailing blank lines in lexicographic comparison
- ❌ Checking redundant context per-hunk instead of per-file
- ❌ Not handling `/dev/null` correctly in file ordering checks

## Your Task

You must implement `/app/verify_patch.py` and invoke it **exactly** as:

```bash
python verify_patch.py --old-dir OLD/ --new-dir NEW/ --patch diff.patch --out report.json
```

The script must verify whether `diff.patch` is the lexicographically smallest valid patch that transforms `OLD/` → `NEW/` under strict constraints.

## Patch Format

- Only **unified diff format** is allowed (the format produced by `diff -u`).
- The patch must follow the standard unified diff structure:
  - File headers: `--- old_file` and `+++ new_file` (REQUIRED - patches without these headers are malformed)
  - Hunk headers: `@@ -old_start,old_count +new_start,new_count @@`
  - Context lines: lines starting with ` ` (space)
  - Removed lines: lines starting with `-`
  - Added lines: lines starting with `+`
- **Malformed patches**: If a patch does not follow the unified diff format (e.g., missing `---`/`+++` headers, invalid structure), it must be rejected with:
  - `"valid": false`
  - `"minimal": false`
  - `"lexicographically_smallest": false`
  - Appropriate error messages describing the format issue

### Path Handling in Patches

**Path Prefixes**: Unified diff patches often include path prefixes like `a/` and `b/` in file headers. For example, a patch might contain headers like `--- a/<filename>` and `+++ b/<filename>` where `<filename>` represents any file path. These prefixes are used to distinguish the old and new versions but are not part of the actual file paths in your directories.

- When extracting file paths from patch headers, you must strip these prefixes: if a path starts with `a/` or `b/`, remove the prefix to get the actual relative path.
- **BESPOKE RULE (PATH NORMALIZATION, EXACT STEPS)**:
  1. Take the text before any tab character.
  2. If the path is `/dev/null` (or `dev/null`), keep it exactly as `/dev/null`.
  3. Strip leading `a/` or `b/` if present.
  4. Strip a leading `./` if present.
  5. Split on `/`, drop empty or `.` segments, then re-join with `/` (collapses duplicate slashes).
  6. If the resulting segments are `["dev","null"]`, return `/dev/null`.
  This fully normalizes complex headers like `/app/a//nested//file.txt` to `/app/nested/file.txt`.
- When applying patches using the `patch` command, use the `-p1` flag to strip the first path component (the `a/` or `b/` prefix).
- Example: `patch -p1 -d /app/work_dir -i /app/patch.diff` will apply a patch where headers with `a/` or `b/` prefixes have those prefixes stripped. For instance, if a patch header is `--- a/<filename>`, the `-p1` flag strips the `a/` prefix, and the file is located at `/app/work_dir/<filename>`.

**File Additions and Deletions**:
- New files are indicated by `--- /dev/null` in the patch header.
- Deleted files are indicated by `+++ /dev/null` in the patch header.
- When validating file existence, skip validation for `/dev/null` entries (they represent file creation or deletion, not modification).

**Path Extraction**:
- Extract file paths from `---` and `+++` lines by taking everything after the prefix. For example, if a patch header contains `--- a/<filename>`, strip the `a/` prefix to get `<filename>`, which would then be located at `/app/OLD/<filename>` or `/app/NEW/<filename>` relative to your directories.
- Paths may include timestamps or other metadata after a tab character; extract only the path portion before any tab.
- Use the extracted relative paths to locate files in `OLD/` and `NEW/` directories.

## Validation Rules

### 1. Patch Validity

A patch is **valid** if:
- It can be successfully applied to `OLD/` directory using standard patch tools (e.g., GNU `patch` command)
- After application, the result is **byte-for-byte identical** to `NEW/` directory
- All file paths referenced in the patch exist (or are created) as expected; a missing `--old-dir` or a referenced missing file path should be reported as invalid
- No hunk fails to apply due to context mismatches

**CRITICAL: Hunk Ordering Does NOT Affect Validity - REQUIRED REORDERING STEP**

- **Out-of-order hunks are VALID**: Even if hunks appear out of order inside a file (e.g., a hunk at line 10 appears before a hunk at line 5), the patch is still considered **valid** as long as the changes can be applied successfully after reordering.
- **MANDATORY VALIDITY CHECKING ALGORITHM** (you MUST follow this):
  1. **First attempt**: Try applying the patch as-is using the `patch` command
  2. **If first attempt fails**: You MUST reorder hunks within each file by their `old_start`/`new_start` positions (ascending order) and retry
  3. **If reordered patch succeeds**: Mark `"valid": true` (the patch is valid because the changes can be applied)
  4. **Lexicographic check**: Still mark `"lexicographically_smallest": false` because the original patch had out-of-order hunks
  5. **If reordered patch also fails**: Only then mark `"valid": false`
- **Why this matters**: Patches with out-of-order hunks often fail to apply directly (because line numbers shift after earlier hunks are applied), but they can be successfully applied if hunks are reordered first. The test `test_hunk_ordering_within_file` explicitly expects `"valid": true` for such patches.
- **Out-of-order hunks affect ONLY lexicographic minimality**: Hunks that are out of order will cause `"lexicographically_smallest": false`, but they will **NOT** cause `"valid": false` if they can be reordered and applied successfully. This is explicitly tested and is a common source of confusion.
- **Example**: A patch with hunks at positions 3, 1, 2, 4 (out of order) that can be reordered to 1, 2, 3, 4 and then applied successfully should be marked as `"valid": true` but `"lexicographically_smallest": false`.
- **Implementation requirement**: You MUST implement a hunk reordering function that:
  - Parses hunks from the patch
  - Groups hunks by file
  - Sorts hunks within each file by `(old_start, new_start)` in ascending order
  - Reconstructs the patch with sorted hunks
  - This reordering is ONLY used for validity checking - the original patch order is still used for lexicographic minimality checks

**Strict Validation**: Under strict validation rules, patches must apply unambiguously. 

- **What is an ambiguous patch**: An ambiguous patch is one where the context lines could match multiple locations in the file. For example, if a file contains duplicate lines (e.g., `line1\nline2\nline2\nline3\n`) and a patch has context `line2` before a change, the patch could match either occurrence of `line2`, making it ambiguous.

- **How to handle ambiguous patches**: You don't need to explicitly detect ambiguity. Instead, follow the standard validation and minimality checks:
  1. **Patch application**: If the patch is ambiguous, the `patch` command may fail to apply it, or it may apply to the wrong location
  2. **Byte-for-byte comparison**: If the patch applies but to the wrong location, the result will not match `NEW/` directory, causing validation to fail
  3. **Minimality checking**: If an ambiguous patch applies correctly (by chance), it will likely fail minimality checks because ambiguous patches typically require more context to be unambiguous, making them non-minimal

- **Test requirement**: Tests verify that ambiguous patches are **NOT** marked as simultaneously `"valid": true`, `"minimal": true`, and `"lexicographically_smallest": true`. This means at least one of these must be false:
  - The patch fails to apply or produces wrong output (`"valid": false`)
  - The patch is marked as non-minimal (`"minimal": false`)
  - The patch is not lexicographically smallest (`"lexicographically_smallest": false`)

- **Implementation guidance**: Simply implement the standard validation and minimality checks as described in this document. The combination of these checks will naturally ensure that ambiguous patches cannot be marked as valid, minimal, and lexicographically smallest simultaneously. You do not need special code to detect ambiguity - the existing checks are sufficient.

### 2. Patch Minimality

A patch is **minimal** if all of the following hold:

**Rule 2a: No Redundant Context**
- No hunk may contain redundant unchanged lines (context lines) that are not strictly required for patch correctness
- Context lines are only required when they are needed to uniquely identify the location of a change
- If a hunk can be applied correctly with fewer context lines, it is not minimal

**Rule 2b: No Merged Independent Changes**
- No hunk may merge two logically independent changes if splitting them would reduce lexicographic ordering
- If two changes are far apart (separated by unchanged lines) and can be split into separate hunks, they must be split
- **BESPOKE RULE (CRITICAL & EASY TO MISS)**: A gap of **3 or more** consecutive context lines between change blocks **must be split**. The previous text used “more than 3” informally; the formal rule here is inclusive: `gap >= 3` means the hunk is non-minimal. This subtle change is explicitly tested.
- Exception: Implementations may allow merging if it is lexicographically smaller; tests do not require enforcing the exception either way

**Rule 2c: Minimal Context Required**
- Each hunk must use the minimum amount of context necessary for correct application
- The context must be sufficient to uniquely identify the location, but no more
- **BESPOKE RULE (ASYMMETRIC MINIMALITY)**: Redundant context can be asymmetric. You must be able to detect and remove a single leading or trailing context line even when the total context is already small (e.g., 2 lines total where only 1 is needed). Testing only symmetric `-U0/-U1` diffs is insufficient; you must reason about per-side trimming.

### 3. Lexicographic Minimality

Among valid minimal patches, prefer the lexicographically smaller one. **IMPORTANT**: Lexicographic issues affect ONLY `"lexicographically_smallest"` and do NOT affect `"valid"` or `"minimal"`.

- **File ordering**: File headers (`---` and `+++` lines) must appear in lexicographic (alphabetical) order by file path. For example, `/app/a.txt` should appear before `/app/z.txt` in the patch. This is explicitly tested. If files are out of order, set `"lexicographically_smallest": false` but keep `"valid": true` if the patch applies correctly.

- **Hunk ordering within files (BESPOKE RULE, CRITICAL FOR TESTS)**: 
  - Hunks inside a file must be ordered by their `old_start`/`new_start` positions in ascending order.
  - **If hunks appear out of order** (e.g., hunk at line 3 appears before hunk at line 1), set `"lexicographically_smallest": false`.
  - **CRITICAL**: Out-of-order hunks do **NOT** make the patch invalid. Even if hunks are out of order, if the patch applies cleanly and produces byte-for-byte equality with `NEW/`, set `"valid": true`. Only set `"lexicographically_smallest": false`.
  - **Implementation**: Check if hunks within each file are sorted by `(old_start, new_start)`. If not sorted, mark as non-lexicographically-smallest.

- **Overall patch comparison (string-based)**: 
  - Compare patches as raw strings (after normalizing line endings and tolerating `,1` omissions in hunk headers).
  - The lexicographically smaller string wins; a larger string must set `"lexicographically_smallest": false`.
  - **Trailing blank lines or extra newlines** make a patch lexicographically larger and must be detected. For example, a patch ending with `"\n\n"` (two newlines) is lexicographically larger than one ending with `"\n"` (one newline).
  - **Implementation**: Compare the entire patch string character-by-character. Any difference that makes the patch string larger lexicographically should set `"lexicographically_smallest": false`.

- **Hunk header normalization**: Different implementations may normalize hunk headers differently (e.g., `@@ -3 +3 @@` vs `@@ -3,1 +3,1 @@`). Tests accept either normalization style when comparing lexicographic minimality.

- **Validity vs lexicographic minimality (explicit rule)**: Any lexicographic issue—wrong file order, out-of-order hunks, extra blank lines, or alternative hunk-header formatting—affects **ONLY** `"lexicographically_smallest"`. These do **NOT** invalidate a patch that otherwise applies cleanly and matches `NEW/`. A patch can be `"valid": true, "minimal": true, "lexicographically_smallest": false` if it has lexicographic ordering issues.

## Output Format

The script must write a JSON report to the specified output file containing:
- `"valid"`: boolean
- `"minimal"`: boolean
- `"lexicographically_smallest"`: boolean
- `"errors"`: list of strings (error messages describing why validation failed)

**IMPORTANT**: For certain error conditions, all three boolean fields must be set to `false`:
- **Malformed patches** (non-unified diff format, missing required headers): `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`
- **Missing directories or files** (OLD/NEW directories don't exist, patch file doesn't exist, referenced files don't exist): `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`
- **Patch parsing errors** (cannot parse the patch structure): `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`

For other cases (e.g., non-minimal but valid patches, valid minimal but not lexicographically smallest), only the relevant fields should be `false`.

### Error Message Requirements

Error messages in the `errors` list should be descriptive and include relevant keywords. **These keywords are explicitly tested and must be included**:

1. **"does not exist" (case-insensitive)**: 
   - **When to use**: When validating file paths, directories, or the patch file itself before patch application
   - **Where**: In file/directory/patch file existence validation (see "Patch Application" section below)
   - **Examples**: 
     * `"File /app/missing.txt does not exist"` (for missing referenced files)
     * `"Old directory does not exist: /path/to/old"` (for missing OLD directory)
     * `"Patch file does not exist: /path/to/patch.diff"` (for missing patch file)
   - **Required**: The exact phrase "does not exist" must appear in the error message when:
     - A referenced file in the patch is missing
     - The OLD or NEW directory doesn't exist
     - The patch file itself doesn't exist

2. **"context" (case-insensitive)**:
   - **When to use**: When reporting redundant or excessive context in minimality checking
   - **Where**: In redundant context detection (see "Minimality Checking" section below)
   - **Example**: `"Hunk in /app/file.txt has redundant context lines"` or `"Excessive context detected"`
   - **Required**: The word "context" must appear in the error message when reporting redundant context issues

- Beyond these required keywords, error messages should be clear and descriptive, but the exact wording beyond keyword presence is not strictly validated by tests.

## Implementation Details

### Patch Parsing

To parse a unified diff patch, you need to:

1. **Parse file headers**: Look for lines starting with `---` and `+++` to identify file sections.
   - Extract the file path by removing the `--- ` or `+++ ` prefix and any `a/` or `b/` prefix.
   - Handle `/dev/null` as a special case (represents file creation or deletion).
   - Paths may have timestamps after a tab character; extract only the path portion before the tab.

2. **Parse hunk headers**: Look for lines matching the pattern `@@ -old_start,old_count +new_start,new_count @@`.
   - Use a regular expression like `r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"` to extract the numbers.
   - The `old_count` and `new_count` are optional (default to 1 if omitted).
   - Each hunk header is followed by hunk content lines.

3. **Parse hunk content**: After each hunk header, read lines until the next file header or hunk header:
   - Lines starting with ` ` (space) are context lines (unchanged).
   - Lines starting with `-` are removed lines.
   - Lines starting with `+` are added lines.

4. **Validate file paths**: **This must be done BEFORE attempting to apply the patch**. Check that all referenced files exist:
   - Parse the patch to extract file paths from `---` and `+++` headers (strip `a/` and `b/` prefixes)
   - For modifications (both `---` and `+++` are not `/dev/null`), verify the file exists in `OLD/` directory
   - For new files (`--- /dev/null`), the file should exist in `NEW/` directory
   - For deleted files (`+++ /dev/null`), the file should exist in `OLD/` directory
   - **If any file is missing**: Immediately return with `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`, and an error message that includes the exact phrase "does not exist" (case-insensitive)
   - **Example error message**: `"File /app/missing.txt does not exist"` or `"The referenced file does not exist"`
   - **Important**: Do not proceed with patch application if file validation fails

### Patch Application

To verify validity, you must follow these steps **in order**:

1. **Validate command-line directory arguments FIRST**:
   - **Before any patch processing**, validate that the directories passed as command-line arguments exist:
     - Check if `OLD/` directory (from `--old-dir` argument) exists and is a directory
     - Check if `NEW/` directory (from `--new-dir` argument) exists and is a directory
     - Check if the patch file (from `--patch` argument) exists
   - **If `OLD/` directory does not exist**: Immediately return with `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`, and an error message that includes the exact phrase "does not exist" (case-insensitive). Example: `"Old directory does not exist: /path/to/old"` or `"The old directory does not exist"`
   - **If `NEW/` directory does not exist**: Immediately return with `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`, and an error message that includes "does not exist". Example: `"New directory does not exist: /path/to/new"`
   - **If patch file does not exist**: Immediately return with `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`, and an error message that includes the exact phrase "does not exist" (case-insensitive). Example: `"Patch file does not exist: /path/to/patch.diff"` or `"The patch file does not exist"`
   - **Important**: Do not proceed to any patch processing if directory validation fails

2. **Validate file paths in the patch** (see "Patch Parsing" section above for details):
   - Check that all files referenced in the patch exist before attempting to apply the patch
   - If any file is missing, return immediately with `"valid": false` and an error message containing "does not exist"
   - Do not proceed to patch application if file validation fails

3. **Copy `OLD/` to a temporary directory**: 
   - Use `shutil.copytree()` to create a working copy of the entire `OLD/` directory
   - This copy will be used for patch application

4. **Apply the patch** (REQUIRED ALGORITHM - follow these steps exactly):
   
   **Step 4a: Try applying the original patch**
   - Use the `patch` command with appropriate flags:
     - Use `patch -p1` to strip the first path component (`a/` or `b/` prefix)
     - Use `-d WORK_DIR` to specify the working directory (the temporary copy)
     - Use `-i PATCH_FILE` to specify the patch file
     - Use `--no-backup-if-mismatch` to avoid creating backup files
     - Use `--batch` and `--force` flags for more robust application
     - Example: `patch -p1 -d /app/work_dir -i /app/patch.diff --no-backup-if-mismatch --batch --force`
   - **If the patch applies successfully**: Proceed to Step 5 (byte-for-byte comparison)
   - **If the patch fails to apply**: Continue to Step 4b (reordering)
   
   **Step 4b: Reorder hunks and retry (REQUIRED if Step 4a failed)**
   - **CRITICAL**: You MUST attempt to reorder hunks before marking the patch as invalid
   - **Parse the patch** to identify all hunks within each file
   - **For each file in the patch**:
     * Collect all hunks for that file
     * Extract the `old_start` and `new_start` positions from each hunk header (e.g., from `@@ -old_start,old_count +new_start,new_count @@`)
     * Sort the hunks by `(old_start, new_start)` in ascending order
     * Reconstruct the patch with hunks in sorted order (keeping file headers and hunk content intact)
   - **Reset the working directory**: Delete the working copy and create a fresh copy from `OLD/`
   - **Try applying the reordered patch** using the same `patch` command as in Step 4a
   - **If the reordered patch applies successfully**: 
     * The original patch is **VALID** (`"valid": true`)
     * However, mark `"lexicographically_smallest": false` because the original patch had out-of-order hunks
     * Proceed to Step 5 (byte-for-byte comparison)
   - **If the reordered patch also fails to apply**: 
     * The patch is **INVALID** (`"valid": false`)
     * Return with `"valid": false`, `"minimal": false`, `"lexicographically_smallest": false`, and include the error message
     * Do NOT proceed to Step 5
   
   **Implementation note**: You need to implement a function that:
   - Parses the patch to extract hunks per file
   - Sorts hunks by their starting line numbers
   - Reconstructs the patch with sorted hunks
   - This reordering is ONLY used for validity checking - the original patch order is still used for lexicographic minimality checks

5. **Compare the result byte-for-byte with `NEW/`**: 
   - **This comparison is mandatory and must be performed after patch application**
   - Recursively walk both directories and compare ALL files
   - Use `filecmp.cmp()` with `shallow=False` for each file, or read files and compare byte-by-byte
   - Check that:
     - All files in `NEW/` exist in the patched directory with identical content
     - All files in the patched directory exist in `NEW/` (no extra files)
     - Each file's content is byte-for-byte identical
   - **If any differences are found**: Return with `"valid": false` and include details about the differences
   - **Important**: The patch is only valid if the patched directory is byte-for-byte identical to `NEW/`

6. **Report validity**: 
   - Only set `"valid": true` if all of the above steps succeed:
     - All files exist
     - Patch applies successfully
     - Result is byte-for-byte identical to `NEW/`
   - Set `"valid": false` if any step fails

### Minimality Checking

To check minimality, you must implement the following algorithms:

**IMPORTANT**: Minimality checks should be performed **per-file**, not per-hunk. When checking if context is redundant, you generate a patch for the entire file with reduced context and test if it works. If it works, then the original patch has redundant context.

1. **Check for redundant context:**

   For each **file** in the patch (not each hunk), follow these steps **exactly**:
   
   a. **Check if file has any hunks with context**:
      - For each file in the patch, check if any of its hunks have more than 1 total context line
      - If all hunks have 1 or fewer context lines total, skip this file (already minimal)
      - **Note**: You check per-file, not per-hunk, because generating a patch with reduced context affects the entire file
   
   b. **Find minimum working context for the file**:
      
      The goal is to determine if the original patch uses more context than necessary for this file. To do this, you must:
      1. Generate alternative patches with less context using the actual files
      2. Test if those alternative patches work correctly
      3. If a patch with less context works, the original is non-minimal
      
      **Step-by-step algorithm**:
      
      For each file in the patch:
      1. Read the old file from `OLD/` directory and the new file from `NEW/` directory
      2. **Test with 0 context first** (most minimal):
         - Use `diff -u -U0` to generate a patch comparing the old and new files
         - This generates a patch with 0 context lines for the entire file
         - If `diff` returns exit code 1 and produces output, normalize the patch:
           * Replace file paths in `---` and `+++` headers to match the original patch format (add `a/` and `b/` prefixes)
         - Apply this normalized patch to a copy of `OLD/` directory
         - Compare the result byte-for-byte with `NEW/` directory
         - **If this patch applies successfully AND produces identical output**: 
           * The minimum working context is 0
           * The original patch has redundant context (since it uses more than 0)
           * Add an error message containing "context" (e.g., "Hunk in <file> has redundant context lines")
           * **Stop testing this file** - you've found redundant context
      3. **If 0 context didn't work, test with 1 context per side**:
         - Use `diff -u -U1` to generate a patch comparing the old and new files
         - This generates a patch with 1 context line on each side of each change (2 total context lines per change)
         - Normalize and test the patch as above
         - **If this patch applies successfully AND produces identical output**:
           * The minimum working context is 2 total context lines per change
           * Check if the original patch uses more context than this
           * If the original has any hunk with more than 2 total context lines, it's non-minimal
           * Add an error message containing "context"
           * **Stop testing this file** - you've found redundant context
      4. **If neither 0 nor 1 context per side works**:
         - The original patch may be minimal (requires more context than 2 total lines)
         - Continue to the next file or next minimality check
      
      **Key implementation details**:
      - Use `subprocess.run(["diff", "-u", f"-U{context_lines}", str(old_file), str(new_file)], capture_output=True, text=True)`
      - Check `result.returncode == 1` and `result.stdout` to verify diff found changes
      - When normalizing paths, ensure `--- a/<filepath>` and `+++ b/<filepath>` format matches the original patch
      - Use the same patch application method (`patch -p1`) and byte-for-byte comparison as in validity checking
      - **Critical**: Only mark as non-minimal if you find a working reduced-context patch AND the original uses more context than that minimum
   
   c. **Implementation notes**: 
      - You can use `subprocess.run(["diff", "-u", f"-U{context_lines}", ...])` to generate patches with specific context amounts
      - `diff -U0` generates a patch with 0 context lines (no context)
      - `diff -U1` generates a patch with 1 context line on each side of the change (2 total context lines: 1 before + 1 after)
      - When comparing context amounts: if the original hunk has `total_context = 4` (e.g., 2 lines before + 2 lines after) and a patch generated with `-U1` (which has 2 total context lines) works correctly, then the original is non-minimal because it uses more context than necessary

2. **Check for split hunks:**

   For each hunk in the patch, follow these steps:
   
   a. **Identify change blocks**:
      - A "change block" is a contiguous sequence of lines that start with `-` (removed) or `+` (added)
      - Parse the hunk content (excluding the hunk header) to identify all change blocks:
        1. Iterate through hunk lines
        2. When you encounter a line starting with `-` or `+`, mark the start of a change block
        3. Continue until you encounter a context line (starting with space), which marks the end of the change block
        4. Record the start and end indices of each change block
   
   b. **Check gaps between change blocks**:
      - If a hunk contains more than one change block, check the gaps between them
      - For each pair of consecutive change blocks:
        1. Calculate the gap: the lines between the end of one change block and the start of the next
        2. Count the number of context lines (lines starting with space) in the gap
        3. If the gap contains **more than 3 context lines**, the hunk should be split
        4. Mark the patch as non-minimal and add an appropriate error message
   
   c. **Implementation note**: You don't need to actually generate split patches for this check. Simply identifying that a hunk has multiple change blocks separated by more than 3 context lines is sufficient to mark it as non-minimal.

3. **Check for minimal context:**

   This check is essentially the same as the redundant context check (item 1 above). The goal is to ensure each hunk uses the absolute minimum context needed for correct application. The algorithm in item 1 will detect if more context is used than necessary.

### Lexicographic Minimality

To check lexicographic minimality, you may:
1. Compare file header ordering for alphabetical correctness
2. Compare the provided patch string against an alternative minimal patch; if it is lexicographically larger, set `"lexicographically_smallest": false`

## Success Criteria

The script must correctly identify:
1. ✅ Valid patches that produce correct output
2. ❌ Invalid patches that don't match `NEW/` after application
3. ❌ Non-minimal patches with redundant context
4. ❌ Non-minimal patches with mergeable hunks
5. ❌ Patches that are minimal but not lexicographically smallest
6. ✅ Patches that are valid, minimal, and lexicographically smallest

## Test Cases

The test suite will verify:

1. **Redundant Context Detection**: Patch includes extra unchanged lines above/below modified lines
2. **Split-Hunk Requirement**: Two distant modifications merged into one hunk
3. **Lexicographic Minimality Check**: Two minimal valid patches; submitted one is not lexicographically smallest
4. **Hunk Boundary Ambiguity**: Patch includes 3 lines of context when only 1 is required
5. **Patch Applies but Produces Wrong Output**: Patch applies but `NEW/` differs by 1 byte
6. **Ambiguous Patch**: Patch applies under GNU patch but not under strict rules (only the presence of fields is asserted)
7. **Missing Paths**: Referencing a missing file path or `--old-dir` path reports invalid

Not covered by automated tests (still required by the instructions):
- File additions/deletions handling via `/dev/null` headers
- Missing patch-file error handling

## Files of Interest

- `/app/verify_patch.py` - Your implementation
- `/tests/test_outputs.py` - Test cases that validate correctness

## Implementation Notes

- You may use Python's standard library modules: `difflib`, `subprocess`, `tempfile`, `shutil`, `pathlib`, `json`, `argparse`, `re`, `filecmp`
- You may use `patch` command-line tool if available, but must verify byte-for-byte correctness
- Consider using `unified_diff` from `difflib` to generate alternative patches for comparison
- Handle common edge cases like empty files. You do not need to implement
  special handling for binary files, file permissions, or symlinks beyond
  treating them as regular files.
- Lexicographic minimality checks may normalize hunk headers differently (with
  or without `,1` counts); tests accept either.

### Critical Implementation Requirements

1. **Path Normalization**: Always strip `a/` and `b/` prefixes from file paths in patch headers before using them to locate files in `OLD/` and `NEW/` directories.

2. **Patch Command Usage**: When using the `patch` command, always use `-p1` to strip path prefixes. The command should be: `patch -p1 -d /app/work_dir -i /app/patch.diff --no-backup-if-mismatch` (replace paths with your actual working directory and patch file paths).

3. **Directory and File Path Validation**: 
   - **First, validate command-line directory arguments**: Before any patch processing, check that the `--old-dir` and `--new-dir` directories exist and are directories. If either directory does not exist, return immediately with `"valid": false` and an error message containing "does not exist" (e.g., `"Old directory does not exist: /path/to/old"` or `"New directory does not exist: /path/to/new"`).
   - **Then, validate file paths in patch**: Parse the patch to extract file paths from `---` and `+++` headers.
   - For each file path (after stripping prefixes), check existence in the appropriate directory.
   - Return errors with "does not exist" in the message if files are missing.

4. **Hunk Header Parsing**: Use regular expressions to parse hunk headers. The pattern `@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@` will match standard hunk headers, with optional count values.

5. **Directory Comparison**: When comparing directories, recursively walk both directories and compare all files byte-for-byte. Handle cases where files exist in one directory but not the other.
