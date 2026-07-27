"""Upgrade-safe Mission Control context-efficiency compatibility layer.

Observer hooks record content-free request/session metrics. Stable LLM request
middleware optionally measures or removes earlier exact duplicate tool output;
legacy and shadow modes never change the provider request, and middleware
failure remains fail-open through Hermes' compatibility contract.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from dataclasses import dataclass, field
from functools import lru_cache
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
_MC_OBJECTIVE_ID_PATTERN = re.compile(
    r"(?m)^\s*Objective ID:\s*([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\s*$",
    re.IGNORECASE,
)
_COMPLETE_CONTEXT_MODES = {"legacy", "shadow", "bounded"}
_DUPLICATE_TOOL_OUTPUT_MIN_BYTES = 512
_PROTECTED_TAIL_MESSAGES = 6
_SETTINGS_VERSION = "mc-context-efficiency-settings.v1"


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
    task_ids: set[str] = set()

    def collect(value: Any) -> None:
        if isinstance(value, str):
            task_ids.update(match.group(1).lower() for match in _MC_TASK_ID_PATTERN.finditer(value))
            try:
                decoded = json.loads(value)
            except (TypeError, ValueError):
                return
            if decoded != value:
                collect(decoded)
            return
        if isinstance(value, dict):
            for item in value.values():
                collect(item)
            return
        if isinstance(value, list):
            for item in value:
                collect(item)

    for message in messages:
        collect(_message_text(message))
    return task_ids


def _mc_objective_ids(messages: list[dict[str, Any]]) -> set[str]:
    objective_ids: set[str] = set()
    for message in messages:
        text = _message_text(message)
        objective_ids.update(
            match.group(1).lower()
            for match in _MC_OBJECTIVE_ID_PATTERN.finditer(text)
        )
    return objective_ids


@lru_cache(maxsize=16)
def _profile_settings(home: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            (Path(home).expanduser() / "context-efficiency.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            isinstance(payload, dict)
            and payload.get("version") == _SETTINGS_VERSION
        ):
            return payload
    except Exception:
        pass
    return {}


def _setting_values(env_name: str, setting_name: str) -> set[str]:
    configured = os.environ.get(env_name, "")
    if configured.strip():
        values: Any = configured.split(",")
    else:
        values = _profile_settings(
            os.environ.get("HERMES_HOME", "~/.hermes")
        ).get(setting_name, [])
    if not isinstance(values, list):
        return set()
    return {
        value.strip().lower()
        for value in values
        if isinstance(value, str) and value.strip()
    }


def _complete_context_mode() -> str:
    requested = os.environ.get("HERMES_CONTEXT_MODE") or os.environ.get(
        "BOUNDED_CONTEXT_MODE"
    )
    if not requested:
        requested = str(
            _profile_settings(
                os.environ.get("HERMES_HOME", "~/.hermes")
            ).get("mode", "legacy")
        )
    requested = requested.strip().lower()
    return requested if requested in _COMPLETE_CONTEXT_MODES else "legacy"


def _provider_messages(request: dict[str, Any]) -> tuple[str | None, list[Any]]:
    for key in ("messages", "input"):
        value = request.get(key)
        if isinstance(value, list):
            return key, list(value)
    return None, []


def _duplicate_tool_output_candidate(
    request: dict[str, Any],
) -> tuple[dict[str, Any], bool, list[str], int]:
    """Replace only earlier exact duplicate tool outputs.

    Every unique output, task envelope, system/developer message, user message,
    assistant decision, tool-call identity, and the protected tail remain
    byte-for-byte unchanged. The latest copy of duplicate output remains exact,
    so the candidate removes no unique information.
    """
    key, messages = _provider_messages(request)
    if key is None or not messages:
        return request, False, ["provider_messages"], 0

    latest_by_hash: dict[str, int] = {}
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") != "tool":
            continue
        content = message.get("content")
        if (
            not isinstance(content, str)
            or len(content.encode("utf-8")) < _DUPLICATE_TOOL_OUTPUT_MIN_BYTES
            or _is_task_envelope(content)
        ):
            continue
        latest_by_hash[_stable_hash(content)] = index

    candidate_messages = list(messages)
    replaced = 0
    protected_from = max(0, len(messages) - _PROTECTED_TAIL_MESSAGES)
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            continue
        if index >= protected_from or str(message.get("role") or "") != "tool":
            continue
        content = message.get("content")
        if not isinstance(content, str) or _is_task_envelope(content):
            continue
        content_hash = _stable_hash(content)
        latest_index = latest_by_hash.get(content_hash)
        if latest_index is None or latest_index <= index:
            continue
        compacted = dict(message)
        compacted["content"] = (
            "[Hermes bounded context: exact duplicate tool output retained at "
            f"message {latest_index}; sha256={content_hash}; "
            f"bytes={len(content.encode('utf-8'))}]"
        )
        candidate_messages[index] = compacted
        replaced += 1

    candidate = dict(request)
    candidate[key] = candidate_messages
    return candidate, True, [], replaced


def _bounded_delivery_allowlisted(messages: list[Any]) -> bool:
    structured = [message for message in messages if isinstance(message, dict)]
    task_allowlist = _setting_values("HERMES_CONTEXT_TASK_IDS", "taskIds")
    objective_allowlist = _setting_values(
        "HERMES_CONTEXT_OBJECTIVE_IDS", "objectiveIds"
    )
    if not task_allowlist and not objective_allowlist:
        return False
    return bool(
        _mc_task_ids(structured) & task_allowlist
        or _mc_objective_ids(structured) & objective_allowlist
    )


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
    last_message_count: int = 0
    compaction_count: int = 0
    estimated_categories: Counter[str] = field(default_factory=Counter)
    repeated_tool_calls: int = 0
    task_ids: set[str] = field(default_factory=set)
    complete_prompt_matched_calls: int = 0
    complete_prompt_full_tokens: int = 0
    complete_prompt_bounded_tokens: int = 0
    complete_prompt_fallback_count: int = 0
    complete_prompt_bounded_delivery_count: int = 0


def on_llm_request(**kwargs: Any) -> dict[str, Any] | None:
    """Generate or deliver a complete-request bounded candidate.

    The middleware is inactive in legacy mode. Shadow mode records the exact
    full-versus-candidate request comparison without changing delivery.
    Bounded mode additionally requires an explicit task/objective allowlist,
    complete mechanical preservation, and a smaller candidate.
    """
    mode = _complete_context_mode()
    if mode == "legacy":
        return None
    request = kwargs.get("request")
    if not isinstance(request, dict):
        return None

    full_request = deepcopy(request)
    candidate, mechanically_complete, missing, replaced = (
        _duplicate_tool_output_candidate(full_request)
    )
    full_tokens = _estimated_tokens(full_request)
    bounded_tokens = _estimated_tokens(candidate)
    _, messages = _provider_messages(full_request)
    allowlisted = _bounded_delivery_allowlisted(messages)
    smaller = bounded_tokens < full_tokens
    delivered = (
        "bounded"
        if mode == "bounded" and allowlisted and mechanically_complete and smaller
        else "full"
    )
    fallback_reason = None
    if mode == "shadow":
        fallback_reason = "shadow_only"
    elif not allowlisted:
        fallback_reason = "not_allowlisted"
    elif not mechanically_complete:
        fallback_reason = "incomplete_candidate"
    elif not smaller:
        fallback_reason = "candidate_not_smaller"

    session_id = str(kwargs.get("session_id") or "")
    with _LOCK:
        totals = _SESSIONS.setdefault(session_id, _SessionTotals())
        totals.complete_prompt_matched_calls += 1
        totals.complete_prompt_full_tokens += full_tokens
        totals.complete_prompt_bounded_tokens += bounded_tokens
        if mode == "bounded" and delivered != "bounded":
            totals.complete_prompt_fallback_count += 1
        if delivered == "bounded":
            totals.complete_prompt_bounded_delivery_count += 1

    _write({
        "version": SCHEMA_VERSION,
        "event": "complete_prompt_comparison",
        "recordedAt": time.time(),
        "sessionId": session_id,
        "taskId": str(kwargs.get("task_id") or ""),
        "apiRequestId": str(kwargs.get("api_request_id") or ""),
        "mode": mode,
        "deliveredContext": delivered,
        "mechanicallyComplete": mechanically_complete,
        "missingCategories": missing,
        "fullEstimatedTokens": full_tokens,
        "boundedEstimatedTokens": bounded_tokens,
        "duplicateToolOutputsCompacted": replaced,
        "fallbackReason": fallback_reason,
    })

    if delivered != "bounded":
        return None
    return {
        "request": candidate,
        "source": "mc-context-efficiency",
        "reason": "allowlisted exact-duplicate tool-output compaction",
    }


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
    message_count = int(kwargs.get("message_count") or len(messages))

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
        token_drop = (
            totals.last_prompt_tokens > 0
            and prompt_tokens < totals.last_prompt_tokens * 0.7
        )
        message_drop = (
            totals.last_message_count >= 10
            and message_count < totals.last_message_count * 0.7
        )
        compaction_detected = token_drop or message_drop
        if compaction_detected:
            totals.compaction_count += 1
        totals.last_prompt_tokens = prompt_tokens
        totals.last_message_count = message_count
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
        "messageCount": message_count,
        "compactionDetected": compaction_detected,
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
        "compactionDetection": "request_shape_inference",
        "estimatedCategories": dict(totals.estimated_categories),
        "repeatedToolCalls": totals.repeated_tool_calls,
        "taskIds": sorted(totals.task_ids),
        "guardrails": guardrails,
        "completePromptComparison": {
            "matchedCallCount": totals.complete_prompt_matched_calls,
            "fullEstimatedTokens": totals.complete_prompt_full_tokens,
            "boundedEstimatedTokens": totals.complete_prompt_bounded_tokens,
            "fallbackCount": totals.complete_prompt_fallback_count,
            "boundedDeliveryCount": totals.complete_prompt_bounded_delivery_count,
            "measurementSource": "provider_request",
        },
    })


def register(ctx: Any) -> None:
    ctx.register_middleware("llm_request", on_llm_request)
    ctx.register_hook("pre_api_request", on_pre_api_request)
    ctx.register_hook("post_api_request", on_post_api_request)
    ctx.register_hook("api_request_error", on_api_request_error)
    ctx.register_hook("on_session_finalize", on_session_finalize)
