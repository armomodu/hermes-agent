#!/usr/bin/env python3
"""Validate a Mission Control decomposition_result payload before live submit."""

from __future__ import annotations

import json
import re
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

GENERIC_AUTHORITY_ROOTS = {
    ".",
    "apps",
    "apps/mission-control",
    "apps/mission-control/src",
    "apps/mission-control/src/lib",
}


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


def classify_authority_root(path: str) -> str | None:
    cleaned = path.replace("**", "").rstrip("/")
    if cleaned.startswith("apps/mission-control/src/app/api/tasks"):
        return "task_api"
    if cleaned.startswith("apps/mission-control/src/app/api/objectives"):
        return "objective_api"
    if cleaned == "apps/mission-control/src/lib/workers/handlers.ts":
        return "worker_handler"
    if cleaned == "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts":
        return "readiness_promotion"
    if cleaned == "apps/mission-control/prisma/schema.prisma":
        return "prisma_schema"
    if cleaned.startswith("apps/mission-control/prisma/migrations"):
        return "prisma_migrations"
    if cleaned == "apps/mission-control/src/lib/release/objective-release-service.ts":
        return "release_runtime"
    if cleaned == "apps/mission-control/src/lib/release/objective-deployment-service.ts":
        return "deploy_runtime"
    if cleaned == "apps/mission-control/src/lib/release/objective-activation-service.ts":
        return "activation_runtime"
    if cleaned == "apps/mission-control/src/lib/workers/escalation-events.ts":
        return "escalation_runtime"
    return None


def normalized_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def fail(message: str) -> int:
    print(f"INVALID: {message}", file=sys.stderr)
    return 1


def _path_within_root(path: str, root: str) -> bool:
    clean_path = path.replace("/**", "").rstrip("/")
    clean_root = root.replace("/**", "").rstrip("/")
    return bool(clean_path and clean_root) and (
        clean_path == clean_root or clean_path.startswith(clean_root + "/")
    )


def _has_glob(path: str) -> bool:
    return any(marker in path for marker in ("*", "?", "[", "]", "{", "}"))


def _is_exact_file_path(path: str) -> bool:
    return bool(path.strip()) and not _has_glob(path) and "." in path.rstrip("/").split("/")[-1]


def _patterns_overlap(left: str, right: str) -> bool:
    return _path_within_root(left, right) or _path_within_root(right, left)


def _is_executable_software_test_proof(path: str) -> bool:
    normalized = path.strip().replace("\\", "/").removeprefix("./")
    return bool(
        re.search(r"(?:^|/)__tests__/.+\.[cm]?[jt]sx?$", normalized)
        or re.search(r"\.(?:test|spec)\.[cm]?[jt]sx?$", normalized, re.IGNORECASE)
    )


def _execution_plan_reference_valid(reference: str, task_contract: dict) -> bool:
    if reference in ("authorityRoot", "mutationRoot", "proofRoot"):
        return bool(str(task_contract.get(reference) or "").strip())
    if reference.startswith("consumedToken:"):
        return reference.removeprefix("consumedToken:") in normalized_string_list(task_contract.get("consumes"))
    if reference.startswith("outputArtifact:"):
        try:
            index = int(reference.removeprefix("outputArtifact:"))
        except ValueError:
            return False
        return 0 <= index < len(normalized_string_list(task_contract.get("outputArtifacts")))
    return False


