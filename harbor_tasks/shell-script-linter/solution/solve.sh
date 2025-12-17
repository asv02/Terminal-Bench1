#!/bin/bash
set -euo pipefail

# Create simplified Python linter
cat > /app/lint_shell.py << 'EOF'
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
    
    # Check shebang
    if not lines or not lines[0].startswith('#!'):
        issues.append({
            'line': 1,
            'severity': 'error',
            'code': 'MISSING_SHEBANG',
            'message': 'Script missing shebang line',
            'suggestion': 'Add #!/bin/bash as first line'
        })
    
    # Check each line
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Check for unquoted variables
        # First check if this line is an assignment
        is_assignment = False
        assign_match = re.match(r'^\s*([a-zA-Z_]\w*)=(.*)$', stripped)
        if assign_match:
            is_assignment = True
            lhs_var = assign_match.group(1)
        
        # Find all variables in the line
        var_matches = re.finditer(r'\$([a-zA-Z_]\w*|\?|#|\$|!|@|\*)', stripped)
        for match in var_matches:
            var_name = match.group(1)
            # Skip special variables
            if var_name in ['?', '#', '$', '!', '@', '*']:
                continue
            
            var_pattern = f'\${var_name}'
            var_pos = match.start()
            
            # Skip if this is an assignment line and variable is on RHS
            if is_assignment:
                # Find position of = sign
                eq_pos = stripped.find('=')
                # If variable is after the =, it's on RHS - skip it
                if var_pos > eq_pos:
                    continue
            
            # Skip if it's in arithmetic context - both (( )) and $(( ))
            if re.search(r'\(\([^)]*' + re.escape(var_pattern), stripped):
                continue
            if re.search(r'\$\(\([^)]*' + re.escape(var_pattern), stripped):
                continue
            # Skip if it's in array index: ${array[$var]}
            if re.search(r'\$\{[^}]*\[' + re.escape(var_pattern) + r'\]', stripped):
                continue
            
            # Check if variable is inside double quotes
            # Find all quoted sections in the line
            in_quotes = False
            quote_start = -1
            for i, char in enumerate(stripped):
                if char == '"' and (i == 0 or stripped[i-1] != '\\'):
                    if quote_start == -1:
                        quote_start = i
                    else:
                        # Check if variable is in this quoted section
                        if quote_start < var_pos < i:
                            in_quotes = True
                            break
                        quote_start = -1
            
            # Flag if not quoted
            if not in_quotes:
                issues.append({
                    'line': line_num,
                    'severity': 'error',
                    'code': 'UNQUOTED_VAR',
                    'message': f'Variable ${var_name} used without quotes',
                    'suggestion': 'Wrap variable in double quotes: "$' + var_name + '"'
                })
                break  # Only report once per line
        
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
        
        # Check for missing error handling
        has_set_e = any('set -e' in l for l in lines)
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
        
        # Check for unclosed quotes
        quote_count = stripped.count('"') - stripped.count('\\"')
        if quote_count % 2 != 0:
            issues.append({
                'line': line_num,
                'severity': 'error',
                'code': 'INVALID_SYNTAX',
                'message': 'Unclosed quote in line',
                'suggestion': 'Close all quote marks'
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
                'suggestion': 'Use input redirection or pass file directly'
            })
    
    # Check for unclosed structures (if/for/while without fi/done)
    if_count = sum(1 for line in lines if re.match(r'^\s*if\s+', line.strip()))
    fi_count = sum(1 for line in lines if re.match(r'^\s*fi\s*$', line.strip()))
    if if_count > fi_count:
        issues.append({
            'line': len(lines),
            'severity': 'error',
            'code': 'INVALID_SYNTAX',
            'message': 'Unclosed if statement (missing fi)',
            'suggestion': 'Add fi to close if statement'
        })
    
    for_count = sum(1 for line in lines if re.match(r'^\s*for\s+', line.strip()))
    done_count = sum(1 for line in lines if re.match(r'^\s*done\s*$', line.strip()))
    if for_count > done_count:
        issues.append({
            'line': len(lines),
            'severity': 'error',
            'code': 'INVALID_SYNTAX',
            'message': 'Unclosed for loop (missing done)',
            'suggestion': 'Add done to close for loop'
        })
    
    # Second pass: check for unquoted command substitution and function-specific issues
    in_function = False
    for line_num, line in enumerate(lines, 1):
        stripped = line.strip()
        
        # Track function scope
        if re.match(r'^(function\s+)?\w+\s*\(\s*\)', stripped):
            in_function = True
        elif stripped == '}':
            in_function = False
        
        # Skip comments and empty lines
        if not stripped or stripped.startswith('#'):
            continue
        
        # Check for unquoted command substitution
        # Find $(...) or `...` patterns
        cmd_sub_matches = list(re.finditer(r'\$\([^)]+\)|`[^`]+`', stripped))
        for match in cmd_sub_matches:
            cmd_sub_pos = match.start()
            
            # Check if command substitution is inside double quotes
            in_quotes = False
            quote_start = -1
            for i, char in enumerate(stripped):
                if char == '"' and (i == 0 or stripped[i-1] != '\\'):
                    if quote_start == -1:
                        quote_start = i
                    else:
                        if quote_start < cmd_sub_pos < i:
                            in_quotes = True
                            break
                        quote_start = -1
            
            # Flag if not quoted
            if not in_quotes:
                issues.append({
                    'line': line_num,
                    'severity': 'error',
                    'code': 'UNQUOTED_COMMAND_SUB',
                    'message': 'Command substitution without quotes',
                    'suggestion': 'Wrap command substitution in double quotes'
                })
                break  # Only report once per line
        
        # Check for missing local variables in functions
        if in_function:
            # Check for variable assignment without local keyword
            if re.match(r'^\s*[a-zA-Z_]\w*=', stripped):
                if not stripped.startswith('local '):
                    issues.append({
                        'line': line_num,
                        'severity': 'error',
                        'code': 'MISSING_LOCAL_VAR',
                        'message': 'Variable assignment in function without local keyword',
                        'suggestion': 'Declare variable as local: local varname=value'
                    })
        
        # Check for glob patterns in [ ] tests (not [[ ]])
        if re.search(r'\[\s+[^]]*[*?]', stripped) and not re.search(r'\[\[', stripped):
            # Check if the glob pattern is quoted
            if not re.search(r'"[^"]*[*?][^"]*"', stripped):
                issues.append({
                    'line': line_num,
                    'severity': 'warning',
                    'code': 'GLOB_IN_TEST',
                    'message': 'Unquoted glob pattern in [ ] test',
                    'suggestion': 'Quote glob patterns or use [[ ]] for pattern matching'
                })
    
    # Sort issues by line number
    issues.sort(key=lambda x: x['line'])
    
    result = {
        'has_issues': len(issues) > 0,
        'issue_count': len(issues),
        'issues': issues
    }
    
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--script', required=True, help='Path to shell script')
    parser.add_argument('--out', required=True, help='Output JSON path like /app/report.json')
    cli_args = parser.parse_args()
    
    # Extract command line arguments (both will be absolute paths)
    script_path = cli_args.script
    output_path = getattr(cli_args, 'out')  # Output path like /app/report.json
    lint_shell(script_path, output_path)
EOF

chmod +x /app/lint_shell.py
