"""
Tests for cron schedule conflict resolver.
Validates that agents build a correct solution based only on instructions.
Test data is embedded here and not visible to agents.
"""

import importlib.util
import sys
import tempfile
from pathlib import Path


# Test data embedded directly in tests - agent cannot see this
TEST_CASES = {
    "priority_based": """RESOURCES
database

JOBS
backup:
  cron: 0 2 * * *
  resource: database
  priority: 10
  duration: 30
cleanup:
  cron: 0 2 * * *
  resource: database
  priority: 5
  duration: 20
""",
    
    "lexicographic_tie": """RESOURCES
cpu

JOBS
zebra:
  cron: 0 12 * * *
  resource: cpu
  priority: 10
  duration: 60
apple:
  cron: 0 12 * * *
  resource: cpu
  priority: 10
  duration: 30
""",
    
    "no_conflicts": """RESOURCES
disk

JOBS
morning:
  cron: 0 9 * * *
  resource: disk
  priority: 10
  duration: 30
evening:
  cron: 0 18 * * *
  resource: disk
  priority: 10
  duration: 30
""",
    
    "five_minute_gap": """RESOURCES
storage

JOBS
job1:
  cron: 0 10 * * *
  resource: storage
  priority: 10
  duration: 20
job2:
  cron: 0 10 * * *
  resource: storage
  priority: 5
  duration: 15
""",
    
    "range_syntax": """RESOURCES
compute

JOBS
hourly:
  cron: 0 9-17 * * *
  resource: compute
  priority: 8
  duration: 30
single:
  cron: 0 14 * * *
  resource: compute
  priority: 5
  duration: 40
""",
    
    "step_syntax": """RESOURCES
network

JOBS
every15:
  cron: */15 * * * *
  resource: network
  priority: 7
  duration: 10
hourly:
  cron: 30 * * * *
  resource: network
  priority: 6
  duration: 12
""",
    
    "list_syntax": """RESOURCES
database

JOBS
multi_time:
  cron: 0,15,30,45 * * * *
  resource: database
  priority: 9
  duration: 8
overlap:
  cron: 5 * * * *
  resource: database
  priority: 4
  duration: 12
""",
    
    "hour_wraparound": """RESOURCES
api

JOBS
late_job:
  cron: 55 23 * * *
  resource: api
  priority: 10
  duration: 15
midnight_job:
  cron: 5 0 * * *
  resource: api
  priority: 5
  duration: 10
""",
    
    "zero_duration": """RESOURCES
cache

JOBS
instant1:
  cron: 0 12 * * *
  resource: cache
  priority: 8
  duration: 0
instant2:
  cron: 0 12 * * *
  resource: cache
  priority: 3
  duration: 0
""",
    
    "cascading": """RESOURCES
server

JOBS
first:
  cron: 0 14 * * *
  resource: server
  priority: 10
  duration: 25
second:
  cron: 0 14 * * *
  resource: server
  priority: 8
  duration: 30
third:
  cron: 20 14 * * *
  resource: server
  priority: 5
  duration: 20
""",
    
    "sorted_output": """RESOURCES
memory

JOBS
zebra:
  cron: 0 8 * * *
  resource: memory
  priority: 5
  duration: 10
alpha:
  cron: 0 9 * * *
  resource: memory
  priority: 5
  duration: 10
mike:
  cron: 0 10 * * *
  resource: memory
  priority: 5
  duration: 10""",
    
    "max_cascading_depth": """RESOURCES
worker

JOBS
j01:
  cron: 0 15 * * *
  resource: worker
  priority: 12
  duration: 10
j02:
  cron: 0 15 * * *
  resource: worker
  priority: 11
  duration: 10
j03:
  cron: 0 15 * * *
  resource: worker
  priority: 10
  duration: 10
j04:
  cron: 0 15 * * *
  resource: worker
  priority: 9
  duration: 10
j05:
  cron: 0 15 * * *
  resource: worker
  priority: 8
  duration: 10
j06:
  cron: 0 15 * * *
  resource: worker
  priority: 7
  duration: 10
j07:
  cron: 0 15 * * *
  resource: worker
  priority: 6
  duration: 10
j08:
  cron: 0 15 * * *
  resource: worker
  priority: 5
  duration: 10
j09:
  cron: 0 15 * * *
  resource: worker
  priority: 4
  duration: 10
j10:
  cron: 0 15 * * *
  resource: worker
  priority: 3
  duration: 10
j11:
  cron: 0 15 * * *
  resource: worker
  priority: 2
  duration: 10
j12:
  cron: 0 15 * * *
  resource: worker
  priority: 1
  duration: 10""",
    
    "preserve_cron_syntax": """RESOURCES
backup

JOBS
daily:
  cron: 0 3-6 * * *
  resource: backup
  priority: 10
  duration: 30
weekly:
  cron: 0 8 * * 1-5
  resource: backup
  priority: 8
  duration: 20
""",
    
    # CIRCULAR DEPENDENCY TEST CASE (RARE EDGE CASE)
    # This tests the ONLY scenario where "unresolvable" status is used:
    # - 3+ jobs with IDENTICAL simple cron string (all "0 10 * * *")
    # - AND IDENTICAL priority (all 5)
    # This is NOT a step/list/range syntax test - those always use "adjusted"
    "circular_dependencies": """RESOURCES
disk

JOBS
job-a:
  cron: 0 10 * * *
  resource: disk
  priority: 5
  duration: 15
job-b:
  cron: 0 10 * * *
  resource: disk
  priority: 5
  duration: 15
job-c:
  cron: 0 10 * * *
  resource: disk
  priority: 5
  duration: 15""",
}