def validate_task_contract_local(
    task_contract: object,
    task_id: str,
    *,
    strict_plan: bool = False,
    strict_graph: bool = False,
    allow_read_only: bool = False,
) -> str | None:
    if not isinstance(task_contract, dict):
        return f"taskContract must be an object for {task_id}"
    if task_contract.get("version") != "task-contract.v1":
        return f"taskContract.version must be task-contract.v1 for {task_id}"
    roots = {
        field: str(task_contract.get(field) or "").strip()
        for field in ("mutationRoot", "authorityRoot", "proofRoot")
    }
    for field, value in roots.items():
        if not value:
            return f"taskContract.{field} is required for {task_id}"
    if strict_graph and roots["authorityRoot"].replace("/**", "").rstrip("/") in GENERIC_AUTHORITY_ROOTS:
        return f"taskContract.authorityRoot is too broad for {task_id}: {roots['authorityRoot']}"
    if strict_graph and not _is_exact_file_path(roots["proofRoot"]):
        return f"taskContract.proofRoot must be one exact proof path for {task_id}: {roots['proofRoot']}"
    for field in ("semanticHinge", "acceptanceHinge"):
        if not str(task_contract.get(field) or "").strip():
            return f"taskContract.{field} is required for {task_id}"
    list_fields = (
        "writableFiles", "proofFiles", "createdFileGlobs", "readOnlyAnchors",
        "outputArtifacts", "provides", "consumes",
    )
    for field in list_fields:
        values = task_contract.get(field, [])
        if not isinstance(values, list):
            return f"taskContract.{field} must be a list for {task_id}"
        for item in values:
            if not isinstance(item, str):
                return f"taskContract.{field} must contain only strings for {task_id}"
            if "\\*\\*" in item:
                return f"escaped glob found in taskContract.{field}: {item}"

    writable_files = normalized_string_list(task_contract.get("writableFiles"))
    created_file_globs = normalized_string_list(task_contract.get("createdFileGlobs"))
    read_only_anchors = normalized_string_list(task_contract.get("readOnlyAnchors"))
    if not writable_files and not allow_read_only:
        return f"taskContract.writableFiles is required for executable task {task_id}"
    if (
        strict_graph
        and len(writable_files) == 1
        and _is_exact_file_path(writable_files[0])
        and roots["mutationRoot"].replace("/**", "").rstrip("/") != writable_files[0].rstrip("/")
    ):
        return (
            f"taskContract.mutationRoot must equal its one exact writable file for {task_id}: "
            f"{roots['mutationRoot']} != {writable_files[0]}"
        )
    if strict_graph:
        for writable_file in writable_files:
            if "**" in writable_file and writable_file not in created_file_globs:
                return (
                    f"recursive writable scope over existing files is forbidden for {task_id}: "
                    f"{writable_file}"
                )
    for anchor in read_only_anchors:
        if any(_patterns_overlap(anchor, path) for path in writable_files + created_file_globs):
            return f"taskContract.readOnlyAnchors overlaps writable scope for {task_id}: {anchor}"

    verification = task_contract.get("verification", {})
    if not isinstance(verification, dict):
        return f"taskContract.verification must be an object for {task_id}"
    proof_files = normalized_string_list(task_contract.get("proofFiles"))
    quality_gates = normalized_string_list(verification.get("qualityGates"))
    if (
        proof_files
        and "software_test" in quality_gates
        and not any(_is_executable_software_test_proof(path) for path in proof_files)
    ):
        return (
            f"taskContract.verification.qualityGates requests software_test but "
            f"taskContract.proofFiles contains no executable test path for {task_id}"
        )
    for field, root_field in (
        ("writableFiles", "mutationRoot"),
        ("proofFiles", "proofRoot"),
        ("readOnlyAnchors", "authorityRoot"),
    ):
        for item in normalized_string_list(task_contract.get(field)):
            if not _path_within_root(item, roots[root_field]):
                return f"taskContract.{field} escapes {root_field} for {task_id}: {item} not under {roots[root_field]}"
    for item in created_file_globs:
        exact_proof_creation = (
            _is_exact_file_path(item)
            and _path_within_root(item, roots["proofRoot"])
            and item in proof_files
        )
        if not _path_within_root(item, roots["mutationRoot"]) and not exact_proof_creation:
            return f"taskContract.createdFileGlobs escapes mutationRoot for {task_id}: {item}"
    execution_plan = task_contract.get("executionPlan")
    if not isinstance(execution_plan, dict):
        return f"taskContract.executionPlan is required for {task_id}"
    if execution_plan.get("version") != "task-execution-plan.v1":
        return f"taskContract.executionPlan.version must be task-execution-plan.v1 for {task_id}"
    outcome = str(execution_plan.get("outcome") or "").strip()
    if not outcome:
        return f"taskContract.executionPlan.outcome is required for {task_id}"
    if strict_plan and outcome.lower() == str(task_contract.get("semanticHinge") or "").strip().lower():
        return f"taskContract.executionPlan.outcome must add detail beyond semanticHinge for {task_id}"
    steps = execution_plan.get("steps")
    if not isinstance(steps, list):
        return f"taskContract.executionPlan.steps must be a list for {task_id}"
    step_kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
    required = ["inspect_authority", "derive_delta", "apply_change", "verify"]
    if any(kind not in step_kinds for kind in required):
        return f"taskContract.executionPlan must include inspect, derive, apply, and verify steps for {task_id}"
    positions = [step_kinds.index(kind) for kind in required]
    if positions != sorted(positions):
        return f"taskContract.executionPlan steps are out of order for {task_id}"
    for index, step in enumerate(steps):
        if not isinstance(step, dict) or not str(step.get("instruction") or "").strip():
            return f"taskContract.executionPlan step instruction is required for {task_id}"
        references = step.get("references")
        if not isinstance(references, list) or not references:
            return f"taskContract.executionPlan step references are required for {task_id}"
        if strict_plan:
            for reference in references:
                if not isinstance(reference, str) or not _execution_plan_reference_valid(reference.strip(), task_contract):
                    return f"taskContract.executionPlan.steps[{index}] has unresolved reference {reference!r} for {task_id}"
            if step.get("kind") == "apply_change" and "mutationRoot" not in references:
                return f"taskContract.executionPlan apply_change must reference mutationRoot for {task_id}"
            if step.get("kind") == "verify" and "proofRoot" not in references:
                return f"taskContract.executionPlan verify must reference proofRoot for {task_id}"
    expected_changes = execution_plan.get("expectedChanges")
    if not isinstance(expected_changes, list) or not expected_changes:
        return f"taskContract.executionPlan.expectedChanges is required for {task_id}"
    if strict_plan:
        for index, change in enumerate(expected_changes):
            if not isinstance(change, dict) or change.get("target") != "mutationRoot":
                return f"taskContract.executionPlan.expectedChanges[{index}].target must be mutationRoot for {task_id}"
            if change.get("operation") not in ("add", "modify", "remove"):
                return f"taskContract.executionPlan.expectedChanges[{index}].operation is invalid for {task_id}"
            if not normalized_string_list(change.get("symbols")):
                return f"taskContract.executionPlan.expectedChanges[{index}].symbols is required for {task_id}"
            if not str(change.get("invariant") or "").strip():
                return f"taskContract.executionPlan.expectedChanges[{index}].invariant is required for {task_id}"
    if not normalized_string_list(execution_plan.get("completionChecks")):
        return f"taskContract.executionPlan.completionChecks is required for {task_id}"
    return None


