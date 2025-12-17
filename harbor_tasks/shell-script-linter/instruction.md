# Shell Script Linter

Implement a comprehensive shell script analyzer that detects common bugs, security issues, and best practice violations in bash/shell scripts. This is a **bug-fixing task**: you must identify specific issues with line numbers and provide actionable error messages.

## Quick Reference: Key Rules

**CRITICAL CHECKS**:
1. **Unquoted Variables**: Variables used without quotes can cause word splitting and globbing issues
2. **Missing Error Handling**: Commands without error checking can hide failures
3. **Unsafe Patterns**: Use of `eval`, `rm -rf` without safeguards, etc.
4. **Syntax Errors**: Invalid bash syntax, missing closing brackets, etc.
5. **Best Practices**: Shellcheck-style recommendations for robust scripts

**COMMON MISTAKES TO AVOID**:
- ❌ Not detecting `$var` in command substitutions or test conditions
- ❌ Missing line numbers in error reports
- ❌ Not checking for `set -e` or error handling patterns
- ❌ Ignoring security issues like hardcoded credentials
- ❌ Not validating shebang lines

## Your Task

You must implement `/app/lint_shell.py` and invoke it **exactly** as:

```bash
python /app/lint_shell.py --script /path/to/script.sh --out /app/report.json
```

The script must analyze the shell script and report all detected issues in a structured JSON format.

## Output Format

Your script must output a JSON file with the following structure:

```json
{
  "has_issues": boolean,
  "issue_count": integer,
  "issues": [
    {
      "line": integer,
      "severity": "error" | "warning" | "info",
      "code": "ERROR_CODE",
      "message": "Descriptive error message",
      "suggestion": "How to fix the issue"
    }
  ]
}
```

### Issue Codes

**Errors** (severity: "error"):
- `MISSING_SHEBANG`: Script missing shebang line
- `UNQUOTED_VAR`: Variable used without quotes in dangerous contexts
- `UNQUOTED_COMMAND_SUB`: Command substitution without quotes
- `INVALID_SYNTAX`: Bash syntax error detected
- `UNSAFE_RM`: Use of `rm -rf` without safeguards
- `EVAL_USAGE`: Use of dangerous `eval` command
- `MISSING_ERROR_CHECK`: Command without error handling
- `MISSING_LOCAL_VAR`: Function modifies variables without declaring them local

**Warnings** (severity: "warning"):
- `HARDCODED_PATH`: Absolute path that may not be portable
- `USELESS_CAT`: Unnecessary use of `cat` command
- `GLOB_IN_TEST`: Unquoted glob patterns in test conditions

## Validation Rules

### 1. Missing Shebang (MISSING_SHEBANG)

**Critical**: Scripts should start with a shebang line.

**Detect**:
- First line doesn't start with `#!`

**Note**: Any line starting with `#!` is considered valid. Don't validate specific shebang formats.

### 2. Unquoted Variables (UNQUOTED_VAR)

**Critical**: Variables used without quotes can cause word splitting and globbing.

**Detect**:
- Variables in command arguments: `echo $var` (should be `echo "$var"`)
- Variables in test conditions: `[ $x = "value" ]` (should be `[ "$x" = "value" ]`)
- Variables passed to commands: `rm $file` (should be `rm "$file"`)

**DO NOT flag** (these are safe contexts):
- Variables in arithmetic: `((count++))`
- Special variables: `$?`, `$#`, `$$`, `$!`, `$@`, `$*`
- Variables in array indices: `${array[$i]}`
- **Variables after `=` in assignments: `new_var=$old_var`** (right side of assignment is safe)

**Examples**:
```bash
# BAD - should be flagged
echo $message
rm $file
if [ $status = "ok" ]; then

# GOOD - should NOT be flagged
echo "$message"
rm "$file"
if [ "$status" = "ok" ]; then
count=$((count + 1))  # arithmetic is safe
exit_code=$?  # special variable is safe
```

### 3. Missing Error Handling (MISSING_ERROR_CHECK)

**Critical**: Commands that can fail should have error handling.

