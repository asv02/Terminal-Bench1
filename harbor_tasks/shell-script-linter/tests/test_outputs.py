import json
import subprocess
from pathlib import Path
import tempfile


def run_linter(script_content: str) -> dict:
    """Helper function to run the linter on a test script."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        output_path = Path("/app/report.json")
        result = subprocess.run(
            ["python", "/app/lint_shell.py", "--script", script_path, "--out", str(output_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, f"Linter failed: {result.stderr}"
        assert output_path.exists(), "Output file not created"
        
        with open(output_path) as f:
            return json.load(f)
    finally:
        Path(script_path).unlink(missing_ok=True)


def test_missing_shebang():
    """Test 2: Detect missing shebang line."""
    script = '''echo "Hello World"
cd /tmp
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect missing shebang"
    
    shebang_issues = [i for i in result["issues"] if i["code"] == "MISSING_SHEBANG"]
    assert len(shebang_issues) == 1, "Should have exactly one MISSING_SHEBANG issue"
    assert shebang_issues[0]["line"] == 1, "Shebang issue should be on line 1"
    assert shebang_issues[0]["severity"] == "error", "Missing shebang should be an error"


def test_unsafe_rm_command():
    """Test 3: Detect unsafe rm -rf usage."""
    script = '''#!/bin/bash
dir=$1
rm -rf $dir
rm -rf /tmp/$var
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect unsafe rm commands"
    
    unsafe_rm_issues = [i for i in result["issues"] if i["code"] == "UNSAFE_RM"]
    assert len(unsafe_rm_issues) >= 1, "Should detect at least one unsafe rm"
    assert unsafe_rm_issues[0]["severity"] == "error", "Unsafe rm should be an error"


def test_missing_error_handling():
    """Test 4: Detect commands without error handling."""
    script = '''#!/bin/bash
cd /some/directory
cp file.txt backup/
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect missing error handling"
    
    error_check_issues = [i for i in result["issues"] if i["code"] == "MISSING_ERROR_CHECK"]
    assert len(error_check_issues) >= 1, "Should detect commands without error handling"


def test_eval_usage():
    """Test 5: Detect dangerous eval command."""
    script = '''#!/bin/bash
command="ls -la"
eval $command
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect eval usage"
    
    eval_issues = [i for i in result["issues"] if i["code"] == "EVAL_USAGE"]
    assert len(eval_issues) == 1, "Should detect eval usage"
    assert eval_issues[0]["severity"] == "error", "Eval usage should be an error"
    assert "eval" in eval_issues[0]["message"].lower(), "Error message should mention eval"


def test_syntax_errors():
    """Test 6: Detect bash syntax errors."""
    script = '''#!/bin/bash
if [ $x -eq 1 ]
    echo "Missing then"
fi

for i in 1 2 3
    echo $i
done
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect syntax errors"
    
    syntax_issues = [i for i in result["issues"] if i["code"] == "INVALID_SYNTAX"]
    assert len(syntax_issues) >= 1, "Should detect syntax errors"


def test_multiple_issues():
    """Test 7: Script with multiple different issues."""
    script = '''echo "No shebang"
file=$1
echo $file
rm -rf $file
eval "ls -la"
cd /tmp
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect multiple issues"
    assert result["issue_count"] >= 4, "Should find at least 4 different issues"
    
    # Check for variety of issue codes
    codes = set(i["code"] for i in result["issues"])
    assert "MISSING_SHEBANG" in codes, "Should detect missing shebang"
    assert "UNSAFE_RM" in codes or "EVAL_USAGE" in codes, "Should detect unsafe patterns"


def test_clean_script():
    """Test 8: Well-written script with no issues."""
    script = '''#!/bin/bash
set -euo pipefail

file="$1"

if [ -z "$file" ]; then
    echo "Error: No file specified" >&2
    exit 1
fi

if [ -f "$file" ]; then
    cp "$file" "/tmp/backup" || {
        echo "Copy failed" >&2
        exit 1
    }
fi

echo "Success"
'''
    result = run_linter(script)
    
    # A clean script might have info-level suggestions but no errors
    error_issues = [i for i in result["issues"] if i["severity"] == "error"]
    assert len(error_issues) == 0, "Clean script should have no errors"


def test_complex_script_with_functions():
    """Test 9: Complex script with functions, loops, and conditionals."""
    script = '''#!/bin/bash
set -e

process_file() {
    local file=$1
    if [ -f "$file" ]; then
        cat "$file" | grep pattern
    fi
}

for file in *.txt; do
    process_file "$file"
done
'''
    result = run_linter(script)
    
    # Should detect useless cat in function
    assert result["has_issues"] is True, "Should detect issues in complex script"
    
    useless_cat_issues = [i for i in result["issues"] if i["code"] == "USELESS_CAT"]
    
    assert len(useless_cat_issues) >= 1, "Should detect useless cat"


def test_edge_case_empty_file():
    """Test 10: Empty file edge case."""
    script = ''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Empty file should have missing shebang issue"
    assert result["issue_count"] >= 1, "Should report at least missing shebang"


def test_edge_case_comments_only():
    """Test 11: File with only comments."""
    script = '''#!/bin/bash
# This is a comment
# Another comment
'''
    result = run_linter(script)
    
    # File with shebang and only comments should have no issues at all
    assert result["has_issues"] is False, "Comments-only script should have has_issues=false"
    assert result["issue_count"] == 0, "Comments-only script should have issue_count=0"
    assert len(result["issues"]) == 0, "Comments-only script should have empty issues list"


def test_unquoted_variables():
    """Test 12: Detect unquoted variables in dangerous contexts."""
    script = '''#!/bin/bash
set -e

message="Hello"
echo $message
rm $file
if [ $status = "ok" ]; then
    echo "Status is ok"
fi
'''
    result = run_linter(script)
    
    # Should detect unquoted variables
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    assert len(unquoted_issues) >= 2, "Should detect at least 2 unquoted variables"


def test_quoted_variables_not_flagged():
    """Test 13: Properly quoted variables should not be flagged."""
    script = '''#!/bin/bash
set -e

file="$1"
echo "Processing: $file"
rm "$file"
if [ "$status" = "ok" ]; then
    echo "Status is ok"
fi
'''
    result = run_linter(script)
    
    # Should not flag quoted variables
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    assert len(unquoted_issues) == 0, "Should not flag quoted variables"


def test_special_variables_not_flagged():
    """Test 14: Special variables should not be flagged."""
    script = '''#!/bin/bash
set -e

exit_code=$?
arg_count=$#
pid=$$
last_bg=$!
all_args=$@
'''
    result = run_linter(script)
    
    # Special variables should not be flagged
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    assert len(unquoted_issues) == 0, "Should not flag special variables"


def test_hardcoded_paths():
    """Test 15: Detect hardcoded absolute paths."""
    script = '''#!/bin/bash
cp /app/file.txt /home/user/backup/
cd /home/user/project
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect hardcoded paths"
    
    hardcoded_issues = [i for i in result["issues"] if i["code"] == "HARDCODED_PATH"]
    assert len(hardcoded_issues) >= 1, "Should detect hardcoded paths"
    assert hardcoded_issues[0]["severity"] == "warning", "Hardcoded paths should be warnings"


def test_set_e_skips_error_handling():
    """Test 16: Scripts with set -e should skip error handling checks."""
    script = '''#!/bin/bash
set -e

cd /some/directory
cp file.txt backup/
mv old.txt new.txt
'''
    result = run_linter(script)
    
    # Should not flag missing error handling when set -e is present
    error_check_issues = [i for i in result["issues"] if i["code"] == "MISSING_ERROR_CHECK"]
    assert len(error_check_issues) == 0, "Should not flag error handling when set -e is present"


def test_issue_sorting_by_line_number():
    """Test 17: Issues should be sorted by line number."""
    script = '''#!/bin/bash
eval "ls"
cd /tmp
rm -rf $dir
cp file.txt /home/user/backup/
'''
    result = run_linter(script)
    
    assert result["has_issues"] is True, "Should detect multiple issues"
    assert len(result["issues"]) >= 3, "Should have at least 3 issues"
    
    # Verify issues are sorted by line number
    line_numbers = [issue["line"] for issue in result["issues"]]
    assert line_numbers == sorted(line_numbers), "Issues must be sorted by line number"


def test_unquoted_command_substitution():
    """Test 18: Detect unquoted command substitution."""
    script = '''#!/bin/bash
set -e

files=$(ls *.txt)
result=`grep pattern file`
echo $(date)
'''
    result = run_linter(script)
    
    # Should detect unquoted command substitutions
    cmd_sub_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_COMMAND_SUB"]
    assert len(cmd_sub_issues) >= 2, "Should detect at least 2 unquoted command substitutions"


def test_quoted_command_substitution_not_flagged():
    """Test 19: Quoted command substitutions should not be flagged."""
    script = '''#!/bin/bash
set -e

files="$(ls *.txt)"
result="$(grep pattern file)"
echo "Current time: $(date)"
'''
    result = run_linter(script)
    
    # Should not flag quoted command substitutions
    cmd_sub_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_COMMAND_SUB"]
    assert len(cmd_sub_issues) == 0, "Should not flag quoted command substitutions"


def test_missing_local_variables():
    """Test 20: Detect missing local keyword in functions."""
    script = '''#!/bin/bash
set -e

function process_file() {
    filename="$1"
    count=0
    echo "Processing $filename"
}

process_file "test.txt"
'''
    result = run_linter(script)
    
    # Should detect missing local declarations
    local_issues = [i for i in result["issues"] if i["code"] == "MISSING_LOCAL_VAR"]
    assert len(local_issues) >= 1, "Should detect at least 1 missing local variable"


def test_local_variables_not_flagged():
    """Test 21: Functions with local variables should not be flagged."""
    script = '''#!/bin/bash
set -e

function process_file() {
    local filename="$1"
    local count=0
    echo "Processing $filename"
}

process_file "test.txt"
'''
    result = run_linter(script)
    
    # Should not flag proper local declarations
    local_issues = [i for i in result["issues"] if i["code"] == "MISSING_LOCAL_VAR"]
    assert len(local_issues) == 0, "Should not flag functions with local variables"


def test_glob_in_test():
    """Test 22: Detect unquoted glob patterns in [ ] tests."""
    script = '''#!/bin/bash
set -e

file="test.txt"
if [ $file = *.txt ]; then
    echo "Text file"
fi
'''
    result = run_linter(script)
    
    # Should detect glob in test
    glob_issues = [i for i in result["issues"] if i["code"] == "GLOB_IN_TEST"]
    assert len(glob_issues) >= 1, "Should detect glob pattern in test"
    assert glob_issues[0]["severity"] == "warning", "Glob in test should be warning"


def test_glob_in_double_bracket_not_flagged():
    """Test 23: Globs in [[ ]] tests should not be flagged."""
    script = '''#!/bin/bash
set -e

file="test.txt"
if [[ $file == *.txt ]]; then
    echo "Text file"
fi
'''
    result = run_linter(script)
    
    # Should not flag globs in [[ ]] tests
    glob_issues = [i for i in result["issues"] if i["code"] == "GLOB_IN_TEST"]
    assert len(glob_issues) == 0, "Should not flag globs in [[ ]] tests"


def test_arithmetic_context_not_flagged():
    """Test 24: Variables in arithmetic contexts should not be flagged."""
    script = '''#!/bin/bash
set -e

count=5
((count++))
((total = count + 10))
result=$((count * 2))
echo "Result: $result"
'''
    result = run_linter(script)
    
    # Variables in arithmetic should not be flagged as unquoted
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    # Check that variables on lines 6-8 (arithmetic contexts) are not flagged
    arithmetic_lines = {6, 7, 8}  # Lines with ((count++)), ((total = count + 10)), $((count * 2))
    for issue in unquoted_issues:
        issue_line = issue.get("line", 0)
        assert issue_line not in arithmetic_lines, f"Should not flag variables in arithmetic context on line {issue_line}"


def test_array_indices_not_flagged():
    """Test 25: Variables in array indices should not be flagged."""
    script = '''#!/bin/bash
set -e

array=(one two three)
index=1
value=${array[$index]}
echo "Value: $value"
'''
    result = run_linter(script)
    
    # Variables in array indices should not be flagged
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    # Line 7 has ${array[$index]} - the $index should not be flagged
    array_index_line = 7
    for issue in unquoted_issues:
        issue_line = issue.get("line", 0)
        message = issue.get("message", "")
        if issue_line == array_index_line and "index" in message:
            assert False, f"Should not flag $index in array index on line {issue_line}"


def test_unclosed_quotes_syntax_error():
    """Test 26: Detect unclosed quotes as syntax error."""
    script = '''#!/bin/bash
set -e

echo "This is unclosed
echo "Another line"
'''
    result = run_linter(script)
    
    # Should detect syntax error for unclosed quotes
    syntax_issues = [i for i in result["issues"] if i["code"] == "INVALID_SYNTAX"]
    assert len(syntax_issues) >= 1, "Should detect unclosed quotes as syntax error"


def test_unclosed_brackets_syntax_error():
    """Test 27: Detect unclosed brackets as syntax error."""
    script = '''#!/bin/bash
set -e

if [ -f "file.txt" ; then
    echo "File exists"
# Missing fi

for i in 1 2 3; do
    echo $i
# Missing done
'''
    result = run_linter(script)
    
    # Should detect syntax errors for unclosed structures
    syntax_issues = [i for i in result["issues"] if i["code"] == "INVALID_SYNTAX"]
    assert len(syntax_issues) >= 1, "Should detect unclosed brackets/structures as syntax error"


def test_output_format_validation():
    """Test 28: Validate JSON output format."""
    script = '''#!/bin/bash
echo $var
'''
    result = run_linter(script)
    
    # Validate required fields
    assert "has_issues" in result, "Output must have 'has_issues' field"
    assert "issue_count" in result, "Output must have 'issue_count' field"
    assert "issues" in result, "Output must have 'issues' field"
    assert isinstance(result["has_issues"], bool), "'has_issues' must be boolean"
    assert isinstance(result["issue_count"], int), "'issue_count' must be integer"
    assert isinstance(result["issues"], list), "'issues' must be list"
    
    # Validate issue structure
    if result["issues"]:
        issue = result["issues"][0]
        assert "line" in issue, "Issue must have 'line' field"
        assert "severity" in issue, "Issue must have 'severity' field"
        assert "code" in issue, "Issue must have 'code' field"
        assert "message" in issue, "Issue must have 'message' field"
        assert "suggestion" in issue, "Issue must have 'suggestion' field"


def test_variables_in_assignments_not_flagged():
    """Test 29: Variables in assignments (new_var=$old_var) should not be flagged."""
    script = '''#!/bin/bash
set -e

old_value="test"
new_value=$old_value
result=$old_value
path=$HOME/data
'''
    result = run_linter(script)
    
    # Variables in assignments should not be flagged as UNQUOTED_VAR
    unquoted_issues = [i for i in result["issues"] if i["code"] == "UNQUOTED_VAR"]
    # Lines 5, 6, 7 have assignments - none should be flagged
    assignment_lines = {5, 6, 7}
    for issue in unquoted_issues:
        issue_line = issue.get("line", 0)
        if issue_line in assignment_lines:
            assert False, f"Should not flag variable in assignment on line {issue_line}"


def test_output_path_parameter():
    """Test 30: Verify --out parameter works with arbitrary paths."""
    import tempfile
    import os
    
    script_content = '''#!/bin/bash
set -e
echo "test"
'''
    
    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = os.path.join(tmpdir, "test_script.sh")
        output_path = os.path.join(tmpdir, "custom_output.json")
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Run linter with custom output path
        cmd = f"python /app/lint_shell.py --script {script_path} --out {output_path}"
        exit_code = subprocess.run(cmd, shell=True, capture_output=True).returncode
        
        assert exit_code == 0, "Linter should run successfully with custom --out path"
        assert os.path.exists(output_path), f"Output file should be created at {output_path}"
        
        # Verify output is valid JSON
        with open(output_path, 'r') as f:
            result = json.load(f)
        
        assert "has_issues" in result, "Output must have 'has_issues' field"
        assert result["has_issues"] is False, "Clean script should have no issues"


def test_non_critical_commands_not_flagged():
    """Test 31: Only cd/cp/mv should be checked for error handling, not other commands."""
    script = '''#!/bin/bash

echo "test"
mkdir /tmp/test
touch /tmp/file
ls /tmp
grep pattern file
'''
    result = run_linter(script)
    
    # Should not flag echo, mkdir, touch, ls, grep for missing error handling
    error_check_issues = [i for i in result["issues"] if i["code"] == "MISSING_ERROR_CHECK"]
    assert len(error_check_issues) == 0, "Should not flag non-cd/cp/mv commands for error handling"


def test_line_continuations():
    """Test 32: Handle line continuations with backslash."""
    script = '''#!/bin/bash
set -e

echo "This is a long line" \\
     "continued here" \\
     "and here"

command \\
    --option1 \\
    --option2
'''
    result = run_linter(script)
    
    # Should handle line continuations without crashing
    # No specific issues expected for line continuations themselves
    assert "has_issues" in result, "Should return valid result"
    assert "issues" in result, "Should have issues field"
