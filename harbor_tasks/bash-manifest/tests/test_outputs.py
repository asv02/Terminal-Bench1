"""
Test suite for Bash File Integrity Monitor task.

This test suite validates that the agent correctly implements a file integrity
monitoring script with manifest generation and comparison capabilities.

All tests verify behaviors that are explicitly described in instruction.md.
"""

import json
import os
import subprocess
import tempfile

class TestScriptExistence:
    """Tests that verify the basic script setup and executability."""

    def test_script_exists(self):
        """
        Verify that /app/integrity.sh script was created.

        This checks success criteria #1: The script /app/integrity.sh exists.
        """
        assert os.path.exists("/app/integrity.sh"), (
            "Script /app/integrity.sh does not exist"
        )

    def test_script_is_executable(self):
        """
        Verify that /app/integrity.sh has executable permissions.

        This checks success criteria #1: The script is executable.
        """
        assert os.access("/app/integrity.sh", os.X_OK), (
            "Script /app/integrity.sh is not executable"
        )


class TestManifestGeneration:
    """Tests for Mode 1: Generate Manifest functionality."""

    def test_generate_mode_basic_execution(self):
        """
        Verify that --generate mode executes without errors.

        This checks that the script accepts the --generate flag and
        target directory argument as specified in instruction.md Mode 1.
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )
        assert result.returncode == 0, (
            f"Manifest generation failed with exit code {result.returncode}. "
            f"Stderr: {result.stderr}"
        )


    def test_manifest_format_hash_space_path(self):
        """
        Verify manifest format: HASH  /app/path (two spaces).

        This checks instruction.md requirement: "Each line must follow this exact
        format: HASH  /app/path/to/file (Note: exactly two spaces
        between the hash and the path)".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) > 0, "Manifest output is empty"

        for line_num, line in enumerate(lines, 1):
            # Must contain exactly two spaces as delimiter
            parts = line.split("  ")
            assert len(parts) == 2, (
                f"Line {line_num} has incorrect format. Expected 'HASH  ./path' "
                f"with exactly two spaces. Got: {line}"
            )

            hash_part, path_part = parts

            # Hash must be 64 hex characters (SHA-256)
            assert len(hash_part) == 64, (
                f"Line {line_num}: Hash length is {len(hash_part)}, expected 64. "
                f"Hash: {hash_part}"
            )
            assert all(c in '0123456789abcdef' for c in hash_part.lower()), (
                f"Line {line_num}: Hash contains non-hex characters: {hash_part}"
            )

    def test_manifest_absolute_paths(self):
        """
        Verify that paths are absolute starting with /app/.

        This checks instruction.md requirement: "The paths must be **absolute** (starting with /app/)".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        lines = result.stdout.strip().split("\n")
        
        # Filter out empty lines
        lines = [line for line in lines if line.strip()]

        for line_num, line in enumerate(lines, 1):
            # Handle potential escaping from sha256sum (leading backslash)
            clean_line = line.lstrip("\\")
            parts = clean_line.split("  ", 1)
            
            # Skip malformed lines (checked by other tests)
            if len(parts) < 2:
                continue
                
            path_part = parts[1]
            assert path_part.startswith("/app/"), (
                f"Line {line_num}: Path must start with '/app/' but got: {path_part}"
            )

    def test_manifest_alphabetical_sorting(self):
        """
        Verify that manifest output is sorted alphabetically by file path.

        This checks instruction.md requirement: "The entire output must be
        sorted alphabetically by the file path".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        lines = result.stdout.strip().split("\n")
        paths = [line.split("  ", 1)[1] for line in lines]

        sorted_paths = sorted(paths)

        assert paths == sorted_paths, (
            f"Manifest is not sorted alphabetically. "
            f"Expected order (first 10): {sorted_paths[:10]}, "
            f"Got: {paths[:10]}"
        )

    def test_sha256_hash_correctness(self):
        """
        Verify that SHA-256 hashes are correctly calculated for actual files.

        This checks instruction.md requirement: "Calculate the SHA-256 cryptographic 
        hash for each file" by verifying hashes match actual file content using
        sha256sum verification.
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        lines = result.stdout.strip().split("\n")
        assert len(lines) > 0, "Manifest is empty"

        # Pick at least 10 random files to verify (or all if less than 10)
        import random
        sample_size = min(10, len(lines))
        sampled_lines = random.sample(lines, sample_size)

        for line in sampled_lines:

            # Handle potential backslash escaping from sha256sum
            clean_line = line.lstrip("\\")
            hash_from_manifest, path = clean_line.split("  ", 1)
            # Path is already absolute like /app/data/subdir/file.txt
            abs_path = path

            # Verify file exists
            assert os.path.exists(abs_path), f"File {abs_path} does not exist"

            # Calculate actual SHA-256 hash using sha256sum
            actual_hash = subprocess.run(
                ["sha256sum", abs_path],
                capture_output=True,
                text=True,
                check=True,
                env={"LC_ALL": "C", "LANG": "C"}
            ).stdout.split()[0]

            assert hash_from_manifest == actual_hash, (
                f"SHA-256 hash mismatch for {path}. "
                f"Manifest has: {hash_from_manifest}, "
                f"Actual SHA-256: {actual_hash}. "
                f"This indicates hashes are not being calculated correctly."
            )

    def test_handles_files_with_spaces(self):
        """
        Verify that files with spaces in names are correctly processed.

        This checks success criteria #4: "The script correctly handles
        files with spaces and special characters in names" and instruction.md
        note: "Files with spaces in their names".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        output = result.stdout

        # Verify at least one file with spaces is present
        has_spaces = any(" " in line.split("  ", 1)[1] for line in output.strip().split("\n"))
        assert has_spaces, (
            "No files with spaces in names found in output. "
            "Test data should contain such files."
        )

    def test_handles_files_with_special_characters(self):
        """
        Verify that files with special characters are correctly processed.

        This checks success criteria #4 and instruction.md note about
        "Files with special characters".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        output = result.stdout
        lines = output.strip().split("\n")

        # Files with special chars should be present
        # Look for quotes, parentheses, brackets, or other special chars
        special_char_pattern = any(
            any(c in path for c in ['"', "'", "(", ")", "[", "]", "{", "}", "&", "|"])
            for line in lines
            for path in [line.split("  ", 1)[1]]
        )

        assert special_char_pattern or len(lines) > 100, (
            "Expected files with special characters in test data"
        )

    def test_handles_empty_files(self):
        """
        Verify that empty files are processed correctly.

        This checks instruction.md note: "Empty files". Empty files have a
        known SHA-256 hash: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        EMPTY_FILE_HASH = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

        # Check if at least one empty file exists
        has_empty = EMPTY_FILE_HASH in result.stdout

        # This is informational - empty files should exist in test data
        assert has_empty or len(result.stdout.split("\n")) > 100, (
            f"Test data should include empty files with hash {EMPTY_FILE_HASH}"
        )

    def test_recursive_directory_processing(self):
        """
        Verify that nested subdirectories are processed recursively.

        This checks instruction.md requirement: "Recursively process all files
        in the target directory".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        lines = result.stdout.strip().split("\n")

        # Check that we have a substantial number of files
        assert len(lines) >= 100, (
            f"Expected at least 100 files in manifest, got {len(lines)}. "
            "Recursive processing may not be working."
        )
    
    def test_skips_symlinks(self):
        """
        Verify that symlinks are skipped during manifest generation.
        
        This checks instruction.md requirement: "Symlinks in the target directory 
        MUST be skipped - only process regular files (-type f)".
        """
        import tempfile
        import shutil
        
        # Create temp directory with file and symlink
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create a regular file
            real_file = os.path.join(temp_dir, "real_file.txt")
            with open(real_file, "w") as f:
                f.write("real content")
            
            # Create a symlink pointing to the real file
            symlink_file = os.path.join(temp_dir, "symlink_file.txt")
            os.symlink(real_file, symlink_file)
            
            # Generate manifest
            result = subprocess.run(
                ["/app/integrity.sh", "--generate", temp_dir],
                capture_output=True,
                text=True,
                env={"LC_ALL": "C", "LANG": "C"}
            )
            
            lines = result.stdout.strip().split("\n")
            
            # Should only have 1 entry (real file), not 2
            assert len(lines) == 1, (
                f"Expected 1 file (real), got {len(lines)}. "
                f"Symlinks should be skipped."
            )
            
            # Verify it's the real file, not the symlink
            path = lines[0].split("  ", 1)[1]
            assert "real_file.txt" in path
            assert "symlink_file.txt" not in path
            
        finally:
            shutil.rmtree(temp_dir)

    def test_handles_filenames_starting_with_dash(self):
        """
        Verify that files starting with dash (-) are processed correctly.
        
        This checks instruction.md requirement: "Files with names starting with 
        dash (-) must be processed correctly (not treated as flags)".
        """
        import tempfile
        import shutil
        
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create file starting with dash
            dash_file = os.path.join(temp_dir, "-myfile.txt")
            with open(dash_file, "w") as f:
                f.write("test content")
            
            # Create normal file for comparison
            normal_file = os.path.join(temp_dir, "normal.txt")
            with open(normal_file, "w") as f:
                f.write("normal content")
            
            # Generate manifest - should not fail
            result = subprocess.run(
                ["/app/integrity.sh", "--generate", temp_dir],
                capture_output=True,
                text=True,
                env={"LC_ALL": "C", "LANG": "C"}
            )
            
            assert result.returncode == 0, (
                f"Script failed on file starting with dash. "
                f"stderr: {result.stderr}"
            )
            
            lines = result.stdout.strip().split("\n")
            
            # Should have both files
            assert len(lines) == 2, (
                f"Expected 2 files, got {len(lines)}"
            )
            
            # Verify dash file is present
            paths = [line.split("  ", 1)[1] for line in lines]
            dash_paths = [p for p in paths if "-myfile.txt" in p]
            
            assert len(dash_paths) == 1, (
                f"File starting with dash not found in manifest. "
                f"Paths: {paths}"
            )
            
            # Verify it has valid hash
            dash_line = [line for line in lines if "-myfile.txt" in line][0]
            hash_part = dash_line.split("  ", 1)[0]
            assert len(hash_part) == 64, "Invalid hash for dash file"
            assert all(c in '0123456789abcdef' for c in hash_part.lower())
            
        finally:
            shutil.rmtree(temp_dir)



class TestManifestComparison:
    """Tests for Mode 2: Compare Manifests functionality."""

    def setup_method(self):
        """Set up test fixtures for manifest comparison tests."""
        # Generate baseline manifest
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )
        self.baseline_manifest = result.stdout

        # Create temporary manifest files
        self.temp_dir = tempfile.mkdtemp()
        self.old_manifest = os.path.join(self.temp_dir, "old.txt")
        self.new_manifest = os.path.join(self.temp_dir, "new.txt")

        with open(self.old_manifest, "w") as f:
            f.write(self.baseline_manifest)

    def teardown_method(self):
        """Clean up temporary files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_compare_mode_basic_execution(self):
        """
        Verify that --old and --new flags work correctly.

        This checks that the script accepts Mode 2 command format:
        /app/integrity.sh --old <path> --new <path>
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        result = subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        assert result.returncode == 0, (
            f"Comparison mode failed with exit code {result.returncode}. "
            f"Stderr: {result.stderr}"
        )

    def test_diff_json_file_created(self):
        """
        Verify that /app/diff.json is created.

        This checks instruction.md requirement: "Write the results to /app/diff.json"
        and success criteria #3: "Mode 2 produces valid JSON output at /app/diff.json".
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        # Remove any existing diff.json
        if os.path.exists("/app/diff.json"):
            os.remove("/app/diff.json")

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        assert os.path.exists("/app/diff.json"), (
            "/app/diff.json was not created after comparison"
        )

    def test_diff_json_is_valid_json(self):
        """
        Verify that /app/diff.json contains syntactically valid JSON.

        This checks instruction.md JSON requirement: "Must be syntactically
        valid (parseable by standard JSON parsers)".
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            try:
                data = json.load(f)
                print(data)
            except json.JSONDecodeError as e:
                raise AssertionError(
                    f"Invalid JSON in /app/diff.json: {e}. "
                    f"Content: {f.read()}"
                )

    def test_diff_json_has_required_keys(self):
        """
        Verify that JSON has required keys: added, removed, modified.

        This checks instruction.md requirement for exact JSON structure with
        "added", "removed", and "modified" keys.
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        assert "added" in data, "Missing 'added' key in JSON output"
        assert "removed" in data, "Missing 'removed' key in JSON output"
        assert "modified" in data, "Missing 'modified' key in JSON output"

    def test_diff_json_values_are_arrays(self):
        """
        Verify that JSON values are arrays.

        This checks instruction.md requirement that each key maps to an array
        of file paths.
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        assert isinstance(data["added"], list), "'added' must be an array"
        assert isinstance(data["removed"], list), "'removed' must be an array"
        assert isinstance(data["modified"], list), "'modified' must be an array"

    def test_identifies_added_files(self):
        """
        Verify that added files are correctly identified.

        This checks instruction.md requirement: "Determine which files have been
        added (present in new, absent in old)" and success criteria #5.
        """
        # Create new manifest with additional file
        lines = self.baseline_manifest.strip().split("\n")
        new_lines = lines + ["a" * 64 + "  /app/data/newly_added_test_file.txt"]

        with open(self.new_manifest, "w") as f:
            f.write("\n".join(new_lines))

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        assert "/app/data/newly_added_test_file.txt" in data["added"], (
            f"Added file not detected. Added array: {data['added']}"
        )

    def test_identifies_removed_files(self):
        """
        Verify that removed files are correctly identified.

        This checks instruction.md requirement: "Determine which files have been
        removed (present in old, absent in new)" and success criteria #5.
        """
        # Create new manifest with one file removed
        lines = self.baseline_manifest.strip().split("\n")

        if len(lines) > 1:
            removed_line = lines[0]
            removed_path = removed_line.split("  ", 1)[1]
            new_lines = lines[1:]

            with open(self.new_manifest, "w") as f:
                f.write("\n".join(new_lines))

            subprocess.run(
                ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
                env={"LC_ALL": "C", "LANG": "C"}
            )

            with open("/app/diff.json", "r") as f:
                data = json.load(f)

            assert removed_path in data["removed"], (
                f"Removed file '{removed_path}' not detected. "
                f"Removed array: {data['removed']}"
            )

    def test_identifies_modified_files(self):
        """
        Verify that modified files are correctly identified.

        This checks instruction.md requirement: "Determine which files have been
        modified (same path, different hash)" and success criteria #5.
        """
        # Create new manifest with one file modified (same path, different hash)
        lines = self.baseline_manifest.strip().split("\n")

        if len(lines) > 0:
            # Change hash of first file
            original_line = lines[0]
            path = original_line.split("  ", 1)[1]
            modified_hash = "b" * 64  # Different hash
            lines[0] = f"{modified_hash}  {path}"

            with open(self.new_manifest, "w") as f:
                f.write("\n".join(lines))

            subprocess.run(
                ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
                env={"LC_ALL": "C", "LANG": "C"}
            )

            with open("/app/diff.json", "r") as f:
                data = json.load(f)

            assert path in data["modified"], (
                f"Modified file '{path}' not detected. "
                f"Modified array: {data['modified']}"
            )

    def test_no_trailing_commas_in_json(self):
        """
        Verify that JSON has no trailing commas.

        This checks instruction.md JSON requirement: "No trailing commas after
        the last element in any array".
        """
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            content = f.read()

        # Check for trailing comma patterns
        assert ",]" not in content, "Found trailing comma before ] in JSON"
        assert ",}" not in content, "Found trailing comma before } in JSON"

    def test_special_characters_escaped_in_json(self):
        """
        Verify that special characters in file paths are properly escaped in JSON.

        This checks instruction.md JSON requirement: "Proper escaping of special
        characters in file paths (quotes, backslashes, etc.)".
        """
        # Create manifest with file containing quotes
        test_line = "a" * 64 + '  /app/data/file_with_"quotes".txt'
        lines = self.baseline_manifest.strip().split("\n")
        new_lines = lines + [test_line]

        with open(self.new_manifest, "w") as f:
            f.write("\n".join(new_lines))

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        # Verify JSON is still valid despite special characters
        with open("/app/diff.json", "r") as f:
            data = json.load(f)  # Will fail if escaping is wrong

        # The file should appear in added
        assert any('"' in item or 'quotes' in item for item in data["added"]), (
            "File with quotes not found in added files"
        )

    def test_unchanged_files_not_in_diff(self):
        """
        Verify that unchanged files don't appear in any category.

        This validates the comparison logic: files that exist in both
        manifests with the same hash should not be reported.
        """
        # Identical manifests
        with open(self.new_manifest, "w") as f:
            f.write(self.baseline_manifest)

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        assert len(data["added"]) == 0, f"Expected no added files, got: {data['added']}"
        assert len(data["removed"]) == 0, f"Expected no removed files, got: {data['removed']}"
        assert len(data["modified"]) == 0, f"Expected no modified files, got: {data['modified']}"


    def test_paths_in_json_match_manifest_format(self):
        """
        Verify that file paths in JSON match manifest format exactly.

        This checks instruction.md requirement: "File paths must be listed
        exactly as they appear in the manifest files".
        """
        # Add a file with specific path format
        test_path = "/app/data/subdir/test_file_with_exact_format.custom"
        test_line = "c" * 64 + f"  {test_path}"
        lines = self.baseline_manifest.strip().split("\n")
        new_lines = lines + [test_line]

        with open(self.new_manifest, "w") as f:
            f.write("\n".join(new_lines))

        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        # Path should appear EXACTLY as in manifest (with /app/ prefix)
        assert test_path in data["added"], (
            f"Path not found exactly as in manifest. Expected '{test_path}' "
            f"in added array: {data['added']}"
        )

    def test_handles_blank_lines_in_manifest(self):
        """
        Verify that blank lines in manifest files are ignored.
        
        This checks instruction.md requirement: "Manifest files may contain 
        blank lines - these MUST be ignored during parsing".
        """
        # Create manifest with blank lines
        lines = self.baseline_manifest.strip().split("\n")
        lines_with_blanks = [lines[0], "", lines[1], "   ", lines[2]]
        
        with open(self.new_manifest, "w") as f:
            f.write("\n".join(lines_with_blanks))
        
        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )
        
        with open("/app/diff.json", "r") as f:
            data = json.load(f)
        
        # Should detect 2 removed files (lines[3:] missing)
        assert len(data["removed"]) > 0, "Blank lines broke parsing"


    def test_handles_comment_lines_in_manifest(self):
        """
        Verify that comment lines starting with # are skipped.
        
        This checks instruction.md requirement: "Manifest files may contain 
        comment lines starting with # - these MUST be skipped".
        """
        lines = self.baseline_manifest.strip().split("\n")
        lines_with_comments = ["# This is a comment", lines[0], "# Another comment", lines[1]]
        
        with open(self.new_manifest, "w") as f:
            f.write("\n".join(lines_with_comments))
        
        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )
        
        with open("/app/diff.json", "r") as f:
            data = json.load(f)
        
        assert len(data["removed"]) > 0, "Comment lines broke parsing"


    def test_case_insensitive_hash_comparison(self):
        """
        Verify that hash comparison is case-insensitive.
        
        This checks instruction.md requirement: "Hash comparison MUST be 
        case-insensitive (accept both uppercase/lowercase hex)".
        """
        lines = self.baseline_manifest.strip().split("\n")
        
        # Convert first line hash to uppercase
        first_line = lines[0]
        hash_part, path_part = first_line.split("  ", 1)
        uppercase_hash = hash_part.upper()
        lines[0] = f"{uppercase_hash}  {path_part}"
        
        with open(self.new_manifest, "w") as f:
            f.write("\n".join(lines))
        
        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )
        
        with open("/app/diff.json", "r") as f:
            data = json.load(f)
        
        # Uppercase hash should match lowercase - file NOT in modified
        first_path = path_part
        assert first_path not in data["modified"], (
            f"Case-insensitive comparison failed. {first_path} in modified: {data['modified']}"
        )


    def test_handles_empty_manifest(self):
        """
        Verify that empty manifest files produce empty arrays.
        
        This checks instruction.md requirement: "Empty manifest files must 
        produce {\"added\": [], \"removed\": [], \"modified\": []}".
        """
        # Create empty manifest
        with open(self.new_manifest, "w") as f:
            f.write("")
        
        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )
        
        with open("/app/diff.json", "r") as f:
            data = json.load(f)
        
        # All files from old should be in removed
        assert len(data["removed"]) > 0, "Empty manifest handling failed"
        assert len(data["added"]) == 0
        assert len(data["modified"]) == 0


    def test_handles_duplicate_paths(self):
        """
        Verify that duplicate paths use first occurrence.
        
        This checks instruction.md requirement: "If a manifest contains 
        duplicate entries for the same path, use the first occurrence only".
        """
        lines = self.baseline_manifest.strip().split("\n")
        
        # Duplicate first entry with different hash
        first_line = lines[0]
        hash_part, path_part = first_line.split("  ", 1)
        fake_hash = "f" * 64
        duplicate_line = f"{fake_hash}  {path_part}"
        
        lines_with_dup = [lines[0], duplicate_line] + lines[1:]
        
        with open(self.new_manifest, "w") as f:
            f.write("\n".join(lines_with_dup))
        
        subprocess.run(
            ["/app/integrity.sh", "--old", self.old_manifest, "--new", self.new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )
        
        # Should use first occurrence, not second
        # If it used second (fake hash), file would appear modified
        with open("/app/diff.json", "r") as f:
            data = json.load(f)
        
        # Path should NOT be in modified (first hash matches old)
        assert path_part not in data["modified"]

    def test_both_manifests_empty(self):
        """
        Verify that comparing two empty manifests produces empty arrays.
        
        This checks instruction.md requirement: "If **both** manifest files are 
        effectively empty, the output must be {\"added\": [], \"removed\": [], \"modified\": []}".
        """
        # Create two empty manifest files
        temp_dir = tempfile.mkdtemp()
        try:
            empty_old = os.path.join(temp_dir, "empty_old.txt")
            empty_new = os.path.join(temp_dir, "empty_new.txt")
            
            # Write empty/comment-only manifests
            with open(empty_old, "w") as f:
                f.write("# Just a comment\n\n")
            
            with open(empty_new, "w") as f:
                f.write("# Another comment\n")
            
            subprocess.run(
                ["/app/integrity.sh", "--old", empty_old, "--new", empty_new],
                env={"LC_ALL": "C", "LANG": "C"},
                check=True
            )
            
            with open("/app/diff.json", "r") as f:
                data = json.load(f)
            
            assert data == {"added": [], "removed": [], "modified": []}, (
                f"Empty manifests should produce empty arrays, got: {data}"
            )
        finally:
            import shutil
            shutil.rmtree(temp_dir)


class TestEdgeCases:
    """Tests for edge cases and corner cases that challenge the implementation."""

    def test_handles_unicode_filenames(self):
        """
        Verify correct handling of Unicode characters in filenames.

        This tests robustness with international characters as mentioned
        in instruction.md: "Files with various naming patterns".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        # Should handle unicode without crashing
        assert result.returncode == 0
        assert len(result.stdout) > 0

    def test_handles_very_long_filenames(self):
        """
        Verify handling of files with very long names.

        This tests robustness with edge case naming patterns.
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        # Check for presence of long filenames
        lines = result.stdout.strip().split("\n")
        has_long_name = any(len(line.split("  ", 1)[1]) > 50 for line in lines)

        # This is informational - test data should include long names
        assert has_long_name or len(lines) > 100

    def test_handles_files_with_dots_in_names(self):
        """
        Verify handling of files with multiple dots in names.

        This tests that extension parsing doesn't break on complex filenames
        like "file.tar.gz.backup.custom".
        """
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        # Look for files with multiple dots
        lines = result.stdout.strip().split("\n")
        multi_dot_files = [
            line for line in lines
            if line.split("  ", 1)[1].count(".") > 2
        ]

        assert len(multi_dot_files) > 0 or len(lines) > 100, (
            "Test data should include files with multiple dots"
        )

    def test_empty_arrays_when_no_changes(self):
        """
        Verify that empty arrays are valid when no files match a category.

        This checks instruction.md JSON requirement: "Arrays may be empty if
        no files match that category".
        """
        temp_dir = tempfile.mkdtemp()
        old_manifest = os.path.join(temp_dir, "old.txt")
        new_manifest = os.path.join(temp_dir, "new.txt")

        # Create identical manifests
        result = subprocess.run(
            ["/app/integrity.sh", "--generate", "/app/data"],
            capture_output=True,
            text=True,
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open(old_manifest, "w") as f:
            f.write(result.stdout)
        with open(new_manifest, "w") as f:
            f.write(result.stdout)

        subprocess.run(
            ["/app/integrity.sh", "--old", old_manifest, "--new", new_manifest],
            env={"LC_ALL": "C", "LANG": "C"}
        )

        with open("/app/diff.json", "r") as f:
            data = json.load(f)

        # All arrays should be empty and valid
        assert data["added"] == []
        assert data["removed"] == []
        assert data["modified"] == []

        import shutil
        shutil.rmtree(temp_dir)
