# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_solution():
    import sys
    spec = importlib.util.spec_from_file_location("solution", "/app/solution.py")
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise ImportError("Could not load /app/solution.py")
    module = importlib.util.module_from_spec(spec)
    # Register module in sys.modules before execution to fix dataclass processing
    sys.modules["solution"] = module
    spec.loader.exec_module(module)
    return module


def _run_audit(tmp_path: Path, trace_content: str) -> dict:
    """Write trace.log and run the solution, return parsed results."""
    trace_path = tmp_path / "trace.log"
    trace_path.write_text(trace_content, encoding="utf-8")
    
    solution = _load_solution()
    out_path = tmp_path / "results.json"
    solution.audit_renames(str(trace_path), str(out_path))
    
    assert out_path.exists(), "results.json must be created"
    return json.loads(out_path.read_text(encoding="utf-8"))


def test_solution_file_exists_and_has_audit_renames():
    """Test 0: Verify solution file exists and has required function."""
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "/app/solution.py must exist"
    solution = _load_solution()
    assert callable(getattr(solution, "audit_renames", None)), "audit_renames() must be defined"


def test_write_after_fsync_invalidation(tmp_path):
    """Test 1: Write After fsync Invalidation
    
    Scenario: A file is written, fsynced, written again, renamed, then crash.
    Checks: Agent must detect that post-fsync write invalidates durability.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:write:fd=3:size=50
1:rename:/tmp/file.txt:/target/file.txt
1:close:fd=3"""
    
    results = _run_audit(tmp_path, trace)
    
    # Find the rename operation
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None, "Rename operation must be found"
    assert rename_result["status"] == "UNSAFE", "Post-fsync write invalidates durability"
    assert "post-fsync write" in rename_result.get("reason", "").lower() or "write after fsync" in rename_result.get("reason", "").lower()


def test_rename_without_directory_fsync(tmp_path):
    """Test 2: Rename Without Directory fsync
    
    Scenario: File is fsynced, renamed into new directory, crash before directory fsync.
    Checks: Rename is not durable, must be UNSAFE or AMBIGUOUS.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/newdir/file.txt
# Directory fsync missing - crash would lose rename"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/newdir/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] in ["UNSAFE", "AMBIGUOUS"], "Rename without directory fsync must be unsafe or ambiguous"
    assert "directory" in rename_result.get("reason", "").lower() or "dir" in rename_result.get("reason", "").lower()


def test_cross_process_file_descriptor_leak(tmp_path):
    """Test 3: Cross-Process File Descriptor Leak
    
    Scenario: Process A opens file, Process B renames it, Process A writes more, Crash
    Checks: FD still points to inode → unsafe rename.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
2:rename:/tmp/file.txt:/target/file.txt
1:write:fd=3:size=50
1:close:fd=3"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "Cross-process FD leak makes rename unsafe"
    assert ("fd" in rename_result.get("reason", "").lower() or 
            "descriptor" in rename_result.get("reason", "").lower() or
            "open" in rename_result.get("reason", "").lower())


def test_rename_over_existing_file(tmp_path):
    """Test 4: Rename Over Existing File
    
    Scenario: rename(tmp, target) where target existed and had data.
    Checks: Atomic replacement must preserve full tmp content or none.
    """
    trace = """1:open:/tmp/tmpfile.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=200
1:fsync:fd=3
1:close:fd=3
2:open:/target/existing.txt:O_WRONLY|O_CREAT:fd=4
2:write:fd=4:size=50
2:close:fd=4
1:rename:/tmp/tmpfile.txt:/target/existing.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/existing.txt"), None)
    assert rename_result is not None
    # Rename over existing file should be SAFE if properly fsynced (atomic replace)
    assert rename_result["status"] in ["SAFE", "AMBIGUOUS"], "Rename over existing file should be evaluated"


def test_fsync_on_wrong_fd(tmp_path):
    """Test 5: fsync on Wrong FD
    
    Scenario: Two files open; fsync called on unrelated fd before rename.
    Checks: fsync must match renamed file.
    """
    trace = """1:open:/tmp/file1.txt:O_WRONLY|O_CREAT:fd=3
