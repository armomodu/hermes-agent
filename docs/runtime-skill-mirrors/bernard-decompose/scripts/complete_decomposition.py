#!/usr/bin/env python3
"""Atomically submit and complete one validator-clean decomposition."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from decomposition_checkpoint import artifact_digest, mark_status
from submit_decomposition import SERVICE_USER_AGENT, load_payload, submit


def load_accepted_result(checkpoint_path: Path, result_path: Path) -> tuple[dict, str]:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if checkpoint.get("checkpointStatus") not in {"validator_clean", "accepted"}:
        raise ValueError("decomposition checkpoint must be validator_clean or accepted before completion")

    expected_result = Path(str(checkpoint.get("decompositionPath") or "")).resolve()
    if expected_result != result_path.resolve():
        raise ValueError("result path does not match the accepted decomposition checkpoint")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("kind") != "decomposition_result":
        raise ValueError("accepted result must have kind=decomposition_result")
    if result.get("objectiveId") != checkpoint.get("objectiveId"):
        raise ValueError("accepted result objectiveId does not match the checkpoint")
    if artifact_digest(result_path) != checkpoint.get("decompositionDigest"):
        raise ValueError("result digest does not match the validator-clean checkpoint")

    manifest_path = Path(str(checkpoint.get("manifestPath") or ""))
    if not manifest_path.is_file() or artifact_digest(manifest_path) != checkpoint.get("manifestDigest"):
        raise ValueError("manifest digest does not match the validator-clean checkpoint")

    compact_result = json.dumps(result, separators=(",", ":"), sort_keys=True)
    return result, compact_result


def persisted_graph_matches(payload: dict, api_base: str, token: str, timeout: float) -> bool:
    objective_id = urllib.parse.quote(str(payload["objectiveId"]), safe="")
    request = urllib.request.Request(
        f"{api_base.rstrip('/')}/objectives/{objective_id}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": SERVICE_USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        objective = json.loads(response.read().decode("utf-8"))
    expected_ids = {
        str(task.get("id") or "")
        for task in payload.get("tasks", [])
        if isinstance(task, dict) and task.get("id")
    }
    actual_ids = set(objective.get("childTaskIds") or []) if isinstance(objective, dict) else set()
    return bool(expected_ids) and expected_ids == actual_ids


def ensure_submitted(
    payload: dict,
    checkpoint_path: Path,
    response_path: Path,
    *,
    api_base: str,
    token: str,
    timeout: float,
) -> None:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if checkpoint.get("checkpointStatus") == "accepted":
        return
    try:
        status, response = submit(payload, api_base, token, timeout)
        response_path.write_text(json.dumps(response, indent=2) + "\n", encoding="utf-8")
        if status < 200 or status >= 300:
            raise RuntimeError(f"Mission Control returned HTTP {status}")
    except (OSError, urllib.error.URLError, TimeoutError):
        if not persisted_graph_matches(payload, api_base, token, timeout):
            raise
    mark_status("accepted", checkpoint_path.parent)


def build_completion_command(
    task_id: str,
    compact_result: str,
    result: dict,
    *,
    hermes_bin: str = "hermes",
) -> list[str]:
    if not task_id.strip():
        raise ValueError("HERMES_KANBAN_TASK or --task-id is required")
    summary = str(result.get("statusNote") or "Accepted decomposition submitted to Mission Control")
    return [
        hermes_bin,
        "kanban",
        "complete",
        task_id,
        "--result",
        compact_result,
        "--summary",
        summary,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", default=".mc-decomposition-checkpoint.json")
    parser.add_argument("--result", default="decomposition.json")
    parser.add_argument("--response", default="decomposition-response.json")
    parser.add_argument("--task-id", default=os.environ.get("HERMES_KANBAN_TASK", ""))
    parser.add_argument("--hermes-bin", default="hermes")
    parser.add_argument("--timeout", type=float, default=60.0)
    args = parser.parse_args()

    try:
        checkpoint_path = Path(args.checkpoint)
        result_path = Path(args.result)
        result, compact_result = load_accepted_result(checkpoint_path, result_path)
        api_base = os.environ.get("MC_API_URL", "").strip()
        token = os.environ.get("CRON_SERVICE_TOKEN", "").strip()
        if not api_base or not token:
            raise ValueError("MC_API_URL and CRON_SERVICE_TOKEN are required")
        ensure_submitted(
            load_payload(result_path),
            checkpoint_path,
            Path(args.response),
            api_base=api_base,
            token=token,
            timeout=args.timeout,
        )
        command = build_completion_command(
            args.task_id,
            compact_result,
            result,
            hermes_bin=args.hermes_bin,
        )
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"Hermes completion failed: {detail}")
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, urllib.error.URLError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Completed accepted decomposition task {args.task_id}. "
        "This was the final tool action; end the session without further tool calls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
