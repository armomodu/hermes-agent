#!/usr/bin/env python3
"""Validate a Mission Control decomposition_result payload before live submit."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path


REQUIRED_TASK_FIELDS = (
    "id",
    "title",
    "assignee",
    "taskType",
    "priority",
    "summary",
    "acceptanceCriteria",
    "constraints",
    "relatedFiles",
    "nextAction",
)

CONTRACT_MODE_REQUIRED_TASK_FIELDS = (
    "id",
    "title",
    "assignee",
    "taskType",
    "priority",
    "nextAction",
    "taskContract",
)


def classify_writable_cluster(path: str) -> str | None:
    cleaned = path.replace("**", "").rstrip("/")
    if "/src/lib/knowledge-plane/contracts/" in cleaned:
        return "contracts"
    if "/src/lib/knowledge-plane/ledger/" in cleaned:
        return "ledger"
    if cleaned == "apps/mission-control/prisma/schema.prisma":
        return "apps/mission-control/prisma/schema.prisma"
    if cleaned.startswith("apps/mission-control/prisma/migrations"):
        return "apps/mission-control/prisma/migrations"
    if "/src/lib/storage/" in cleaned:
        return "storage"
    if cleaned.startswith("apps/mission-control/src/app/api/tasks"):
        return "apps/mission-control/src/app/api/tasks"
    if cleaned.startswith("apps/mission-control/src/app/api/objectives"):
        return "apps/mission-control/src/app/api/objectives"
    if cleaned == "apps/mission-control/src/lib/workers/handlers.ts":
        return "apps/mission-control/src/lib/workers/handlers.ts"
    if cleaned == "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts":
        return "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts"
    if "/src/app/api/knowledge/ledger/" in cleaned:
        return "knowledge-ledger-api"
    if "/src/lib/release/objective-release-service.ts" in cleaned:
        return "release-runtime"
    if "/src/lib/release/objective-deployment-service.ts" in cleaned:
        return "deploy-verify-runtime"
    if "/src/lib/release/objective-activation-service.ts" in cleaned:
        return "activation-runtime"
    if "/src/lib/workers/escalation-events.ts" in cleaned:
        return "escalation-runtime"
    if "/src/lib/workers/idempotency.ts" in cleaned:
        return "duplicate-prevention-runtime"
    if "/docs/" in cleaned:
        return "docs"
    return None


def fail(message: str) -> int:
    print(f"INVALID: {message}", file=sys.stderr)
    return 1


def main() -> int:
    if len(sys.argv) not in (2, 3):
        print(
            "usage: validate_decomposition_json.py <decomposition.json> [max_task_count]",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[1])
    max_tasks = int(sys.argv[2]) if len(sys.argv) == 3 else None

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("kind") != "decomposition_result":
        return fail("kind must be decomposition_result")
    if payload.get("actor") != "Bernard":
        return fail("actor must be Bernard")
    if payload.get("requestReview") is not True:
        return fail("requestReview must be true")

    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        return fail("tasks must be a non-empty list")
    if max_tasks is not None and len(tasks) > max_tasks:
        return fail(f"task count {len(tasks)} exceeds max {max_tasks}")

    task_ids: set[str] = set()
    review_tasks = []
    execution_ids: set[str] = set()
    providers: dict[str, list[str]] = {}

    for task in tasks:
        task_contract = task.get("taskContract")
        if isinstance(task_contract, dict):
            for token in task_contract.get("provides", []):
                if not isinstance(token, str) or not token.strip():
                    continue
                providers.setdefault(token.strip(), []).append(task["id"])

    for task in tasks:
        contract_mode = isinstance(task.get("taskContract"), dict)
        required_fields = CONTRACT_MODE_REQUIRED_TASK_FIELDS if contract_mode else REQUIRED_TASK_FIELDS

        for field in required_fields:
            if field not in task:
                return fail(f"task missing required field {field}: {task!r}")

        task_id = task["id"]
        try:
            uuid.UUID(task_id)
        except Exception as exc:  # pragma: no cover - defensive
            return fail(f"invalid UUID {task_id}: {exc}")

        if task_id in task_ids:
            return fail(f"duplicate task id {task_id}")
        task_ids.add(task_id)

        if task["taskType"] not in ("execution", "review"):
            return fail(f"invalid taskType {task['taskType']} for {task_id}")
        if task["priority"] not in ("P1", "P2", "P3"):
            return fail(f"invalid priority {task['priority']} for {task_id}")

        if task["taskType"] == "review":
            review_tasks.append(task)
        else:
            execution_ids.add(task_id)

        derived_depends_on = list(task.get("dependsOn", []) or [])
        if contract_mode and not derived_depends_on:
            if task["taskType"] == "review" and task.get("reviewMode") == "gate_review":
                derived_depends_on = [candidate["id"] for candidate in tasks if candidate.get("taskType") != "review"]
            else:
                task_contract = task["taskContract"]
                for token in task_contract.get("consumes", []):
                    if not isinstance(token, str) or not token.strip():
                        continue
                    derived_depends_on.extend(providers.get(token.strip(), []))
                derived_depends_on = sorted({dep for dep in derived_depends_on if dep != task_id})

        for dep in derived_depends_on:
            if dep not in task_ids and dep not in {t["id"] for t in tasks}:
                return fail(f"dependsOn {dep} not found for task {task_id}")

        for field in ("relatedFiles", "artifactPaths"):
            for item in task.get(field, []):
                if "\\*\\*" in item:
                    return fail(f"escaped glob found in {field}: {item}")
        if contract_mode:
            task_contract = task["taskContract"]
            if task_contract.get("version") != "task-contract.v1":
                return fail(f"taskContract.version must be task-contract.v1 for {task_id}")
            for field in ("writableFiles", "proofFiles", "createdFileGlobs", "readOnlyAnchors", "outputArtifacts", "provides", "consumes"):
                values = task_contract.get(field, [])
                if not isinstance(values, list):
                    return fail(f"taskContract.{field} must be a list for {task_id}")
                for item in values:
                    if not isinstance(item, str):
                        return fail(f"taskContract.{field} must contain only strings for {task_id}")
                    if "\\*\\*" in item:
                        return fail(f"escaped glob found in taskContract.{field}: {item}")
            writable_files = list(task_contract.get("writableFiles", []))
            proof_files = list(task_contract.get("proofFiles", []))
            semantic_hinge = str(task_contract.get("semanticHinge", "")).lower()
            title_lower = str(task.get("title", "")).lower()
            proof_only = "prove task/objective workflow exact parity" in semantic_hinge or "prove task/objective workflow exact parity" in title_lower
            if proof_only:
                if sorted(writable_files) != sorted(proof_files):
                    return fail(
                        f"proof-only task must keep writable scope equal to proof files for {task_id}: "
                        f"writable={writable_files} proof={proof_files}"
                    )
            elif task.get("assignee") == "William":
                leaked_tests = [path for path in writable_files if "/__tests__/" in path]
                if leaked_tests:
                    return fail(f"William writable scope must not include test globs/files for {task_id}: {leaked_tests}")

            if task.get("assignee") == "William":
                clusters = sorted(
                    {
                        cluster
                        for cluster in (classify_writable_cluster(path) for path in writable_files)
                        if cluster
                    }
                )
                if len(clusters) > 1:
                    return fail(
                        f"William writable scope spans multiple production clusters for {task_id}: {clusters}"
                    )

    if len(review_tasks) != 1:
        return fail(f"expected exactly 1 review task, found {len(review_tasks)}")

    gate = review_tasks[0]
    if gate.get("reviewMode") != "gate_review":
        return fail("review task must use reviewMode=gate_review")

    gate_deps = set(gate.get("dependsOn", []))
    if not gate_deps and isinstance(gate.get("taskContract"), dict):
        for token in gate["taskContract"].get("consumes", []):
            if not isinstance(token, str) or not token.strip():
                continue
            gate_deps.update(providers.get(token.strip(), []))
        if not gate_deps:
            gate_deps.update(execution_ids)
    missing = execution_ids - gate_deps
    if missing:
        return fail(f"gate_review missing execution dependencies: {sorted(missing)}")

    print(
        json.dumps(
            {
                "ok": True,
                "taskCount": len(tasks),
                "executionTasks": len(execution_ids),
                "reviewTasks": len(review_tasks),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
