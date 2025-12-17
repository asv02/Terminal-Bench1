# Cron Schedule Conflict Resolver

Create a Python program at `/app/solution.py` that resolves conflicts in cron job schedules.

## Conflict Resolution Requirements

### Status Assignment Rules

**CRITICAL: Step syntax (`*/15`), ranges (`9-12`), and lists (`0,30`) are NORMAL conflicts**
**Always use status `"adjusted"` for these, NEVER `"unresolvable"`**

**CRITICAL: Two jobs with same priority but DIFFERENT cron strings are NORMAL conflicts**
**Use lexicographic ordering: first alphabetically gets `"kept"`, second gets `"adjusted"`**
**NEVER use `"unresolvable"` unless 3+ jobs have IDENTICAL cron strings AND priorities**

**Normal conflicts (99% of cases):** Use status `"adjusted"` for rescheduled jobs
- Step syntax (`*/15`), list syntax (`0,30`), and range syntax (`9-12`) conflicts → status: `"adjusted"`
- Different priorities → Higher priority keeps (`"kept"`), lower gets `"adjusted"`
- Same priority with DIFFERENT cron strings → First alphabetically keeps (`"kept"`), second gets `"adjusted"`
- **Two jobs with same priority are NEVER unresolvable** - always use lexicographic ordering

**Circular dependency (rare):** Use status `"unresolvable"` ONLY when ALL these conditions are met:
- **REQUIRES 3 or more jobs** (not just 2!)
- ALL jobs have IDENTICAL cron string character-for-character (e.g., all exactly `0 10 * * *`)
- AND ALL jobs have IDENTICAL priority number (e.g., all priority 5)
- AND ALL jobs use the SAME resource

When this occurs (circular dependency):
- First job alphabetically gets status `"kept"` 
- All other jobs get status `"unresolvable"` with `conflict_reason` describing the circular dependency
- Do NOT attempt to reschedule these jobs - they cannot be resolved through normal priority/lexicographic rules

**Examples:**
```
# Normal conflicts - use "adjusted" (reschedulable)
*/15 * * * * (priority 7) vs 30 * * * * (priority 6) → second job adjusted (different priorities)
0,30 * * * * (priority 8) vs 30 * * * * (priority 4) → second job adjusted (different priorities)
0 9-12 * * * (priority 5) vs 0 10 * * * (priority 3) → second job adjusted (different priorities)
0 10 * * * (priority 9) vs 0 10 * * * (priority 2) → second job adjusted (different priorities)
0 10 * * * (priority 5) vs 0 10 * * * (priority 5) → second job adjusted (only 2 jobs, use lexicographic)
0 10 * * * (priority 5) vs 15 10 * * * (priority 5) → second job adjusted (different cron, use lexicographic)

# Circular dependency - use "unresolvable" (cannot be resolved)
# All 3 jobs: identical cron "0 10 * * *", identical priority 5, same resource "disk"
job-a: 0 10 * * *, priority 5, resource disk → kept (first alphabetically)
job-b: 0 10 * * *, priority 5, resource disk → unresolvable (circular dependency)
job-c: 0 10 * * *, priority 5, resource disk → unresolvable (circular dependency)
# This is unresolvable because no rule can determine which job should win - all are truly equal
```

## Processing Requirements

### Cron Expression Expansion

Must correctly expand all cron syntax to trigger times:
- Wildcards: `*` matches all values
- Specific values: `15` matches minute 15
- Ranges: `9-12` expands to {9,10,11,12}
- Steps: `*/15` expands to {0,15,30,45}
- Lists: `0,30` expands to {0,30}
- Combinations: `0,30 9-11 * * *` → triggers at 9:00, 9:30, 10:00, 10:30, 11:00, 11:30

### Conflict Detection

**Algorithm for detecting conflicts between any cron expressions:**

1. **Expand both cron expressions** to get all trigger times
   - `*/15 * * * *` → {0, 15, 30, 45} for each hour
   - `30 * * * *` → {30} for each hour
   - `0,15,30,45 * * * *` → {0, 15, 30, 45} for each hour
   - `9-17 * * * *` → {9, 10, 11, 12, 13, 14, 15, 16, 17} for each hour

2. **For each trigger time in job A**, check if it overlaps with **any trigger time in job B**
   - Calculate execution window: [start, start + duration) in minutes
   - Two windows overlap if: `start1 < end2 AND start2 < end1`

3. **Example: Detecting conflict between step and specific syntax (wildcard hour)**
   - Job A: `*/15 * * * *`, duration 10, resource "network" → triggers at 0, 15, 30, 45 every hour
   - Job B: `30 * * * *`, duration 12, resource "network" → triggers at 30 every hour
   - At any hour (e.g., 10:00 hour):
     - Job A windows: [10:00-10:10), [10:15-10:25), [10:30-10:40), [10:45-10:55)
     - Job B window: [10:30-10:42)
     - Check overlap at 10:30: 10:30 < 10:42 AND 10:30 < 10:40 → **YES, conflict detected**
   - Same conflict occurs in every hour where both jobs trigger

