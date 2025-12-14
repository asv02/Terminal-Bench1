#!/bin/bash

# Oracle Solution - Creates the integrity monitoring script
# This is the step-by-step solution that the OracleAgent will execute

set -e

# Create the integrity monitoring script at /app/integrity.sh
cat > /app/integrity.sh << 'INTEGRITY_SCRIPT_EOF'
#!/bin/bash
# File Integrity Monitor Script

set -e
set -u

# Ensure consistent locale for deterministic sorting
export LC_ALL=C
export LANG=C

# Function to generate manifest for a directory
generate_manifest() {
    local target_dir="$1"

    if [[ ! -d "$target_dir" ]]; then
        echo "Error: Directory does not exist" >&2
        exit 1
    fi

    # Use find with null-delimited output for safe handling of special chars
    # -type f ensures only regular files (skips symlinks)
    find "$target_dir" -type f -print0 | sort -z | while IFS= read -r -d '' filepath; do
        # Use absolute path directly (filepath from find is already absolute)
        local abs_path="$filepath"

        # Calculate SHA-256 hash (use -- to handle files starting with dash)
        # sha256sum outputs lowercase by default, no need to convert
        local hash=$(sha256sum -- "$filepath" | awk '{print $1}')

        # Output with exactly two spaces
        printf "%s  %s\n" "$hash" "$abs_path"
    done
}

# Function to escape string for JSON
json_escape() {
    local input="$1"
    local output=""

    local i
    for (( i=0; i<${#input}; i++ )); do
        local char="${input:$i:1}"
        case "$char" in
            '"')  output+='\"' ;;
            '\') output+='\\' ;;
            $'\n') output+='\n' ;;
            $'\t') output+='\t' ;;
            $'\r') output+='\r' ;;
            *)    output+="$char" ;;
        esac
    done

    echo "$output"
}

# Function to generate JSON array
generate_json_array() {
    local first=true
    echo -n "["

    for item in "$@"; do
        # Skip empty strings (from empty array sorting)
        if [[ -z "$item" ]]; then
            continue
        fi

        if [[ "$first" == "true" ]]; then
            first=false
        else
            echo -n ","
        fi

        local escaped=$(json_escape "$item")
        echo -n "\"$escaped\""
    done

    echo -n "]"
}

# Function to compare manifests
compare_manifests() {
    local old_manifest="$1"
    local new_manifest="$2"
    local output_file="/app/diff.json"

    if [[ ! -f "$old_manifest" ]] || [[ ! -f "$new_manifest" ]]; then
        echo "Error: Manifest files do not exist" >&2
        exit 1
    fi

    # Parse old manifest into associative array
    declare -A old_files
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip blank lines
        [[ -z "$line" ]] && continue
        
        # Skip comment lines starting with #
        [[ "$line" =~ ^# ]] && continue
        
        local hash="${line%%  *}"
        local path="${line#*  }"
        
        # Skip duplicate paths (use first occurrence)
        [[ -v old_files["$path"] ]] && continue
        
        # Store hash as-is (don't normalize case here)
        old_files["$path"]="$hash"
    done < "$old_manifest"

    # Parse new manifest into associative array
    declare -A new_files
    while IFS= read -r line || [[ -n "$line" ]]; do
        # Skip blank lines
        [[ -z "$line" ]] && continue
        
        # Skip comment lines starting with #
        [[ "$line" =~ ^# ]] && continue
        
        local hash="${line%%  *}"
        local path="${line#*  }"
        
        # Skip duplicate paths (use first occurrence)
        [[ -v new_files["$path"] ]] && continue
        
        # Store hash as-is (don't normalize case here)
        new_files["$path"]="$hash"
    done < "$new_manifest"

    # Identify changes
    local added_files=()
    local removed_files=()
    local modified_files=()

    # Check for removed and modified
    for path in "${!old_files[@]}"; do
        if [[ ! -v new_files["$path"] ]]; then
            removed_files+=("$path")
        else
            # Case-insensitive hash comparison using ${var,,} (bash 4.0+)
            local old_hash_lower="${old_files[$path],,}"
            local new_hash_lower="${new_files[$path],,}"
            
            if [[ "$old_hash_lower" != "$new_hash_lower" ]]; then
                modified_files+=("$path")
            fi
        fi
    done

    # Check for added
    for path in "${!new_files[@]}"; do
        if [[ ! -v old_files["$path"] ]]; then
            added_files+=("$path")
        fi
    done

    # Sort for deterministic output - ONLY if arrays are not empty
    if [[ ${#added_files[@]} -gt 0 ]]; then
        IFS=$'\n' added_files=($(printf '%s\n' "${added_files[@]}" | sort))
    fi

    if [[ ${#removed_files[@]} -gt 0 ]]; then
        IFS=$'\n' removed_files=($(printf '%s\n' "${removed_files[@]}" | sort))
    fi

    if [[ ${#modified_files[@]} -gt 0 ]]; then
        IFS=$'\n' modified_files=($(printf '%s\n' "${modified_files[@]}" | sort))
    fi

    # Generate JSON
    {
        echo "{"
        echo -n "  \"added\": "
        generate_json_array "${added_files[@]}"
        echo ","

        echo -n "  \"removed\": "
        generate_json_array "${removed_files[@]}"
        echo ","

        echo -n "  \"modified\": "
        generate_json_array "${modified_files[@]}"
        echo ""

        echo "}"
    } > "$output_file"
}

# Main entry point
main() {
    case "${1:-}" in
        --generate)
            generate_manifest "$2"
            ;;
        --old)
            if [[ "${3:-}" == "--new" ]]; then
                compare_manifests "$2" "$4"
            else
                echo "Error: Invalid arguments" >&2
                exit 1
            fi
            ;;
        *)
            echo "Usage: $0 --generate <dir> OR $0 --old <old> --new <new>" >&2
            exit 1
            ;;
    esac
}

main "$@"
INTEGRITY_SCRIPT_EOF

# Make the script executable
chmod +x /app/integrity.sh

# Verify the script was created successfully
if [[ -f /app/integrity.sh ]] && [[ -x /app/integrity.sh ]]; then
    echo "Successfully created /app/integrity.sh"
else
    echo "Error: Failed to create executable script" >&2
    exit 1
fi