Implement a deterministic, secure, asynchronous workflow engine from scratch that executes a sequence of tasks defined by a configuration object. The engine must enforce strict sandboxing for expressions, avoid any time/date/randomness-based behavior, and match the exact behaviors and message formats below.
Implement all behaviors and prohibitions exactly as written, including cases not explicitly exercised by the provided workflows.

runtime
- allowed deps: standard library, httpx=0.27.0, Jinja2=3.1.4
- deterministic and offline: no weekday checks, no time-based branching; use only the injected httpx.AsyncClient for network calls
- identical inputs MUST yield identical shared_state dicts; do not write transient/internal counters or non-deterministic values into shared_state or stdout


files
- single module: workflow_engine.py
  - must export: WorkflowEngine, WorkflowFailedError
  - may define internal TaskFailedError for control flow

class and api
- class WorkflowFailedError(Exception): raised when the entire workflow fails unrecoverably
- class TaskFailedError(Exception): internal signal that a single task permanently failed
- class WorkflowEngine:
  - __init__(self,
              workflow_definition: dict,
              custom_handlers: dict[str, callable] | None = None,
              http_client: httpx.AsyncClient | None = None)
    - workflow_definition: includes "tasks": [...] and optional "on_error_workflow": [...]
    - custom_handlers: optional mapping name -> async function; lookup must be case-insensitive
    - http_client: optional injected httpx.AsyncClient to use for all HTTP calls
  - async execute(self, initial_state: dict) -> dict
    - runs tasks in order, returning the final shared_state
    - on unrecoverable failure in the main workflow, always attempt on_error_workflow if present; if it succeeds, return the final shared_state (do not raise); if it fails, raise WorkflowFailedError

task model
- each task supports:
  - task_id: <string>
  - type: <string>  # "http_request", "data_transform", "log_message", or custom
  - run_if: <python_expr>  # optional; sandboxed
  - params: <dict>         # handler-specific
  - retry:                 # optional
      max_attempts: <int>                # default 1
      delay_seconds: <float>             # default 1.0 (use exactly 1.0 when omitted)
      backoff_multiplier: <float>        # default 1.0 (use exactly 1.0 when omitted)
      on_exceptions: [<ExceptionName>, ...]  # match by class name, e.g., ["ConnectError"]
      on_status_codes: [<int>, ...]      # http_request only; retry when response status is in this list

expression sandboxing and context
- evaluate run_if and data_transform expressions in a strict sandbox with only safe builtins (True, False, None, str, int, float, len, list, dict); no __import__, no open, no module access
- expressions see a top-level variable shared_state; state must be accessed as shared_state['key']
- data_transform additionally exposes source to its expression after evaluating params.source
- any run_if evaluation error results in the required failure message: "Failed to evaluate 'run_if' expression"


handler registry and custom handlers
- task type lookup must be deterministic and case-insensitive (applies to both built-in and custom handlers)
- custom handlers must be async and accept (state: dict, params: dict) -> dict; if a non-async handler is provided, treat it as a permanent failure when executing the task (do not raise in __init__); the resulting error must follow the standard "Task {task_id} failed after 1 attempt" wording.

built-in handlers
- http_request:
  - params map directly to httpx.AsyncClient.request kwargs: method, url, headers, json, params
  - Jinja2 rendering: render string fields (e.g., url) with direct access to shared_state keys and a shared_state variable
  - do not call response.raise_for_status(); treat all HTTP statuses as data
  - always write:
      shared_state["response"] = {
        "status_code": int,
        "headers": dict,  # header names MUST be lowercase
        "body": parsed_json_or_text
      }
  - Normalize response header names to lowercase and construct the headers dict by iterating over sorted(response.headers.items()) before storing, so insertion order is deterministic.
  - if status_code in retry.on_status_codes and attempt < max_attempts, retry with the same backoff rules as for exceptions; if still in retry.on_status_codes after the final attempt, treat as a permanent failure and raise WorkflowFailedError with the standard message ("Task {task_id} failed after {n} attempts").


- data_transform:
  - evaluate params.source with {"shared_state": shared_state}
  - if params.expression present, evaluate with {"source": evaluated_source}; else result = source
  - params.target is a string expression referencing shared_state, e.g., "shared_state['user']['profile']['email']"
    - support nested writes and create missing dicts; plain keys like "new_key" are invalid
  - any error evaluating source/expression or an invalid target MUST immediately raise WorkflowFailedError with the message exactly:
    "Failed to execute 'data_transform'"
    (do not wrap into "Task {...} failed...", do not include attempt counts, and do not append exception details).


- log_message:
  - use Python logging
  - params.level in {info, warning, error} (case-insensitive), default info
  - message is Jinja2-rendered with access to shared_state keys and shared_state

resilience and retries
- retry attempt numbering in logs is 1-indexed (first retry is Attempt 1)
- delay for retry number attempt = delay_seconds * (backoff_multiplier ** (attempt-1))
- retry when:
  - exception class name in retry.on_exceptions
  - http_request completed but status_code in retry.on_status_codes
- do not retry on internal expression errors