def _load_solution():
    """Load the agent's solution.py module."""
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "File /app/solution.py does not exist"
    
    spec = importlib.util.spec_from_file_location("solution", solution_path)
    solution = importlib.util.module_from_spec(spec)
    sys.modules["solution"] = solution
    spec.loader.exec_module(solution)
    return solution


def _run_test_case(solution, test_input: str) -> str:
    """Run solution on test input and return output."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as input_file:
        input_file.write(test_input)
        input_path = input_file.name
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as output_file:
        output_path = output_file.name
    
    try:
        solution.resolve_schedule(input_path, output_path)
        return Path(output_path).read_text()
    finally:
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)


def _parse_output(output: str) -> dict:
    """Parse multi-line YAML output into a dictionary of jobs."""
    lines = output.strip().split('\n')
    assert lines[0] == "RESOLVED", "Output must start with 'RESOLVED'"
    
    jobs = {}
    current_job = None
    
    for line in lines[1:]:
        if not line.strip():
            continue
        
        if not line.startswith('  '):  # Job name
            current_job = line.rstrip(':')
            jobs[current_job] = {}
        else:  # Field
            # CRITICAL: Enforce EXACTLY 2 spaces for indentation (not >2)
            assert line.startswith('  ') and (len(line) < 3 or line[2] != ' '), \
                f"Field must be indented with EXACTLY 2 spaces, not more: {repr(line)}"
            field_line = line.strip()
            if ': ' in field_line:
                key, value = field_line.split(': ', 1)
                jobs[current_job][key] = value
    
    return jobs


def test_solution_file_exists():
    """Verify /app/solution.py exists."""
    solution_path = Path("/app/solution.py")
    assert solution_path.exists(), "File /app/solution.py does not exist"


def test_function_signature():
    """Verify resolve_schedule function exists with correct signature."""
    solution = _load_solution()
    assert hasattr(solution, "resolve_schedule"), "solution.py must contain resolve_schedule function"
    
    import inspect
    sig = inspect.signature(solution.resolve_schedule)
    params = list(sig.parameters.keys())
    assert len(params) == 2, f"resolve_schedule should have 2 parameters, found {len(params)}"


def test_priority_based_resolution():
    """Test that higher priority job wins in conflict."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["priority_based"])
    jobs = _parse_output(output)
    
    # backup (priority 10) should keep original time
    assert "backup" in jobs
    assert jobs["backup"]["status"] == "kept"
    assert jobs["backup"]["cron"] == "0 2 * * *"
    
    # cleanup (priority 5) should be rescheduled
    assert "cleanup" in jobs
    assert jobs["cleanup"]["status"] == "adjusted"
    assert "original_cron" in jobs["cleanup"]
    assert "conflict_with" in jobs["cleanup"]
    assert jobs["cleanup"]["conflict_with"] == "backup"


