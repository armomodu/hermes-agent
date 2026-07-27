import importlib.util
import json
from pathlib import Path
import sys


PLUGIN_PATH = (
    Path(__file__).resolve().parents[2]
    / "plugins"
    / "observability"
    / "mc_context_efficiency"
    / "__init__.py"
)


def _load_plugin():
    spec = importlib.util.spec_from_file_location("mc_context_efficiency_test", PLUGIN_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_records_complete_content_free_request_breakdown(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))

    plugin.on_pre_api_request(
        session_id="session-1",
        task_id="task-1",
        api_request_id="request-1",
        api_call_count=1,
        model="test-model",
        provider="test-provider",
        approx_input_tokens=100,
        message_count=4,
        tool_count=1,
        request={
            "body": {
                "messages": [
                    {"role": "system", "content": "system guidance"},
                    {"role": "user", "content": "MC Task ID: task-1\nTask Contract: bounded"},
                    {
                        "role": "assistant",
                        "content": "",
                        "tool_calls": [
                            {"function": {"name": "terminal", "arguments": "{\"cmd\":\"pwd\"}"}},
                            {"function": {"name": "terminal", "arguments": "{\"cmd\":\"pwd\"}"}},
                        ],
                    },
                    {"role": "tool", "content": "large output"},
                ],
                "tools": [{"type": "function", "function": {"name": "terminal"}}],
            },
        },
    )

    record = json.loads(output.read_text().strip())
    assert record["version"] == "mc-context-efficiency.v1"
    assert record["categories"]["system"] > 0
    assert record["categories"]["task_context"] > 0
    assert record["categories"]["tool_schemas"] > 0
    assert record["categories"]["tool_results"] > 0
    assert record["repeatedToolCalls"] == 1
    assert "system guidance" not in output.read_text()
    assert "large output" not in output.read_text()


def test_correlates_explicit_mc_task_id_and_classifies_tool_envelope(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    mc_task_id = "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"

    plugin.on_pre_api_request(
        session_id="session-mc",
        task_id="internal-turn-id",
        api_call_count=1,
        request={
            "body": {
                "messages": [
                    {"role": "system", "content": "system guidance"},
                    {
                        "role": "tool",
                        "content": f"MC Task ID: {mc_task_id}\nMC Completion Contract: execution_result",
                    },
                ],
            },
        },
    )
    plugin.on_session_finalize(session_id="session-mc", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert records[0]["categories"]["task_context"] > 0
    assert records[0]["categories"]["tool_results"] == 1
    assert records[-1]["taskIds"] == [mc_task_id, "internal-turn-id"]


def test_telemetry_failure_never_escapes(monkeypatch):
    plugin = _load_plugin()
    monkeypatch.setattr(plugin, "_output_path", lambda: Path("/dev/null/not-writable"))
    plugin.on_pre_api_request(session_id="session-1", request={})
    plugin.on_post_api_request(session_id="session-1", usage={})
    plugin.on_session_finalize(session_id="session-1", reason="done")


def test_session_finalization_reports_cumulative_usage(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))

    plugin.on_pre_api_request(
        session_id="session-2",
        task_id="task-2",
        api_request_id="request-1",
        api_call_count=1,
        approx_input_tokens=120,
        request={"body": {"messages": []}},
    )
    plugin.on_post_api_request(
        session_id="session-2",
        task_id="task-2",
        api_request_id="request-1",
        api_call_count=1,
        api_duration=0.1,
        usage={"input_tokens": 110, "output_tokens": 10, "cache_read_tokens": 40},
    )
    plugin.on_session_finalize(session_id="session-2", reason="kanban_complete")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    final = records[-1]
    assert final["event"] == "session_finalized"
    assert final["apiCallCount"] == 1
    assert final["inputTokens"] == 110
    assert final["outputTokens"] == 10
    assert final["cacheReadTokens"] == 40
    assert final["maxPromptTokens"] == 120
    assert final["taskIds"] == ["task-2"]
    assert final["compactionCount"] == 0
    assert final["guardrails"] == []


def test_shadow_guardrails_flag_cost_without_blocking(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.setenv("HERMES_CONTEXT_MAX_API_CALLS", "1")
    monkeypatch.setenv("HERMES_CONTEXT_MAX_CUMULATIVE_INPUT", "100")

    plugin.on_pre_api_request(
        session_id="session-3",
        task_id="task-3",
        api_request_id="request-1",
        api_call_count=1,
        approx_input_tokens=120,
        request={"body": {"messages": []}},
    )
    plugin.on_post_api_request(
        session_id="session-3",
        usage={"input_tokens": 120},
    )
    plugin.on_session_finalize(session_id="session-3", reason="done")

    final = json.loads(output.read_text().splitlines()[-1])
    assert final["guardrails"] == [
        "api_call_budget_exceeded",
        "cumulative_input_budget_exceeded",
        "cache_utilization_missing",
    ]