**Detect**:
- **ONLY** `cd`, `cp`, `mv` commands without `||` or `&&` on the same line
- **Do NOT flag** other commands like `echo`, `mkdir`, `touch`, `ls`, `grep`, etc.
- Skip if `set -e` is present anywhere in the script

**Examples**:
```bash
# BAD - should be flagged (only cd/cp/mv)
cd /tmp
cp file1 file2
mv file1 file2
cd /some/directory
cp /app/file.txt /app/backup/

# GOOD - should NOT be flagged
cd /some/directory || exit 1
if ! cp /app/file.txt /app/backup/; then
    echo "Copy failed"
    exit 1
fi
```

### 4. Unsafe rm Command (UNSAFE_RM)

**Critical**: Dangerous `rm -rf` commands that can cause data loss.

**Detect**:
- `rm -rf` with unquoted variables
- `rm -rf` without variable validation

**Detection Algorithm**:

1. **Find `rm` commands with `-rf` or `-fr` flags**:
   - Use regex: `rm\s+.*-[a-z]*r[a-z]*f` or `rm\s+.*-[a-z]*f[a-z]*r`
   - This matches: `rm -rf`, `rm -fr`, `rm -Rf`, etc.

2. **Check if command contains variables**:
   - Look for `$variable` or `${variable}` patterns
   - If no variables found, don't flag (static paths are okay)

3. **Check if variables are quoted**:
   - If variable is inside double quotes like `"$var"`, don't flag
   - If variable is unquoted like `$var`, flag as UNSAFE_RM

4. **Flag criteria**:
   - `rm -rf` + unquoted variable = **FLAG**
   - `rm -rf` + quoted variable = **DON'T FLAG**
   - `rm -rf` + no variables = **DON'T FLAG**

**Implementation Example**:
```python
if re.search(r'rm\s+.*-[a-z]*r[a-z]*f', line):
    # Check for unquoted variables
    if re.search(r'\$[a-zA-Z_]\w*', line):  # Has variable
        # Check if variable is quoted
        if not re.search(r'"\$[a-zA-Z_]\w*"', line):
            # Flag: unquoted variable in rm -rf
```

**Examples**:
```bash
# BAD - should be flagged
rm -rf $dir              # Unquoted variable
rm -rf /tmp/$var         # Unquoted variable in path
rm -fr $HOME/data        # Unquoted variable

# GOOD - should NOT be flagged
rm -rf "$dir"            # Quoted variable
rm -rf /tmp/static       # No variables
if [ -n "$dir" ] && [ -d "$dir" ]; then
    rm -rf "$dir"        # Quoted variable with validation
fi
```

### 5. Eval Usage (EVAL_USAGE)

**Critical**: Use of dangerous `eval` command.

**Detect**:
- Any use of `eval` command

**Examples**:
```bash
# BAD - should be flagged
eval $command
eval "ls -la"

# GOOD - use safer alternatives
"${command[@]}"  # Use arrays instead
```

### 6. Syntax Errors (INVALID_SYNTAX)

**Detect**:
- Unclosed quotes (odd number of unescaped quotes on a line)
- Missing `then`, `do`, `done`, `fi`
- Unclosed if/for/while structures (more opening keywords than closing)
- Invalid test conditions

**Detection Algorithm for Unclosed Structures**:

1. **Track structure balance across the entire script**:
   - Maintain counters for: `if_count`, `for_count`, `while_count`
   - Increment when you see: `if`, `for`, `while`
   - Decrement when you see: `fi`, `done`, `done`
   - At end of script, if any counter > 0, flag as INVALID_SYNTAX

2. **Detect missing `then` after `if`**:
   - If line matches `^if\s+\[.*\]\s*$` (if with condition, no then)
   - Check next line: if it doesn't start with `then`, flag as INVALID_SYNTAX

3. **Detect missing `do` after `for`/`while`**:
   - If line matches `^(for|while)\s+.*$` and doesn't end with `; do`
   - Check next line: if it doesn't start with `do`, flag as INVALID_SYNTAX

