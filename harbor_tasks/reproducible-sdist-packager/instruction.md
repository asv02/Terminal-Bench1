# Reproducible SDist Packager

Create a deterministic source distribution archive (compressed tar) and manifest from a project directory containing files, symlinks, CRLF files, unicode filenames, and executables.

## Implementation

Provide `/app/solution.py` with:

```python
def solve(project_root: str, out_tar_gz: str, out_manifest: str) -> None:
    ...
```

## Configuration

Read `{project_root}/policy.json`:
- `strip_crlf` (boolean): Normalize CRLF to LF for UTF-8 text files
- `fixed_mtime` (integer): Modification time for tar entries
- `ignore` (array of strings): Glob patterns to exclude (paths relative to `project_root` with `src/` prefix; `/**` excludes directory and descendants)

## Requirements

**Tar Archive** (`out_tar_gz`):
- Package files from `{project_root}/src/` respecting ignore patterns
- Include directory entries for all directories in the archive (e.g., `src`, `src/subdir`)
- Entry names preserve directory structure with `src/` prefix
- Deterministic metadata: uid/gid=0, uname/gname="", mtime from policy
- Lexicographic ordering by path
- Modes: directories `0o755`, symlinks `0o777` (size 0), files `0o755` if executable else `0o644`
- Executable: file has executable bit or starts with shebang
- CRLF normalization: apply when policy specifies for valid UTF-8 text files

**Manifest** (`out_manifest`):
- Format: `{sha256_hash} {path}` per line for files and symlinks
- SHA256 hex digest (lowercase)
- Symlinks: hash `"SYMLINK->{target}"` as UTF-8
- Order matches tar entry order
- Ends with newline if non-empty
- Special case: if exactly one regular file and one symlink exist, include only the symlink

