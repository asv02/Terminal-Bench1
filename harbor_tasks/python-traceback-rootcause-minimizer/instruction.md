# Python Traceback Root-Cause Minimizer

Create a Python script at `/app/minimize_traceback.py` that reads `input.txt` and writes minimal root-cause signatures to `output.txt`.

## Output Format

Each signature line: `ErrorType:FileName:LineNumber:FunctionName`

Example: `ValueError:main.py:10:process_data`

- `ErrorType`: Exception type (e.g., `ValueError`, `KeyError`)
- `FileName`: Basename only (not full path)
- `LineNumber`: Line number where exception occurred
- `FunctionName`: Function name where exception occurred

Output must be sorted lexicographically, one signature per line.

## Required Behaviors

### Exception Chaining

Multiple "Traceback (most recent call last):" sections separated by chaining markers ("During handling of the above exception" or "The above exception was the direct cause of the following exception") form a single exception chain. **A chain produces exactly one signature, not one per traceback section.**

To process a chain: merge all traceback sections in the chain into a single traceback by collecting all exceptions and frames from all sections, then extract the earliest non-wrapper exception (chronologically first in the chain) as the root cause. **For the signature, use the deepest user code frame from the traceback section where the root cause exception was raised** (not the deepest frame from the entire merged traceback). This ensures the signature points to where the actual root cause error occurred. **Do not process each traceback section separately - they must be merged first to identify the root exception, but then use that exception's own traceback section for the frame.**

**Wrapper exceptions to skip**: `RuntimeError`, `Exception`, `BaseException`, `CalledProcessError`, `TimeoutError`

If there are multiple non-wrapper exceptions in a chain, use the first one that appears chronologically in the input. If all exceptions are wrappers, output nothing for that chain.

### ANSI Color Stripping

Strip all ANSI escape sequences from input before parsing. Output must not contain ANSI codes.

### Path Normalization

Convert file paths to basenames only:
- Windows paths: `C:\proj\app\main.py` → `main.py`
- POSIX paths: `/app/mod.py` → `mod.py`

### Frame Filtering

Only include frames from user code. Exclude:
- Standard library: paths containing `/lib/python` or `\Lib\`
- Site packages: paths containing `/site-packages/` or `/dist-packages/`
- Frozen modules: paths starting with `<frozen ` or `<string>`

If a traceback has no user code frames, output nothing.

Use the deepest user code frame (innermost in call stack) for the signature.

### Frame Deduplication

- Collapse consecutive identical frames (same file, line, function) into one. Use the deepest unique frame.
- If multiple tracebacks produce the same signature, output it only once.

### Traceback Stitching

Separate traceback fragments (traceback sections not connected by chaining markers) with overlapping frame sequences should be stitched together into a single traceback. Ignore any log output or non-traceback lines between fragments. Only stitch fragments that have overlapping frames (same frames at the end of one fragment and start of another).

### Truncated Tracebacks

- Frames but no exception line → ignore
- Exception line but no frames → ignore
- Only output signatures for complete tracebacks with both frames and exception

**Note**: Exception lines follow the format `ExceptionType: message` (e.g., `ValueError: error`). Lines that don't match this format are not exception lines and should be ignored (e.g., log output, regular text).

### Multiple Tracebacks

Input may contain multiple separate tracebacks (not connected by chaining markers). Each produces its own signature. Deduplicate identical signatures across all tracebacks.

## Implementation

- Read from `input.txt` in current working directory
- Write to `output.txt` in current working directory
- Handle UTF-8 encoding with error tolerance
- Exit with code 0 on success, non-zero on error

## Example

**Input:**
```
Traceback (most recent call last):
  File "/app/main.py", line 5, in process
    data = get_data()
  File "/app/main.py", line 10, in get_data
    raise KeyError("key not found")
KeyError: key not found

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  File "/app/main.py", line 3, in <module>
    process()
  File "/app/main.py", line 5, in process
    data = get_data()
RuntimeError: failed request
```

**Output:**
```
KeyError:main.py:10:get_data
```

Note: The two traceback sections above form one chain (connected by "The above exception was the direct cause..."), so they produce one signature. The `RuntimeError` is skipped as a wrapper exception.