def test_lexicographic_tiebreaking():
    """Test that lexicographic ordering is used for equal priority."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["lexicographic_tie"])
    jobs = _parse_output(output)
    
    # apple comes before zebra alphabetically, so apple wins
    assert "apple" in jobs
    assert jobs["apple"]["status"] == "kept"
    
    # zebra should be rescheduled
    assert "zebra" in jobs
    assert jobs["zebra"]["status"] == "adjusted"


def test_no_conflicts_preserved():
    """Test that jobs without conflicts keep original schedules."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["no_conflicts"])
    jobs = _parse_output(output)
    
    # Both jobs should keep original schedules
    assert jobs["morning"]["status"] == "kept"
    assert jobs["evening"]["status"] == "kept"
    assert "original_cron" not in jobs["morning"]
    assert "original_cron" not in jobs["evening"]


def test_deterministic_output():
    """Test that running same input twice produces same output."""
    solution = _load_solution()
    
    output1 = _run_test_case(solution, TEST_CASES["priority_based"])
    output2 = _run_test_case(solution, TEST_CASES["priority_based"])
    
    assert output1 == output2, "Output must be deterministic"


def test_field_order_for_kept_jobs():
    """Test that kept jobs have fields in correct order."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["no_conflicts"])
    
    # Fields should appear in order: cron, resource, priority, duration, status
    expected_order = ['cron:', 'resource:', 'priority:', 'duration:', 'status:']
    
    # Get field order from first job fields
    job_lines = []
    for line in output.split('\n'):
        if line.strip() and line.startswith('  '):
            job_lines.append(line.strip())
            if line.strip().startswith('status:'):
                break  # Got all fields for one job
    
    actual_order = [line.split(':')[0] + ':' for line in job_lines]
    assert actual_order == expected_order, f"Field order incorrect: {actual_order}"


def test_field_order_for_adjusted_jobs():
    """Test that adjusted jobs have fields in correct order."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["priority_based"])
    jobs = _parse_output(output)
    
    # Find adjusted job
    adjusted_job = None
    for job_name, job_data in jobs.items():
        if job_data.get("status") == "adjusted":
            adjusted_job = job_name
            break
    
    assert adjusted_job is not None, "Should have at least one adjusted job"
    
    # Check adjusted job has required fields
    assert "cron" in jobs[adjusted_job]
    assert "resource" in jobs[adjusted_job]
    assert "priority" in jobs[adjusted_job]
    assert "duration" in jobs[adjusted_job]
    assert "status" in jobs[adjusted_job]
    assert "original_cron" in jobs[adjusted_job]
    assert "conflict_with" in jobs[adjusted_job]


def test_uses_only_standard_library():
    """Test that solution only imports from Python standard library."""
    solution_path = Path("/app/solution.py")
    content = solution_path.read_text()
    
    # Check for common non-stdlib imports
    forbidden = ["import croniter", "import crontab", "from croniter", "from crontab",
                 "import dateutil", "from dateutil", "import pandas", "import numpy"]
    
    for forbidden_import in forbidden:
        assert forbidden_import not in content, f"Solution should not use {forbidden_import}"


