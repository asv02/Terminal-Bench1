# This is a template test file. Each of these functions will be called
# by the test harness to evaluate the final state of the terminal

import sys
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

import json
from pathlib import Path

import pytest
import httpx
import logging
import subprocess

from workflow_engine import WorkflowEngine, WorkflowFailedError


BASE = Path("/app")


def _read(path: Path | str) -> str:
    """Read a file and return its trimmed UTF-8 text contents."""
    p = Path(path)
    return p.read_text(encoding="utf-8").strip()


def _read_json(path: Path | str):
    """Load JSON from a file path (using _read for strict trimming)."""
    return json.loads(_read(path))


def test_cli_artifacts_exist_and_contents_minimal():
    """All required CLI artifacts exist in /app and are non-empty."""
    base = BASE
    files = [
        "_cli_ok.json",
        "_cli_404.json",
        "_cli_retry_status.json",
        "_cli_retry_exception.json",
        "_cli_transform.json",
        "_cli_nested.json",
        "_cli_log.txt",
        "_cli_skip.json",
        "_cli_error_workflow.json",
        "_cli_runif_syntax_error.txt",
        "_cli_headers.txt",
        "_cli_status_code.txt",
    ]
    for name in files:
        p = base / name
        assert p.exists(), f"missing artifact {p}"
        assert p.stat().st_size > 0, f"artifact {p} is empty"


def test_cli_ok_json_compact_and_status_200():
    """ok.json: compact JSON (no spaces around separators; string values may contain spaces) and status_code == 200."""
    p = BASE / "_cli_ok.json"
    data = _read_json(p)
    raw = _read(p)
    assert data.get("ok") is True
    canonical = json.dumps(data, separators=(",", ":"), ensure_ascii=True)
    assert raw == canonical
    assert data["shared_state"]["response"]["status_code"] == 200


def test_cli_404_json_compact_and_status_404():
    """404.json: compact JSON (no spaces except within string values) and status_code == 404."""
    p = BASE / "_cli_404.json"
    data = _read_json(p)
    raw = _read(p)
    assert data.get("ok") is True
    # NB: Compact JSON ensures no spaces inserted by the serializer.
    # String values may contain spaces legitimately (e.g., "Not Found").
    assert "{" in raw and "}" in raw and ":" in raw and "," in raw
    assert data["shared_state"]["response"]["status_code"] == 404


def test_cli_retry_status_has_int_status_code():
    """retry_status.json: ok true and an integer status_code in shared_state.response."""
    p = BASE / "_cli_retry_status.json"
    data = _read_json(p)
    assert data.get("ok") is True
    assert isinstance(data["shared_state"]["response"]["status_code"], int)


def test_cli_retry_exception_status_ok():
    """retry_exception.json: final body.status is 'ok' after retry on exception."""
    p = BASE / "_cli_retry_exception.json"
    data = _read_json(p)
    assert data.get("ok") is True
    assert data["shared_state"]["response"]["body"].get("status") == "ok"


def test_cli_transform_values_present():
    """transform.json: arr is the trimmed literal and msg is 'HELLO WORLD'."""
    p = BASE / "_cli_transform.json"
    data = _read_json(p)
    assert data.get("ok") is True
    st = data["shared_state"]
    assert st.get("arr") == "[1,2,3]"
    assert st.get("msg") == "HELLO WORLD"


def test_cli_nested_email_written():
    """nested.json: ensures deep dict creation and value assignment for email."""
    p = BASE / "_cli_nested.json"
    data = _read_json(p)
    assert data.get("ok") is True
    assert data["shared_state"]["user"]["profile"]["email"] == "a@b.com"


def test_cli_log_compact_json_output():
    """log.txt: contains compact JSON with ok true (stdout redirected to file)."""
    p = BASE / "_cli_log.txt"
    raw = _read(p)
    data = json.loads(raw)
    assert data.get("ok") is True
    assert " " not in raw


