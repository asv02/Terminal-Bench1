# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

from pathlib import Path
import pytest


def test_output_file_exists():
    """Test that output.log file exists in the current directory."""
    output_path = Path("/app/output.log")
    assert output_path.exists(), f"File {output_path} does not exist"


def test_timestamp_reassignment():
    """Test 1: Timestamp Reassignment Trap - Output timestamps must be 0..k-1, not original values."""
    output_path = Path("/app/output.log")
    assert output_path.exists(), "output.log should exist"
    
    content = output_path.read_text()
    if not content.strip():
        # Empty output is valid (no events)
        return
    
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    
    # Check that timestamps start from 0 and are consecutive
    for i, line in enumerate(lines):
        parts = line.split()
        assert len(parts) >= 3, f"Line {i+1} should have at least 3 parts: {line}"
        assert parts[0] == str(i), f"Timestamp should be {i}, got {parts[0]} in line: {line}"


def test_same_timestamp_mixed_ops():
    """Test 2: Same Timestamp, Mixed Ops - DEL b must appear before SET b when timestamps are equal."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return  # Skip if output doesn't exist
    
    lines = [line.strip() for line in output_path.read_text().strip().split('\n') if line.strip()]
    
    # Find positions of DEL b and SET b at the same timestamp
    events_at_same_ts = {}
    for i, line in enumerate(lines):
        parts = line.split()
        if len(parts) >= 3:
            ts = int(parts[0])
            op = parts[1]
            key = parts[2] if len(parts) > 2 else ""
            
            if ts not in events_at_same_ts:
                events_at_same_ts[ts] = []
            events_at_same_ts[ts].append((i, op, key))
    
    # Check ordering at same timestamps
    for ts, events in events_at_same_ts.items():
        if len(events) > 1:
            # Find DEL and SET for same key
            for i, (pos1, op1, key1) in enumerate(events):
                for j, (pos2, op2, key2) in enumerate(events):
                    if i != j and key1 == key2 and op1 == "SET" and op2 == "DEL":
                        assert pos2 < pos1, f"DEL {key1} should appear before SET {key1} at timestamp {ts}"


def test_canceling_set_del_pair():
    """Test 3: Canceling SET–DEL Pair - key must disappear entirely from compacted log if SET immediately followed by DEL."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    if not input_path.exists() or not output_path.exists():
        pytest.skip("Input or output file not found")
    
    # Parse input to find immediate SET-DEL pairs
    input_content = input_path.read_text()
    input_events = []
    for line_num, line in enumerate(input_content.split('\n'), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            break
        try:
            timestamp = int(parts[0])
            if timestamp < 0:
                break
            op = parts[1]
            if op not in ("SET", "DEL"):
                break
            key = parts[2]
            if not key:
                break
            if op == "SET" and len(parts) < 4:
                break
            value = parts[3] if op == "SET" else None
            input_events.append((timestamp, op, key, value, line_num))
        except (ValueError, IndexError):
            break
    
    if len(input_events) < 2:
        pytest.skip("Input has fewer than 2 events - cannot test SET-DEL pair removal")
    
    # Sort events by timestamp, then input order
    sorted_events = sorted(input_events, key=lambda x: (x[0], x[4]))
    
    # Find immediate SET-DEL pairs (same key, consecutive timestamps with no other events for that key in between)
    immediate_pairs = []
    events_by_key = {}
    for ts, op, key, value, line_num in sorted_events:
        if key not in events_by_key:
            events_by_key[key] = []
        events_by_key[key].append((ts, op, value, line_num))
    
    for key, key_events in events_by_key.items():
        # Check for SET immediately followed by DEL
        for i in range(len(key_events) - 1):
            ts1, op1, val1, ln1 = key_events[i]
            ts2, op2, val2, ln2 = key_events[i + 1]
            if op1 == "SET" and op2 == "DEL":
                # Check if they're immediate (consecutive timestamps with no other events for this key in between)
                # Immediate means: ts2 == ts1 + 1 and no other events for this key between them
                if ts2 == ts1 + 1:
                    # Check if there are any other events for this key between these timestamps
                    has_intermediate = False
                    for other_ts, other_op, _, _ in key_events:
                        if ts1 < other_ts < ts2:
                            has_intermediate = True
                            break
                    if not has_intermediate:
                        immediate_pairs.append(key)
                        break
    
    # Verify that these keys do not appear in output at all
    output_content = output_path.read_text()
    output_lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
    
    output_keys = set()
    for line in output_lines:
        parts = line.split()
        if len(parts) >= 3:
            output_keys.add(parts[2])
    
    # If immediate pairs exist, verify they're removed
    if immediate_pairs:
        for key in immediate_pairs:
            assert key not in output_keys, \
                f"Key '{key}' had an immediate SET-DEL pair and should be completely removed from output, but it appears in output"
    # If no immediate pairs, test still passes (basic output validation already done by other tests)


def test_multiple_sets_interleaved_deletes():
    """Test 4: Multiple SETs, Interleaved Deletes - Only the last effective SET should survive."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    content = output_path.read_text()
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    
    # Count SET events per key - should be at most 1 per key
    set_events_by_key = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[1] == "SET":
            key = parts[2]
            if key not in set_events_by_key:
                set_events_by_key[key] = 0
            set_events_by_key[key] += 1
    
    for key, count in set_events_by_key.items():
        assert count == 1, f"Key {key} should have exactly one SET event, got {count}"


def test_del_before_any_set():
    """Test 5: DEL Before Any SET - DEL without prior SET should not appear."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    content = output_path.read_text()
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    
    # Track which keys were SET
    keys_set = set()
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[1] == "SET":
            keys_set.add(parts[2])
    
    # Check that all DELs are for keys that were SET
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "DEL":
            key = parts[2]
            assert key in keys_set, f"DEL for key {key} appears but key was never SET"


def test_final_state_preservation():
    """Test that applying the compacted log produces the same final state as original."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    if not input_path.exists() or not output_path.exists():
        return
    
    # Simulate applying original log
    store_original = {}
    events_original = []
    
    with open(input_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                try:
                    timestamp = int(parts[0])
                    op = parts[1]
                    if op in ("SET", "DEL"):
                        key = parts[2]
                        value = parts[3] if len(parts) > 3 and op == "SET" else None
                        events_original.append((timestamp, op, key, value, line_num))
                except (ValueError, IndexError):
                    # Invalid line - stop processing
                    break
    
    # Sort by timestamp, then input order
    events_original.sort(key=lambda x: (x[0], x[4]))
    
    for ts, op, key, value, _ in events_original:
        if op == "SET":
            store_original[key] = value
        elif op == "DEL":
            store_original.pop(key, None)
    
    # Simulate applying compacted log
    store_compacted = {}
    with open(output_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                op = parts[1]
                key = parts[2]
                value = parts[3] if len(parts) > 3 and op == "SET" else None
                if op == "SET":
                    store_compacted[key] = value
                elif op == "DEL":
                    store_compacted.pop(key, None)
    
    assert store_original == store_compacted, f"Final states don't match: original={store_original}, compacted={store_compacted}"


def test_canonical_ordering():
    """Test that events are ordered correctly: timestamp, then DEL before SET, then key order."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    lines = [line.strip() for line in output_path.read_text().strip().split('\n') if line.strip()]
    
    # Parse events
    events = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                ts = int(parts[0])
                op = parts[1]
                key = parts[2]
                events.append((ts, op, key))
            except (ValueError, IndexError):
                continue
    
    # Check ordering
    for i in range(len(events) - 1):
        ts1, op1, key1 = events[i]
        ts2, op2, key2 = events[i + 1]
        
        # Primary: timestamp order
        assert ts1 <= ts2, f"Timestamps should be non-decreasing: {events[i]} before {events[i+1]}"
        
        if ts1 == ts2:
            # Secondary: DEL before SET
            if op1 == "SET" and op2 == "DEL":
                assert False, f"DEL should come before SET at same timestamp: {events[i]} before {events[i+1]}"
            
            # Tertiary: key order (if ops are same type)
            if op1 == op2:
                assert key1 <= key2, f"Keys should be in ASCII order: {events[i]} before {events[i+1]}"


def test_canonical_formatting():
    """Test that output follows canonical formatting rules."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    content = output_path.read_text()
    
    # Check that file ends with newline (Unix text file requirement)
    if content:
        assert content.endswith('\n'), "Output file must end with a newline character (Unix text file requirement)"
    
    # Split content into lines (this removes trailing newlines from each line)
    lines = content.split('\n')
    
    # Check formatting
    for i, line in enumerate(lines):
        if line.strip():  # Non-empty lines
            # Should have exactly one space between tokens
            parts = line.split()
            assert len(parts) >= 3, f"Line {i+1} should have at least 3 parts: {line}"
            
            # Check no extra whitespace (line should equal its stripped version)
            assert line == line.strip(), f"Line {i+1} has extra whitespace: {repr(line)}"
            
            # Verify exactly one space between tokens (not multiple spaces, not tabs)
            # Reconstruct expected line and compare
            if parts[1] == "SET" and len(parts) >= 4:
                expected_line = f"{parts[0]} {parts[1]} {parts[2]} {parts[3]}"
            elif parts[1] == "DEL" and len(parts) >= 3:
                expected_line = f"{parts[0]} {parts[1]} {parts[2]}"
            else:
                expected_line = " ".join(parts)
            
            # Check that line matches expected format (exactly one space between tokens)
            assert line == expected_line, \
                f"Line {i+1} must have exactly one space between tokens, got: {repr(line)}, expected: {repr(expected_line)}"
            
            # Also check no tabs or multiple consecutive spaces
            assert '\t' not in line, f"Line {i+1} contains tabs, must use only single spaces"
            if '  ' in line:  # Multiple consecutive spaces
                assert False, f"Line {i+1} contains multiple consecutive spaces, must have exactly one space between tokens: {repr(line)}"
            
            # Check operation is valid
            assert parts[1] in ("SET", "DEL"), f"Invalid operation on line {i+1}: {parts[1]}"
            
            # Check SET has value
            if parts[1] == "SET":
                assert len(parts) >= 4, f"SET operation on line {i+1} should have a value"
    
    # Verify that each non-empty line in the original content ends with newline
    # (except possibly the last line if file doesn't end with newline)
    if content:
        content_lines = content.splitlines(keepends=True)
        for i, orig_line in enumerate(content_lines):
            if orig_line.strip():  # Non-empty lines
                # Each line should end with newline (Unix text file format)
                assert orig_line.endswith('\n'), \
                    f"Line {i+1} must end with a newline character, got: {repr(orig_line)}"


def test_minimality_no_redundant_sets():
    """Test that no key has more than one SET event (minimality rule 1)."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    lines = [line.strip() for line in output_path.read_text().strip().split('\n') if line.strip()]
    
    set_count_by_key = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[1] == "SET":
            key = parts[2]
            set_count_by_key[key] = set_count_by_key.get(key, 0) + 1
    
    for key, count in set_count_by_key.items():
        assert count == 1, f"Key {key} has {count} SET events, but should have at most 1"


def test_empty_output_for_no_ops():
    """Test 8: Large Repeated No-Op Deletes - Output should not contain DELs for keys never SET."""
    output_path = Path("/app/output.log")
    if not output_path.exists():
        return
    
    content = output_path.read_text().strip()
    if not content:
        return  # Empty output is valid
    
    lines = content.split('\n')
    
    # Track which keys were SET
    keys_set = set()
    for line in lines:
        parts = line.split()
        if len(parts) >= 4 and parts[1] == "SET":
            keys_set.add(parts[2])
    
    # Check that all DELs are for keys that were SET
    for line in lines:
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "DEL":
            key = parts[2]
            assert key in keys_set, f"DEL for key {key} appears but key was never SET (minimality rule 2)"


def test_invalid_input_stops_at_first_invalid_line():
    """Test that processing stops at first invalid line and outputs compacted log for valid prefix."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    # Check if input exists with invalid content pattern
    # This test assumes test harness provides input with invalid line
    if not input_path.exists() or not output_path.exists():
        pytest.skip("Input or output file not found - test harness should provide input with invalid line")
    
    input_content = input_path.read_text()
    
    # Check if input contains an invalid line (non-parseable)
    # Look for lines that don't match the expected format
    has_invalid = False
    first_invalid_line_num = None
    valid_prefix_events = []
    
    for line_num, line in enumerate(input_content.split('\n'), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            has_invalid = True
            first_invalid_line_num = line_num
            break
        try:
            timestamp = int(parts[0])
            if timestamp < 0 or parts[1] not in ("SET", "DEL"):
                has_invalid = True
                first_invalid_line_num = line_num
                break
            if parts[1] == "SET" and len(parts) < 4:
                has_invalid = True
                first_invalid_line_num = line_num
                break
            valid_prefix_events.append((timestamp, parts[1], parts[2]))
        except (ValueError, IndexError):
            has_invalid = True
            first_invalid_line_num = line_num
            break
    
    # Verify output exists and is valid
    output_content = output_path.read_text()
    output_lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
    
    # Parse output events
    output_keys = set()
    for line in output_lines:
        parts = line.split()
        if len(parts) >= 3:
            output_keys.add(parts[2])
    
    # If invalid line exists, verify output doesn't contain events that would come after invalid line
    if has_invalid:
        assert len(output_keys) <= len(valid_prefix_events), \
            f"Output should only contain events from valid prefix (before line {first_invalid_line_num})"
    # If no invalid line, test still passes (output validation done by other tests)


def test_quaternary_tie_break_original_input_order():
    """Test that quaternary tie-break uses original input order when timestamps, ops, and keys are equal."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    if not input_path.exists() or not output_path.exists():
        pytest.skip("Input or output file not found")
    
    # Read input to check if it has events with same timestamp that would test tie-break
    input_content = input_path.read_text()
    input_events = []
    for line_num, line in enumerate(input_content.split('\n'), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                timestamp = int(parts[0])
                op = parts[1]
                if op in ("SET", "DEL") and len(parts) >= 3:
                    key = parts[2]
                    input_events.append((timestamp, op, key, line_num))
            except (ValueError, IndexError):
                continue
    
    # Check if there are events with same timestamp (would test tie-break)
    timestamps = [ts for ts, _, _, _ in input_events]
    has_same_timestamp = len(timestamps) != len(set(timestamps))
    
    output_content = output_path.read_text()
    lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
    
    if not has_same_timestamp:
        # If no same timestamp events, just verify basic ordering (test still passes)
        # Check that timestamps are non-decreasing
        events = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    ts = int(parts[0])
                    events.append(ts)
                except (ValueError, IndexError):
                    continue
        for i in range(len(events) - 1):
            assert events[i] <= events[i + 1], "Timestamps should be non-decreasing"
        return  # Test passes
    
    # Parse events
    events = []
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                ts = int(parts[0])
                op = parts[1]
                key = parts[2]
                events.append((ts, op, key))
            except (ValueError, IndexError):
                continue
    
    # Group input events by timestamp to find events that should be ordered by input order
    input_events_by_ts = {}
    for ts, op, key, line_num in input_events:
        if ts not in input_events_by_ts:
            input_events_by_ts[ts] = []
        input_events_by_ts[ts].append((op, key, line_num))
    
    # Parse output events with their positions
    output_events = []
    for pos, line in enumerate(lines):
        parts = line.split()
        if len(parts) >= 3:
            try:
                ts = int(parts[0])
                op = parts[1]
                key = parts[2]
                output_events.append((ts, op, key, pos))
            except (ValueError, IndexError):
                continue
    
    # Group output events by timestamp
    output_events_by_ts = {}
    for ts, op, key, pos in output_events:
        if ts not in output_events_by_ts:
            output_events_by_ts[ts] = []
        output_events_by_ts[ts].append((op, key, pos))
    
    # For each timestamp that had multiple events in input, verify quaternary tie-break
    for ts, input_ts_events in input_events_by_ts.items():
        if len(input_ts_events) < 2:
            continue
        
        # Find corresponding output timestamp (after reassignment)
        # Since timestamps are reassigned, we need to map original timestamp to output timestamp
        # For simplicity, check events at same output timestamp
        for output_ts, output_ts_events in output_events_by_ts.items():
            if len(output_ts_events) < 2:
                continue
            
            # Check if these output events correspond to input events at same original timestamp
            # by checking if they have same ops and keys
            input_keys_ops = {(op, key) for op, key, _ in input_ts_events}
            output_keys_ops = {(op, key) for op, key, _ in output_ts_events}
            
            # If they match, verify ordering
            if input_keys_ops == output_keys_ops and len(input_ts_events) == len(output_ts_events):
                # Sort input events by line number to get original order
                input_sorted = sorted(input_ts_events, key=lambda x: x[2])  # Sort by line_num
                # Sort output events by position
                output_sorted = sorted(output_ts_events, key=lambda x: x[2])  # Sort by position
                
                # After primary (timestamp), secondary (DEL before SET), tertiary (ASCII key order),
                # quaternary (input order) should determine ordering
                # Check that for events with same timestamp, same op type, and same key ordering,
                # the input order is preserved
                for i in range(len(input_sorted) - 1):
                    op1, key1, ln1 = input_sorted[i]
                    op2, key2, ln2 = input_sorted[i + 1]
                    
                    # Find corresponding output events
                    out1_idx = next((j for j, (o, k, _) in enumerate(output_sorted) if o == op1 and k == key1), None)
                    out2_idx = next((j for j, (o, k, _) in enumerate(output_sorted) if o == op2 and k == key2), None)
                    
                    if out1_idx is not None and out2_idx is not None:
                        # If they have same op and key order would be same, input order should determine
                        if op1 == op2 and key1 == key2:
                            # Same key, same op - input order must be preserved
                            assert out1_idx < out2_idx, \
                                f"Quaternary tie-break violated: input order {ln1} < {ln2} but output order is reversed"
                        elif op1 == op2 and key1 < key2:
                            # Keys in order - should be preserved
                            assert out1_idx < out2_idx, \
                                f"Tertiary rule (ASCII key order) violated: {key1} < {key2} but output order is reversed"
                        elif op1 == "DEL" and op2 == "SET" and key1 == key2:
                            # DEL should come before SET (secondary rule)
                            assert out1_idx < out2_idx, \
                                "Secondary rule violated: DEL should come before SET for same key at same timestamp"


def test_nontrivial_canonicalization():
    """Test nontrivial input that exercises full canonicalization logic."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    if not input_path.exists() or not output_path.exists():
        pytest.skip("Input or output file not found")
    
    # Read and parse input
    input_content = input_path.read_text()
    input_events = []
    for line_num, line in enumerate(input_content.split('\n'), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 3:
            break
        try:
            timestamp = int(parts[0])
            if timestamp < 0:
                break
            op = parts[1]
            if op not in ("SET", "DEL"):
                break
            key = parts[2]
            if not key:
                break
            if op == "SET" and len(parts) < 4:
                break
            value = parts[3] if op == "SET" else None
            input_events.append((timestamp, op, key, value, line_num))
        except (ValueError, IndexError):
            break
    
    # Skip if input is too simple (less than 3 events)
    if len(input_events) < 3:
        pytest.skip("Input has fewer than 3 events - need nontrivial input for this test")
    
    # Verify output exists and is properly formatted
    output_content = output_path.read_text()
    output_lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
    
    # Compute expected final state from input
    sorted_events = sorted(input_events, key=lambda x: (x[0], x[4]))
    expected_state = {}
    for ts, op, key, value, _ in sorted_events:
        if op == "SET":
            expected_state[key] = value
        elif op == "DEL":
            expected_state.pop(key, None)
    
    # Parse output state
    output_state = {}
    for line in output_lines:
        parts = line.split()
        if len(parts) >= 3:
            op = parts[1]
            key = parts[2]
            if op == "SET" and len(parts) >= 4:
                output_state[key] = parts[3]
            elif op == "DEL":
                output_state.pop(key, None)
    
    # Verify final states match
    assert output_state == expected_state, \
        f"Output state {output_state} does not match expected final state {expected_state} from input"


def test_ascii_key_ordering_comprehensive():
    """Test that ASCII key ordering is enforced for all events at same timestamp with same op."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    if not input_path.exists() or not output_path.exists():
        pytest.skip("Input or output file not found")
    
    # Check if input has multiple events with same timestamp
    input_content = input_path.read_text()
    input_events = []
    for line_num, line in enumerate(input_content.split('\n'), 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                timestamp = int(parts[0])
                op = parts[1]
                if op in ("SET", "DEL") and len(parts) >= 3:
                    key = parts[2]
                    input_events.append((timestamp, op, key, line_num))
            except (ValueError, IndexError):
                continue
    
    # Group by timestamp
    events_by_ts = {}
    for ts, op, key, line_num in input_events:
        if ts not in events_by_ts:
            events_by_ts[ts] = []
        events_by_ts[ts].append((op, key))
    
    # Check if there are timestamps with multiple events
    has_multiple_at_same_ts = any(len(events) > 1 for events in events_by_ts.values())
    
    if not has_multiple_at_same_ts:
        # If no same timestamp events, just verify basic key ordering in output (test still passes)
        output_content = output_path.read_text()
        output_lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
        
        events = []
        for line in output_lines:
            parts = line.split()
            if len(parts) >= 3:
                try:
                    ts = int(parts[0])
                    op = parts[1]
                    key = parts[2]
                    events.append((ts, op, key))
                except (ValueError, IndexError):
                    continue
        
        # Verify timestamps are non-decreasing
        for i in range(len(events) - 1):
            assert events[i][0] <= events[i + 1][0], "Timestamps should be non-decreasing"
        return  # Test passes
    
    output_content = output_path.read_text()
    lines = [line.strip() for line in output_content.strip().split('\n') if line.strip()]
    
    # Parse events
    events_by_ts = {}
    for line in lines:
        parts = line.split()
        if len(parts) >= 3:
            try:
                ts = int(parts[0])
                op = parts[1]
                key = parts[2]
                if ts not in events_by_ts:
                    events_by_ts[ts] = []
                events_by_ts[ts].append((op, key))
            except (ValueError, IndexError):
                continue
    
    # Check ordering at each timestamp
    for ts, events in events_by_ts.items():
        if len(events) > 1:
            # Group by operation
            sets = [(op, key) for op, key in events if op == "SET"]
            dels = [(op, key) for op, key in events if op == "DEL"]
            
            # Check SET ordering
            for i in range(len(sets) - 1):
                _, key1 = sets[i]
                _, key2 = sets[i + 1]
                assert key1 <= key2, f"SET keys should be in ASCII order: {key1} <= {key2} at timestamp {ts}"
            
            # Check DEL ordering
            for i in range(len(dels) - 1):
                _, key1 = dels[i]
                _, key2 = dels[i + 1]
                assert key1 <= key2, f"DEL keys should be in ASCII order: {key1} <= {key2} at timestamp {ts}"


def test_non_trivial_input_produces_output():
    """Anti-cheating: If input has valid events, output must exist and be properly processed."""
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    # If input doesn't exist or is empty, skip (empty input is valid)
    if not input_path.exists():
        return
    
    input_content = input_path.read_text().strip()
    if not input_content:
        return
    
    # Parse input to find valid events and compute expected final state
    valid_events = []
    with open(input_path) as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 3:
                break
            try:
                timestamp = int(parts[0])
                if timestamp < 0:
                    break
                op = parts[1]
                if op not in ("SET", "DEL"):
                    break
                key = parts[2]
                if not key:
                    break
                if op == "SET" and len(parts) < 4:
                    break
                value = parts[3] if op == "SET" else None
                valid_events.append((timestamp, op, key, value, line_num))
            except (ValueError, IndexError):
                break
    
    # If there are no valid events, empty output is acceptable
    if not valid_events:
        return
    
    # If there are valid events, output must exist
    assert output_path.exists(), f"Output file must exist when input has {len(valid_events)} valid events"
    
    # Compute expected final state from input
    sorted_events = sorted(valid_events, key=lambda x: (x[0], x[4]))
    expected_final_state = {}
    for ts, op, key, value, _ in sorted_events:
        if op == "SET":
            expected_final_state[key] = value
        elif op == "DEL":
            expected_final_state.pop(key, None)
    
    # If final state is non-empty, output must have content
    # This prevents trivial solutions that create empty output.log
    if expected_final_state:
        output_content = output_path.read_text().strip()
        assert output_content, f"Output must be non-empty when input produces non-empty final state {expected_final_state}"
        
        # Verify output produces the correct final state
        output_state = {}
        for line in output_content.split('\n'):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 3:
                op = parts[1]
                key = parts[2]
                if op == "SET" and len(parts) >= 4:
                    output_state[key] = parts[3]
                elif op == "DEL":
                    output_state.pop(key, None)
        
        assert output_state == expected_final_state, \
            f"Output state {output_state} does not match expected final state {expected_final_state}"