1:open:/tmp/file2.txt:O_WRONLY|O_CREAT:fd=4
1:write:fd=3:size=100
1:write:fd=4:size=200
1:fsync:fd=4
1:close:fd=4
1:rename:/tmp/file1.txt:/target/file1.txt
1:close:fd=3"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file1.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "fsync on wrong FD doesn't protect rename"
    assert ("wrong" in rename_result.get("reason", "").lower() or 
            "different" in rename_result.get("reason", "").lower() or
            "fsync" in rename_result.get("reason", "").lower())


def test_multiple_renames_single_fsync(tmp_path):
    """Test 6: Multiple Renames, Single fsync
    
    Scenario: File renamed multiple times but fsync only once early.
    Checks: Later renames unsafe.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/dir1/file.txt
1:dir_fsync:/dir1
1:rename:/dir1/file.txt:/dir2/file.txt
1:rename:/dir2/file.txt:/dir3/file.txt"""
    
    results = _run_audit(tmp_path, trace)
    
    # First rename should be safe
    rename1 = next((r for r in results["renames"] if r["to"] == "/dir1/file.txt"), None)
    assert rename1 is not None
    assert rename1["status"] == "SAFE", "First rename with fsync should be safe"
    
    # Later renames without directory fsync should be unsafe
    rename2 = next((r for r in results["renames"] if r["to"] == "/dir2/file.txt"), None)
    rename3 = next((r for r in results["renames"] if r["to"] == "/dir3/file.txt"), None)
    assert rename2 is not None and rename3 is not None
    assert rename2["status"] in ["UNSAFE", "AMBIGUOUS"], "Later rename without directory fsync"
    assert rename3["status"] in ["UNSAFE", "AMBIGUOUS"], "Later rename without directory fsync"
    # Verify keyword requirements for multiple renames to same directory
    if rename2["status"] == "UNSAFE":
        assert "directory" in rename2.get("reason", "").lower() or "dir" in rename2.get("reason", "").lower(), "Multiple renames to same directory must mention 'directory' or 'dir'"
    if rename3["status"] == "UNSAFE":
        assert "directory" in rename3.get("reason", "").lower() or "dir" in rename3.get("reason", "").lower(), "Multiple renames to same directory must mention 'directory' or 'dir'"


def test_crash_between_rename_and_close(tmp_path):
    """Test 7: Crash Between rename and close
    
    Scenario: rename occurs, fd still open, crash before close
    Checks: Rename may be durable but content may not be.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target
# fd=3 still open - crash before close"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    # With directory fsync, rename is durable, but open FD might indicate incomplete content
    assert rename_result["status"] in ["SAFE", "AMBIGUOUS"], "Rename with dir fsync but open FD"


def test_missing_write_size_information(tmp_path):
    """Test 8: Missing Write Size Information
    
    Scenario: Trace omits write byte count for one operation.
    Checks: Result must be AMBIGUOUS, not guessed.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:write:fd=3:size=?
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "AMBIGUOUS", "Missing write size must result in AMBIGUOUS"
    assert "size" in rename_result.get("reason", "").lower() or "unknown" in rename_result.get("reason", "").lower()


def test_directory_fsync_before_rename(tmp_path):
    """Test 9: Directory fsync Before Rename
    
    Scenario: Directory fsync happens before rename, not after.
    Checks: Must not count.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:dir_fsync:/target
1:rename:/tmp/file.txt:/target/file.txt
# Directory fsync happened before rename - doesn't help"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] in ["UNSAFE", "AMBIGUOUS"], "Directory fsync before rename doesn't help"
    assert ("before" in rename_result.get("reason", "").lower() or 
            "order" in rename_result.get("reason", "").lower() or
            "after" in rename_result.get("reason", "").lower())


def test_interleaved_renames_across_same_directory(tmp_path):
    """Test 10: Interleaved Renames Across Same Directory
    
    Scenario: Multiple renames in same directory by different pids with interleaved fsyncs.
    Checks: Each rename evaluated independently with correct directory state.
    """
    trace = """1:open:/tmp/file1.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
