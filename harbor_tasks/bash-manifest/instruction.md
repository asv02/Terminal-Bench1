You are working on a restricted embedded Linux environment with limited tooling.
Your task is to develop a Bash script that monitors file integrity within a directory.

## Task Overview
Create a script at /app/integrity.sh that operates in two distinct modes:

### Mode 1: Generate Manifest

When invoked with the --generate flag, the script must scan a target directory and produce a file integrity manifest:
Command format:
/app/integrity.sh --generate <target_directory>

Requirements:
- Recursively process all files in the target directory
- Calculate the SHA-256 cryptographic hash for each file
- Output the manifest to stdout (standard output)
- Each line must follow this exact format: HASH  /app/path/to/file
  (Note: exactly two spaces between the hash and the path)
- The paths must be **absolute** (starting with /app/)
  - When scanning /app/data, output paths like /app/data/file.txt and /app/data/subdir/file.txt
  - Paths must be sorted alphabetically
- The entire output must be sorted alphabetically by the file path

### Mode 2: Compare Manifests

When invoked with --old and --new flags, the script must compare two manifest files and identify differences:
Command format:
/app/integrity.sh --old <path_to_old_manifest> --new <path_to_new_manifest>

Requirements:
- Read both manifest files provided as arguments
- Determine which files have been added (present in new, absent in old)
- Determine which files have been removed (present in old, absent in new)
- Determine which files have been modified (same path, different hash)
- Write the results to /app/diff.json

The output file /app/diff.json must be a valid JSON object with this exact structure:
{
  "added": ["/app/data/file1.txt", "/app/data/subdir/file2.log"],
  "removed": ["/app/data/file3.conf"],
  "modified": ["/app/data/file4.dat"]
}
JSON Requirements:
- Must be syntactically valid (parseable by standard JSON parsers)
- No trailing commas after the last element in any array
- Proper escaping of special characters in file paths (quotes, backslashes, etc.)
- Arrays may be empty if no files match that category
- File paths must be listed exactly as they appear in the manifest files (absolute paths)

Manifest File Format Tolerance:
- Manifest files may contain blank lines - these MUST be ignored during parsing
- Manifest files may contain comment lines starting with # - these MUST be skipped
- Hash comparison MUST be case-insensitive (accept both uppercase/lowercase hex)

Additional Edge Cases to Handle:
- Files with names starting with dash (-) must be processed correctly (not treated as flags)
- If **both** manifest files are effectively empty, the output must be {"added": [], "removed": [], "modified": []}
- If a manifest contains duplicate entries for the same path, use the first occurrence only
- Symlinks in the target directory MUST be skipped - only process regular files (-type f)

Additional Clarifications:
- An "empty" manifest file (or one containing only comments/whitespace) implies that the directory contains zero files.
    - Example: If --old is empty and --new has files, all files in --new are considered "added".
- JSON string values must follow standard JSON escaping rules (escape backslashes, quotes, control characters per RFC 8259)

## Environment Constraints
You are working in a restricted environment with only basic utilities available:
- bash, sh
- awk, sed, grep
- sort, diff
- sha256sum
- printf, echo
- ls, find
- Standard text processing tools from coreutils
The following tools are NOT available:
- python, perl, ruby, node, or any other high-level scripting language
- jq or any JSON processing tools
- Advanced text editors with scripting capabilities

## Test Data
A directory containing test files is located at /app/data. This directory contains
files with various naming patterns, including:
- Files with spaces in their names
- Files with special characters
- Files with various extensions
- Empty files
- Files with unusual content
Your script must handle all of these cases correctly.

## Success Criteria
Your solution will be considered successful if:
1. The script /app/integrity.sh exists and is executable
2. Mode 1 generates a correctly formatted and sorted manifest using absolute paths
3. Mode 2 produces valid JSON output at /app/diff.json
4. The script correctly handles files with spaces and special characters in names
5. The comparison logic accurately identifies added, removed, and modified files