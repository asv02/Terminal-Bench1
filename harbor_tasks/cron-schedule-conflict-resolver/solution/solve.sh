#!/bin/bash
# Reference solution for cron schedule conflict resolver
# Creates solution.py that will be called by test harness

# Create the solution.py at /app/solution.py
cat > /app/solution.py << 'SOLUTION_EOF'
#!/usr/bin/env python3
"""
Cron Schedule Conflict Resolver
Resolves conflicts in cron job schedules based on priority and resource constraints.
"""

import sys
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple, Optional, Union
from collections import defaultdict


class CronParser:
    """Parse and evaluate cron expressions."""
    
    @staticmethod
    def parse_field(field: str, min_val: int, max_val: int) -> Set[int]:
        """Parse a single cron field and return set of valid values."""
        values = set()
        
        # Handle comma-separated values
        for part in field.split(','):
            if '/' in part:
                # Step values
                range_part, step = part.split('/')
                step = int(step)
                
                if range_part == '*':
                    start, end = min_val, max_val
                elif '-' in range_part:
                    start, end = map(int, range_part.split('-'))
                else:
                    start = end = int(range_part)
                
                values.update(range(start, end + 1, step))
            elif '-' in part:
                # Range
                start, end = map(int, part.split('-'))
                values.update(range(start, end + 1))
            elif part == '*':
                # Wildcard
                values.update(range(min_val, max_val + 1))
            else:
                # Single value
                values.add(int(part))
        
        return values
    
    @staticmethod
    def get_trigger_times(cron: str, start_date: datetime, hours: int = 24) -> List[datetime]:
        """Get all trigger times for a cron expression within a time window."""
        parts = cron.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression: {cron}")
        
        minute_str, hour_str, day_str, month_str, weekday_str = parts
        
        minutes = CronParser.parse_field(minute_str, 0, 59)
        hours_set = CronParser.parse_field(hour_str, 0, 23)
        days = CronParser.parse_field(day_str, 1, 31)
        months = CronParser.parse_field(month_str, 1, 12)
        weekdays = CronParser.parse_field(weekday_str, 0, 6)
        
        triggers = []
        current = start_date
        end = start_date + timedelta(hours=hours)
        
        while current < end:
            if (current.minute in minutes and
                current.hour in hours_set and
                current.day in days and
                current.month in months and
                current.weekday() % 7 in weekdays):
                triggers.append(current)
            
            current += timedelta(minutes=1)
        
        return triggers


class Job:
    """Represents a cron job with schedule and resource requirements."""
    
    def __init__(self, name: str, cron: str, resource: str, priority: int, duration: int):
        self.name = name
        self.cron = cron
        self.original_cron = cron
        self.resource = resource
        self.priority = priority
        # Treat duration 0 as 1 minute
        self.duration = max(1, duration)
        self.status = "kept"
        self.conflict_with: Optional[str] = None
        self.conflict_reason: Optional[str] = None
    
    def get_execution_windows(self, start_date: datetime) -> List[Tuple[datetime, datetime]]:
        """Get all execution windows (start, end) for this job."""
        triggers = CronParser.get_trigger_times(self.cron, start_date, hours=24)
        return [(t, t + timedelta(minutes=self.duration)) for t in triggers]
    
    def conflicts_with(self, other: 'Job', start_date: datetime) -> bool:
        """Check if this job conflicts with another job."""
        if self.resource != other.resource:
            return False
        
        windows1 = self.get_execution_windows(start_date)
        windows2 = other.get_execution_windows(start_date)
        
        for start1, end1 in windows1:
            for start2, end2 in windows2:
                # Windows overlap if: start1 < end2 AND start2 < end1
                if start1 < end2 and start2 < end1:
                    return True
        
        return False
    
    def reschedule_to_avoid(self, other: 'Job', start_date: datetime) -> bool:
        """Reschedule this job to avoid conflict with another job."""
        other_windows = other.get_execution_windows(start_date)
        
        # Find the earliest conflicting window
        my_triggers = CronParser.get_trigger_times(self.cron, start_date)
        
        for trigger in my_triggers:
            my_end = trigger + timedelta(minutes=self.duration)
            
            # Check if this trigger conflicts with any of other's windows
            conflicts = False
            latest_conflict_end = None
            
            for other_start, other_end in other_windows:
                if trigger < other_end and other_start < my_end:
                    conflicts = True
                    if latest_conflict_end is None or other_end > latest_conflict_end:
                        latest_conflict_end = other_end
            
            if conflicts and latest_conflict_end:
                # Reschedule to right after this conflict with 5-minute gap
                new_trigger = latest_conflict_end + timedelta(minutes=5)
                self.cron = self._adjust_cron_to_time(new_trigger)
                self.status = "adjusted"
                self.conflict_with = other.name
                return True
            
            if not conflicts:
                # No conflict with this trigger, keep it
                continue
        
        return False
    
    def _adjust_cron_to_time(self, dt: datetime) -> str:
        """Create a new cron expression for a specific datetime."""
        parts = self.cron.split()
        
        # Adjust minute and hour, keep day/month/weekday as wildcards if they were
        minute_part = str(dt.minute)
        hour_part = str(dt.hour)
        day_part = parts[2] if parts[2] != '*' else '*'
        month_part = parts[3] if parts[3] != '*' else '*'
        weekday_part = parts[4] if parts[4] != '*' else '*'
        
        return f"{minute_part} {hour_part} {day_part} {month_part} {weekday_part}"


