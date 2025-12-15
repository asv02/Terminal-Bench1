#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

cat > /app/compact.py <<'EOF'
#!/usr/bin/env python3
"""
Incremental Log Compaction Canonicalizer

This script reads an append-only event log, validates it, and produces
a canonical compacted log that preserves final state while satisfying
strict minimality and ordering rules.
"""

import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class Event:
    """Represents a log event."""
    def __init__(self, timestamp: int, op: str, key: str, value: Optional[str] = None, input_index: int = 0):
        self.timestamp = timestamp
        self.op = op
        self.key = key
        self.value = value
        self.input_index = input_index
    
    def __repr__(self):
        if self.op == "SET":
            return f"{self.timestamp} {self.op} {self.key} {self.value}"
        else:
            return f"{self.timestamp} {self.op} {self.key}"


def parse_line(line: str, line_num: int) -> Optional[Event]:
    """Parse a single line into an Event, or return None if invalid."""
    line = line.strip()
    if not line:
        return None
    
    parts = line.split()
    if len(parts) < 3:
        return None  # Invalid: need at least timestamp, op, key
    
    try:
        timestamp = int(parts[0])
        if timestamp < 0:
            return None  # Invalid: negative timestamp
    except ValueError:
        return None  # Invalid: non-integer timestamp
    
    op = parts[1]
    if op not in ("SET", "DEL"):
        return None  # Invalid: unknown operation
    
    key = parts[2]
    if not key:
        return None  # Invalid: empty key
    
    value = None
    if op == "SET":
        if len(parts) < 4:
            return None  # Invalid: SET needs a value
        value = parts[3]
    
    return Event(timestamp, op, key, value, line_num)


def validate_and_parse_log(input_path: Path) -> Tuple[List[Event], bool]:
    """Parse and validate the input log. Returns (valid_events, fully_valid)."""
    events = []
    
    with open(input_path, 'r') as f:
        for line_num, line in enumerate(f, 1):
            event = parse_line(line, line_num)
            if event is None:
                # Invalid line - return events up to (but not including) this line
                return events, False
            events.append(event)
    
    if not events:
        return [], False  # No valid events
    
    return events, True


def apply_events(events: List[Event]) -> Dict[str, str]:
    """Apply events in timestamp order to determine final state."""
    # Sort by timestamp, then input order (for same timestamp)
    sorted_events = sorted(events, key=lambda e: (e.timestamp, e.input_index))
    
    store = {}
    for event in sorted_events:
        if event.op == "SET":
            store[event.key] = event.value
        elif event.op == "DEL":
            store.pop(event.key, None)
    
    return store