4. **Detect unclosed quotes**:
   - Count unescaped double quotes in a line
   - If count is odd, flag as INVALID_SYNTAX

**Implementation Example**:
```python
# Track structure balance
if_count = 0
for_count = 0
while_count = 0

for line in lines:
    if re.match(r'^\s*if\s+', line):
        if_count += 1
    elif re.match(r'^\s*fi\s*$', line):
        if_count -= 1
    elif re.match(r'^\s*(for|while)\s+', line):
        for_count += 1
    elif re.match(r'^\s*done\s*$', line):
        for_count -= 1

# At end of script
if if_count > 0:
    # Flag: Missing fi
if for_count > 0:
    # Flag: Missing done
```

**Examples**:
```bash
# BAD - should be flagged
if [ $x -eq 1 ]  # missing 'then'
for i in 1 2 3   # missing 'do'
echo "unclosed string
if [ -f file ]; then
    echo "test"
# missing fi

# GOOD
if [ $x -eq 1 ]; then
for i in 1 2 3; do
echo "closed string"
if [ -f file ]; then
    echo "test"
fi
```

### 7. Hardcoded Paths (HARDCODED_PATH)

**Warning**: Absolute paths that may not be portable.

**Detect**:
- Paths like `/home/user/...` or `/Users/user/...`

**Examples**:
```bash
# BAD - should be flagged
cp /app/data.txt /home/user/backup/
cd /Users/john/project

# GOOD - use relative paths or variables
cp /app/data.txt "$HOME/backup/"
cd "$PROJECT_DIR"
```

### 8. Useless Cat (USELESS_CAT)

**Warning**: Unnecessary use of `cat` in pipelines.

**Detect**:
- `cat file | command` pattern

**Examples**:
```bash
# BAD - should be flagged
cat /app/data.txt | grep pattern

# GOOD - redirect instead
grep pattern < /app/data.txt
grep pattern /app/data.txt
```

### 9. Unquoted Command Substitution (UNQUOTED_COMMAND_SUB)

**Critical**: Command substitution without quotes can cause word splitting.

**Detect**:
- `$(command)` not wrapped in quotes
- `` `command` `` (backticks) not wrapped in quotes

**Detection Algorithm**:
1. Find ALL command substitutions using regex: `\$\([^)]+\)` for `$()` and `` `[^`]+` `` for backticks
2. For EACH match found, check if it's inside double quotes
3. To check if inside quotes:
   - Track quote positions in the line
   - A command substitution is quoted if its position falls between an opening `"` and closing `"`
   - Handle escaped quotes `\"` (they don't count as quote boundaries)
4. Flag as UNQUOTED_COMMAND_SUB if NOT inside quotes

**Important**: 
- You must detect BOTH `$()` and backtick forms
- A line can have MULTIPLE command substitutions - check each one
- Only report once per line (break after first unquoted one found)

**Examples**:
```bash
# BAD - should be flagged (3 instances on 3 different lines)
files=$(ls *.txt)          # Line 1: unquoted $()
result=`grep pattern file` # Line 2: unquoted backticks
echo $(date)               # Line 3: unquoted $()

# GOOD - should NOT be flagged
files="$(ls *.txt)"        # Quoted $()
result="$(grep pattern file)" # Quoted $()
echo "$(date)"             # Quoted $()

# MIXED - only flag the unquoted one
echo "$(date)" $(whoami)  # Flag: second $(whoami) is unquoted
```

**Regex patterns to use**:
- Find `$()`: `\$\([^)]+\)` or `\$\([^)]*\)`
- Find backticks: `` `[^`]+` ``
- Use `re.finditer()` to find ALL matches, not just the first one

### 10. Missing Local Variables (MISSING_LOCAL_VAR)

**Critical**: Functions should use `local` for variables to avoid polluting global scope.

**Detect**:
- Variable assignments inside functions without `local` keyword
- Exclude: parameters (`$1`, `$2`, etc.) and special variables

**Examples**:
```bash
# BAD - should be flagged
function process_file() {
    filename="$1"
    count=0
    echo "Processing $filename"
}