def parse_input(content: str) -> Tuple[List[str], List[Job]]:
    """Parse input file and return resources and jobs."""
    lines = content.strip().split('\n')
    
    resources = []
    jobs = []
    current_section = None
    current_job = None
    job_data = {}
    
    for line in lines:
        line_stripped = line.rstrip()
        
        if not line_stripped:
            continue
        
        if line_stripped == 'RESOURCES':
            current_section = 'RESOURCES'
            continue
        elif line_stripped == 'JOBS':
            current_section = 'JOBS'
            continue
        
        if current_section == 'RESOURCES':
            resources.append(line_stripped)
        elif current_section == 'JOBS':
            if not line.startswith('  '):
                # New job
                if current_job and job_data:
                    jobs.append(Job(
                        current_job,
                        job_data['cron'],
                        job_data['resource'],
                        job_data['priority'],
                        job_data['duration']
                    ))
                    job_data = {}
                
                current_job = line_stripped.rstrip(':')
            else:
                # Job field
                field_line = line.strip()
                if ': ' in field_line:
                    key, value = field_line.split(': ', 1)
                    if key == 'priority':
                        job_data[key] = int(value)
                    elif key == 'duration':
                        job_data[key] = int(value)
                    else:
                        job_data[key] = value
    
    # Add last job
    if current_job and job_data:
        jobs.append(Job(
            current_job,
            job_data['cron'],
            job_data['resource'],
            job_data['priority'],
            job_data['duration']
        ))
    
    return resources, jobs