prohibited nondeterminism
- no disabling retries based on self._execution_count or weekday
- no time-based case-sensitivity toggles for handler lookup
- no time.time() % n behavior in any handler
- no sandbox weakening or attribute access tricks that escape the sandbox

global error handling (on_error_workflow)
- on permanent failure in main workflow:
  - set shared_state["error"] = {"task_id": <id>, "reason": <string>}
  - attempt on_error_workflow if present; if it completes, return final state; if it fails, raise WorkflowFailedError
  - The task_id used in failure messages and in shared_state["error"]["task_id"] MUST be the actual failing task's task_id (never hard-coded).

error and log formats (must match exactly)
- WorkflowFailedError messages:
  - immediate failures: "Task {task_id} failed after 1 attempt"
  - after retries: "Task {task_id} failed after {n} attempts"
  - run_if expression error: "Failed to evaluate 'run_if' expression"
  - when on_error_workflow fails: "Error workflow failed"
  - Use correct singular/plural: when n == 1 the message MUST be "Task {task_id} failed after 1 attempt", otherwise use "attempts".

- retry log line:
    - must be logged at WARNING level with exact text:
      "Retrying in {delay:.1f} seconds... (Attempt {attempt} of {max_attempts})"
    - the {delay} value MUST be formatted to exactly one decimal place (e.g., 0.1 → "0.1", 0.2 → "0.2"), and a line MUST be emitted for every retry attempt.
    - {attempt} is the retry ordinal starting at 1; with max_attempts = N there are exactly N-1 such lines (i.e., attempts 1..N-1).
    - When 'retry' is present but 'delay_seconds' or 'backoff_multiplier' are omitted, the engine MUST use delay_seconds=1.0 and backoff_multiplier=1.0 and still emit the WARNING line with "1.0".



cli interface in workflow_engine.py
- provide: python3 workflow_engine.py run <workflow_json_path> [--state '<json>'] [--log-level <level>]
- Note: The CLI may accept an optional --log-level; the option only needs to be parsed (no specific logging behavior required).
- the cli must:
  - load workflow json from path
  - optionally merge initial shared_state from --state json (default {})
  - execute the workflow and print compact json to stdout: {"ok": true, "shared_state": {...}}
  - on error, print {"ok": false, "error": "<message>"} and exit code 3
- all CLI JSON must be compact: the serializer must not insert spaces around separators (use separators=(",", ":")); spaces inside string values are allowed.
- all logging MUST be sent to stderr; stdout MUST contain only the compact JSON payload (no logs, prefixes, or extra text)
- exit codes: 0 success, 3 workflow failure
- unless a command specifies otherwise, construct the engine as: WorkflowEngine(workflow_definition=<loaded>, http_client=<injected client>)
- The CLI must construct the engine with a deterministic offline httpx.AsyncClient (MockTransport) whose behavior matches the provided workflows:
  - GET /404 → respond 404 (text ok)
  - GET /status503_then_ok → first response 503, second 200
  - GET /exc_then_ok → first request raises httpx.ConnectError, second 200 with JSON {"status":"ok"}
  - GET /log → 200
  - GET /customers/<id> → 200 with JSON including the id
  - Otherwise → 200 with JSON body (any stable default)


build outputs to produce
- after implementing the module, run the cli to generate exactly these files with these commands
  1) /app/_cli_ok.json                 <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_ok.json --state '{"customer_id":"cust-123"}'
  2) /app/_cli_404.json                <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_404.json
  3) /app/_cli_retry_status.json       <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_retry_status.json
  4) /app/_cli_retry_exception.json    <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_retry_exception.json
  5) /app/_cli_transform.json          <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_transform.json
  6) /app/_cli_nested.json             <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_nested.json
  7) /app/_cli_log.txt                 <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_log.json --state '{"user_id":42,"status":"active"}' > /app/_cli_log.txt
  8) /app/_cli_skip.json               <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_skip.json
  9) /app/_cli_error_workflow.json     <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_error_path.json
  10) /app/_cli_runif_syntax_error.txt <- output of: sh -c 'python3 /app/workflow_engine.py run /app/workflows/wf_bad_runif.json; echo $? > /app/_cli_runif_syntax_error.txt'
  11) /app/_cli_headers.txt            <- output of: python3 /app/workflow_engine.py run /app/workflows/wf_ok.json ; python3 -c "import json,sys;print(type(json.load(open('/app/_cli_ok.json'))['shared_state']['response']['headers']).__name__)" > /app/_cli_headers.txt
  12) /app/_cli_status_code.txt        <- output of: python3 -c "import json;print(json.load(open('/app/_cli_404.json'))['shared_state']['response']['status_code'])" > /app/_cli_status_code.txt

success criteria
- workflow_engine.py implements the behavior and api above
- a CLI main() in workflow_engine.py implements the commands above with the specified stdout contract and exit codes (0 = success, 3 = workflow failure)
- functionality covers expression sandboxing, http response storage without raise_for_status, case-insensitive handler lookup, nested data_transform writes, retries (exceptions and status codes), and on_error_workflow handling
