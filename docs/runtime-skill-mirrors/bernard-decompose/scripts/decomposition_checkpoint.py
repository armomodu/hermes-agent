#!/usr/bin/env python3
"""Persist Bernard decomposition continuity metadata inside its Hermes workspace."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


CHECKPOINT_NAME = ".mc-decomposition-checkpoint.json"
REPORT_NAME = "decomposition-validator-report.json"
VERSION = "decomposition-checkpoint.v1"
ARCHIVE_DIR_NAME = ".mc-decomposition-checkpoints"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _digest(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _finding_key(finding: object) -> str:
    if not isinstance(finding, dict):
        return _digest({"invalidFinding": finding})
    return _digest(
        {
            "code": finding.get("code"),
            "group": finding.get("group"),
            "taskId": finding.get("taskId"),
            "requirementId": finding.get("requirementId"),
            "paths": sorted(finding.get("paths") or []),
            "dependencyReferences": sorted(finding.get("dependencyReferences") or []),
        }
    )


def _expose_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    exposed = dict(metrics)
    builds = max(1, int(exposed.get("buildCount", 0)))
    exposed["manifestReuseRate"] = int(exposed.get("manifestReuseCount", 0)) / builds
    exposed["firstPassValidatorSuccessRate"] = (
        1.0 if exposed.get("firstPassValidatorSuccess") else 0.0
    )
    exposed["terminalConvergenceRate"] = (
        1.0 if exposed.get("terminalConverged") else 0.0
    )
    exposed["averageCorrectionRounds"] = (
        float(exposed.get("terminalCorrectionRound", 0))
        if exposed.get("terminalConverged")
        else None
    )
    attempts = int(exposed.get("workspaceResumeAttempts", 0))
    exposed["workspaceResumeSuccessRate"] = (
        int(exposed.get("workspaceResumeSuccesses", 0)) / attempts
        if attempts
        else None
    )
    return exposed


def checkpoint_path(workspace: Path | None = None) -> Path:
    return (workspace or Path.cwd()) / CHECKPOINT_NAME


def load_checkpoint(workspace: Path | None = None) -> dict[str, Any] | None:
    path = checkpoint_path(workspace)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) and payload.get("version") == VERSION else None


def _write_checkpoint(payload: dict[str, Any], workspace: Path | None = None) -> dict[str, Any]:
    path = checkpoint_path(workspace)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def _accepted_archive_path(
    checkpoint: dict[str, Any],
    workspace: Path | None = None,
) -> Path:
    root_override = os.environ.get("BERNARD_DECOMPOSITION_ARCHIVE_ROOT")
    root = (
        Path(root_override).expanduser()
        if root_override
        else (workspace or Path.cwd()).parent / ARCHIVE_DIR_NAME
    )
    return root / str(checkpoint["objectiveId"]) / str(checkpoint["manifestDigest"])


def _archive_accepted_checkpoint(
    checkpoint: dict[str, Any],
    workspace: Path | None = None,
) -> dict[str, Any]:
    archive_path = _accepted_archive_path(checkpoint, workspace)
    archive_path.mkdir(parents=True, exist_ok=True)
    artifact_paths = {
        "canonical-manifest.json": Path(str(checkpoint["manifestPath"])),
        "accepted-decomposition.json": Path(str(checkpoint["decompositionPath"])),
        "validator-report.json": Path(str(checkpoint["validatorReportPath"])),
    }
    for archive_name, source_path in artifact_paths.items():
        if not source_path.is_file():
            raise ValueError(f"accepted checkpoint artifact is missing: {source_path}")
        shutil.copy2(source_path, archive_path / archive_name)
    checkpoint["archivePath"] = str(archive_path.resolve())
    (archive_path / "checkpoint.json").write_text(
        json.dumps(checkpoint, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return checkpoint


def record_build(
    *,
    objective_id: str,
    manifest_path: Path,
    decomposition_path: Path,
    objective_path: Path | None = None,
    workspace: Path | None = None,
) -> dict[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_digest = _digest(manifest)
    objective_digest = None
    if objective_path:
        objective_digest = _digest(json.loads(objective_path.read_text(encoding="utf-8")))
    current = load_checkpoint(workspace)
    same_objective = bool(
        current
        and current.get("objectiveId") == objective_id
        and (
            not objective_digest
            or not current.get("objectiveDigest")
            or current.get("objectiveDigest") == objective_digest
        )
    )
    previous_digest = current.get("manifestDigest") if same_objective else None
    correction_round = int(current.get("correctionRound", 0)) if same_objective else 0
    task_keys = sorted(
        str(task.get("key") or "").strip()
        for task in manifest.get("tasks", [])
        if isinstance(task, dict) and str(task.get("key") or "").strip()
    )
    previous_task_keys = current.get("manifestTaskKeys") if same_objective else None
    preserved_task_keys = (
        sorted(set(previous_task_keys).intersection(task_keys))
        if isinstance(previous_task_keys, list)
        else []
    )
    full_regeneration = bool(previous_task_keys and task_keys and not preserved_task_keys)
    metrics = dict(current.get("metrics") or {}) if same_objective else {}
    if previous_digest and previous_digest != manifest_digest:
        correction_round += 1
    if correction_round > 2:
        raise ValueError(
            "decomposition exceeded two correction rounds; stop instead of regenerating"
        )
    retention_hours = max(
        1,
        int(os.environ.get("BERNARD_DECOMPOSITION_RETENTION_HOURS", "72")),
    )
    now = _now()
    payload = {
        "version": VERSION,
        "objectiveId": objective_id,
        "manifestPath": str(manifest_path.resolve()),
        "decompositionPath": str(decomposition_path.resolve()),
        "validatorReportPath": str((manifest_path.parent / REPORT_NAME).resolve()),
        "manifestDigest": manifest_digest,
        "manifestTaskKeys": task_keys,
        "objectiveDigest": objective_digest,
        "correctionRound": correction_round,
        "checkpointStatus": "drafted",
        "updatedAt": _iso(now),
        "retainUntil": _iso(now + timedelta(hours=retention_hours)),
        "retryContext": {
            "objectiveDigest": objective_digest,
            "manifestDigest": manifest_digest,
            "correctionRound": correction_round,
            "manifestTaskKeys": task_keys,
            "lastFindingKeys": list(metrics.get("lastFindingKeys") or []),
        },
        "metrics": {
            **metrics,
            "buildCount": int(metrics.get("buildCount", 0)) + 1,
            "manifestReuseCount": int(metrics.get("manifestReuseCount", 0))
            + (1 if previous_digest == manifest_digest else 0),
            "fullRegenerationCount": int(metrics.get("fullRegenerationCount", 0))
            + (1 if full_regeneration else 0),
            "stableTaskIdentityCount": len(preserved_task_keys),
            "stableTaskIdentityRate": (
                len(preserved_task_keys) / len(previous_task_keys)
                if isinstance(previous_task_keys, list) and previous_task_keys
                else None
            ),
        },
    }
    return _write_checkpoint(payload, workspace)


def record_validation(
    *,
    report: dict[str, Any],
    workspace: Path | None = None,
) -> dict[str, Any] | None:
    current = load_checkpoint(workspace)
    if not current:
        return None
    now = _now()
    metrics = dict(current.get("metrics") or {})
    validation_runs = int(metrics.get("validationRuns", 0)) + 1
    current_codes = sorted(
        {
            str(finding.get("code"))
            for finding in report.get("findings", [])
            if isinstance(finding, dict) and finding.get("code")
        }
    )
    current_finding_keys = sorted(
        _finding_key(finding)
        for finding in report.get("findings", [])
    )
    previous_finding_keys = set(metrics.get("lastFindingKeys") or [])
    introduced = (
        sorted(set(current_finding_keys) - previous_finding_keys)
        if validation_runs > 1
        else []
    )
    previous_finding_count = metrics.get("lastFindingCount")
    correction_reduced_findings = (
        validation_runs == 1
        or bool(report.get("ok"))
        or (
            isinstance(previous_finding_count, int)
            and int(report.get("findingCount", 0)) < previous_finding_count
        )
    )
    correction_accepted = not introduced and correction_reduced_findings
    checkpoint_status = (
        "validator_clean"
        if report.get("ok")
        else "correction_required"
        if correction_accepted
        else "correction_rejected"
    )
    retry_context = dict(current.get("retryContext") or {})
    retry_context.update(
        {
            "correctionRound": int(current.get("correctionRound", 0)),
            "lastFindingKeys": current_finding_keys,
            "lastFindingCount": int(report.get("findingCount", 0)),
            "checkpointStatus": checkpoint_status,
        }
    )
    next_metrics = _expose_metrics(
        {
            **metrics,
            "validationRuns": validation_runs,
            "firstPassValidatorSuccess": (
                bool(report.get("ok"))
                if validation_runs == 1
                else metrics.get("firstPassValidatorSuccess")
            ),
            "lastFindingCodes": current_codes,
            "lastFindingKeys": current_finding_keys,
            "lastFindingCount": int(report.get("findingCount", 0)),
            "lastCorrectionReducedFindings": correction_reduced_findings,
            "lastCorrectionAccepted": correction_accepted,
            "defectsIntroducedDuringCorrection": int(
                metrics.get("defectsIntroducedDuringCorrection", 0)
            ) + len(introduced),
            "terminalConverged": bool(report.get("ok")),
            "terminalCorrectionRound": (
                int(current.get("correctionRound", 0))
                if report.get("ok")
                else metrics.get("terminalCorrectionRound")
            ),
        }
    )
    current.update(
        {
            "checkpointStatus": checkpoint_status,
            "findingCount": int(report.get("findingCount", 0)),
            "retryContext": retry_context,
            "updatedAt": _iso(now),
            "metrics": next_metrics,
        }
    )
    return _write_checkpoint(current, workspace)


def mark_status(status: str, workspace: Path | None = None) -> dict[str, Any]:
    current = load_checkpoint(workspace)
    if not current:
        raise ValueError(f"{CHECKPOINT_NAME} is missing or invalid")
    current["checkpointStatus"] = status
    current["updatedAt"] = _iso(_now())
    if status == "accepted":
        current = _archive_accepted_checkpoint(current, workspace)
    return _write_checkpoint(current, workspace)


def resume_checkpoint(workspace: Path | None = None) -> dict[str, Any]:
    current = load_checkpoint(workspace)
    if not current:
        raise ValueError(f"{CHECKPOINT_NAME} is missing or invalid")
    manifest_path = Path(str(current.get("manifestPath") or ""))
    decomposition_path = Path(str(current.get("decompositionPath") or ""))
    if not manifest_path.is_file() or not decomposition_path.is_file():
        raise ValueError("checkpoint artifacts are missing; do not regenerate from memory")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _digest(manifest) != current.get("manifestDigest"):
        raise ValueError("checkpoint manifest digest does not match the persisted manifest")
    metrics = dict(current.get("metrics") or {})
    metrics["workspaceResumeAttempts"] = int(metrics.get("workspaceResumeAttempts", 0)) + 1
    metrics["workspaceResumeSuccesses"] = int(metrics.get("workspaceResumeSuccesses", 0)) + 1
    current["metrics"] = metrics
    current["updatedAt"] = _iso(_now())
    return _write_checkpoint(current, workspace)


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    resume_parser = subparsers.add_parser("resume")
    resume_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    metrics_parser = subparsers.add_parser("metrics")
    metrics_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    mark_parser = subparsers.add_parser("mark")
    mark_parser.add_argument("status", choices=("submitted", "accepted", "reset"))
    mark_parser.add_argument("--workspace", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        if args.command == "status":
            checkpoint = load_checkpoint(args.workspace)
            if not checkpoint:
                raise ValueError(f"{CHECKPOINT_NAME} is missing or invalid")
            print(json.dumps(checkpoint, sort_keys=True))
            return 0
        if args.command == "resume":
            print(json.dumps(resume_checkpoint(args.workspace), sort_keys=True))
            return 0
        if args.command == "metrics":
            checkpoint = load_checkpoint(args.workspace)
            if not checkpoint:
                raise ValueError(f"{CHECKPOINT_NAME} is missing or invalid")
            metrics = _expose_metrics(dict(checkpoint.get("metrics") or {}))
            print(json.dumps(metrics, sort_keys=True))
            return 0
        print(json.dumps(mark_status(args.status, args.workspace), sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"INVALID CHECKPOINT: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