def test_cli_skip_did_not_write_never_key():
    """skip.json: run_if False prevents writing the 'never' key."""
    p = BASE / "_cli_skip.json"
    data = _read_json(p)
    assert data.get("ok") is True
    assert "never" not in data["shared_state"]


def test_cli_error_workflow_recovered_flag():
    """error_workflow.json: on_error_workflow sets 'error_handled' flag and returns ok true."""
    p = BASE / "_cli_error_workflow.json"
    data = _read_json(p)
    assert data.get("ok") is True
    assert data["shared_state"].get("error_handled") is True


def test_cli_runif_syntax_error_exit_code_is_3():
    """_cli_runif_syntax_error.txt: captured exit code must be 3 for run_if syntax errors."""
    p = BASE / "_cli_runif_syntax_error.txt"
    exit_code_line = _read(p)
    assert exit_code_line == "3"


def test_cli_headers_type_is_dict():
    """_cli_headers.txt: printed Python typename for headers is 'dict'."""
    p = BASE / "_cli_headers.txt"
    headers_type = _read(p)
    assert headers_type == "dict"


def test_cli_status_code_file_is_404():
    """_cli_status_code.txt: line equals '404' extracted from 404 output JSON."""
    p = BASE / "_cli_status_code.txt"
    status_code_line = _read(p)
    assert status_code_line == "404"