2:open:/tmp/file2.txt:O_WRONLY|O_CREAT:fd=4
2:write:fd=4:size=200
2:fsync:fd=4
2:close:fd=4
1:rename:/tmp/file1.txt:/target/file1.txt
2:rename:/tmp/file2.txt:/target/file2.txt
1:dir_fsync:/target
2:rename:/target/file2.txt:/target/file2_renamed.txt"""
    
    results = _run_audit(tmp_path, trace)
    
    rename1 = next((r for r in results["renames"] if r["to"] == "/target/file1.txt"), None)
    rename2 = next((r for r in results["renames"] if r["to"] == "/target/file2.txt"), None)
    rename3 = next((r for r in results["renames"] if r["to"] == "/target/file2_renamed.txt"), None)
    
    assert rename1 is not None and rename2 is not None and rename3 is not None
    
    # First rename should benefit from directory fsync
    assert rename1["status"] == "SAFE", "First rename with directory fsync should be safe"
    
    # Second rename happens before directory fsync
    assert rename2["status"] in ["UNSAFE", "AMBIGUOUS"], "Second rename before directory fsync"
    if rename2["status"] == "UNSAFE":
        assert "directory" in rename2.get("reason", "").lower() or "dir" in rename2.get("reason", "").lower(), "Multiple renames to same directory must mention 'directory' or 'dir'"
    
    # Third rename happens after directory fsync but is a second rename of same file
    assert rename3["status"] in ["UNSAFE", "AMBIGUOUS"], "Third rename needs new directory fsync"
    if rename3["status"] == "UNSAFE":
        assert "directory" in rename3.get("reason", "").lower() or "dir" in rename3.get("reason", "").lower(), "Multiple renames to same directory must mention 'directory' or 'dir'"


def test_file_not_fsynced_before_rename(tmp_path):
    """Test 11: File Not fsynced Before Rename
    
    Scenario: File is written but not fsynced before rename.
    Checks: Rename must be UNSAFE because file was not fsynced.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None, "Rename operation must be found"
    assert rename_result["status"] == "UNSAFE", "File not fsynced before rename must be unsafe"
    assert "fsync" in rename_result.get("reason", "").lower(), "Reason should mention fsync"


def test_all_renames_emitted_in_order(tmp_path):
    """Test 12: All Renames Emitted Exactly Once in Order
    
    Scenario: Multiple renames in trace.
    Checks: All renames must appear exactly once in results, in the order they appear in trace.
    """
    trace = """1:open:/tmp/file1.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:open:/tmp/file2.txt:O_WRONLY|O_CREAT:fd=4
1:write:fd=4:size=200
1:fsync:fd=4
1:close:fd=4
1:rename:/tmp/file1.txt:/target/file1.txt
1:dir_fsync:/target
1:rename:/tmp/file2.txt:/target/file2.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 2, "Must have exactly 2 rename operations"
    
    # Check order: first rename should be file1.txt, second should be file2.txt
    assert results["renames"][0]["from"] == "/tmp/file1.txt", "First rename should be file1.txt"
    assert results["renames"][0]["to"] == "/target/file1.txt", "First rename target should be /target/file1.txt"
    assert results["renames"][1]["from"] == "/tmp/file2.txt", "Second rename should be file2.txt"
    assert results["renames"][1]["to"] == "/target/file2.txt", "Second rename target should be /target/file2.txt"
    
    # Check that each rename appears exactly once
    file1_renames = [r for r in results["renames"] if r["from"] == "/tmp/file1.txt"]
    file2_renames = [r for r in results["renames"] if r["from"] == "/tmp/file2.txt"]
    assert len(file1_renames) == 1, "file1.txt rename must appear exactly once"
    assert len(file2_renames) == 1, "file2.txt rename must appear exactly once"


def test_function_called_with_app_paths(tmp_path):
    """Test 13: Function Called with /app Paths
    
    Scenario: Verify that the solution can be called with /app/trace.log and /app/results.json.
    Checks: Solution must work with the specified absolute paths from instructions.
    The instructions mandate calling the function with trace_path="/app/trace.log" and out_path="/app/results.json".
    """
    # Create trace file (simulating the actual task environment where /app/trace.log exists)
    trace_content = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
    
    # Use tmp_path to create files, but verify the function accepts file paths
    # In the actual task environment, these will be /app/trace.log and /app/results.json
    trace_path = tmp_path / "trace.log"
    trace_path.write_text(trace_content, encoding="utf-8")
    
    out_path = tmp_path / "results.json"
    
    solution = _load_solution()
    # The function must accept file paths as specified in instructions
    # Instructions state: "Call this function with trace_path="/app/trace.log" and out_path="/app/results.json""
    solution.audit_renames(str(trace_path), str(out_path))
    
    assert out_path.exists(), "results.json must be created at the specified out_path"
    results = json.loads(out_path.read_text(encoding="utf-8"))
    
    # Verify the function works correctly with the paths
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 1, "Must have exactly 1 rename operation"
    assert results["renames"][0]["to"] == "/target/file.txt", "Rename target must match"


def test_priority_missing_size_over_other_conditions(tmp_path):
    """Test 14: Priority - Missing Size Over Other Conditions
    
    Scenario: File has missing write size AND other unsafe conditions (write after fsync, no dir fsync).
    Checks: Missing size must result in AMBIGUOUS, not UNSAFE, regardless of other conditions.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:write:fd=3:size=?