def resolve_conflicts(jobs: List[Job]) -> Union[List[Job], str]:
    """Resolve conflicts between jobs based on priority and name.
    
    Returns:
        List[Job] on success, or error string starting with 'ERROR' on failure.
    """
    start_date = datetime(2024, 1, 1, 0, 0, 0)  # Reference date for calculations
    
    # Sort jobs by priority (descending) and name (ascending) for resolution order
    sorted_jobs = sorted(jobs, key=lambda j: (-j.priority, j.name))
    
    # PRE-PROCESS: Detect circular dependencies (3+ jobs at same time/priority)
    # Mark losers as unresolvable to prevent cascading reschedules
    # NOTE: 2 jobs at same time/priority use lexicographic tiebreaking (reschedule loser)
    for i, job in enumerate(sorted_jobs):
        if job.status == "unresolvable":
            continue
            
        # Find other jobs with same priority and EXACT same original cron
        same_priority_same_time = []
        for other_job in sorted_jobs[i+1:]:
            if (other_job.status != "unresolvable" and
                other_job.priority == job.priority and
                other_job.original_cron == job.original_cron and
                other_job.resource == job.resource):
                same_priority_same_time.append(other_job)
        
        # If 2+ OTHER jobs at exact same time/priority (3+ total including current job),
        # this is a circular dependency - mark all but first as unresolvable
        if len(same_priority_same_time) >= 2:
            for other_job in same_priority_same_time:
                other_job.status = "unresolvable"
                other_job.conflict_reason = f"Circular dependency with {job.name}"
    
    # Check for excessive cascading BEFORE starting resolution
    # Count jobs that start at the exact same time on the same resource
    same_time_groups = defaultdict(list)
    for job in sorted_jobs:
        if job.status != "unresolvable":
            triggers = CronParser.get_trigger_times(job.original_cron, start_date, hours=24)
            if triggers:
                key = (job.resource, triggers[0])
                same_time_groups[key].append(job)
    
    # If any group has more than 10 jobs, that's excessive cascading
    for group in same_time_groups.values():
        if len(group) > 10:
            return "ERROR: Cascading chain exceeds maximum depth of 10"
    
    # Track reschedule attempts to prevent infinite loops
    max_iterations = 100  # Safety limit for complex cases
    iteration = 0
    
    while iteration < max_iterations:
        iteration += 1
        had_changes = False
        
        # Process conflicts
        for i, job in enumerate(sorted_jobs):
            if job.status == "unresolvable":
                continue
                
            # Check against higher priority jobs OR same-priority jobs that come earlier (lexicographically)
            for higher_job in sorted_jobs[:i]:
                if higher_job.status == "unresolvable":
                    continue
                    
                if job.conflicts_with(higher_job, start_date):
                    # Need to reschedule this job
                    old_cron = job.cron
                    job.reschedule_to_avoid(higher_job, start_date)
                    if job.cron != old_cron:
                        had_changes = True
                        break  # Move to next job after rescheduling
        
        if not had_changes:
            break
    
    # POST-PROCESSING: Detect circular dependencies (same-priority conflicts that remain)
    # These are jobs that still conflict AFTER all rescheduling attempts
    for job in sorted_jobs:
        if job.status != "kept":
            continue
            
        # Check for conflicts with other kept jobs of same priority
        for other_job in sorted_jobs:
            if (other_job != job and 
                other_job.status == "kept" and
                other_job.priority == job.priority and
                job.conflicts_with(other_job, start_date)):
                # Same priority conflict that persists - mark lexicographically later one as unresolvable
                if job.name > other_job.name:
                    job.status = "unresolvable"
                    job.conflict_reason = f"Circular dependency with {other_job.name}"
                    break
    
    # Sort by name for output
    return sorted(jobs, key=lambda j: j.name)


def format_output(jobs: List[Job]) -> str:
    """Format jobs into output string."""
    lines = ['RESOLVED']
    
    for job in jobs:
        lines.append(f"{job.name}:")
        lines.append(f"  cron: {job.cron}")
        lines.append(f"  resource: {job.resource}")
        lines.append(f"  priority: {job.priority}")
        lines.append(f"  duration: {job.duration}")
        lines.append(f"  status: {job.status}")
        
        if job.status == "adjusted":
            lines.append(f"  original_cron: {job.original_cron}")
            lines.append(f"  conflict_with: {job.conflict_with}")
        elif job.status == "unresolvable":
            lines.append(f"  conflict_reason: {job.conflict_reason}")
    
    return '\n'.join(lines) + '\n'


def resolve_schedule(input_path: str, output_path: str) -> None:
    """Main function to resolve schedule conflicts."""
    # Read input
    with open(input_path, 'r') as f:
        content = f.read()
    
    # Parse
    resources, jobs = parse_input(content)
    
    # Resolve conflicts
    result = resolve_conflicts(jobs)
    
    # Check if error was returned
    if isinstance(result, str) and result.startswith("ERROR"):
        with open(output_path, 'w') as f:
            f.write(result + '\n')
        return
    
    resolved_jobs = result
    
    # Write output
    output = format_output(resolved_jobs)
    with open(output_path, 'w') as f:
        f.write(output)


def main():
    """CLI entry point."""
    if len(sys.argv) != 3:
        print("Usage: python3 solution.py <input_path> <output_path>")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    
    resolve_schedule(input_path, output_path)


if __name__ == '__main__':
    main()
SOLUTION_EOF

chmod +x /app/solution.py