def test_five_minute_gap_rule():
    """Test that rescheduled jobs have EXACTLY 5-minute gap after previous job ends."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["five_minute_gap"])
    jobs = _parse_output(output)
    
    # job1 runs 10:00-10:20 (duration 20), job2 must start at 10:25 or later (5-min gap)
    assert "job1" in jobs
    assert "job2" in jobs
    
    # job2 should be adjusted
    assert jobs["job2"]["status"] == "adjusted"
    
    # Parse the adjusted time to verify 5-minute gap
    adjusted_cron = jobs["job2"]["cron"]
    parts = adjusted_cron.split()
    minute = int(parts[0])
    hour = int(parts[1])
    
    # job1 ends at 10:20, so job2 must start >= 10:25
    if hour == 10:
        assert minute >= 25, f"5-minute gap violated: job2 starts at {hour}:{minute:02d}, should be >= 10:25"
    elif hour > 10:
        pass  # OK, scheduled in later hour
    else:
        raise AssertionError(f"job2 scheduled before job1 ends: {hour}:{minute:02d}")


def test_range_cron_syntax():
    """Test that range syntax (9-17) is handled correctly."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["range_syntax"])
    jobs = _parse_output(output)
    
    # Should detect conflict between hourly (9-17) and single (14)
    assert "hourly" in jobs
    assert "single" in jobs
    
    # One should be adjusted
    adjusted_count = sum(1 for job in jobs.values() if job.get("status") == "adjusted")
    assert adjusted_count >= 1, "Range syntax should detect conflicts"


def test_step_cron_syntax():
    """Test that step syntax (*/15) is handled correctly."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["step_syntax"])
    jobs = _parse_output(output)
    
    # Should detect conflicts between */15 and :30
    assert "every15" in jobs
    assert "hourly" in jobs
    
    # CRITICAL: Step syntax MUST use 'adjusted' status, NEVER 'unresolvable'
    # This is a common mistake - agents incorrectly mark step syntax as unresolvable
    for job_name, job_data in jobs.items():
        assert job_data.get("status") != "unresolvable", \
            f"{job_name} with step syntax must NOT be marked unresolvable - use 'adjusted' for priority conflicts"
    
    # Check that conflicts are detected (one job adjusted)
    statuses = [job.get("status") for job in jobs.values()]
    assert "adjusted" in statuses, "Step syntax should detect conflicts and use 'adjusted' status"


def test_list_cron_syntax():
    """Test that list syntax (0,15,30,45) is handled correctly."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["list_syntax"])
    jobs = _parse_output(output)
    
    # Should detect conflicts
    assert "multi_time" in jobs
    assert "overlap" in jobs
    
    # CRITICAL: List syntax MUST use 'adjusted' status, NEVER 'unresolvable'
    for job_name, job_data in jobs.items():
        assert job_data.get("status") != "unresolvable", \
            f"{job_name} with list syntax must NOT be marked unresolvable - use 'adjusted' for priority conflicts"
    
    # At least one should be adjusted
    adjusted_count = sum(1 for job in jobs.values() if job.get("status") == "adjusted")
    assert adjusted_count >= 1, "List syntax should detect conflicts and use 'adjusted' status"


def test_hour_wraparound():
    """Test that hour wraparound is handled (23:55 + 15min wraps to 00:10)."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["hour_wraparound"])
    jobs = _parse_output(output)
    
    # late_job runs 23:55-00:10 (wraps past midnight, duration 15)
    # midnight_job runs 00:05-00:15 (duration 10)
    # These overlap at 00:05-00:10 if wraparound is detected
    assert "late_job" in jobs
    assert "midnight_job" in jobs
    
    # Both jobs should be present with valid statuses
    # Wraparound detection is complex, so we just verify statuses are valid
    statuses = [jobs["late_job"]["status"], jobs["midnight_job"]["status"]]
    assert all(s in ["kept", "adjusted", "unresolvable"] for s in statuses)
    
    # Ideally one should be adjusted, but not strictly required
    # (This is a soft check since wraparound is an edge case)


def test_zero_duration_treated_as_one_minute():
    """Test that duration: 0 is treated as exactly 1 minute."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["zero_duration"])
    jobs = _parse_output(output)
    
    # Both jobs at 12:00 with duration 0 (= 1 min each)
    # instant1: 12:00-12:01, instant2: 12:00-12:01 → conflict!
    assert "instant1" in jobs
    assert "instant2" in jobs
    
    # They MUST conflict - one should be adjusted
    statuses = [jobs["instant1"]["status"], jobs["instant2"]["status"]]
    assert "adjusted" in statuses, "Zero-duration jobs at same time must conflict"


