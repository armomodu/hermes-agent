"""Upgrade-safe Mission Control context-efficiency observer.

The plugin records counts, hashes, and token estimates only. It never changes
the provider request and telemetry failures are deliberately non-fatal.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import threading
import time
from typing import Any


SCHEMA_VERSION = "mc-context-efficiency.v1"
_LOCK = threading.RLock()
_SESSIONS: dict[str, "_SessionTotals"] = {}
_MC_TASK_ID_PATTERN = re.compile(
    r"(?m)^\s*(?:MC )?Task ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$",
    re.IGNORECASE,
)


def _estimated_tokens(value: Any) -> int:
    if value is None:
        return 0
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return (len(value.encode("utf-8")) + 3) // 4


def _stable_hash(value: Any) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return sha256(value.encode("utf-8")).hexdigest()


def _output_path() -> Path:
    configured = os.environ.get("HERMES_CONTEXT_TELEMETRY_PATH", "").strip()
    if configured:
        return Path(configured).expanduser()
    home = Path(os.environ.get("HERMES_HOME", "~/.hermes")).expanduser()
    return home / "telemetry" / "context-efficiency.v1.jsonl"


def _write(record: dict[str, Any]) -> None:
    try:
        path = _output_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with _LOCK, path.open("a", encoding="utf-8") as handle:
            handle.write(payload + "\n")
    except Exception:
        # Observability must never change execution behavior.
        return


def _request_body(kwargs: dict[str, Any]) -> dict[str, Any]:
    request = kwargs.get("request")
    if not isinstance(request, dict):
        return {}
    body = request.get("body")
    return body if isinstance(body, dict) else {}


def _messages(body: dict[str, Any], kwargs: dict[str, Any]) -> list[dict[str, Any]]:
    candidate = body.get("messages")
    if not isinstance(candidate, list):
        candidate = body.get("input")
    if not isinstance(candidate, list):
        candidate = kwargs.get("request_messages")
    return [item for item in (candidate or []) if isinstance(item, dict)]


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts)
    return ""


def _is_task_envelope(text: str) -> bool:
    markers = (
        "MC Task ID:",
        "Task ID:",
        "MC Task Type:",
        "MC Completion Contract:",
        "Objective ID:",
        "Task Contract:",
    )
    return any(marker in text for marker in markers)


def _mc_task_ids(messages: list[dict[str, Any]]) -> set[str]:
    return {
        match.group(1).lower()
        for message in messages
        for match in _MC_TASK_ID_PATTERN.finditer(_message_text(message))
    }


def _tool_signatures(messages: list[dict[str, Any]]) -> Counter[str]:
    signatures: Counter[str] = Counter()
    for message in messages:
        calls = message.get("tool_calls")
        if not isinstance(calls, list):
            continue
        for call in calls:
            if not isinstance(call, dict):
                continue
            function = call.get("function")
            if not isinstance(function, dict):
                continue
            name = str(function.get("name") or "")
            arguments = function.get("arguments")
            signatures[f"{name}:{_stable_hash(arguments or '')}"] += 1
    return signatures


def _breakdown(body: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, int]:
    messages = _messages(body, kwargs)
    system: list[dict[str, Any]] = []
    task_context: list[dict[str, Any]] = []
    conversation: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []

    for message in messages:
        role = str(message.get("role") or "")
        text = _message_text(message)
        if _is_task_envelope(text):
            task_context.append(message)
        elif role in {"system", "developer"}:
            system.append(message)
        elif role == "tool":
            tool_results.append(message)
        else:
            conversation.append(message)

    tools = body.get("tools")
    if not isinstance(tools, list):
        tools = []
    return {
        "system": _estimated_tokens(system),
        "task_context": _estimated_tokens(task_context),
        "conversation": _estimated_tokens(conversation),
        "tool_schemas": _estimated_tokens(tools),
        "tool_results": _estimated_tokens(tool_results),
    }


@dataclass
class _SessionTotals:
    started_at: float = field(default_factory=time.time)
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0
    max_prompt_tokens: int = 0
    first_prompt_tokens: int = 0
    last_prompt_tokens: int = 0
    compaction_count: int = 0
    estimated_categories: Counter[str] = field(default_factory=Counter)
    repeated_tool_calls: int = 0
    task_ids: set[str] = field(default_factory=set)


def on_pre_api_request(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "")
    request_id = str(kwargs.get("api_request_id") or "")
    body = _request_body(kwargs)
    messages = _messages(body, kwargs)
    breakdown = _breakdown(body, kwargs)
    signatures = _tool_signatures(messages)
    repeated = sum(count - 1 for count in signatures.values() if count > 1)
    estimated_total = sum(breakdown.values())
    approx_input = int(kwargs.get("approx_input_tokens") or 0)

    with _LOCK:
        totals = _SESSIONS.setdefault(session_id, _SessionTotals())
        task_id = str(kwargs.get("task_id") or "")
        if task_id:
            totals.task_ids.add(task_id)
        totals.task_ids.update(_mc_task_ids(messages))
        totals.api_calls = max(totals.api_calls, int(kwargs.get("api_call_count") or 0))
        prompt_tokens = max(approx_input, estimated_total)
        if totals.first_prompt_tokens == 0:
            totals.first_prompt_tokens = prompt_tokens
        if totals.last_prompt_tokens > 0 and prompt_tokens < totals.last_prompt_tokens * 0.7:
            totals.compaction_count += 1
        totals.last_prompt_tokens = prompt_tokens
        totals.max_prompt_tokens = max(totals.max_prompt_tokens, prompt_tokens)
        totals.estimated_categories.update(breakdown)
        totals.repeated_tool_calls = max(totals.repeated_tool_calls, repeated)

    _write({
        "version": SCHEMA_VERSION,
        "event": "api_request",
        "recordedAt": time.time(),
        "sessionId": session_id,
        "taskId": str(kwargs.get("task_id") or ""),
        "apiRequestId": request_id,
        "apiCallCount": int(kwargs.get("api_call_count") or 0),
        "model": str(kwargs.get("model") or ""),
        "provider": str(kwargs.get("provider") or ""),
        "estimatedPromptTokens": max(approx_input, estimated_total),
        "categories": breakdown,
        "messageCount": int(kwargs.get("message_count") or 0),
        "toolCount": int(kwargs.get("tool_count") or 0),
        "repeatedToolCalls": repeated,
        "requestHash": _stable_hash(body),
    })


def on_post_api_request(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "")
    usage = kwargs.get("usage")
    usage = usage if isinstance(usage, dict) else {}
    input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    cache_read = int(usage.get("cache_read_tokens") or 0)
    cache_write = int(usage.get("cache_write_tokens") or 0)
    with _LOCK:
        totals = _SESSIONS.setdefault(session_id, _SessionTotals())
        totals.input_tokens += input_tokens
        totals.output_tokens += output_tokens
        totals.cache_read_tokens += cache_read
        totals.cache_write_tokens += cache_write

    _write({
        "version": SCHEMA_VERSION,
        "event": "api_response",
        "recordedAt": time.time(),
        "sessionId": session_id,
        "taskId": str(kwargs.get("task_id") or ""),
        "apiRequestId": str(kwargs.get("api_request_id") or ""),
        "apiCallCount": int(kwargs.get("api_call_count") or 0),
        "durationMs": round(float(kwargs.get("api_duration") or 0) * 1000),
        "finishReason": kwargs.get("finish_reason"),
        "usage": {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "cacheReadTokens": cache_read,
            "cacheWriteTokens": cache_write,
        },
    })


def on_api_request_error(**kwargs: Any) -> None:
    _write({
        "version": SCHEMA_VERSION,
        "event": "api_error",
        "recordedAt": time.time(),
        "sessionId": str(kwargs.get("session_id") or ""),
        "taskId": str(kwargs.get("task_id") or ""),
        "apiRequestId": str(kwargs.get("api_request_id") or ""),
        "apiCallCount": int(kwargs.get("api_call_count") or 0),
    })


def on_session_finalize(**kwargs: Any) -> None:
    session_id = str(kwargs.get("session_id") or "")
    with _LOCK:
        totals = _SESSIONS.pop(session_id, _SessionTotals())
    max_calls = int(os.environ.get("HERMES_CONTEXT_MAX_API_CALLS", "40") or 40)
    max_input = int(os.environ.get("HERMES_CONTEXT_MAX_CUMULATIVE_INPUT", "2000000") or 2_000_000)
    guardrails: list[str] = []
    if totals.api_calls >= max_calls:
        guardrails.append("api_call_budget_exceeded")
    if totals.input_tokens >= max_input:
        guardrails.append("cumulative_input_budget_exceeded")
    if (
        totals.first_prompt_tokens > 0
        and totals.max_prompt_tokens >= totals.first_prompt_tokens * 3
    ):
        guardrails.append("prompt_growth_excessive")
    if totals.input_tokens >= max_input and totals.cache_read_tokens == 0:
        guardrails.append("cache_utilization_missing")
    if totals.repeated_tool_calls >= 5:
        guardrails.append("repeated_tool_calls_excessive")

    _write({
        "version": SCHEMA_VERSION,
        "event": "session_finalized",
        "recordedAt": time.time(),
        "sessionId": session_id,
        "endReason": str(kwargs.get("reason") or "unknown"),
        "durationMs": round((time.time() - totals.started_at) * 1000),
        "apiCallCount": totals.api_calls,
        "inputTokens": totals.input_tokens,
        "outputTokens": totals.output_tokens,
        "cacheReadTokens": totals.cache_read_tokens,
        "cacheWriteTokens": totals.cache_write_tokens,
        "maxPromptTokens": totals.max_prompt_tokens,
        "firstPromptTokens": totals.first_prompt_tokens,
        "lastPromptTokens": totals.last_prompt_tokens,
        "compactionCount": totals.compaction_count,
        "estimatedCategories": dict(totals.estimated_categories),
        "repeatedToolCalls": totals.repeated_tool_calls,
        "taskIds": sorted(totals.task_ids),
        "guardrails": guardrails,
    })


def register(ctx: Any) -> None:
    ctx.register_hook("pre_api_request", on_pre_api_request)
    ctx.register_hook("post_api_request", on_post_api_request)
    ctx.register_hook("api_request_error", on_api_request_error)
    ctx.register_hook("on_session_finalize", on_session_finalize)