def validate_repair_payload(payload: object) -> int:
    if not isinstance(payload, dict) or payload.get("kind") != "task_repair_result":
        return fail("kind must be task_repair_result")
    source_task_id = str(payload.get("sourceTaskId") or "").strip()
    try:
        uuid.UUID(source_task_id)
    except Exception as exc:
        return fail(f"invalid sourceTaskId {source_task_id}: {exc}")
    source_attempt = payload.get("sourceAttemptNumber")
    if not isinstance(source_attempt, int) or isinstance(source_attempt, bool) or source_attempt < 1:
        return fail("sourceAttemptNumber must be a positive integer")
    for field in ("title", "nextAction"):
        if field in payload and not isinstance(payload[field], str):
            return fail(f"{field} must be a string when provided")
    issue = validate_task_contract_local(payload.get("taskContract"), source_task_id, strict_plan=True)
    if issue:
        return fail(issue)
    print(json.dumps({
        "ok": True,
        "mode": "repair",
        "sourceTaskId": source_task_id,
        "sourceAttemptNumber": source_attempt,
    }))
    return 0


def main() -> int:
    repair_mode = len(sys.argv) == 3 and sys.argv[1] == "--repair"
    contract_required = len(sys.argv) in (3, 4) and sys.argv[1] == "--contract-required"
    if not repair_mode and not contract_required and len(sys.argv) not in (2, 3):
        print(
            "usage: validate_decomposition_json.py <decomposition.json> [max_task_count]\n"
            "       validate_decomposition_json.py --contract-required <decomposition.json> [max_task_count]\n"
            "       validate_decomposition_json.py --repair <task-repair-result.json>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[2] if (repair_mode or contract_required) else sys.argv[1])
    max_arg = sys.argv[3] if contract_required and len(sys.argv) == 4 else (
        sys.argv[2] if not contract_required and not repair_mode and len(sys.argv) == 3 else None
    )
    max_tasks = int(max_arg) if max_arg is not None else None

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if repair_mode:
        return validate_repair_payload(payload)

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
        if contract_required and not contract_mode:
            return fail(f"taskContract is required for contract-mode task {task.get('id', '<missing-id>')}")
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
            local_issue = validate_task_contract_local(
                task_contract,
                task_id,
                strict_plan=contract_required,
                strict_graph=contract_required,
                allow_read_only=task["taskType"] == "review" and task.get("reviewMode") == "gate_review",
            )
            if local_issue:
                return fail(local_issue)
            writable_files = list(task_contract.get("writableFiles", []))
            proof_files = list(task_contract.get("proofFiles", []))
            read_only_anchors = list(task_contract.get("readOnlyAnchors", []))
            output_artifacts = list(task_contract.get("outputArtifacts", []))
            authority_roots = sorted(
                {
                    root
                    for root in (classify_authority_root(path) for path in read_only_anchors)
                    if root
                }
            )
            writable_authority_roots = sorted(
                {
                    root
                    for root in (classify_authority_root(path) for path in writable_files)
                    if root
                }
            )
            effective_authority_roots = authority_roots or writable_authority_roots
            semantic_hinge = str(task_contract.get("semanticHinge", "")).lower()
            title_lower = str(task.get("title", "")).lower()
            authority_extraction = title_lower.startswith("extract ") and " authority facts" in title_lower
            proof_only = authority_extraction or ("prove " in title_lower and " exact parity " in title_lower)
            proof_only = proof_only or (
                str(task_contract.get("mutationRoot") or "").strip()
                == str(task_contract.get("proofRoot") or "").strip()
                and sorted(writable_files) == sorted(proof_files)
                and bool(proof_files)
            )
            if proof_only:
                if sorted(writable_files) != sorted(proof_files):
                    return fail(
                        f"proof-only task must keep writable scope equal to proof files for {task_id}: "
                        f"writable={writable_files} proof={proof_files}"
                    )
                if authority_extraction and not any(str(item).endswith(".json") for item in output_artifacts):
                    return fail(f"authority-extraction task must emit a json authority artifact for {task_id}")
            elif task.get("assignee") == "William":
                leaked_tests = [path for path in writable_files if "/__tests__/" in path]
                if leaked_tests:
                    return fail(f"William writable scope must not include test globs/files for {task_id}: {leaked_tests}")
                proof_creations = [
                    path
                    for path in normalized_string_list(task_contract.get("createdFileGlobs"))
                    if _path_within_root(path, str(task_contract.get("proofRoot") or ""))
                ]
                if contract_required and proof_creations:
                    return fail(
                        f"normal William task must not create proof files; split proof ownership for {task_id}: "
                        f"{proof_creations}"
                    )

            if (
                contract_required
                and task.get("taskType") == "execution"
                and not proof_only
                and proof_files
                and task_contract.get("primaryArtifactClass") != "docs"
            ):
                return fail(
                    f"normal implementation task must not declare proofFiles; split proof ownership for {task_id}: "
                    f"{proof_files}"
                )

            if contract_required:
                dependency_ids = set(task.get("dependsOn", []) or [])
                for token in normalized_string_list(task_contract.get("consumes")):
                    provider_ids = [provider_id for provider_id in providers.get(token, []) if provider_id != task_id]
                    if not provider_ids or not dependency_ids.intersection(provider_ids):
                        return fail(
                            f"taskContract.consumes token {token} requires explicit dependsOn provider for {task_id}: "
                            f"providers={provider_ids}"
                        )

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

                if title_lower.startswith("author task api workflow parity") and effective_authority_roots != ["task_api"]:
                    return fail(
                        f"task API parity authority must stay on task_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("prove task api workflow exact parity") and effective_authority_roots != ["task_api"]:
                    return fail(
                        f"task API proof authority must stay on task_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("author objective api workflow parity") and effective_authority_roots != ["objective_api"]:
                    return fail(
                        f"objective API parity authority must stay on objective_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("prove objective api workflow exact parity") and effective_authority_roots != ["objective_api"]:
                    return fail(
                        f"objective API proof authority must stay on objective_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("author worker-handler workflow parity") and effective_authority_roots != ["worker_handler"]:
                    return fail(
                        f"worker-handler parity authority must stay on worker_handler only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("prove worker-handler workflow exact parity") and effective_authority_roots != ["worker_handler"]:
                    return fail(
                        f"worker-handler proof authority must stay on worker_handler only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("author readiness/promotion workflow parity") and effective_authority_roots != ["readiness_promotion"]:
                    return fail(
                        f"readiness/promotion parity authority must stay on readiness_promotion only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower.startswith("prove readiness/promotion workflow exact parity") and effective_authority_roots != ["readiness_promotion"]:
                    return fail(
                        f"readiness/promotion proof authority must stay on readiness_promotion only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define shared task/objective workflow contract taxonomy" and authority_roots:
                    return fail(
                        f"shared taxonomy must consume prior proofs, not live sibling authority roots for {task_id}: {authority_roots}"
                    )
                if title_lower == "define ledgerevent repository boundary" and effective_authority_roots != ["prisma_schema"]:
                    return fail(
                        f"repository boundary authority must stay on prisma_schema only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define release workflow contract taxonomy" and effective_authority_roots != ["release_runtime"]:
                    return fail(
                        f"release taxonomy authority must stay on release_runtime only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define activation workflow contract taxonomy" and effective_authority_roots != ["activation_runtime"]:
                    return fail(
                        f"activation taxonomy authority must stay on activation_runtime only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define escalation workflow contract taxonomy" and effective_authority_roots != ["escalation_runtime"]:
                    return fail(
                        f"escalation taxonomy authority must stay on escalation_runtime only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "wire task api entrypoint emitters to the canonical ledger path" and effective_authority_roots != ["task_api"]:
                    return fail(
                        f"task API emitter authority must stay on task_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "wire objective api entrypoint emitters to the canonical ledger path" and effective_authority_roots != ["objective_api"]:
                    return fail(
                        f"objective API emitter authority must stay on objective_api only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "wire worker handler transition emitters to the canonical ledger path" and effective_authority_roots != ["worker_handler"]:
                    return fail(
                        f"worker handler emitter authority must stay on worker_handler only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "wire readiness/promotion transition emitters to the canonical ledger path" and effective_authority_roots != ["readiness_promotion"]:
                    return fail(
                        f"readiness/promotion emitter authority must stay on readiness_promotion only for {task_id}: {effective_authority_roots}"
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

    if contract_required:
        integration_tasks = [
            task
            for task in tasks
            if task.get("taskType") == "execution"
            and isinstance(task.get("taskContract"), dict)
            and task["taskContract"].get("primaryArtifactClass") == "integration_proof"
        ]
        if len(integration_tasks) != 1:
            return fail(
                f"contract-required graph must contain exactly one integration_proof task, found {len(integration_tasks)}"
            )
        integration = integration_tasks[0]
        integration_id = integration["id"]
        integration_dependencies = set(integration.get("dependsOn", []) or [])
        missing_integration_dependencies = (execution_ids - {integration_id}) - integration_dependencies
        if missing_integration_dependencies:
            return fail(
                "integration_proof missing execution dependencies: "
                f"{sorted(missing_integration_dependencies)}"
            )
        if integration_id not in gate_deps:
            return fail("gate_review must depend on the final integration_proof task")

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