1:fsync:fd=3
1:write:fd=3:size=50
1:rename:/tmp/file.txt:/target/file.txt
# Missing size, write after fsync, and no directory fsync - should be AMBIGUOUS due to missing size"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "AMBIGUOUS", "Missing write size must take priority over other conditions"
    assert "size" in rename_result.get("reason", "").lower() or "unknown" in rename_result.get("reason", "").lower()


def test_priority_cross_process_over_write_after_fsync(tmp_path):
    """Test 15: Priority - Cross-Process FD Over Write After Fsync
    
    Scenario: Same process has write after fsync, but another process also writes after rename.
    Checks: Cross-process FD issue must be reported, not write after fsync.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:write:fd=3:size=50
2:rename:/tmp/file.txt:/target/file.txt
2:dir_fsync:/target
1:write:fd=3:size=25
1:close:fd=3"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "Cross-process FD leak must be detected"
    # Should report cross-process issue, not write after fsync
    assert ("fd" in rename_result.get("reason", "").lower() or 
            "descriptor" in rename_result.get("reason", "").lower() or
            "open" in rename_result.get("reason", "").lower()), "Cross-process FD must take priority over write after fsync"


def test_priority_cross_process_over_directory_fsync(tmp_path):
    """Test 16: Priority - Cross-Process FD Over Directory Fsync
    
    Scenario: Cross-process FD issue AND missing directory fsync.
    Checks: Cross-process FD issue must be reported, not directory fsync.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
2:rename:/tmp/file.txt:/target/file.txt
1:write:fd=3:size=50
1:close:fd=3
# Cross-process FD issue and no directory fsync - should report cross-process issue"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "Cross-process FD leak must be detected"
    # Should report cross-process issue, not directory fsync
    assert ("fd" in rename_result.get("reason", "").lower() or 
            "descriptor" in rename_result.get("reason", "").lower() or
            "open" in rename_result.get("reason", "").lower()), "Cross-process FD must take priority over directory fsync"


def test_priority_write_after_fsync_over_directory_fsync(tmp_path):
    """Test 17: Priority - Write After Fsync Over Directory Fsync
    
    Scenario: Write after fsync AND missing directory fsync.
    Checks: Write after fsync must be reported, not directory fsync.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:write:fd=3:size=50
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
# Write after fsync and no directory fsync - should report write after fsync"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "Write after fsync must be detected"
    # Should report write after fsync, not directory fsync
    assert ("post-fsync write" in rename_result.get("reason", "").lower() or 
            "write after fsync" in rename_result.get("reason", "").lower()), "Write after fsync must take priority over directory fsync"


def test_priority_file_not_fsynced_over_directory_fsync(tmp_path):
    """Test 18: Priority - File Not Fsynced Over Directory Fsync
    
    Scenario: File not fsynced AND missing directory fsync.
    Checks: File not fsynced must be reported, not directory fsync.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