# GOOD - should NOT be flagged
function process_file() {
    local filename="$1"
    local count=0
    echo "Processing $filename"
}
```

### 11. Glob in Test (GLOB_IN_TEST)

**Warning**: Unquoted glob patterns in test conditions can cause unexpected behavior.

**Detect**:
- Patterns with `*` or `?` in `[ ]` tests without quotes
- **IMPORTANT**: Only flag `[ ]` (single bracket), NOT `[[ ]]` (double bracket)

**Detection Algorithm**:

1. **Check if line contains glob patterns (`*` or `?`)**:
   - Use regex: `[*?]`

2. **Check if it's in a `[ ]` test (NOT `[[ ]]`)**:
   - Look for `[ ` (single bracket with space)
   - Make sure it's NOT `[[ ` (double bracket)
   - Use regex: `\[\s+[^]]*[*?]` and ensure no `\[\[`

3. **Check if glob pattern is quoted**:
   - If glob is inside quotes like `"*.txt"`, don't flag
   - If glob is unquoted like `*.txt`, flag as GLOB_IN_TEST

4. **Flag criteria**:
   - `[ ]` + unquoted glob = **FLAG**
   - `[ ]` + quoted glob = **DON'T FLAG**
   - `[[ ]]` + any glob = **DON'T FLAG** (double brackets handle globs correctly)

**Implementation Example**:
```python
# Check for glob patterns in [ ] tests
if re.search(r'\[\s+[^]]*[*?]', line):
    # Make sure it's NOT [[ ]]
    if not re.search(r'\[\[', line):
        # Check if glob is quoted
        if not re.search(r'"[^"]*[*?][^"]*"', line):
            # Flag: unquoted glob in [ ] test
```

**Examples**:
```bash
# BAD - should be flagged (single bracket [ ] with unquoted glob)
if [ $file = *.txt ]; then
if [ "$file" = *.txt ]; then  # Glob is unquoted

# GOOD - should NOT be flagged
if [ "$file" = "*.txt" ]; then      # Quoted glob in [ ]
if [[ $file = *.txt ]]; then         # [[ ]] handles globs correctly
if [[ "$file" = *.txt ]]; then       # [[ ]] with any glob pattern
```

## Implementation Details

### Required Approach

1. **Read the shell script** line by line
2. **Parse each line** using simple regex patterns (no need for full bash parser)
3. **Apply detection rules** for each issue type
4. **Generate structured output** with all required fields

### Starter Code Template

Here's a complete structure to get you started:

```python
import re
import json
import argparse
from pathlib import Path

def lint_shell(script_path, output_path):
    issues = []
    
    try:
        with open(script_path, 'r') as f:
            lines = f.readlines()
    except:
        lines = []
    
    # Check shebang - CRITICAL: Check if empty or first line doesn't start with #!
    if not lines or not lines[0].startswith('#!'):
        issues.append({
            'line': 1,
            'severity': 'error',
            'code': 'MISSING_SHEBANG',
            'message': 'Script missing shebang line',
            'suggestion': 'Add #!/bin/bash as first line'
        })
    
    # Check if script has set -e (if yes, skip error handling checks)
    has_set_e = any('set -e' in l for l in lines)
    
    # Check each line
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Check for eval
        if re.search(r'\beval\b', stripped):
            issues.append({
                'line': line_num,
                'severity': 'error',
                'code': 'EVAL_USAGE',
                'message': 'Use of dangerous eval command',
                'suggestion': 'Avoid eval; use safer alternatives'
            })
        
        # Check for unsafe rm -rf
        if re.search(r'\brm\s+.*-[a-z]*r[a-z]*f', stripped):
            if re.search(r'\$[a-zA-Z_]\w*', stripped):
                if not re.search(r'"\$[a-zA-Z_]\w*"', stripped):
                    issues.append({
                        'line': line_num,
                        'severity': 'error',
                        'code': 'UNSAFE_RM',
                        'message': 'Unsafe rm -rf with unquoted variable',
                        'suggestion': 'Quote variables and add validation'
                    })
        
        # Check for missing error handling (only if no set -e)
        if not has_set_e:
            for cmd in ['cd', 'cp', 'mv']:
                if re.search(rf'\b{cmd}\b', stripped):
                    if '||' not in stripped and '&&' not in stripped and not stripped.startswith('if '):
                        issues.append({
                            'line': line_num,
                            'severity': 'error',
                            'code': 'MISSING_ERROR_CHECK',
                            'message': f"Command '{cmd}' without error handling",
                            'suggestion': f'Add error handling: {cmd} ... || exit 1'
                        })
                        break
        
        # Check for syntax errors (if without then)
        if re.match(r'^if\s+\[.*\]\s*$', stripped):
            if line_num < len(lines):
                next_line = lines[line_num].strip()
                if not next_line.startswith('then'):
                    issues.append({
                        'line': line_num,
                        'severity': 'error',
                        'code': 'INVALID_SYNTAX',
                        'message': "if statement missing 'then'",
                        'suggestion': "Add 'then' after condition"
                    })
        
        # Check for syntax errors (for without do)
        if re.match(r'^for\s+\w+\s+in\s+.*$', stripped) and not stripped.endswith('; do'):
            if line_num < len(lines):
                next_line = lines[line_num].strip()
                if not next_line.startswith('do'):
                    issues.append({
                        'line': line_num,
                        'severity': 'error',
                        'code': 'INVALID_SYNTAX',
                        'message': "for loop missing 'do'",
                        'suggestion': "Add 'do' after for statement"
                    })
        
        # Check for hardcoded paths
        if re.search(r'/home/[a-zA-Z0-9_]+', stripped) or re.search(r'/Users/[a-zA-Z0-9_]+', stripped):
            issues.append({
                'line': line_num,
                'severity': 'warning',
                'code': 'HARDCODED_PATH',
                'message': 'Hardcoded absolute path may not be portable',
                'suggestion': 'Use relative paths or $HOME'
            })
        
        # Check for useless cat
        if re.search(r'cat\s+[^|]+\s*\|', stripped):
            issues.append({
                'line': line_num,
                'severity': 'warning',
                'code': 'USELESS_CAT',
                'message': 'Unnecessary use of cat in pipeline',
                'suggestion': 'Use command < file instead'
            })
    
    result = {
        'has_issues': len(issues) > 0,
        'issue_count': len(issues),
        'issues': sorted(issues, key=lambda x: x['line'])
    }
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--script', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    
    lint_shell(args.script, '/app/report.json')
```

**CRITICAL IMPLEMENTATION NOTES**:

1. **Empty files**: If the file is empty or can't be read, still check for missing shebang (line 1)
2. **Comments-only files**: Files with only a shebang and comments should have `has_issues: false` and `issue_count: 0`
3. **set -e detection**: If ANY line contains `set -e`, skip ALL error handling checks
4. **Error handling**: Only check cd, cp, mv commands. Look for `||` or `&&` on the SAME line
5. **Syntax errors**: Check if next line starts with `then` or `do` keywords
6. **Always sort issues by line number** before outputting

### Key Patterns to Detect

**Missing shebang**:
```python
# Check first line
if not lines or not lines[0].startswith('#!'):
    # Flag as MISSING_SHEBANG
```

**Unquoted variables**:
```python
# Pattern: $var not in quotes, not special vars, not in arithmetic
# Must exclude: $?, $#, $$, $!, $@, $*, assignments, arithmetic
if re.search(r'\$[a-zA-Z_]\w*', line):
    # Check if it's quoted
    if not re.search(r'"\$[a-zA-Z_]\w*"', line):
        # Check if it's in safe context (assignment, arithmetic, etc.)
        if not (line.strip().startswith('((') or '=$' in line):
            # Flag as UNQUOTED_VAR
```

**Missing error handling**:
```python
# Commands that should have error checking
critical_commands = ['cd', 'cp', 'mv']
has_set_e = any('set -e' in line for line in lines)
```

**Unsafe rm**:
```python
# Pattern: rm -rf with unquoted variable
pattern = r'\brm\s+.*-[a-z]*r[a-z]*f.*\$\w+'
```

**Eval usage**:
```python
# Pattern: eval command
pattern = r'\beval\b'
```

**Hardcoded paths**:
```python
# Pattern: /home/user or /Users/user
pattern = r'/home/[a-zA-Z0-9_]+|/Users/[a-zA-Z0-9_]+'
```

**Useless cat**:
```python
# Pattern: cat file | command
pattern = r'cat\s+[^|]+\s*\|'
```

**Unquoted command substitution**:
```python
# CRITICAL: Use re.finditer() to find ALL matches, not just first one
import re

# Find all command substitutions (both forms)
for match in re.finditer(r'\$\([^)]+\)|`[^`]+`', line):
    cmd_sub_pos = match.start()
    
    # Check if this command substitution is inside double quotes
    in_quotes = False
    quote_start = -1
    for i, char in enumerate(line):
        if char == '"' and (i == 0 or line[i-1] != '\\'):
            if quote_start == -1:
                quote_start = i
            else:
                if quote_start < cmd_sub_pos < i:
                    in_quotes = True
                    break
                quote_start = -1
    
    # Flag if not quoted
    if not in_quotes:
        # Add UNQUOTED_COMMAND_SUB issue
        break  # Only report once per line
```

**Missing local variables**:
```python
# Track if we're inside a function
# Pattern: variable assignment without 'local' keyword
if in_function and re.match(r'^\s*[a-zA-Z_]\w*=', line):
    if not line.strip().startswith('local '):
        # Flag as MISSING_LOCAL_VAR
```

**Glob in test**:
```python
# Pattern: [ ... = *.ext ] or [ ... = ?.ext ]
if re.search(r'\[\s+[^]]*[*?][^]]*\]', line):
    # Check if glob pattern is quoted
```

## Success Criteria

Your implementation must:
1. Detect the following error types with correct line numbers:
   - MISSING_SHEBANG
   - UNQUOTED_VAR (with proper context awareness)
   - UNQUOTED_COMMAND_SUB (detect unquoted $() and backticks)
   - UNSAFE_RM
   - MISSING_ERROR_CHECK
   - EVAL_USAGE
   - INVALID_SYNTAX
   - MISSING_LOCAL_VAR (function scope tracking)
   - HARDCODED_PATH (warning)
   - USELESS_CAT (warning)
   - GLOB_IN_TEST (warning)
2. Provide actionable suggestions for each issue
3. Not produce false positives for:
   - Special variables ($?, $#, $$, $!, $@, $*)
   - Variables in arithmetic contexts
   - Variables in assignments
   - Variables in array indices
   - Quoted variables and command substitutions
   - Global variable assignments outside functions
   - Globs in [[ ]] tests (which handle them correctly)
4. Output valid JSON matching the schema
5. Handle edge cases (empty files, comments-only files)
6. Recognize `set -e` to skip error handling checks
7. Track function scope for local variable detection

## Test Cases

Your implementation will be tested against:

1. **Missing Shebang**: Script without shebang line
2. **Unsafe rm Command**: Script with `rm -rf $var`
3. **Missing Error Handling**: Commands without error checks
4. **Eval Usage**: Script using dangerous `eval`
5. **Syntax Errors**: Invalid bash syntax
6. **Multiple Issues**: Script with various problems
7. **Clean Script**: Well-written script with no issues
8. **Complex Script**: Script with functions, loops, and conditionals
9. **Edge Case - Empty File**: Empty file handling
10. **Edge Case - Comments Only**: File with only shebang and comments (must return has_issues=false, issue_count=0)
11. **Unquoted Variables**: Detect unquoted variables in dangerous contexts (echo $var, rm $file, test conditions)
12. **Quoted Variables**: Properly quoted variables should not be flagged
13. **Special Variables**: Special variables ($?, $#, $$, $!, $@) should not be flagged
14. **Hardcoded Paths**: Detect hardcoded absolute paths
15. **set -e Behavior**: Scripts with `set -e` should skip error handling checks
16. **Issue Sorting**: Issues must be sorted by line number
17. **Unquoted Command Substitution**: Detect unquoted $(cmd) and `cmd`
18. **Quoted Command Substitution**: Quoted command substitutions should not be flagged
19. **Missing Local Variables**: Detect variable assignments in functions without local keyword
20. **Local Variables**: Functions with proper local declarations should not be flagged
21. **Glob in Test**: Detect unquoted glob patterns in [ ] tests
22. **Glob in Double Bracket**: Globs in [[ ]] tests should not be flagged
23. **Arithmetic Context**: Variables in (( )) and $(( )) should not be flagged
24. **Array Indices**: Variables in ${array[$var]} should not be flagged
25. **Unclosed Quotes**: Detect unclosed quotes as syntax error
26. **Unclosed Brackets**: Detect missing fi/done as syntax error
27. **Output Format**: Validate JSON output format
28. **Variables in Assignments**: Variables on right side of assignments (new_var=$old_var) should not be flagged
29. **Output Path Parameter**: Verify --out parameter works with arbitrary paths (not just /app/report.json)
30. **Non-Critical Commands**: Only cd/cp/mv should be checked for error handling, not echo/mkdir/touch/ls/grep
31. **Line Continuations**: Handle line continuations with backslash without crashing

## Files of Interest

- `/app/lint_shell.py` - Your implementation
- `/tests/test_outputs.py` - Test cases that validate correctness

## Implementation Notes

### Command Line Arguments

Your implementation MUST:
1. Accept `--script` parameter for input script path
2. Accept `--out` parameter for output JSON path
3. **Use the exact path provided in `--out`** - do not hardcode `/app/report.json`
4. Create output file at the specified `--out` path

```python
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--script', required=True, help='Path to shell script')
    parser.add_argument('--out', required=True, help='Output JSON path like /app/report.json')
    cli_args = parser.parse_args()
    
    # Extract command line arguments (both will be absolute paths)
    script_path = cli_args.script
    output_path = getattr(cli_args, 'out')  # Output path like /app/report.json
    lint_shell(script_path, output_path)
```

### Line Continuations

Handle line continuations (backslash `\` at end of line):
- Lines ending with `\` continue to the next line
- For simplicity, you may process each line independently
- Don't crash on line continuations - handle gracefully

### Required Approach

1. **Use regex for pattern matching** - most efficient for line-by-line analysis
2. **Track script context** - know if you're inside a function, loop, etc.
3. **Handle continuations** - lines ending with `\` continue on next line
4. **Validate output** - ensure JSON is valid and matches schema
5. **Provide line numbers** - critical for debugging

### Common Pitfalls to Avoid

1. **Shebang Detection**:
   - Check the very first line only
   - Don't flag scripts that start with `#!`

2. **Error Handling**:
   - Recognize `set -e` at script level
   - Check for `||`, `&&`, or `if` patterns
   - Only flag critical commands (cd, cp, mv)

3. **Syntax Validation**:
   - Check for missing `then` after `if [ ... ]`
   - Check for missing `do` after `for ... in ...`
   - Use regex, don't execute bash code

## Example Project Structure

```
/app/
├── lint_shell.py        # Your implementation
├── /app/test_script.sh  # Script to analyze
└── /app/report.json     # Output file
```

## Implementation Tips

1. **Error Handling Detection**:
   - ✅ Check for `set -e` at the start of the script
   - ✅ Look for `||`, `&&`, or `if` patterns on the same line
   - ✅ Focus on critical commands: cd, cp, mv

2. **Unsafe rm Detection**:
   - ✅ Look for `rm -rf` or `rm -fr` patterns
   - ✅ Check if there's an unquoted variable (no quotes around `$var`)
   - ✅ Flag when both conditions are met

3. **Syntax Validation**:
   - ✅ Use regex patterns, never execute bash code
   - ✅ Check the next line for `then` or `do` keywords
   - ✅ Keep it simple - basic pattern matching is sufficient
