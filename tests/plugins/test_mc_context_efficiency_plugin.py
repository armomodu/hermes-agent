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


def test_correlates_mission_control_bounded_envelope_task_id(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    mc_task_id = "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"

    plugin.on_pre_api_request(
        session_id="session-bounded",
        task_id="internal-turn-id",
        api_call_count=1,
        request={
            "body": {
                "messages": [
                    {
                        "role": "tool",
                        "content": (
                            "Mission Control bounded context candidate (shadow only)\n\n"
                            f"Task ID: {mc_task_id}\n\n"
                            "Objective ID: 749b54d1-52b4-4352-8539-c4a2fc9c7710"
                        ),
                    },
                ],
            },
        },
    )
    plugin.on_session_finalize(session_id="session-bounded", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert records[0]["categories"]["task_context"] > 0
    assert records[-1]["taskIds"] == [mc_task_id, "internal-turn-id"]


def test_correlates_json_wrapped_kanban_task_body(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    mc_task_id = "1e8cf388-89b3-59be-84ba-cab230c1bbca"
    tool_result = json.dumps(
        {
            "task": {
                "id": "t_c688c25a",
                "body": (
                    "Mission Control bounded context candidate (shadow only)\n\n"
                    f"Task ID: {mc_task_id}\n\n"
                    "Completion Contract: execution_result"
                ),
            },
        },
    )

    plugin.on_pre_api_request(
        session_id="session-kanban",
        task_id="internal-turn-id",
        api_call_count=1,
        request={"body": {"messages": [{"role": "tool", "content": tool_result}]}},
    )
    plugin.on_session_finalize(session_id="session-kanban", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert records[0]["categories"]["task_context"] > 0
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
    assert final["compactionDetection"] == "request_shape_inference"
    assert final["guardrails"] == []


def test_infers_compaction_from_large_message_count_drop(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))

    plugin.on_pre_api_request(
        session_id="session-compaction",
        api_call_count=1,
        approx_input_tokens=70_000,
        message_count=120,
        request={"body": {"messages": []}},
    )
    plugin.on_pre_api_request(
        session_id="session-compaction",
        api_call_count=2,
        approx_input_tokens=61_000,
        message_count=16,
        request={"body": {"messages": []}},
    )
    plugin.on_session_finalize(session_id="session-compaction", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert records[0]["compactionDetected"] is False
    assert records[1]["compactionDetected"] is True
    assert records[-1]["compactionCount"] == 1


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


def _duplicate_tool_request(task_id):
    duplicate = "same governed proof output " * 80
    messages = [
        {"role": "system", "content": "system contract"},
        {
            "role": "user",
            "content": (
                f"MC Task ID: {task_id}\n"
                "Objective ID: 749b54d1-52b4-4352-8539-c4a2fc9c7710\n"
                "MC Completion Contract: execution_result"
            ),
        },
        {
            "role": "assistant",
            "tool_calls": [{"id": "call-old", "function": {"name": "terminal"}}],
        },
        {"role": "tool", "tool_call_id": "call-old", "content": duplicate},
    ]
    messages.extend(
        {"role": "assistant", "content": f"working-memory-{index}"}
        for index in range(20)
    )
    messages.extend([
        {
            "role": "assistant",
            "tool_calls": [{"id": "call-new", "function": {"name": "terminal"}}],
        },
        {"role": "tool", "tool_call_id": "call-new", "content": duplicate},
    ])
    return {
        "model": "test-model",
        "messages": messages,
        "tools": [{"type": "function", "function": {"name": "terminal"}}],
        "unknown_future_field": {"preserve": True},
    }


def test_complete_prompt_shadow_measures_without_mutating_request(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.setenv("HERMES_CONTEXT_MODE", "shadow")
    task_id = "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"
    request = _duplicate_tool_request(task_id)

    assert plugin.on_llm_request(
        session_id="session-shadow",
        task_id=task_id,
        api_request_id="request-shadow",
        request=request,
    ) is None
    plugin.on_session_finalize(session_id="session-shadow", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    comparison = records[0]
    assert comparison["event"] == "complete_prompt_comparison"
    assert comparison["deliveredContext"] == "full"
    assert comparison["fallbackReason"] == "shadow_only"
    assert comparison["boundedEstimatedTokens"] < comparison["fullEstimatedTokens"]
    assert comparison["duplicateToolOutputsCompacted"] == 1
    assert request == _duplicate_tool_request(task_id)
    assert records[-1]["completePromptComparison"] == {
        "matchedCallCount": 1,
        "fullEstimatedTokens": comparison["fullEstimatedTokens"],
        "boundedEstimatedTokens": comparison["boundedEstimatedTokens"],
        "fallbackCount": 0,
        "boundedDeliveryCount": 0,
        "measurementSource": "provider_request",
    }


def test_allowlisted_bounded_delivery_preserves_unique_and_unknown_context(
    tmp_path, monkeypatch
):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.setenv("HERMES_CONTEXT_MODE", "bounded")
    task_id = "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"
    monkeypatch.setenv("HERMES_CONTEXT_TASK_IDS", task_id)
    request = _duplicate_tool_request(task_id)

    result = plugin.on_llm_request(
        session_id="session-bounded",
        task_id=task_id,
        api_request_id="request-bounded",
        request=request,
    )

    assert result["source"] == "mc-context-efficiency"
    bounded = result["request"]
    assert bounded["unknown_future_field"] == {"preserve": True}
    assert bounded["messages"][0] == request["messages"][0]
    assert bounded["messages"][1] == request["messages"][1]
    assert bounded["messages"][-1] == request["messages"][-1]
    assert bounded["messages"][3]["tool_call_id"] == "call-old"
    assert "exact duplicate tool output retained" in bounded["messages"][3]["content"]
    assert request["messages"][3]["content"].startswith("same governed proof output")


def test_bounded_mode_falls_back_when_not_allowlisted(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.setenv("HERMES_CONTEXT_MODE", "bounded")
    request = _duplicate_tool_request(
        "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"
    )

    assert plugin.on_llm_request(
        session_id="session-fallback",
        api_request_id="request-fallback",
        request=request,
    ) is None
    plugin.on_session_finalize(session_id="session-fallback", reason="done")

    records = [json.loads(line) for line in output.read_text().splitlines()]
    assert records[0]["fallbackReason"] == "not_allowlisted"
    assert records[-1]["completePromptComparison"]["fallbackCount"] == 1


def test_unknown_context_mode_preserves_legacy_request(tmp_path, monkeypatch):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.setenv("HERMES_CONTEXT_MODE", "future-mode")

    assert plugin.on_llm_request(
        session_id="session-future",
        request={"messages": [{"role": "user", "content": "keep exact"}]},
    ) is None
    assert not output.exists()


def test_profile_settings_survive_gateway_environment_regeneration(
    tmp_path, monkeypatch
):
    plugin = _load_plugin()
    output = tmp_path / "context.jsonl"
    task_id = "000d205e-5dc9-5eb1-95f2-8bcad1cac23e"
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.setenv("HERMES_CONTEXT_TELEMETRY_PATH", str(output))
    monkeypatch.delenv("HERMES_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("BOUNDED_CONTEXT_MODE", raising=False)
    monkeypatch.delenv("HERMES_CONTEXT_TASK_IDS", raising=False)
    (tmp_path / "context-efficiency.json").write_text(json.dumps({
        "version": "mc-context-efficiency-settings.v1",
        "mode": "bounded",
        "taskIds": [task_id],
        "objectiveIds": [],
    }))

    result = plugin.on_llm_request(
        session_id="session-profile-settings",
        task_id=task_id,
        request=_duplicate_tool_request(task_id),
    )

    assert result["source"] == "mc-context-efficiency"