# File not fsynced and no directory fsync - should report file not fsynced"""
    
    results = _run_audit(tmp_path, trace)
    
    rename_result = next((r for r in results["renames"] if r["to"] == "/target/file.txt"), None)
    assert rename_result is not None
    assert rename_result["status"] == "UNSAFE", "File not fsynced must be detected"
    # Should report file not fsynced, not directory fsync
    assert "fsync" in rename_result.get("reason", "").lower(), "File not fsynced must take priority over directory fsync"


def test_json_output_no_extra_fields(tmp_path):
    """Test 19: JSON Output - No Extra Fields
    
    Scenario: Verify that each rename object contains exactly the 5 required fields.
    Checks: No additional fields are permitted in the JSON output.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 1, "Must have exactly 1 rename operation"
    
    rename_result = results["renames"][0]
    
    # Verify exactly 5 required fields are present
    required_fields = {"from", "to", "pid", "status", "reason"}
    actual_fields = set(rename_result.keys())
    
    assert actual_fields == required_fields, f"Rename object must have exactly these fields: {required_fields}. Found: {actual_fields}"
    
    # Verify no extra fields
    assert len(rename_result) == 5, f"Rename object must have exactly 5 fields, found {len(rename_result)}"


def test_json_output_all_required_fields_present(tmp_path):
    """Test 20: JSON Output - All Required Fields Present
    
    Scenario: Verify that all required fields (from, to, pid, status, reason) are present.
    Checks: All fields must be present and have correct types.
    """
    trace = """1:open:/tmp/file1.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
2:open:/tmp/file2.txt:O_WRONLY|O_CREAT:fd=4
2:write:fd=4:size=200
2:fsync:fd=4
2:close:fd=4
1:rename:/tmp/file1.txt:/target/file1.txt
1:dir_fsync:/target
2:rename:/tmp/file2.txt:/target/file2.txt
2:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 2, "Must have exactly 2 rename operations"
    
    for i, rename_result in enumerate(results["renames"]):
        # Verify all required fields are present
        assert "from" in rename_result, f"Rename {i+1} must have 'from' field"
        assert "to" in rename_result, f"Rename {i+1} must have 'to' field"
        assert "pid" in rename_result, f"Rename {i+1} must have 'pid' field"
        assert "status" in rename_result, f"Rename {i+1} must have 'status' field"
        assert "reason" in rename_result, f"Rename {i+1} must have 'reason' field"
        
        # Verify field types
        assert isinstance(rename_result["from"], str), f"Rename {i+1} 'from' must be a string"
        assert isinstance(rename_result["to"], str), f"Rename {i+1} 'to' must be a string"
        assert isinstance(rename_result["pid"], int), f"Rename {i+1} 'pid' must be an integer"
        assert isinstance(rename_result["status"], str), f"Rename {i+1} 'status' must be a string"
        assert isinstance(rename_result["reason"], str), f"Rename {i+1} 'reason' must be a string"
        
        # Verify pid matches the trace
        if i == 0:
            assert rename_result["pid"] == 1, f"First rename pid must be 1, found {rename_result['pid']}"
            assert rename_result["from"] == "/tmp/file1.txt", "First rename from path must match"
            assert rename_result["to"] == "/target/file1.txt", "First rename to path must match"
        else:
            assert rename_result["pid"] == 2, f"Second rename pid must be 2, found {rename_result['pid']}"
            assert rename_result["from"] == "/tmp/file2.txt", "Second rename from path must match"
            assert rename_result["to"] == "/target/file2.txt", "Second rename to path must match"
        
        # Verify reason is non-empty
        assert len(rename_result["reason"]) > 0, f"Rename {i+1} 'reason' must be non-empty"


def test_missing_size_unrelated_file_does_not_affect_rename(tmp_path):
    """Test 21: Missing Size - Unrelated File Does Not Affect Rename
    
    Scenario: A write with size=? to an unrelated file (not being renamed).
    Checks: Only writes to the file being renamed affect the rename status.
    Unrelated files with unknown size do not make the rename AMBIGUOUS.
    """
    trace = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