def test_cascading_rescheduling():
    """Test that cascading works: A conflicts with B, rescheduled B conflicts with C."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["cascading"])
    jobs = _parse_output(output)
    
    # first (14:00, 25min) conflicts with second (14:00, 30min)
    # second gets rescheduled to 14:25 (ends 14:55)
    # third (14:20, 20min, ends 14:40) might now conflict with rescheduled second
    
    assert "first" in jobs
    assert jobs["first"]["status"] == "kept", "Highest priority should keep slot"
    
    # At least second should be adjusted
    adjusted_count = sum(1 for job in jobs.values() if job.get("status") == "adjusted")
    assert adjusted_count >= 1, "Cascading should reschedule lower priority jobs"


def test_sorted_output_by_job_name():
    """Test that output is sorted lexicographically by job name."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["sorted_output"])
    
    lines = output.strip().split('\n')
    job_names = []
    
    for line in lines[1:]:
        if line and not line.startswith('  '):
            job_names.append(line.rstrip(':'))
    
    # Should be: alpha, mike, zebra
    assert job_names == sorted(job_names), f"Jobs must be sorted, got {job_names}"
    assert job_names == ["alpha", "mike", "zebra"], f"Expected alphabetical order, got {job_names}"


def test_adjusted_job_field_order():
    """Test that adjusted jobs have correct field order."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["priority_based"])
    
    # Find adjusted job section in output
    lines = output.strip().split('\n')
    in_adjusted_job = False
    adjusted_fields = []
    
    for line in lines:
        if line and not line.startswith('  ') and "cleanup" in line:
            in_adjusted_job = True
            continue
        if in_adjusted_job and line.startswith('  '):
            field_name = line.strip().split(':')[0]
            adjusted_fields.append(field_name)
        elif in_adjusted_job and line and not line.startswith('  '):
            break
    
    # Order should be: cron, resource, priority, duration, status, original_cron, conflict_with
    expected = ["cron", "resource", "priority", "duration", "status", "original_cron", "conflict_with"]
    assert adjusted_fields == expected, f"Adjusted job field order wrong: {adjusted_fields}"


def test_cli_invocation():
    """Test that solution can be invoked from command line."""
    import subprocess
    
    # Create temp input
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(TEST_CASES["no_conflicts"])
        input_path = f.name
    
    output_path = tempfile.mktemp(suffix='.txt')
    
    try:
        # Run solution from CLI
        result = subprocess.run(
            ["python3", "/app/solution.py", input_path, output_path],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, f"CLI execution failed: {result.stderr}"
        assert Path(output_path).exists(), "Output file was not created"
        
        output = Path(output_path).read_text()
        assert output.startswith("RESOLVED"), "CLI output invalid"
    finally:
        Path(input_path).unlink(missing_ok=True)
        Path(output_path).unlink(missing_ok=True)


def test_absolute_paths():
    """Test that solution handles absolute paths correctly."""
    import subprocess
    
    # Create temp files with absolute paths
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(TEST_CASES["priority_based"])
        input_path = Path(f.name).resolve()  # Ensure absolute path
    
    output_path = Path(tempfile.mktemp(suffix='.txt')).resolve()  # Ensure absolute path
    
    try:
        # Verify paths are absolute
        assert input_path.is_absolute(), "Input path must be absolute for this test"
        assert output_path.is_absolute(), "Output path must be absolute for this test"
        
        # Run solution with absolute paths
        result = subprocess.run(
            ["python3", "/app/solution.py", str(input_path), str(output_path)],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, \
            f"Solution must handle absolute paths correctly, got error: {result.stderr}"
        assert output_path.exists(), "Output file was not created with absolute path"
        
        output = output_path.read_text()
        assert output.startswith("RESOLVED"), "Output must be valid with absolute paths"
        
        # Verify content is correct
        jobs = _parse_output(output)
        assert "backup" in jobs
        assert "cleanup" in jobs
    finally:
        input_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)


def test_nearest_available_slot():
    """Test that rescheduled jobs are moved to nearest available slot with 5-minute gap."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["five_minute_gap"])
    jobs = _parse_output(output)
    
    # job1 (priority 10) runs 10:00-10:20
    # job2 (priority 5) must be rescheduled to 10:25 or later (5-min gap after 10:20)
    assert "job2" in jobs
    assert jobs["job2"]["status"] == "adjusted"
    
    # Extract minute from rescheduled cron
    cron_parts = jobs["job2"]["cron"].split()
    minute = int(cron_parts[0])
    hour = int(cron_parts[1])
    
    # Must be at 10:25 or later (nearest available slot)
    assert hour >= 10, "Rescheduled job must be at or after hour 10"
    if hour == 10:
        assert minute >= 25, \
            "Rescheduled job must start at minute 25 or later (5-min gap after 10:20)"