4. **Example: Detecting conflict between list and specific syntax**
   - Job A: `0,15,30,45 * * * *`, duration 8, resource "db" → triggers at 0, 15, 30, 45 each hour
   - Job B: `5 * * * *`, duration 12, resource "db" → triggers at 5 each hour
   - Job A windows: [0-8), [15-23), [30-38), [45-53)
   - Job B window: [5-17)
   - Check overlap at 15: 15 < 17 AND 5 < 23 → **YES, conflict detected**

**Jobs conflict when:**
- They use the **same resource**
- At least one of their execution windows overlap
- Must check all trigger times in 24-hour period for multi-trigger jobs

### Rescheduling

**  CRITICAL: Multi-trigger conflict resolution algorithm**

When a job conflicts with a multi-trigger job (e.g., `*/15 10 * * *`), you MUST use this iterative algorithm:

**STEP 1:** Expand the multi-trigger cron to get ALL trigger times
   - Example: `*/15 10 * * *` → triggers at {10:00, 10:15, 10:30, 10:45}

**STEP 2:** Calculate execution window for EACH trigger using `[start, start + duration)`
   - With duration=20: [10:00-10:20), [10:15-10:35), [10:30-10:50), [10:45-11:05)

**STEP 3:** Find ALL triggers whose windows overlap with the original job position
   - Overlap formula: `start1 < end2 AND start2 < end1`
   - Identify which triggers conflict with the job's original time

**STEP 4:** Calculate LATEST end time among conflicting triggers
   - Take max(end_times) from all triggers that overlap original position

**STEP 5:** Try new position = LATEST end time + 5 minutes

**STEP 6 (CRITICAL - DO NOT SKIP):** Verify new position against ALL triggers
   - Calculate new job's window: [new_position, new_position + duration)
   - Check if it overlaps with ANY of the multi-trigger job's windows
   - If YES → Go back to STEP 4 and include this trigger's end time in LATEST calculation
   - If NO → This position is valid ✓

**WHY STEP 6 IS CRITICAL:** The first calculated position may still conflict with other triggers that didn't overlap the original position. You MUST verify the new position against ALL triggers, not just the initially conflicting ones.

**Concrete worked example (test_multi_trigger_rescheduling):**

**Given:**
- Multi-trigger job: `*/15 10 * * *`, duration 20, priority 10, resource "worker"
- Conflicting job: `15 10 * * *`, duration 15, priority 5, resource "worker"
- Question: Where should the lower-priority job be rescheduled?

**Solution step-by-step:**

**STEP 1: Expand multi-trigger cron**
- `*/15 10 * * *` → triggers at 10:00, 10:15, 10:30, 10:45

**STEP 2: Calculate ALL trigger windows**
- 10:00 trigger → [10:00, 10:20) because 10:00 + 20 = 10:20
- 10:15 trigger → [10:15, 10:35) because 10:15 + 20 = 10:35
- 10:30 trigger → [10:30, 10:50) because 10:30 + 20 = 10:50
- 10:45 trigger → [10:45, 11:05) because 10:45 + 20 = 11:05

**STEP 3: Find triggers overlapping original position [10:15, 10:30)**
- [10:15, 10:30) vs [10:00, 10:20)? → 10:15 < 10:20 AND 10:00 < 10:30 → **YES**
- [10:15, 10:30) vs [10:15, 10:35)? → 10:15 < 10:35 AND 10:15 < 10:30 → **YES**
- [10:15, 10:30) vs [10:30, 10:50)? → 10:15 < 10:50 AND 10:30 < 10:30 → **NO**
- [10:15, 10:30) vs [10:45, 11:05)? → **NO**
- Initially conflicting triggers: 10:00 (ends 10:20) and 10:15 (ends 10:35)

**STEP 4: Find LATEST end time**
- Conflicting end times: {10:20, 10:35}
- LATEST = 10:35

**STEP 5: Try new position**
- New position = 10:35 + 5 = 10:40

**STEP 6: Verify 10:40 against ALL triggers (CRITICAL STEP)**
- New job window: [10:40, 10:55) because 10:40 + 15 = 10:55
- Check against ALL four triggers:
  - [10:40, 10:55) vs [10:00, 10:20)? → 10:40 < 10:20? **NO** → No conflict 
  - [10:40, 10:55) vs [10:15, 10:35)? → 10:40 < 10:35? **NO** → No conflict 
  - [10:40, 10:55) vs [10:30, 10:50)? → 10:40 < 10:50 AND 10:30 < 10:55? **YES** → **CONFLICT!** 
  - Position 10:40 does NOT work!

**STEP 4 (revised): Update LATEST to include 10:30 trigger**
- Conflicting end times: {10:20, 10:35, 10:50}
- LATEST = 10:50

**STEP 5 (revised): Try new position**
- New position = 10:50 + 5 = 10:55

**STEP 6 (revised): Verify 10:55 against ALL triggers**
- New job window: [10:55, 11:10) because 10:55 + 15 = 11:10
- Check against ALL four triggers:
  - [10:55, 11:10) vs [10:00, 10:20)? → **NO** 
  - [10:55, 11:10) vs [10:15, 10:35)? → **NO** 
  - [10:55, 11:10) vs [10:30, 10:50)? → 10:55 < 10:50? **NO** 
  - [10:55, 11:10) vs [10:45, 11:05)? → 10:55 < 11:05 AND 10:45 < 11:10 → **NO** (10:55 >= 11:05 is false) 

