#!/bin/bash
# Hint from Snorkel
# Expert-authored step-by-step solution contained with a shell script that reliably and accurately completes the task.

# Install exact pinned deps
python3 - <<'PY'
import sys, subprocess
pkgs = ["httpx==0.27.0","Jinja2==3.1.4"]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--no-cache-dir", *pkgs])
print("Installed deps:", ", ".join(pkgs))
PY

# Write workflow_engine.py module + CLI
cat > /app/workflow_engine.py << 'EOF'
import sys
import json
import asyncio
import logging
import re
from typing import Callable, Any, Dict

import httpx
from jinja2 import Environment

log = logging.getLogger("workflow")


class WorkflowFailedError(Exception):
    """Raised when the entire workflow fails unrecoverably."""
    pass


class TaskFailedError(Exception):
    """Internal signal that a single task permanently failed."""
    def __init__(self, message: str, task_id: str, original_exception: Exception | None = None):
        super().__init__(message)
        self.task_id = task_id
        self.original_exception = original_exception


class WorkflowEngine:
    def __init__(
        self,
        workflow_definition: dict,
        custom_handlers: dict[str, Callable] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ):
        self.workflow_def = workflow_definition
        self.tasks = self.workflow_def.get("tasks", [])
        self.error_workflow = self.workflow_def.get("on_error_workflow")
        self._client = http_client or httpx.AsyncClient()
        self.jinja_env = Environment(autoescape=False)

        # Built-ins (lookup must be case-insensitive)
        self.task_handlers: Dict[str, Callable] = {
            "http_request": self._handle_http_request,
            "data_transform": self._handle_data_transform,
            "log_message": self._handle_log_message,
        }

        # Custom handlers, case-insensitive registration
        self.custom_handlers = custom_handlers or {}
        for k, v in self.custom_handlers.items():
            self.task_handlers[k.lower()] = v

    async def execute(self, initial_state: dict) -> dict:
        """Runs tasks in order, returns final shared_state or raises WorkflowFailedError."""
        shared_state = dict(initial_state)

        try:
            await self._run_tasks(shared_state, self.tasks)
            return shared_state
        except TaskFailedError as e:
            # On main failure, populate error and attempt on_error_workflow
            if self.error_workflow:
                log.warning("Main workflow failed at task '%s'. Triggering on_error_workflow.", e.task_id)
                shared_state["error"] = {"task_id": e.task_id, "reason": str(e)}
                try:
                    await self._run_tasks(shared_state, self.error_workflow)
                    return shared_state
                except Exception:
                    # Exact message required by spec
                    raise WorkflowFailedError("Error workflow failed")
            # No error workflow: bubble as WorkflowFailedError with the precise message text
            raise WorkflowFailedError(str(e))

    async def _run_tasks(self, shared_state: dict, tasks: list[dict]) -> None:
        for task in tasks:
            await self._process_task_with_retry(task, shared_state)


    # Helpers / sandbox / write


    def _safe_eval(self, expression: str, context: dict):
        """Evaluate in a strict sandbox."""
        safe_builtins = {
            "True": True,
            "False": False,
            "None": None,
            "str": str,
            "int": int,
            "float": float,
            "len": len,
            "list": list,
            "dict": dict,
        }
        return eval(expression, {"__builtins__": safe_builtins}, context)

    def _format_string(self, s: str, state: dict) -> str:
        """Render Jinja2 string with direct access to shared_state keys and a shared_state var."""
        tpl = self.jinja_env.from_string(s)
        return tpl.render(shared_state=state, **state)

    def _set_nested_value(self, d: dict, path: str, value: Any):
        """
        path is a string expression referencing shared_state, e.g.,
        "shared_state['user']['profile']['email']".
        """
        keys = re.findall(r"\['(.*?)'\]", path)
        if not path.startswith("shared_state") or not keys:
            raise ValueError("Invalid target path")
        cur = d
        for k in keys[:-1]:
            nxt = cur.get(k)
            if nxt is None:
                nxt = {}
                cur[k] = nxt
            elif not isinstance(nxt, dict):
                raise ValueError("Intermediate path is not a dict")
            cur = nxt
        cur[keys[-1]] = value


    # Core task processing


    async def _process_task_with_retry(self, task: dict, state: dict) -> None:
        task_id = task.get("task_id", "untitled")
        ttype = (task.get("type") or "").lower()

        # run_if evaluation
        run_if_expr = task.get("run_if")
        if run_if_expr is not None:
            try:
                should_run = self._safe_eval(run_if_expr, {"shared_state": state})
            except Exception as e:
                # exact message required by spec
                raise TaskFailedError("Failed to evaluate 'run_if' expression", task_id, e)
            if not should_run:
                # Skip silently; do not modify state
                return

        # Retry config (defaults must be exact)
        retry = task.get("retry") or {}
        max_attempts = int(retry.get("max_attempts", 1))
        delay_seconds = float(retry.get("delay_seconds", 1.0))
        backoff_multiplier = float(retry.get("backoff_multiplier", 1.0))
        on_exc_names = set(retry.get("on_exceptions", []) or [])
        on_status_codes = set(retry.get("on_status_codes", []) or [])

        attempt = 1
        while True:
            try:
                # Dispatch
                handler = self.task_handlers.get(ttype)
                if handler is None or not callable(handler):
                    raise TaskFailedError(f"Unknown or invalid task type: '{task.get('type')}'", task_id)

                await self._execute_single(handler, ttype, task, state)

                # If it's an http_request and status is still in retry list, handle retry/final fail
                if ttype == "http_request" and on_status_codes:
                    status = int(state.get("response", {}).get("status_code", 0))
                    if status in on_status_codes:
                        if attempt < max_attempts:
                            delay = delay_seconds * (backoff_multiplier ** (attempt - 1))
                            # WARNING with one decimal place; do NOT actually sleep (determinism)
                            log.warning(
                                "Retrying in %.1f seconds... (Attempt %d of %d)",
                                delay,
                                attempt,
                                max_attempts,
                            )
                            attempt += 1
                            continue
                        # Final attempt still bad: permanent failure
                        raise TaskFailedError(self._fail_msg(task_id, attempt), task_id)

                # Success
                return

            except TaskFailedError:
                # Propagate permanent failure for the task
                raise
            except WorkflowFailedError:
                # *** IMPORTANT FIX ***
                # data_transform (and only it) must raise WorkflowFailedError IMMEDIATELY with exact text.
                # Do NOT wrap or retry.
                raise
            except Exception as e:
                # Retryable by exception name?
                if e.__class__.__name__ in on_exc_names and attempt < max_attempts:
                    delay = delay_seconds * (backoff_multiplier ** (attempt - 1))
                    log.warning(
                        "Retrying in %.1f seconds... (Attempt %d of %d)",
                        delay,
                        attempt,
                        max_attempts,
                    )
                    attempt += 1
                    # No actual sleep to keep runs deterministic
                    continue
                # Permanent failure for this task
                raise TaskFailedError(self._fail_msg(task_id, attempt), task_id, e)

    def _fail_msg(self, task_id: str, attempt: int) -> str:
        return (
            f"Task {task_id} failed after 1 attempt"
            if attempt == 1
            else f"Task {task_id} failed after {attempt} attempts"
        )

    async def _execute_single(self, handler: Callable, ttype: str, task: dict, state: dict) -> None:
        params = task.get("params", {})
        # Special-case data_transform per spec: must raise WorkflowFailedError on any expression/target error
        if ttype == "data_transform":
            try:
                await self._handle_data_transform(state, params)
            except WorkflowFailedError:
                raise
            except Exception:
                # Enforce exact message and type
                raise WorkflowFailedError("Failed to execute 'data_transform'")
            return

        # Built-in or custom
        result_state = await handler(state, params)
        if result_state is not state:
            # Handlers should mutate state in-place; but if they returned a new dict, adopt it.
            state.clear()
            state.update(result_state)


    # Handlers


    async def _handle_http_request(self, state: dict, params: dict) -> dict:
        method = params.get("method", "GET")
        url = params.get("url") or ""
        url = self._format_string(url, state)

        req_kwargs = {}
        if "params" in params:
            req_kwargs["params"] = params["params"]
        if "headers" in params:
            req_kwargs["headers"] = params["headers"]
        if "json" in params:
            req_kwargs["json"] = params["json"]

        resp = await self._client.request(method, url, **req_kwargs)

        # Deterministic lowercase, sorted header insertion order
        headers_sorted: dict[str, str] = {}
        for k, v in sorted(resp.headers.items(), key=lambda kv: kv[0].lower()):
            headers_sorted[k.lower()] = v

        # Body without raise_for_status
        content_type = resp.headers.get("Content-Type", "")
        try:
            body = resp.json() if "application/json" in content_type else (resp.text or "")
        except Exception:
            body = resp.text or ""

        state["response"] = {
            "status_code": int(resp.status_code),
            "headers": headers_sorted,
            "body": body,
        }
        return state

    async def _handle_data_transform(self, state: dict, params: dict) -> dict:
        # Evaluate source in sandbox
        src = self._safe_eval(params["source"], {"shared_state": state})
        # expression optional
        if "expression" in params and params["expression"] is not None:
            res = self._safe_eval(params["expression"], {"source": src})
        else:
            res = src

        target = params.get("target", "")
        if not isinstance(target, str) or not target.startswith("shared_state"):
            # Must raise WorkflowFailedError with exact message
            raise WorkflowFailedError("Failed to execute 'data_transform'")

        # Nested write; create dicts as needed
        try:
            self._set_nested_value(state, target, res)
        except Exception:
            # Exact message, exact type
            raise WorkflowFailedError("Failed to execute 'data_transform'")

        return state

    async def _handle_log_message(self, state: dict, params: dict) -> dict:
        level = (params.get("level") or "info").lower()
        lvl = {"info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}.get(level, logging.INFO)
        msg_tpl = params.get("message", "")
        msg = self._format_string(msg_tpl, state)
        log.log(lvl, msg)
        return state



# CLI


def _dump_compact(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"), ensure_ascii=True)


def _build_mock_client() -> httpx.AsyncClient:
    """
    Deterministic offline client:
      - GET /404 → 404
      - GET /status503_then_ok → first 503, second 200
      - GET /exc_then_ok → first raises ConnectError, second 200 with {"status":"ok"}
      - GET /log → 200
      - GET /customers/<id> → 200 with JSON including the id
      - Otherwise → 200 with stable default JSON
    """
    counters = {"status503_then_ok": 0, "exc_then_ok": 0}

    async def handler(request: httpx.Request):
        path = request.url.path or "/"

        if path.endswith("/404"):
            return httpx.Response(404, json={"error": "NotFound"})
        if path.endswith("/status503_then_ok"):
            counters["status503_then_ok"] += 1
            if counters["status503_then_ok"] == 1:
                return httpx.Response(503, json={"error": "Service Unavailable"})
            return httpx.Response(200, json={"status": "ok"})
        if path.endswith("/exc_then_ok"):
            counters["exc_then_ok"] += 1
            if counters["exc_then_ok"] == 1:
                raise httpx.ConnectError("simulated")
            return httpx.Response(200, json={"status": "ok"})
        if path.endswith("/log"):
            return httpx.Response(200, json={"logged": True})
        if "/customers/" in path:
            cust_id = path.rsplit("/", 1)[-1]
            return httpx.Response(200, json={"status": "ok", "id": cust_id})

        return httpx.Response(200, json={"status": "ok"})

    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


async def _cli_run(argv: list[str]) -> None:
    # usage: python workflow_engine.py run <workflow_json_path> [--state '<json>'] [--log-level <level>]
    if len(argv) < 3 or argv[1] != "run":
        print("Usage: python workflow_engine.py run <workflow_json_path> [--state '<json>'] [--log-level <level>']")
        raise SystemExit(1)

    wf_path = argv[2]
    state: dict = {}
    log_level = "WARNING"

    i = 3
    while i < len(argv):
        tok = argv[i]
        if tok == "--state" and i + 1 < len(argv):
            state = json.loads(argv[i + 1])
            i += 2
            continue
        if tok == "--log-level" and i + 1 < len(argv):
            log_level = argv[i + 1].upper()
            i += 2
            continue
        i += 1

    logging.basicConfig(
        level=getattr(logging, log_level, logging.WARNING),
        format="%(levelname)s:%(name)s:%(message)s",
    )

    try:
        with open(wf_path, "r", encoding="utf-8") as f:
            wf = json.load(f)

        client = _build_mock_client()
        try:
            engine = WorkflowEngine(wf, http_client=client)
            final_state = await engine.execute(state)
            print(_dump_compact({"ok": True, "shared_state": final_state}))
            raise SystemExit(0)
        finally:
            await client.aclose()

    except WorkflowFailedError as e:
        print(_dump_compact({"ok": False, "error": str(e)}))
        raise SystemExit(3)


def main():
    asyncio.run(_cli_run(sys.argv))


if __name__ == "__main__":
    main()
EOF

# Produce the 12 required build outputs using the workflows under /app/workflows

# 1
python3 /app/workflow_engine.py run /app/workflows/wf_ok.json --state '{"customer_id":"cust-123"}' > /app/_cli_ok.json
# 2
python3 /app/workflow_engine.py run /app/workflows/wf_404.json > /app/_cli_404.json
# 3
python3 /app/workflow_engine.py run /app/workflows/wf_retry_status.json > /app/_cli_retry_status.json
# 4
python3 /app/workflow_engine.py run /app/workflows/wf_retry_exception.json > /app/_cli_retry_exception.json
# 5
python3 /app/workflow_engine.py run /app/workflows/wf_transform.json > /app/_cli_transform.json
# 6
python3 /app/workflow_engine.py run /app/workflows/wf_nested.json > /app/_cli_nested.json
# 7
python3 /app/workflow_engine.py run /app/workflows/wf_log.json --state '{"user_id":42,"status":"active"}' > /app/_cli_log.txt
# 8
python3 /app/workflow_engine.py run /app/workflows/wf_skip.json > /app/_cli_skip.json
# 9
python3 /app/workflow_engine.py run /app/workflows/wf_error_path.json > /app/_cli_error_workflow.json
# 10 capture exit code on bad run_if
sh -c 'python3 /app/workflow_engine.py run /app/workflows/wf_bad_runif.json ; echo $? > /app/_cli_runif_syntax_error.txt'
# 11 headers type check derived from ok json
python3 -c "import json;print(type(json.load(open('/app/_cli_ok.json'))['shared_state']['response']['headers']).__name__)" > /app/_cli_headers.txt
# 12 status code line from 404
python3 -c "import json;print(json.load(open('/app/_cli_404.json'))['shared_state']['response']['status_code'])" > /app/_cli_status_code.txt