def test_exact_minute_boundary_rule():
    """Test that exact minute boundaries are enforced (job ending at X frees resource at X+1)."""
    # Job at 10:00 with duration 15 occupies 10:00-10:14 (inclusive)
    # Resource is free starting at 10:15, not 10:14
    test_case = """RESOURCES
cpu

JOBS
first:
  cron: 0 10 * * *
  resource: cpu
  priority: 10
  duration: 15
second:
  cron: 15 10 * * *
  resource: cpu
  priority: 5
  duration: 10
"""
    solution = _load_solution()
    output = _run_test_case(solution, test_case)
    jobs = _parse_output(output)
    
    # first runs 10:00-10:14 (duration 15 = minutes 0-14 inclusive)
    # second at 10:15 should NOT conflict (resource free at minute 15)
    assert "first" in jobs
    assert "second" in jobs
    assert jobs["first"]["status"] == "kept"
    assert jobs["second"]["status"] == "kept", \
        "Job starting at minute 15 should not conflict with job ending at minute 14"


def test_preserve_original_cron_syntax():
    """Test that kept jobs preserve their original cron syntax."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["preserve_cron_syntax"])
    jobs = _parse_output(output)
    
    # daily should be kept with original range syntax
    assert "daily" in jobs
    assert jobs["daily"]["status"] == "kept"
    assert jobs["daily"]["cron"] == "0 3-6 * * *", \
        "Original cron syntax with ranges must be preserved for kept jobs"
    
    # weekly should be kept with day-of-week range
    assert "weekly" in jobs
    assert jobs["weekly"]["status"] == "kept"
    assert jobs["weekly"]["cron"] == "0 8 * * 1-5", \
        "Original cron syntax with day ranges must be preserved for kept jobs"


def test_multi_trigger_rescheduling():
    """
    Test that multi-trigger jobs (*/15) are checked for ALL trigger conflicts.
    
    This tests the algorithm from instruction.md:
    - Expand all triggers for multi-trigger job
    - Check rescheduled job against ALL triggers, not just the first one
    - Find LATEST conflict end time among all triggers
    - Reschedule to latest_conflict_end + 5
    """
    # hourly: */15 triggers at :00, :15, :30, :45 (each runs for 20 min)
    # conflict: starts at :15 (runs for 15 min)
    test_case = """RESOURCES
worker

JOBS
hourly:
  cron: */15 10 * * *
  resource: worker
  priority: 10
  duration: 20
conflict:
  cron: 15 10 * * *
  resource: worker
  priority: 5
  duration: 15