**ANSWER: 10:55** 

**  Common mistake:** Rescheduling to 10:40 or 10:10 because agents skip STEP 6 verification against ALL triggers.

**5-minute gap rule:**
- Applies ONLY to rescheduled jobs (status "adjusted")
- Kept jobs (status "kept") are NOT subject to this rule

**Cron format in output:**
- **Kept jobs:** Preserve original cron syntax exactly (e.g., `*/15 10 * * *`, `0,30 * * * *`, `9-12 * * * *`)
- **Adjusted jobs:** Output as specific time (e.g., `55 10 * * *`), NOT range/step/list syntax
- **Unresolvable jobs:** Preserve original cron syntax exactly

The program must be runnable as: `python3 /app/solution.py <input_path> <output_path>`

## Input Format

The input file contains two sections separated by blank lines:

**RESOURCES section:**
```
RESOURCES
database
api
cpu
```

Each line after `RESOURCES` header is a resource name (alphanumeric, no spaces).

**JOBS section:**
```
JOBS
backup:
  cron: 0 2 * * *
  resource: database
  priority: 10
  duration: 30
```

Each job has:
- Job name (alphanumeric with underscores/hyphens, followed by colon)
- Indented fields (exactly 2 spaces):
  - `cron`: Standard 5-field cron expression (minute hour day month weekday)
  - `resource`: Which shared resource it uses
  - `priority`: Integer 1-100 (higher = more important)
  - `duration`: Minutes the job runs

### Cron Expression Syntax

Format: `minute hour day month weekday`
- minute: 0-59
- hour: 0-23  
- day: 1-31
- month: 1-12
- weekday: 0-6 (0=Sunday)

Supported patterns:
- `*` - any value
- `5` - specific value
- `1-5` - range (inclusive)
- `*/15` - step values
- `1,3,5` - list of values

### Edge Cases and Special Rules

**Zero-duration jobs:** Jobs with `duration: 0` are treated as `duration: 1` (occupy exactly one minute).

**Cascading limit:** When resolving conflicts, jobs may need to be rescheduled, which can trigger further conflicts in a cascading chain. If this cascading chain requires rescheduling more than 10 jobs (i.e., more than 10 jobs need status "adjusted"), output ONLY this line (entire file content):
```
ERROR: Cascading chain exceeds maximum depth of 10
```
Do NOT raise exception - write to output file and return normally. Count only jobs that are adjusted due to cascading conflicts, not jobs that keep their original time.

**Wraparound handling (optional):** Jobs can wrap to next hour (e.g., minute 59 with duration 10 runs 59-68, wrapping to next hour).

**Exact minute boundaries:** Job with duration D starting at minute M occupies the half-open interval [M, M+D). This means a job at 10:00 with duration 20 occupies minutes 10:00 through 10:19 (i.e., [10:00, 10:20) in interval notation), and the next available time is 10:20.

**5-minute gap:** Applies ONLY to rescheduled jobs (status "adjusted"). Kept jobs (status "kept") are NOT subject to this rule.

## Output Format

Write to output_path with this exact structure:

```
RESOLVED
apple:
  cron: 0 12 * * *
  resource: cpu
  priority: 10
  duration: 30
  status: kept
zebra:
  cron: 35 12 * * *
  resource: cpu
  priority: 10
  duration: 60
  status: adjusted
  original_cron: 0 12 * * *
  conflict_with: apple
```

Requirements:
- Jobs sorted lexicographically by name
- **CRITICAL: Exactly 2 spaces for indentation** - each field must be indented with exactly 2 spaces, no more, no less
- Field order for kept jobs: cron, resource, priority, duration, status
- Field order for adjusted jobs: cron, resource, priority, duration, status, original_cron, conflict_with
- Field order for unresolvable jobs: cron, resource, priority, duration, status, conflict_reason
- `status`: "kept" (unchanged), "adjusted" (rescheduled), or "unresolvable" (circular dependency)
- If adjusted: include `original_cron` and `conflict_with` fields. The adjusted cron MUST include the 5-minute gap if applicable.
- If unresolvable: include `conflict_reason` describing the circular dependency

## Implementation Constraints

- **REQUIRED FUNCTION**: Your solution MUST define a function named `resolve_schedule(input_path: str, output_path: str) -> None` that takes absolute paths to input and output files. This function will be called by the test harness.
- The program must also be runnable as: `python3 /app/solution.py <input_path> <output_path>` (implement a `__main__` block that calls `resolve_schedule`)
- Use only Python standard library (no external packages)
- Handle all cron syntax: wildcards, ranges, steps, lists
- Output must be deterministic (same input = same output)
- Use absolute paths for all file operations
- **CRITICAL**: Implement 5-minute gap rule for rescheduled jobs
- **CRITICAL**: Handle excessive cascading (>10 jobs at same time triggers ERROR)