2:open:/tmp/unrelated.txt:O_WRONLY|O_CREAT:fd=4
2:write:fd=4:size=?
2:close:fd=4
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 1, "Must have exactly 1 rename operation"
    
    rename_result = results["renames"][0]
    assert rename_result is not None
    # The unrelated file with unknown size does not affect this rename
    # Only writes to the file being renamed (file.txt) are checked
    assert rename_result["status"] == "SAFE", "Unrelated file with size=? does not affect rename status"


def test_missing_size_multiple_renames_unrelated_file(tmp_path):
    """Test 22: Missing Size - Multiple Renames with Unrelated File
    
    Scenario: Multiple renames with one write having size=? to an unrelated file.
    Checks: Unrelated files with unknown size do not affect rename status.
    Only writes to the files being renamed are checked.
    Note: The second rename may be UNSAFE due to multiple renames to same directory logic.
    """
    trace = """1:open:/tmp/file1.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
2:open:/tmp/file2.txt:O_WRONLY|O_CREAT:fd=4
2:write:fd=4:size=200
2:fsync:fd=4
2:close:fd=4
3:open:/tmp/unrelated.txt:O_WRONLY|O_CREAT:fd=5
3:write:fd=5:size=?
3:close:fd=5
1:rename:/tmp/file1.txt:/target/file1.txt
1:dir_fsync:/target
2:rename:/tmp/file2.txt:/target/file2.txt
2:dir_fsync:/target"""
    
    results = _run_audit(tmp_path, trace)
    
    assert "renames" in results, "Results must contain 'renames' key"
    assert len(results["renames"]) == 2, "Must have exactly 2 rename operations"
    
    # First rename should be SAFE - unrelated file with unknown size does not affect it
    rename1 = results["renames"][0]
    assert rename1["status"] == "SAFE", "First rename should be SAFE - unrelated file with size=? does not affect it"
    
    # Second rename: The unrelated file with unknown size does not affect it,
    # but it may be UNSAFE due to multiple renames to same directory logic
    # (if the oracle checks for other renames before the directory fsync)
    rename2 = results["renames"][1]
    # The unrelated file should not cause AMBIGUOUS status
    assert rename2["status"] != "AMBIGUOUS", "Second rename should not be AMBIGUOUS due to unrelated file with size=?"
    # It may be SAFE or UNSAFE depending on directory fsync logic, but not AMBIGUOUS
    assert rename2["status"] in ["SAFE", "UNSAFE"], "Second rename should be SAFE or UNSAFE, not AMBIGUOUS"


def test_function_must_accept_app_paths(tmp_path):
    """Test 23: Function Must Accept /app/trace.log and /app/results.json
    
    Scenario: Verify that the function can be called with the exact paths specified in instructions.
    Checks: Function must work with /app/trace.log and /app/results.json as mandated.
    """
    import tempfile
    import os
    
    # Create temporary directory to simulate /app
    with tempfile.TemporaryDirectory() as temp_dir:
        trace_path = os.path.join(temp_dir, "trace.log")
        out_path = os.path.join(temp_dir, "results.json")
        
        trace_content = """1:open:/tmp/file.txt:O_WRONLY|O_CREAT:fd=3
1:write:fd=3:size=100
1:fsync:fd=3
1:close:fd=3
1:rename:/tmp/file.txt:/target/file.txt
1:dir_fsync:/target"""
        
        # Write trace file
        with open(trace_path, "w", encoding="utf-8") as f:
            f.write(trace_content)
        
        # Load solution and call with the paths
        solution = _load_solution()
        solution.audit_renames(trace_path, out_path)
        
        # Verify output file was created
        assert os.path.exists(out_path), f"results.json must be created at {out_path}"
        
        # Verify output is valid JSON
        with open(out_path, "r", encoding="utf-8") as f:
            results = json.load(f)
        
        assert "renames" in results, "Results must contain 'renames' key"
        assert len(results["renames"]) == 1, "Must have exactly 1 rename operation"
        assert results["renames"][0]["to"] == "/target/file.txt", "Rename target must match"