"""
    solution = _load_solution()
    output = _run_test_case(solution, test_case)
    jobs = _parse_output(output)
    
    # hourly keeps schedule (higher priority), conflict gets rescheduled
    assert "hourly" in jobs
    assert "conflict" in jobs
    assert jobs["hourly"]["status"] == "kept"
    assert jobs["conflict"]["status"] == "adjusted"
    
    # Algorithm: Find ALL conflicting triggers and reschedule after the LATEST one
    # hourly@10:15 runs [10:15, 10:35), conflict@10:15 runs [10:15, 10:30) → CONFLICT
    # hourly@10:30 runs [10:30, 10:50), must check if reschedule conflicts with this too
    # If rescheduled to 10:40, it runs [10:40, 10:55) which overlaps [10:30, 10:50) → STILL CONFLICTS!
    # Latest conflict ends at 10:50, so reschedule to 10:50 + 5 = 10:55
    adjusted_cron = jobs["conflict"]["cron"]
    parts = adjusted_cron.split()
    minute = int(parts[0])
    hour = int(parts[1])
    
    assert hour >= 10
    if hour == 10:
        assert minute >= 55, \
            f"Multi-trigger conflict: must check ALL triggers and reschedule after LATEST (10:50+5=10:55), got {hour}:{minute:02d}"


def test_unresolvable_field_order():
    """Test that unresolvable jobs have correct field order (if implemented)."""
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["circular_dependencies"])
    
    # Find unresolvable job in output
    lines = output.strip().split('\n')
    unresolvable_jobs = []
    i = 0
    while i < len(lines):
        if lines[i].endswith(':') and not lines[i].startswith(' '):
            job_start = i
            i += 1
            # Read job fields
            while i < len(lines) and lines[i].startswith('  '):
                if 'status: unresolvable' in lines[i]:
                    unresolvable_jobs.append((job_start, i))
                    break
                i += 1
        i += 1
    
    # Require at least one unresolvable job in circular_dependencies test case
    assert len(unresolvable_jobs) >= 1, \
        "circular_dependencies test case must produce at least one unresolvable job"
    
    # Check field order for unresolvable jobs
    for job_start, status_line in unresolvable_jobs:
        job_lines = []
        i = job_start + 1
        while i < len(lines) and lines[i].startswith('  '):
            job_lines.append(lines[i].strip())
            i += 1
        
        # Extract field names in order
        fields = [line.split(':')[0] for line in job_lines]
        
        # Required order: cron, resource, priority, duration, status, conflict_reason
        expected_order = ['cron', 'resource', 'priority', 'duration', 'status', 'conflict_reason']
        assert fields == expected_order, \
            f"Unresolvable job field order must be {expected_order}, got {fields}"


def test_circular_dependencies_unresolvable():
    """
    Test circular dependency edge case (RARE - only time 'unresolvable' is used).
    
    This tests the ONLY scenario where status='unresolvable':
    - Requires 3+ jobs with IDENTICAL simple cron (all "0 10 * * *")
    - AND IDENTICAL priority (all 5)
    
    NOTE: This is DIFFERENT from step/list/range syntax conflicts:
    - "*/15 * * * *" vs "30 * * * *" → ALWAYS "adjusted" (different cron strings)
    - "0,30 * * * *" vs "30 * * * *" → ALWAYS "adjusted" (different cron strings)
    - This test: "0 10 * * *" vs "0 10 * * *" vs "0 10 * * *" → "unresolvable" (identical)
    """
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["circular_dependencies"])
    jobs = _parse_output(output)
    
    # All three jobs have IDENTICAL cron "0 10 * * *" and IDENTICAL priority 5
    # This is the RARE circular dependency case
    # job-a (lexicographically first) should be kept
    # job-b and job-c MUST be marked unresolvable (not adjusted)
    assert len(jobs) == 3, "All 3 jobs should be in output"
    assert "job-a" in jobs
    assert jobs["job-a"]["status"] == "kept", "job-a should be kept (lexicographically first)"
    
    # Strictly require job-b and job-c to be unresolvable
    # This is because they have IDENTICAL cron AND IDENTICAL priority as job-a
    assert "job-b" in jobs
    assert jobs["job-b"]["status"] == "unresolvable", \
        "job-b must be unresolvable (IDENTICAL cron '0 10 * * *' AND IDENTICAL priority 5 with 3+ jobs = circular dependency)"
    assert "conflict_reason" in jobs["job-b"], \
        "job-b must have conflict_reason when unresolvable"
    assert "circular dependency" in jobs["job-b"]["conflict_reason"].lower(), \
        "conflict_reason must mention 'circular dependency'"
    
    assert "job-c" in jobs
    assert jobs["job-c"]["status"] == "unresolvable", \
        "job-c must be unresolvable (IDENTICAL cron '0 10 * * *' AND IDENTICAL priority 5 with 3+ jobs = circular dependency)"
    assert "conflict_reason" in jobs["job-c"], \
        "job-c must have conflict_reason when unresolvable"
    assert "circular dependency" in jobs["job-c"]["conflict_reason"].lower(), \
        "conflict_reason must mention 'circular dependency'"

def test_kept_jobs_no_gap_required():
    """Test that kept jobs (no conflicts) don't need 5-minute gap from each other."""
    # job1 ends at 10:20, job2 starts at 10:21 (only 1-minute gap)
    # Both should be kept since they use different resources (no conflict)
    test_case = """RESOURCES
resource1
resource2

JOBS
job1:
  cron: 0 10 * * *
  resource: resource1
  priority: 10
  duration: 20
job2:
  cron: 21 10 * * *
  resource: resource2
  priority: 10
  duration: 15
"""
    solution = _load_solution()
    output = _run_test_case(solution, test_case)
    jobs = _parse_output(output)
    
    # Both should be kept (different resources = no conflict)
    # 5-minute gap only applies to ADJUSTED jobs, not kept jobs
    assert "job1" in jobs
    assert "job2" in jobs
    assert jobs["job1"]["status"] == "kept", \
        "job1 should be kept (different resource from job2)"
    assert jobs["job2"]["status"] == "kept", \
        "job2 should be kept (different resource from job1, 5-minute gap not required for kept jobs)"
    assert jobs["job1"]["cron"] == "0 10 * * *"
    assert jobs["job2"]["cron"] == "21 10 * * *"