def compute_canonical_log(events: List[Event]) -> List[Event]:
    """
    Compute the canonical compacted log.
    
    Strategy:
    1. Apply events in timestamp order to determine final state
    2. For each key, determine minimal set of events needed
    3. Apply minimality rules (remove redundant events)
    4. Order according to canonical rules
    5. Reassign timestamps starting from 0
    """
    if not events:
        return []
    
    # Sort events by timestamp, then input order
    sorted_events = sorted(events, key=lambda e: (e.timestamp, e.input_index))
    
    # Apply events to get final state
    final_state = {}
    for event in sorted_events:
        if event.op == "SET":
            final_state[event.key] = event.value
        elif event.op == "DEL":
            final_state.pop(event.key, None)
    
    # Group events by key, maintaining their order
    events_by_key: Dict[str, List[Event]] = {}
    for event in sorted_events:
        if event.key not in events_by_key:
            events_by_key[event.key] = []
        events_by_key[event.key].append(event)
    
    # Determine which events to keep for each key
    events_to_keep: List[Event] = []
    
    for key, key_events in events_by_key.items():
        # Sort key events by timestamp, then input order
        key_events_sorted = sorted(key_events, key=lambda e: (e.timestamp, e.input_index))
        
        if key in final_state:
            # Key is in final state - need the last SET that sets it to final value
            for event in reversed(key_events_sorted):
                if event.op == "SET" and event.value == final_state[key]:
                    events_to_keep.append(event)
                    break
        else:
            # Key is not in final state
            # Check if key was ever SET
            set_events = [e for e in key_events_sorted if e.op == "SET"]
            
            if not set_events:
                # Key was never SET - all DELs are no-ops, ignore them
                continue
            
            # Key was SET but not in final state - it was deleted
            # Find the last SET
            last_set = set_events[-1]
            
            # Find DEL events after last SET
            del_events_after = [e for e in key_events_sorted 
                               if e.op == "DEL" and e.timestamp >= last_set.timestamp]
            
            if not del_events_after:
                # No DEL after last SET - shouldn't happen if key is not in final state
                continue
            
            first_del_after = del_events_after[0]
            
            # Check if SET-DEL pair is immediate
            # Immediate means: consecutive timestamps with no other events for this key in between
            if first_del_after.timestamp == last_set.timestamp + 1:
                # Check for intermediate events for this key
                has_intermediate = False
                for event in key_events_sorted:
                    if (event.timestamp > last_set.timestamp and 
                        event.timestamp < first_del_after.timestamp):
                        has_intermediate = True
                        break
                
                if not has_intermediate:
                    # Immediate SET-DEL pair - remove both (rule 3)
                    continue
            
            # Not immediate - but key is not in final state, so we don't need any events
            # The minimality principle: if key is not in final state, no events are needed
            continue
    
    # Remove duplicates (shouldn't happen, but be safe)
    seen = set()
    unique_events = []
    for event in events_to_keep:
        # Use a unique identifier for the event
        event_id = (event.timestamp, event.op, event.key, event.input_index)
        if event_id not in seen:
            seen.add(event_id)
            unique_events.append(event)
    
    # Order according to canonical rules:
    # 1. Primary: increasing timestamp (original, before reassignment)
    # 2. Secondary: DEL before SET if timestamps equal
    # 3. Tertiary: ASCII order of key
    # 4. Quaternary: original input order
    
    def sort_key(event: Event) -> Tuple[int, int, str, int]:
        # op_priority: 0 for DEL, 1 for SET (so DEL comes first)
        op_priority = 0 if event.op == "DEL" else 1
        return (event.timestamp, op_priority, event.key, event.input_index)
    
    canonical_events = sorted(unique_events, key=sort_key)
    
    # Reassign timestamps starting from 0 (preserve relative order)
    for i, event in enumerate(canonical_events):
        event.timestamp = i
    
    return canonical_events


def write_output(events: List[Event], output_path: Path):
    """Write the canonical compacted log to output file."""
    # Always create the file, even if empty
    with open(output_path, 'w') as f:
        if events:
            for event in events:
                if event.op == "SET":
                    f.write(f"{event.timestamp} {event.op} {event.key} {event.value}\n")
                else:
                    f.write(f"{event.timestamp} {event.op} {event.key}\n")
        # If no events, file will be empty (which is valid)


def main():
    input_path = Path("/app/input.log")
    output_path = Path("/app/output.log")
    
    # Ensure input file exists
    if not input_path.exists():
        # Create empty output if no input
        output_path.write_text("")
        return
    
    # Parse and validate input
    try:
        valid_events, fully_valid = validate_and_parse_log(input_path)
    except Exception:
        # On any error, create empty output
        output_path.write_text("")
        return
    
    if not valid_events:
        # No valid events - create empty output
        output_path.write_text("")
        return
    
    # Compute canonical log
    canonical_events = compute_canonical_log(valid_events)
    
    # Write output (always create file, even if empty)
    write_output(canonical_events, output_path)


if __name__ == "__main__":
    main()

EOF

chmod +x /app/compact.py

# Run the script to process input.log and create output.log
# Ensure input.log exists (create empty if it doesn't)
if [ ! -f /app/input.log ]; then
    touch /app/input.log
fi

# Run the compaction script
python3 /app/compact.py

# Ensure output.log exists (even if empty)
if [ ! -f /app/output.log ]; then
    touch /app/output.log
fi