def test_cli_accepts_log_level_option():
    """CLI parses --log-level (not graded for behavior, just acceptance)."""
    cmd = [
        "python", "/app/workflow_engine.py", "run",
        "/app/workflows/wf_ok.json",
        "--state", '{"customer_id":"cust-123"}',
        "--log-level", "ERROR",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    out = res.stdout.strip()
    assert " " not in out  # still compact
    data = json.loads(out)
    assert data.get("ok") is True

def test_cli_retry_logs_to_stderr_only():
    """Retry WARNING lines must be emitted to stderr; stdout stays compact JSON only."""
    cmd = ["python", "/app/workflow_engine.py", "run", "/app/workflows/wf_retry_status.json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    # WARNING retry lines must not pollute stdout JSON
    assert "Retrying in" not in res.stdout
    # They must appear on stderr
    assert "Retrying in" in res.stderr
    # stdout remains compact JSON
    out = res.stdout.strip()
    assert " " not in out
    data = json.loads(out)
    assert data.get("ok") is True


@pytest.mark.asyncio
async def test_http_request_get_with_headers_and_params():
    """http_request GET: passes query params + headers through and captures JSON + headers."""
    async def mock_verify_request(request: httpx.Request):
        assert request.url.query == b"query=test&limit=10"
        assert request.headers["x-custom-header"] == "my-value"
        return httpx.Response(200, json={"verified": True}, headers={"X-Request-ID": "abc-123"})

    transport = httpx.MockTransport(mock_verify_request)
    client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "tasks": [
            {
                "task_id": "http_with_extras",
                "type": "http_request",
                "params": {
                    "method": "GET",
                    "url": "https://api.test/search",
                    "params": {"query": "test", "limit": 10},
                    "headers": {"x-custom-header": "my-value"},
                },
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=client)
    state = await engine.execute({})
    assert state["response"]["status_code"] == 200
    assert state["response"]["body"]["verified"] is True
    assert "headers" in state["response"]
    assert state["response"]["headers"]["x-request-id"] == "abc-123"
    await client.aclose()


@pytest.mark.asyncio
async def test_http_request_post_with_json():
    """http_request POST: forwards JSON body and captures 201 + response JSON."""
    payload = {"name": "workflow-engine", "version": "1.0"}

    async def mock_post_response(request: httpx.Request):
        assert request.method == "POST"
        assert json.loads(await request.aread()) == payload
        return httpx.Response(201, json={"status": "created", "id": 123})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_post_response))
    workflow_def = {
        "tasks": [
            {
                "task_id": "create_item",
                "type": "http_request",
                "params": {"method": "POST", "url": "https://api.example.com/items", "json": payload},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    final_state = await engine.execute({})
    assert final_state["response"]["status_code"] == 201
    assert final_state["response"]["body"]["id"] == 123
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_case_insensitive_task_type_lookup():
    """Task type lookup must be case-insensitive for built-in handlers."""
    async def mock_success_response(request: httpx.Request):
        return httpx.Response(200, json={"success": True})

    transport = httpx.MockTransport(mock_success_response)
    client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "tasks": [
            {
                "task_id": "case_test",
                "type": "hTtp_ReQuest",
                "params": {"method": "GET", "url": "https://api.test/test"},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=client)
    final_state = await engine.execute({})
    assert final_state["response"]["status_code"] == 200
    assert final_state["response"]["body"]["success"] is True
    await client.aclose()


@pytest.mark.asyncio
async def test_data_transform_handler():
    """data_transform with expression writes transformed value to shared_state."""
    workflow_def = {
        "tasks": [
            {
                "task_id": "transform_data",
                "type": "data_transform",
                "params": {"source": "'hello'", "target": "shared_state['greeting']", "expression": "source.upper() + ' WORLD'"},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def)
    final_state = await engine.execute({})
    assert final_state["greeting"] == "HELLO WORLD"


@pytest.mark.asyncio
async def test_data_transform_no_expression():
    """data_transform without expression writes the evaluated source value."""
    initial_state = {"user_id": 101}
    workflow_def = {
        "tasks": [
            {
                "task_id": "fetch_id",
                "type": "data_transform",
                "params": {"source": "shared_state['user_id']", "target": "shared_state['new_id']"},
            },
            {
                "task_id": "set_list",
                "type": "data_transform",
                "params": {"source": "[1, 2, 3]", "target": "shared_state['my_list']"},
            },
        ]
    }
    engine = WorkflowEngine(workflow_def)
    final_state = await engine.execute(initial_state)
    assert final_state.get("new_id") == 101
    assert final_state.get("my_list") == [1, 2, 3]


@pytest.mark.asyncio
async def test_data_transform_with_nested_target():
    """data_transform supports nested writes and creates intermediate dicts."""
    workflow_def = {
        "tasks": [
            {
                "task_id": "set_nested_email",
                "type": "data_transform",
                "params": {"source": "'test@example.com'", "target": "shared_state['user']['profile']['email']"},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def)
    final_state = await engine.execute({})
    assert final_state["user"]["profile"]["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_custom_handler_execution():
    """Custom async handler can be injected and executed."""
    async def custom_task_handler(state, params):
        state["custom_ran"] = True
        return state

    engine = WorkflowEngine({"tasks": [{"task_id": "custom_1", "type": "custom"}]}, custom_handlers={"custom": custom_task_handler})
    final_state = await engine.execute({})
    assert final_state.get("custom_ran") is True


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "log_level_str, log_level_const",
    [("info", logging.INFO), ("warning", logging.WARNING), ("error", logging.ERROR)],
)
async def test_log_message_with_state_variables_and_levels(caplog, log_level_str, log_level_const):
    """log_message renders Jinja2 templates and respects the requested log level."""
    workflow_def = {
        "tasks": [
            {
                "task_id": "log_user_status",
                "type": "log_message",
                "params": {"level": log_level_str, "message": "User {{ user_id }} has status {{ status }}."},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def)
    initial_state = {"user_id": 42, "status": "active"}
    with caplog.at_level(logging.INFO):
        await engine.execute(initial_state)

    assert "User 42 has status active." in caplog.text
    assert caplog.records[0].levelno == log_level_const


@pytest.mark.asyncio
async def test_run_if_condition_false_skips_task():
    """run_if False prevents handler execution and avoids writing target key."""
    workflow_def = {
        "tasks": [
            {
                "task_id": "skipped_task",
                "type": "data_transform",
                "run_if": "False",
                "params": {"source": "'should not run'", "target": "shared_state['result']"},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def)
    final_state = await engine.execute({})
    assert "result" not in final_state


@pytest.mark.asyncio
async def test_complex_workflow_with_conditional_dependency():
    """Subsequent task gated by prior http_request result via run_if."""
    async def mock_status_response(request: httpx.Request):
        return httpx.Response(200, json={"status": "processed"})

    transport = httpx.MockTransport(mock_status_response)
    client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "tasks": [
            {"task_id": "check_status", "type": "http_request", "params": {"method": "GET", "url": "https://api.test/status"}},
            {
                "task_id": "process_if_ok",
                "type": "data_transform",
                "run_if": "shared_state['response']['body']['status'] == 'processed'",
                "params": {"source": "True", "target": "shared_state['was_processed']"},
            },
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=client)
    final_state = await engine.execute({})
    assert final_state.get("was_processed") is True
    await client.aclose()


@pytest.mark.asyncio
async def test_workflow_handles_non_2xx_response():
    """Non-2xx response should be stored; conditional transform can react to status_code."""
    async def mock_404_response(request: httpx.Request):
        return httpx.Response(404, json={"error": "Not Found"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_404_response))
    workflow_def = {
        "tasks": [
            {"task_id": "fetch_missing_item", "type": "http_request", "params": {"method": "GET", "url": "https://api.example.com/items/999"}},
            {
                "task_id": "handle_not_found",
                "type": "data_transform",
                "run_if": "shared_state['response']['status_code'] == 404",
                "params": {"source": "'Item was not found'", "target": "shared_state['error_message']"},
            },
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    final_state = await engine.execute({})
    assert final_state["response"]["status_code"] == 404
    assert final_state.get("error_message") == "Item was not found"
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_retry_succeeds_on_second_attempt():
    """Retry on exception: succeeds on the second attempt and returns 200."""
    class FlakyTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.call_count = 0

        async def handle_async_request(self, request: httpx.Request):
            self.call_count += 1
            if self.call_count == 1:
                raise httpx.ConnectError("Simulated connection failure")
            return httpx.Response(200, json={"status": "ok"})

    mock_client = httpx.AsyncClient(transport=FlakyTransport())
    workflow_def = {
        "tasks": [
            {
                "task_id": "flaky_service_call",
                "type": "http_request",
                "params": {"method": "GET", "url": "https://flaky.service.com"},
                "retry": {"max_attempts": 2, "delay_seconds": 0.01, "on_exceptions": ["ConnectError"]},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    final_state = await engine.execute({})
    assert final_state["response"]["status_code"] == 200
    assert final_state["response"]["body"]["status"] == "ok"
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_retry_on_specific_status_code(caplog):
    """Retry on specific status code: 503 -> retry -> 200; logs match required format."""
    class ServiceUnavailableTransport(httpx.AsyncBaseTransport):
        def __init__(self):
            self.call_count = 0

        async def handle_async_request(self, request: httpx.Request):
            self.call_count += 1
            if self.call_count == 1:
                return httpx.Response(503, json={"error": "Service Unavailable"})
            return httpx.Response(200, json={"status": "ok"})

    transport = ServiceUnavailableTransport()
    mock_client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "tasks": [
            {
                "task_id": "status_code_retry",
                "type": "http_request",
                "params": {"method": "GET", "url": "https://api.test/status"},
                "retry": {"max_attempts": 2, "delay_seconds": 0.01, "on_status_codes": [503]},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    with caplog.at_level(logging.WARNING):
        final_state = await engine.execute({})

    assert transport.call_count == 2
    assert "Retrying" in caplog.text
    assert final_state["response"]["status_code"] == 200
    assert final_state["response"]["body"]["status"] == "ok"
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_retry_delay_increases_with_backoff_multiplier(caplog):
    """Backoff multiplier increases the retry delay deterministically and logs reflect it."""
    async def failing_response(request):
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(failing_response)
    client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "tasks": [
            {
                "task_id": "test_backoff",
                "type": "http_request",
                "params": {"url": "https://backoff.test"},
                "retry": {"max_attempts": 3, "delay_seconds": 0.1, "backoff_multiplier": 2, "on_exceptions": ["ConnectError"]},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=client)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(WorkflowFailedError, match="Task test_backoff failed after 3 attempts"):
            await engine.execute({})

    log_text = caplog.text
    assert "Retrying in 0.1 seconds... (Attempt 1 of 3)" in log_text
    assert "Retrying in 0.2 seconds... (Attempt 2 of 3)" in log_text
    await client.aclose()


@pytest.mark.asyncio
async def test_immediate_failure_on_unlisted_exception():
    """Exceptions not listed in on_exceptions cause immediate failure with attempt=1 message."""
    async def mock_timeout_response(request: httpx.Request):
        raise httpx.ReadTimeout("Simulated read timeout")

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_timeout_response))
    workflow_def = {
        "tasks": [
            {
                "task_id": "service_call",
                "type": "http_request",
                "params": {"method": "GET", "url": "https://api.example.com"},
                "retry": {"max_attempts": 3, "delay_seconds": 0.01, "on_exceptions": ["ConnectError"]},
            }
        ]
    }
    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    with pytest.raises(WorkflowFailedError, match="Task service_call failed after 1 attempt"):
        await engine.execute({})
    await mock_client.aclose()


@pytest.mark.asyncio
async def test_invalid_expression_in_run_if_fails_workflow():
    """Invalid run_if expression produces the exact required WorkflowFailedError message."""
    workflow_def = {"tasks": [{"task_id": "bad_run_if", "type": "log_message", "run_if": "shared_state['x'] =="}]}
    engine = WorkflowEngine(workflow_def)
    with pytest.raises(WorkflowFailedError, match="Failed to evaluate 'run_if' expression"):
        await engine.execute({})


@pytest.mark.asyncio
async def test_on_error_workflow_is_triggered():
    """on_error_workflow runs on main failure and can set recovery flags in shared_state."""
    async def failing_response(request):
        raise httpx.ConnectError("Connection failed")

    transport = httpx.MockTransport(failing_response)
    client = httpx.AsyncClient(transport=transport)
    workflow_def = {
        "on_error_workflow": [
            {
                "task_id": "handle_error",
                "type": "data_transform",
                "params": {
                    "source": "shared_state['error']",
                    "target": "shared_state['error_handled']",
                    "expression": "source['task_id'] == 'failing_task'",
                },
            }
        ],
        "tasks": [{"task_id": "failing_task", "type": "http_request", "params": {"url": "https://broken.service"}}],
    }
    engine = WorkflowEngine(workflow_def, http_client=client)
    final_state = await engine.execute({})
    assert final_state.get("error_handled") is True
    await client.aclose()


@pytest.mark.asyncio
async def test_http_request_with_jinja2_url_templating():
    """Jinja2 URL templating has access to shared_state keys and renders correctly."""
    initial_state = {"customer_id": "cust-123"}
    expected_url = "https://api.test/customers/cust-123"

    async def mock_verify_url(request: httpx.Request):
        assert str(request.url) == expected_url
        return httpx.Response(200, json={"status": "ok"})

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(mock_verify_url))

    workflow_def = {
        "tasks": [
            {
                "task_id": "fetch_customer_by_id",
                "type": "http_request",
                "params": {"method": "GET", "url": "https://api.test/customers/{{ customer_id }}"},
            }
        ]
    }

    engine = WorkflowEngine(workflow_def, http_client=mock_client)
    final_state = await engine.execute(initial_state)

    assert final_state["response"]["status_code"] == 200
    await mock_client.aclose()

@pytest.mark.asyncio
async def test_run_if_prohibits_unsafe_builtins_open():
    """Sandboxing: run_if cannot access unsafe builtins like open()."""
    wf = {
        "tasks": [
            {"task_id": "unsafe", "type": "log_message",
             "run_if": "open('/etc/passwd')",  # should be blocked by sandbox
             "params": {"level": "info", "message": "should not run"}}
        ]
    }
    engine = WorkflowEngine(wf)
    with pytest.raises(WorkflowFailedError, match="Failed to evaluate 'run_if' expression"):
        await engine.execute({})


@pytest.mark.asyncio
async def test_data_transform_prohibits_import_escapes():
    """Sandboxing: data_transform cannot use __import__ to escape."""
    wf = {
        "tasks": [
            {"task_id": "escape_attempt", "type": "data_transform",
             "params": {
                 "source": "__import__('os').getcwd()",  # __import__ not present in safe builtins
                 "target": "shared_state['cwd']"
             }}
        ]
    }
    engine = WorkflowEngine(wf)
    with pytest.raises(WorkflowFailedError) as exc:
        await engine.execute({})
    assert str(exc.value) == "Failed to execute 'data_transform'"


@pytest.mark.asyncio
async def test_data_transform_target_must_reference_shared_state():
    """data_transform: target must start with 'shared_state' (plain keys invalid)."""
    wf = {
        "tasks": [
            {"task_id": "bad_target", "type": "data_transform",
             "params": {"source": "'value'", "target": "not_shared"}}
        ]
    }
    engine = WorkflowEngine(wf)
    with pytest.raises(WorkflowFailedError) as exc:
        await engine.execute({})
    assert str(exc.value) == "Failed to execute 'data_transform'"


@pytest.mark.asyncio
async def test_custom_handler_must_be_async_only():
    """Custom handlers must be async; providing a sync handler should fail."""
    def sync_handler(state, params):  # intentionally non-async
        state["ran"] = True
        return state

    wf = {"tasks": [{"task_id": "c", "type": "custom"}]}
    engine = WorkflowEngine(wf, custom_handlers={"custom": sync_handler})
    with pytest.raises(WorkflowFailedError, match=r"Task c failed after 1 attempt"):
        await engine.execute({})


@pytest.mark.asyncio
async def test_engine_uses_injected_http_client_only():
    """HTTP request must go through the injected AsyncClient (no self-created clients)."""
    calls = {"count": 0}

    async def recorder(req: httpx.Request):
        calls["count"] += 1
        assert str(req.url) == "https://only.injected/client"
        return httpx.Response(200, json={"ok": True})

    injected = httpx.AsyncClient(transport=httpx.MockTransport(recorder))
    wf = {
        "tasks": [
            {"task_id": "hit", "type": "http_request",
             "params": {"method": "GET", "url": "https://only.injected/client"}}
        ]
    }
    engine = WorkflowEngine(wf, http_client=injected)
    st = await engine.execute({})
    await injected.aclose()

    assert calls["count"] == 1
    assert st["response"]["status_code"] == 200
    assert st["response"]["body"]["ok"] is True


@pytest.mark.asyncio
async def test_http_request_does_not_raise_for_status():
    """http_request must never call raise_for_status(); 418 should be stored, not raised."""
    async def teapot(req: httpx.Request):
        return httpx.Response(418, json={"msg": "teapot"})

    client = httpx.AsyncClient(transport=httpx.MockTransport(teapot))
    wf = {
        "tasks": [
            {"task_id": "teapot", "type": "http_request",
             "params": {"method": "GET", "url": "https://tea.pot"}}]
    }
    engine = WorkflowEngine(wf, http_client=client)
    st = await engine.execute({})
    await client.aclose()

    assert st["response"]["status_code"] == 418
    assert st["response"]["body"]["msg"] == "teapot"

@pytest.mark.asyncio
async def test_log_message_invalid_level_defaults_to_info(caplog):
    """log_message: invalid 'level' falls back to INFO and still renders message."""
    wf = {
        "tasks": [
            {
                "task_id": "say",
                "type": "log_message",
                "params": {"level": "verbose", "message": "Hello {{ name }}!"},  # invalid level
            }
        ]
    }
    engine = WorkflowEngine(wf)
    with caplog.at_level(logging.INFO):
        await engine.execute({"name": "World"})
    # Should have logged at INFO level
    assert any("Hello World!" in rec.message and rec.levelno == logging.INFO for rec in caplog.records)


@pytest.mark.asyncio
async def test_custom_handler_lookup_is_case_insensitive():
    """Custom handlers: registration and lookup are case-insensitive."""
    async def my_handler(state, params):
        state["ran_custom"] = True
        return state

    # Register with unusual casing, call with different casing
    wf = {"tasks": [{"task_id": "c1", "type": "mYTaSk"}]}
    engine = WorkflowEngine(wf, custom_handlers={"MyTask": my_handler})
    final_state = await engine.execute({})
    assert final_state.get("ran_custom") is True


@pytest.mark.asyncio
async def test_retry_defaults_delay_and_backoff(caplog):
    """Retry defaults: delay_seconds=1.0 and backoff_multiplier=1.0 when omitted."""
    call_count = {"n": 0}

    async def flaky(req: httpx.Request):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.ConnectError("boom")
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(flaky))
    wf = {
        "tasks": [
            {
                "task_id": "r",
                "type": "http_request",
                "params": {"url": "https://retry.defaults"},
                # Provide only max_attempts + on_exceptions; omit delay/backoff to use defaults
                "retry": {"max_attempts": 2, "on_exceptions": ["ConnectError"]},
            }
        ]
    }
    engine = WorkflowEngine(wf, http_client=client)
    with caplog.at_level(logging.WARNING):
        state = await engine.execute({})
    await client.aclose()

    # Default delay is 1.0 and backoff 1.0 => first retry line should show 1.0 seconds
    assert "Retrying in 1.0 seconds... (Attempt 1 of 2)" in caplog.text
    assert state["response"]["status_code"] == 200
    assert state["response"]["body"]["ok"] is True


@pytest.mark.asyncio
async def test_no_retry_means_single_attempt_failure():
    """When 'retry' is omitted entirely, failures produce 'after 1 attempt' message."""
    async def always_fail(req: httpx.Request):
        raise httpx.ConnectError("nope")

    client = httpx.AsyncClient(transport=httpx.MockTransport(always_fail))
    wf = {"tasks": [{"task_id": "once", "type": "http_request", "params": {"url": "https://fail.once"}}]}
    engine = WorkflowEngine(wf, http_client=client)
    with pytest.raises(WorkflowFailedError, match=r"Task once failed after 1 attempt"):
        await engine.execute({})
    await client.aclose()

@pytest.mark.asyncio
async def test_cli_success_exit_code_zero_and_compact_output():
    """CLI: successful run returns exit code 0 and prints compact JSON (no spaces)."""
    cmd = [
        "python",
        "/app/workflow_engine.py",
        "run",
        "/app/workflows/wf_ok.json",
        "--state",
        '{"customer_id":"cust-123"}',
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    out = res.stdout.strip()
    # Compact: serializer + strip => no spaces outside string values
    assert " " not in out
    data = json.loads(out)
    assert data.get("ok") is True
    assert data["shared_state"]["response"]["status_code"] == 200


@pytest.mark.asyncio
async def test_on_error_workflow_failure_raises_workflowfailederror():
    """If on_error_workflow itself fails, engine must raise WorkflowFailedError."""
    # Main request will fail once to trigger error workflow.
    async def always_fail(req: httpx.Request):
        raise httpx.ConnectError("boom")

    client = httpx.AsyncClient(transport=httpx.MockTransport(always_fail))

    # Error workflow contains an invalid data_transform target (plain key), which must fail.
    wf = {
        "on_error_workflow": [
            {
                "task_id": "bad_recovery",
                "type": "data_transform",
                "params": {
                    "source": "'x'",
                    "target": "not_shared_state['oops']",  # invalid by spec
                },
            }
        ],
        "tasks": [
            {"task_id": "main", "type": "http_request", "params": {"url": "https://fail.me"}}
        ],
    }

    engine = WorkflowEngine(wf, http_client=client)
    with pytest.raises(WorkflowFailedError) as exc:
        await engine.execute({})
    # Spec requires the exact text when the on_error_workflow itself fails
    assert str(exc.value) == "Error workflow failed"
    await client.aclose()

@pytest.mark.asyncio
async def test_run_if_error_is_non_retryable(caplog):
    """run_if evaluation errors must be permanent (no retries, exact message)."""
    wf = {
        "tasks": [
            {
                "task_id": "x",
                "type": "log_message",
                "run_if": "shared_state['a'] ==",  # syntax error
                "params": {"level": "info", "message": "hello"},
                "retry": {"max_attempts": 3, "delay_seconds": 0.01, "on_exceptions": ["ConnectError"]},
            }
        ]
    }
    engine = WorkflowEngine(wf)
    with caplog.at_level(logging.WARNING):
        with pytest.raises(WorkflowFailedError) as exc:
            await engine.execute({})
    assert str(exc.value) == "Failed to evaluate 'run_if' expression"
    # Ensure no retry log line appeared
    assert "Retrying in" not in caplog.text

@pytest.mark.asyncio
async def test_error_object_present_before_on_error_workflow():
    """shared_state['error'] must be populated before on_error_workflow runs."""
    async def fail_once(req: httpx.Request):
        raise httpx.ConnectError("boom")

    client = httpx.AsyncClient(transport=httpx.MockTransport(fail_once))
    wf = {
        "on_error_workflow": [
            {
                "task_id": "snapshot_error",
                "type": "data_transform",
                "params": {
                    "source": "shared_state['error']",
                    "target": "shared_state['error_snapshot']"
                },
            }
        ],
        "tasks": [
            {"task_id": "broken", "type": "http_request", "params": {"url": "https://fail.example"}}
        ],
    }
    engine = WorkflowEngine(wf, http_client=client)
    state = await engine.execute({})
    await client.aclose()

    err = state.get("error_snapshot")
    assert isinstance(err, dict)
    assert set(err.keys()) >= {"task_id", "reason"}
    assert err["task_id"] == "broken"

@pytest.mark.asyncio
async def test_deterministic_same_input_same_output():
    """Same inputs produce same outputs (helps enforce 'no nondeterminism')."""
    async def responder(req: httpx.Request):
        return httpx.Response(200, json={"fixed": True, "path": str(req.url)})

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    wf = {
        "tasks": [
            {"task_id": "hit", "type": "http_request", "params": {"url": "https://deterministic.test/a"}}
        ]
    }
    engine = WorkflowEngine(wf, http_client=client)
    s1 = await engine.execute({})
    s2 = await engine.execute({})
    await client.aclose()

    assert s1 == s2

@pytest.mark.asyncio
async def test_http_headers_insertion_order_is_sorted_lowercase():
    """Headers dict must be built from sorted(response.headers.items()) and be lowercase."""
    async def jumbled(req: httpx.Request):
        # Intentionally shuffled and mixed-case header names
        return httpx.Response(
            200,
            json={"ok": True},
            headers={"b-B": "2", "A-a": "1", "c-C": "3"},
        )

    client = httpx.AsyncClient(transport=httpx.MockTransport(jumbled))
    wf = {"tasks": [{"task_id": "h", "type": "http_request", "params": {"url": "https://h"}}]}
    st = await WorkflowEngine(wf, http_client=client).execute({})
    await client.aclose()

    headers = st["response"]["headers"]
    # All lowercase
    assert all(k == k.lower() for k in headers.keys())
    # Insertion order must match sorted lowercase keys
    assert list(headers.keys()) == sorted(headers.keys())

@pytest.mark.asyncio
async def test_retry_on_status_code_permanent_failure_after_max_attempts():
    """If status remains in on_status_codes after max attempts, fail with exact message."""
    class Always503(httpx.AsyncBaseTransport):
        def __init__(self): self.n = 0
        async def handle_async_request(self, request: httpx.Request):
            self.n += 1
            return httpx.Response(503, json={"error": "Service Unavailable"})

    client = httpx.AsyncClient(transport=Always503())
    wf = {
        "tasks": [{
            "task_id": "svc",
            "type": "http_request",
            "params": {"method": "GET", "url": "https://svc"},
            "retry": {"max_attempts": 3, "delay_seconds": 0.01, "on_status_codes": [503]},
        }]
    }
    engine = WorkflowEngine(wf, http_client=client)
    with pytest.raises(WorkflowFailedError, match=r"Task svc failed after 3 attempts"):
        await engine.execute({})
    await client.aclose()