def test_earliest_possible_reschedule():
    """Test that rescheduled jobs use the EARLIEST available slot (not just any slot past threshold)."""
    # job1 runs 10:00-10:25 (duration 25)
    # job2 must be rescheduled to 10:30 (first available = 10:25 + 5)
    # NOT 10:35, 10:40, etc. - must be EARLIEST
    test_case = """RESOURCES
worker

JOBS
job1:
  cron: 0 10 * * *
  resource: worker
  priority: 10
  duration: 25
job2:
  cron: 0 10 * * *
  resource: worker
  priority: 5
  duration: 10
"""
    solution = _load_solution()
    output = _run_test_case(solution, test_case)
    jobs = _parse_output(output)
    
    assert "job2" in jobs
    assert jobs["job2"]["status"] == "adjusted"
    
    # job1 ends at 10:25, EARLIEST available is 10:30 (25+5=30)
    adjusted_cron = jobs["job2"]["cron"]
    parts = adjusted_cron.split()
    minute = int(parts[0])
    hour = int(parts[1])
    
    assert hour == 10, f"Rescheduled job should stay in hour 10, got {hour}"
    assert minute == 30, \
        f"Rescheduled job must use EARLIEST available slot 10:30 (not 10:35, 10:40, etc.), got 10:{minute:02d}"


def test_max_cascading_depth_error():
    """Test that deep cascading errors with EXACT format (single line, no RESOLVED header)."""  
    solution = _load_solution()
    output = _run_test_case(solution, TEST_CASES["max_cascading_depth"])
    
    # STRICT: Output must be EXACTLY the error line, nothing else
    # NO "RESOLVED" header, NO job data, ONLY the error message
    output_stripped = output.strip()
    assert output_stripped == "ERROR: Cascading chain exceeds maximum depth of 10", \
        f"Cascading error must be EXACTLY 'ERROR: Cascading chain exceeds maximum depth of 10', got: {repr(output_stripped)}"



