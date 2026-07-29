#!/usr/bin/env python3
"""Complete an accepted decomposition card without inlining its result in the model."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def load_accepted_result(checkpoint_path: Path, result_path: Path) -> tuple[dict, str]:
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    if checkpoint.get("checkpointStatus") != "accepted":
        raise ValueError("decomposition checkpoint must be accepted before completion")

    expected_result = Path(str(checkpoint.get("decompositionPath") or "")).resolve()
    if expected_result != result_path.resolve():
        raise ValueError("result path does not match the accepted decomposition checkpoint")

    result = json.loads(result_path.read_text(encoding="utf-8"))
    if result.get("kind") != "decomposition_result":
        raise ValueError("accepted result must have kind=decomposition_result")
    if result.get("objectiveId") != checkpoint.get("objectiveId"):
        raise ValueError("accepted result objectiveId does not match the checkpoint")

    compact_result = json.dumps(result, separators=(",", ":"), sort_keys=True)
    return result, compact_result


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
    parser.add_argument("--task-id", default=os.environ.get("HERMES_KANBAN_TASK", ""))
    parser.add_argument("--hermes-bin", default="hermes")
    args = parser.parse_args()

    try:
        result, compact_result = load_accepted_result(
            Path(args.checkpoint),
            Path(args.result),
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
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print(
        f"Completed accepted decomposition task {args.task_id}. "
        "This was the final tool action; end the session without further tool calls."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
