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

SUPPORTED_QUALITY_GATES = {
    "software_test",
    "software_lint",
    "software_build",
}

PRIMARY_ARTIFACT_CLASSES = {
    "contract_family",
    "schema_model",
    "repository_boundary",
    "writer",
    "emitter_wiring",
    "readback_query",
    "readback_api",
    "duplicate_prevention",
    "backfill",
    "docs",
    "code",
    "focused_proof",
    "integration_proof",
    "review_gate",
    "research_evidence",
    "content_draft",
    "content_package",
}

PRODUCTION_EVIDENCE_CATEGORIES = {
    "authentication_authorization",
    "input_validation_pagination",
    "persistence_migration",
    "concurrency_idempotency",
    "cross_backend_equivalence",
    "observability_failure_recovery",
    "final_integration_proof",
}

TASK_TYPE_ALLOWED_ASSIGNEES = {
    "execution": {"William", "Codex", "Librarian"},
    "review": {"Bernard", "Maeve", "Dolores", "Abdul", "operator"},
}


def canonical_agent(value: object) -> str:
    return str(value or "").strip().lower()


def canonical_slice_name(value: object) -> str:
    return re.sub(r"[ -]+", "_", canonical_agent(value))


def is_artifact_delivery_maeve_quality_task(task: dict, objective_contract: dict) -> bool:
    quality_slice_declared = any(
        isinstance(item, dict)
        and canonical_slice_name(item.get("name")) == "maeve_quality_review"
        for item in objective_contract.get("approvedSlices", [])
    )
    return (
        objective_contract.get("deliveryProfile") == "artifact_delivery"
        and quality_slice_declared
        and canonical_slice_name(task.get("title")) == "maeve_quality_review"
        and task.get("taskType") == "execution"
        and canonical_agent(task.get("assignee")) == "maeve"
    )

AUTHORITY_IMPACT_ROLES = {
    "implementation",
    "export",
    "composition",
    "persistence",
    "api",
    "integration_proof",
}


def classify_writable_cluster(path: str) -> str | None:
    cleaned = path.replace("**", "").rstrip("/")
    explicit_roots = [
        "apps/mission-control/prisma/schema.prisma",
        "apps/mission-control/prisma/migrations",
        "apps/mission-control/src/app/api/tasks",
        "apps/mission-control/src/app/api/objectives",
        "apps/mission-control/src/lib/workers/handlers.ts",
        "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts",
        "apps/mission-control/src/lib/workers/objective-runtime-source-sync.ts",
        "apps/mission-control/src/lib/release/objective-activation-service.ts",
        "apps/mission-control/src/lib/storage",
        "apps/mission-control/src/lib/decomposition",
        "apps/mission-control/src/lib/knowledge-plane",
        "apps/mission-control/docs",
    ]
    for root in explicit_roots:
        if _path_within_root(cleaned, root):
            return root
    if "/" not in cleaned:
        return cleaned or None
    return cleaned.rsplit("/", 1)[0]


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


def infer_expected_authority_token(title: str) -> str | None:
    title_lower = title.lower()
    if title_lower.startswith("extract task api workflow authority facts") or title_lower.startswith("author task api workflow parity contract slice"):
        return "task-api-authority-facts-v1"
    if title_lower.startswith("extract objective api workflow authority facts") or title_lower.startswith("author objective api workflow parity contract slice"):
        return "objective-api-authority-facts-v1"
    if title_lower.startswith("extract worker-handler workflow authority facts") or title_lower.startswith("author worker-handler workflow parity contract slice"):
        return "worker-handler-authority-facts-v1"
    if title_lower.startswith("extract readiness/promotion workflow authority facts") or title_lower.startswith("author readiness/promotion workflow parity contract slice"):
        return "readiness-promotion-authority-facts-v1"
    if title_lower.startswith("extract release workflow authority facts") or title_lower.startswith("author release workflow parity contract taxonomy"):
        return "release-workflow-authority-facts-v1"
    if title_lower.startswith("extract escalation workflow authority facts") or title_lower.startswith("author escalation workflow parity contract taxonomy"):
        return "escalation-workflow-authority-facts-v1"
    return None


def normalized_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    cleaned_values: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        cleaned = item.strip()
        if cleaned:
            cleaned_values.append(cleaned)
    return cleaned_values


def contract_without_additive_evidence(value: object) -> object:
    if not isinstance(value, dict):
        return value
    contract = {key: item for key, item in value.items() if key != "consumes"}
    execution_plan = contract.get("executionPlan")
    if not isinstance(execution_plan, dict):
        return contract
    plan = dict(execution_plan)
    steps = plan.get("steps")
    if isinstance(steps, list):
        plan["steps"] = [
            {
                **step,
                "references": [
                    reference
                    for reference in step.get("references", [])
                    if not (
                        isinstance(reference, str)
                        and reference.startswith("consumedToken:")
                    )
                ],
            }
            if isinstance(step, dict)
            else step
            for step in steps
        ]
    contract["executionPlan"] = plan
    return contract


def _task_started(task: dict) -> bool:
    return (
        task.get("status") not in (None, "pending", "ready")
        or task.get("releasedToHermes") is True
        or task.get("hermesDispatchStatus") not in (None, "not_released")
    )


def _safe_narrowing_contract(
    value: object,
    *,
    normalize_legacy_proof_class: bool = False,
) -> object:
    contract = contract_without_additive_evidence(value)
    if not isinstance(contract, dict):
        return contract
    narrowed = dict(contract)
    if (
        normalize_legacy_proof_class
        and narrowed.get("primaryArtifactClass") == "proof"
    ):
        narrowed["primaryArtifactClass"] = "focused_proof"
    narrowed.pop("executionPlan", None)
    verification = narrowed.get("verification")
    if isinstance(verification, dict):
        narrowed["verification"] = {
            key: item
            for key, item in verification.items()
            if key != "qualityGates"
        }
    return narrowed


def _safe_read_only_plan_narrowing(baseline_task: dict, proposed_task: dict) -> bool:
    baseline_contract = baseline_task.get("taskContract")
    proposed_contract = proposed_task.get("taskContract")
    if not isinstance(baseline_contract, dict) or not isinstance(proposed_contract, dict):
        return baseline_contract == proposed_contract
    baseline_plan = baseline_contract.get("executionPlan")
    proposed_plan = proposed_contract.get("executionPlan")
    is_gate = (
        baseline_task.get("taskType") == "review"
        and baseline_task.get("reviewMode") == "gate_review"
    )
    if not is_gate:
        return baseline_plan == proposed_plan
    if not isinstance(baseline_plan, dict) or not isinstance(proposed_plan, dict):
        return baseline_plan == proposed_plan
    baseline_without_apply = [
        step
        for step in baseline_plan.get("steps", [])
        if isinstance(step, dict) and step.get("kind") != "apply_change"
    ]
    return (
        baseline_plan.get("version") == proposed_plan.get("version")
        and baseline_plan.get("outcome") == proposed_plan.get("outcome")
        and baseline_plan.get("completionChecks") == proposed_plan.get("completionChecks")
        and proposed_plan.get("expectedChanges") == []
        and baseline_without_apply == proposed_plan.get("steps")
    )


def _with_valid_source_anchor_addition(
    baseline_contract: object,
    proposed_contract: object,
    objective_source_anchors: set[str],
) -> object:
    if not isinstance(baseline_contract, dict) or not isinstance(proposed_contract, dict):
        return proposed_contract
    baseline_anchors = normalized_string_list(baseline_contract.get("readOnlyAnchors"))
    proposed_anchors = normalized_string_list(proposed_contract.get("readOnlyAnchors"))
    baseline_set = set(baseline_anchors)
    proposed_set = set(proposed_anchors)
    added = proposed_set - baseline_set
    if not baseline_set.issubset(proposed_set) or not added.issubset(objective_source_anchors):
        return proposed_contract
    normalized = dict(proposed_contract)
    normalized["readOnlyAnchors"] = baseline_anchors
    return normalized


def _is_safe_unreleased_narrowing(
    baseline_task: dict,
    proposed_task: dict,
    *,
    objective_source_anchors: set[str] | None = None,
) -> bool:
    if _task_started(baseline_task):
        return False
    baseline_contract = baseline_task.get("taskContract")
    proposed_contract = proposed_task.get("taskContract")
    comparable_proposed_contract = _with_valid_source_anchor_addition(
        baseline_contract,
        proposed_contract,
        objective_source_anchors or set(),
    )
    if (
        _safe_narrowing_contract(
            baseline_contract,
            normalize_legacy_proof_class=True,
        )
        != _safe_narrowing_contract(comparable_proposed_contract)
        or not _safe_read_only_plan_narrowing(baseline_task, proposed_task)
    ):
        return False
    baseline_verification = (
        baseline_contract.get("verification")
        if isinstance(baseline_contract, dict)
        else {}
    )
    proposed_verification = (
        proposed_contract.get("verification")
        if isinstance(proposed_contract, dict)
        else {}
    )
    baseline_gates = set(normalized_string_list(
        baseline_verification.get("qualityGates")
        if isinstance(baseline_verification, dict)
        else []
    ))
    proposed_gates = set(normalized_string_list(
        proposed_verification.get("qualityGates")
        if isinstance(proposed_verification, dict)
        else []
    ))
    return proposed_gates.issubset(baseline_gates)


def fail(message: str) -> int:
    print(f"INVALID: {message}", file=sys.stderr)
    return 1


def _path_within_root(path: str, root: str) -> bool:
    clean_path = path.replace("/**", "").rstrip("/")
    clean_root = root.replace("/**", "").rstrip("/")
    return bool(clean_path and clean_root) and (
        clean_path == clean_root or clean_path.startswith(clean_root + "/")
    )

def _is_cross_family_root_overuse(usages: list[tuple[str, str]]) -> bool:
    workflow_families = {family for _task_id, family in usages if family}
    return len(usages) >= 4 and len(workflow_families) > 1


def _compact_scope_roots(values: list[str]) -> list[str]:
    roots = sorted(
        {value.replace("/**", "").rstrip("/") for value in values if value.strip()},
        key=lambda value: (len(value), value),
    )
    compacted: list[str] = []
    for root in roots:
        if any(_path_within_root(root, existing) for existing in compacted):
            continue
        compacted.append(root)
    return compacted


def _has_glob(path: str) -> bool:
    return any(marker in path for marker in ("*", "?", "[", "]", "{", "}"))


def _is_exact_file_path(path: str) -> bool:
    return bool(path.strip()) and not _has_glob(path) and "." in path.rstrip("/").split("/")[-1]


def _patterns_overlap(left: str, right: str) -> bool:
    return _path_within_root(left, right) or _path_within_root(right, left)


def _is_executable_software_test_proof(path: str) -> bool:
    normalized = path.strip().replace("\\", "/").removeprefix("./")
    package_relative = normalized.removeprefix("apps/mission-control/")
    mission_control_roots = (
        "src/app",
        "src/components",
        "src/lib/__tests__",
        "src/lib/attempt-classification",
        "src/lib/decomposition",
        "src/lib/knowledge-plane",
        "src/lib/auth",
        "src/lib/bernard",
        "src/lib/release",
        "src/lib/workers",
        "src/lib/storage",
        "src/lib/inbox",
        "src/lib/hermes-sync",
        "src/lib/tasks",
    )
    test_suffix = bool(
        re.search(r"\.(?:test|spec)\.(?:[cm]?[jt]sx?|mjs|cjs)$", package_relative, re.IGNORECASE)
    )
    if normalized.startswith("apps/mission-control/"):
        return test_suffix and any(
            package_relative.startswith(f"{root}/") for root in mission_control_roots
        )
    return bool(
        re.search(r"(?:^|/)__tests__/.+\.[cm]?[jt]sx?$", normalized)
        or test_suffix
    )


def _execution_plan_reference_valid(reference: str, task_contract: dict) -> bool:
    if reference in ("authorityRoot", "mutationRoot", "proofRoot"):
        return bool(str(task_contract.get(reference) or "").strip())
    if reference.startswith("consumedToken:"):
        return reference.removeprefix("consumedToken:") in normalized_string_list(
            task_contract.get("consumes")
        )
    if reference.startswith("outputArtifact:"):
        try:
            index = int(reference.removeprefix("outputArtifact:"))
        except ValueError:
            return False
        return 0 <= index < len(normalized_string_list(task_contract.get("outputArtifacts")))
    return False


def _local_finding(
    code: str,
    message: str,
    task_id: str,
    *,
    paths: list[str] | None = None,
) -> dict:
    return {
        "code": code,
        "group": "task",
        "taskId": task_id,
        "requirementId": None,
        "paths": paths or [],
        "dependencyReferences": [],
        "message": message,
    }


def collect_task_contract_local_findings(
    task_contract: object,
    task_id: str,
    *,
    strict_plan: bool = False,
    strict_graph: bool = False,
    allow_read_only: bool = False,
) -> list[dict]:
    findings: list[dict] = []

    def add(code: str, message: str, paths: list[str] | None = None) -> None:
        findings.append(_local_finding(code, message, task_id, paths=paths))

    if not isinstance(task_contract, dict):
        add("task_contract_missing", f"taskContract must be an object for {task_id}")
        return findings
    if task_contract.get("version") != "task-contract.v1":
        add("task_contract_version_invalid", f"taskContract.version must be task-contract.v1 for {task_id}")
    artifact_class = str(task_contract.get("primaryArtifactClass") or "").strip()
    if artifact_class not in PRIMARY_ARTIFACT_CLASSES:
        add(
            "primary_artifact_class_invalid",
            f"taskContract.primaryArtifactClass is unsupported for {task_id}: {artifact_class}",
        )

    roots = {
        field: str(task_contract.get(field) or "").strip()
        for field in ("mutationRoot", "authorityRoot", "proofRoot")
    }
    for field, value in roots.items():
        if not value:
            add(f"{field}_missing", f"taskContract.{field} is required for {task_id}")
    authority_root = roots["authorityRoot"]
    proof_root = roots["proofRoot"]
    mutation_root = roots["mutationRoot"]
    docs_slice = (
        task_contract.get("primaryArtifactClass") == "docs"
        or mutation_root.endswith((".md", ".mdx"))
        or "/docs/" in mutation_root
    )
    if (
        strict_graph
        and docs_slice
        and mutation_root
        and proof_root
        and mutation_root != proof_root
    ):
        add(
            "docs_proof_root_mismatch",
            f"documentation task must verify mutationRoot for {task_id}: {proof_root} != {mutation_root}",
            [proof_root, mutation_root],
        )
    if strict_graph and authority_root and authority_root.replace("/**", "").rstrip("/") in GENERIC_AUTHORITY_ROOTS:
        add(
            "authority_root_too_broad",
            f"taskContract.authorityRoot is too broad for {task_id}: {authority_root}",
            [authority_root],
        )
    if strict_graph and proof_root and not _is_exact_file_path(proof_root):
        add(
            "proof_root_not_exact",
            f"taskContract.proofRoot must be one exact proof path for {task_id}: {proof_root}",
            [proof_root],
        )
    for field in ("semanticHinge", "acceptanceHinge"):
        if not str(task_contract.get(field) or "").strip():
            add(f"{field}_missing", f"taskContract.{field} is required for {task_id}")

    list_fields = (
        "writableFiles",
        "proofFiles",
        "createdFileGlobs",
        "readOnlyAnchors",
        "outputArtifacts",
        "provides",
        "consumes",
    )
    for field in list_fields:
        values = task_contract.get(field, [])
        if not isinstance(values, list):
            add("contract_list_invalid", f"taskContract.{field} must be a list for {task_id}")
            continue
        invalid_items = [item for item in values if not isinstance(item, str)]
        if invalid_items:
            add("contract_list_item_invalid", f"taskContract.{field} must contain only strings for {task_id}")
        escaped = [item for item in values if isinstance(item, str) and "\\*\\*" in item]
        for item in escaped:
            add("escaped_glob", f"escaped glob found in taskContract.{field}: {item}", [item])

    writable_files = normalized_string_list(task_contract.get("writableFiles"))
    created_file_globs = normalized_string_list(task_contract.get("createdFileGlobs"))
    proof_files = normalized_string_list(task_contract.get("proofFiles"))
    read_only_anchors = normalized_string_list(task_contract.get("readOnlyAnchors"))
    if strict_graph and docs_slice and proof_files:
        add(
            "implementation_owns_proof",
            f"documentation task must not declare proofFiles for {task_id}",
            proof_files,
        )
    if not writable_files and not allow_read_only:
        add("writable_files_missing", f"taskContract.writableFiles is required for executable task {task_id}")
    if (
        strict_graph
        and mutation_root
        and len(writable_files) == 1
        and _is_exact_file_path(writable_files[0])
        and mutation_root.replace("/**", "").rstrip("/") != writable_files[0].rstrip("/")
    ):
        add(
            "mutation_root_exact_file_mismatch",
            f"taskContract.mutationRoot must equal its one exact writable file for {task_id}: "
            f"{mutation_root} != {writable_files[0]}",
            [mutation_root, writable_files[0]],
        )
    if strict_graph:
        for writable_file in writable_files:
            if "**" in writable_file and writable_file not in created_file_globs:
                add(
                    "recursive_existing_writable_scope",
                    f"recursive writable scope over existing files is forbidden for {task_id}: {writable_file}",
                    [writable_file],
                )
        if (
            not allow_read_only
            and len(writable_files) == 1
            and _is_exact_file_path(writable_files[0])
            and mutation_root == writable_files[0]
            and writable_files[0] not in created_file_globs
        ):
            add(
                "exact_writable_creation_authorization_missing",
                f"one-file executable task must creation-authorize its exact mutationRoot for {task_id}: "
                f"{writable_files[0]}",
                [writable_files[0]],
            )
    for anchor in read_only_anchors:
        if any(_patterns_overlap(anchor, path) for path in writable_files + created_file_globs):
            add(
                "read_only_writable_overlap",
                f"taskContract.readOnlyAnchors overlaps writable scope for {task_id}: {anchor}",
                [anchor],
            )

    verification = task_contract.get("verification", {})
    if not isinstance(verification, dict):
        add("verification_invalid", f"taskContract.verification must be an object for {task_id}")
        verification = {}
    focused_tests = normalized_string_list(verification.get("focusedTests"))
    quality_gates = normalized_string_list(verification.get("qualityGates"))
    proof_only = (
        bool(proof_files)
        and mutation_root == proof_root
        and sorted(writable_files) == sorted(proof_files)
        and "software_test" in quality_gates
    )
    if artifact_class == "focused_proof" and not proof_only:
        add(
            "focused_proof_scope_invalid",
            f"focused_proof must own exactly its executable proofFiles for {task_id}",
            sorted(set(writable_files + proof_files)),
        )
    if strict_graph and proof_only and artifact_class not in {"focused_proof", "integration_proof"}:
        add(
            "proof_artifact_class_invalid",
            f"proof-only task must use focused_proof for {task_id}: {artifact_class}",
            proof_files,
        )
    production_evidence = task_contract.get("productionEvidence", [])
    if not isinstance(production_evidence, list):
        add("production_evidence_invalid", f"taskContract.productionEvidence must be a list for {task_id}")
        production_evidence = []
    provides = set(normalized_string_list(task_contract.get("provides")))
    for declaration in production_evidence:
        if not isinstance(declaration, dict):
            add("production_evidence_invalid", f"production evidence declaration must be an object for {task_id}")
            continue
        category = str(declaration.get("category") or "").strip()
        token = str(declaration.get("evidenceToken") or "").strip()
        if category not in PRODUCTION_EVIDENCE_CATEGORIES:
            add("production_evidence_category_invalid", f"unknown production evidence category for {task_id}: {category}")
        if not token or token not in provides:
            add(
                "production_evidence_token_invalid",
                f"production evidence token must be declared in provides for {task_id}: {token}",
            )
    for quality_gate in quality_gates:
        if quality_gate not in SUPPORTED_QUALITY_GATES:
            add(
                "unsupported_quality_gate",
                f"unsupported quality gate for {task_id}: {quality_gate}",
                [quality_gate],
            )
    if "software_test" in quality_gates:
        if strict_graph and not proof_files:
            add(
                "software_test_proof_missing",
                f"software_test requires declared proofFiles for {task_id}",
            )
        elif proof_files and not any(_is_executable_software_test_proof(path) for path in proof_files):
            add(
                "software_test_proof_not_executable",
                f"software_test proof scope is not executable for {task_id}",
                proof_files,
            )
        outside = [path for path in focused_tests if path not in proof_files] if strict_graph else []
        if outside:
            add(
                "focused_test_outside_proof_scope",
                f"software_test focused tests escape proofFiles for {task_id}: {outside}",
                outside,
            )

    for field, root_field in (
        ("writableFiles", "mutationRoot"),
        ("proofFiles", "proofRoot"),
    ):
        root = roots[root_field]
        if not root:
            continue
        for item in normalized_string_list(task_contract.get(field)):
            if not _path_within_root(item, root):
                add(
                    f"{field}_outside_{root_field}",
                    f"taskContract.{field} escapes {root_field} for {task_id}: {item} not under {root}",
                    [item, root],
                )
    if strict_graph or strict_plan:
        for anchor in read_only_anchors:
            if authority_root and _path_within_root(anchor, authority_root):
                continue
            if not _is_exact_file_path(anchor):
                add(
                    "read_only_anchor_broad_sibling_scope",
                    f"taskContract.readOnlyAnchors may use only exact preserve-only files outside "
                    f"authorityRoot for {task_id}: {anchor}",
                    [anchor, authority_root],
                )
    for item in created_file_globs:
        exact_proof_creation = (
            proof_root
            and _is_exact_file_path(item)
            and _path_within_root(item, proof_root)
            and item in proof_files
        )
        if mutation_root and not _path_within_root(item, mutation_root) and not exact_proof_creation:
            add(
                "created_file_outside_mutation_root",
                f"taskContract.createdFileGlobs escapes mutationRoot for {task_id}: {item}",
                [item, mutation_root],
            )

    execution_plan = task_contract.get("executionPlan")
    if not isinstance(execution_plan, dict):
        add("execution_plan_missing", f"taskContract.executionPlan is required for {task_id}")
        return findings
    if execution_plan.get("version") != "task-execution-plan.v1":
        add(
            "execution_plan_version_invalid",
            f"taskContract.executionPlan.version must be task-execution-plan.v1 for {task_id}",
        )
    outcome = str(execution_plan.get("outcome") or "").strip()
    if not outcome:
        add("execution_plan_outcome_missing", f"taskContract.executionPlan.outcome is required for {task_id}")
    if strict_plan and outcome and outcome.lower() == str(task_contract.get("semanticHinge") or "").strip().lower():
        add(
            "execution_plan_outcome_not_specific",
            f"taskContract.executionPlan.outcome must add detail beyond semanticHinge for {task_id}",
        )

    steps = execution_plan.get("steps")
    required_step_kinds = (
        ["inspect_authority", "derive_delta", "verify"]
        if allow_read_only
        else ["inspect_authority", "derive_delta", "apply_change", "verify"]
    )
    if not isinstance(steps, list):
        add("execution_plan_steps_invalid", f"taskContract.executionPlan.steps must be a list for {task_id}")
        steps = []
    step_kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
    missing_kinds = [kind for kind in required_step_kinds if kind not in step_kinds]
    if missing_kinds:
        add(
            "execution_plan_steps_missing",
            f"taskContract.executionPlan is missing steps for {task_id}: {missing_kinds}",
        )
    elif [step_kinds.index(kind) for kind in required_step_kinds] != sorted(
        step_kinds.index(kind) for kind in required_step_kinds
    ):
        add("execution_plan_steps_out_of_order", f"taskContract.executionPlan steps are out of order for {task_id}")
    if allow_read_only and "apply_change" in step_kinds:
        add(
            "read_only_execution_plan_applies_change",
            f"read-only gate review executionPlan must not include apply_change for {task_id}",
        )
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            add("execution_plan_step_invalid", f"taskContract.executionPlan.steps[{index}] must be an object for {task_id}")
            continue
        if not str(step.get("instruction") or "").strip():
            add("execution_plan_instruction_missing", f"taskContract.executionPlan step instruction is required for {task_id}")
        references = step.get("references")
        if not isinstance(references, list) or not references:
            add("execution_plan_references_missing", f"taskContract.executionPlan step references are required for {task_id}")
            continue
        if strict_plan:
            for reference in references:
                if not isinstance(reference, str) or not _execution_plan_reference_valid(reference.strip(), task_contract):
                    add(
                        "execution_plan_reference_unresolved",
                        f"taskContract.executionPlan.steps[{index}] has unresolved reference {reference!r} for {task_id}",
                    )
            if step.get("kind") == "apply_change" and "mutationRoot" not in references:
                add("execution_plan_apply_reference_missing", f"taskContract.executionPlan apply_change must reference mutationRoot for {task_id}")
            if step.get("kind") == "verify" and "proofRoot" not in references:
                add("execution_plan_verify_reference_missing", f"taskContract.executionPlan verify must reference proofRoot for {task_id}")

    expected_changes = execution_plan.get("expectedChanges")
    if allow_read_only:
        if not isinstance(expected_changes, list) or expected_changes:
            add(
                "read_only_execution_plan_expected_changes",
                f"read-only gate review executionPlan.expectedChanges must be empty for {task_id}",
            )
        expected_changes = []
    elif not isinstance(expected_changes, list) or not expected_changes:
        add("execution_plan_expected_changes_missing", f"taskContract.executionPlan.expectedChanges is required for {task_id}")
        expected_changes = []
    if strict_plan:
        for index, change in enumerate(expected_changes):
            if not isinstance(change, dict):
                add("execution_plan_expected_change_invalid", f"taskContract.executionPlan.expectedChanges[{index}] must be an object for {task_id}")
                continue
            if change.get("target") != "mutationRoot":
                add("execution_plan_expected_change_target_invalid", f"taskContract.executionPlan.expectedChanges[{index}].target must be mutationRoot for {task_id}")
            if change.get("operation") not in ("add", "modify", "remove"):
                add("execution_plan_expected_change_operation_invalid", f"taskContract.executionPlan.expectedChanges[{index}].operation is invalid for {task_id}")
            if not normalized_string_list(change.get("symbols")):
                add("execution_plan_expected_change_symbols_missing", f"taskContract.executionPlan.expectedChanges[{index}].symbols is required for {task_id}")
            if not str(change.get("invariant") or "").strip():
                add("execution_plan_expected_change_invariant_missing", f"taskContract.executionPlan.expectedChanges[{index}].invariant is required for {task_id}")
    if not normalized_string_list(execution_plan.get("completionChecks")):
        add("execution_plan_completion_checks_missing", f"taskContract.executionPlan.completionChecks is required for {task_id}")
    return findings


def validate_task_contract_local(
    task_contract: object,
    task_id: str,
    *,
    strict_plan: bool = False,
    strict_graph: bool = False,
    allow_read_only: bool = False,
) -> str | None:
    findings = collect_task_contract_local_findings(
        task_contract,
        task_id,
        strict_plan=strict_plan,
        strict_graph=strict_graph,
        allow_read_only=allow_read_only,
    )
    return findings[0]["message"] if findings else None


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
    issue = validate_task_contract_local(
        payload.get("taskContract"),
        source_task_id,
        strict_plan=True,
        strict_graph=True,
    )
    if issue:
        return fail(issue)
    print(json.dumps({
        "ok": True,
        "mode": "repair",
        "sourceTaskId": source_task_id,
        "sourceAttemptNumber": source_attempt,
    }))
    return 0


def _graph_finding(
    code: str,
    group: str,
    message: str,
    *,
    task_id: str | None = None,
    requirement_id: str | None = None,
    paths: list[str] | None = None,
    dependencies: list[str] | None = None,
) -> dict:
    return {
        "code": code,
        "group": group,
        "taskId": task_id,
        "requirementId": requirement_id,
        "paths": paths or [],
        "dependencyReferences": dependencies or [],
        "message": message,
    }


def _find_dependency_cycles(tasks: list[dict]) -> list[list[str]]:
    task_ids = {
        str(task.get("id") or "").strip()
        for task in tasks
        if str(task.get("id") or "").strip()
    }
    dependencies = {
        str(task.get("id") or "").strip(): sorted(
            dependency
            for dependency in normalized_string_list(task.get("dependsOn"))
            if dependency != str(task.get("id") or "").strip()
            and dependency in task_ids
        )
        for task in tasks
        if str(task.get("id") or "").strip()
    }
    state: dict[str, str] = {}
    stack: list[str] = []
    cycle_keys: set[str] = set()
    cycles: list[list[str]] = []

    def record_cycle(cycle: list[str]) -> None:
        nodes = cycle[:-1]
        first = min(nodes)
        first_index = nodes.index(first)
        canonical_nodes = nodes[first_index:] + nodes[:first_index]
        canonical_cycle = canonical_nodes + [canonical_nodes[0]]
        key = "->".join(canonical_cycle)
        if key not in cycle_keys:
            cycle_keys.add(key)
            cycles.append(canonical_cycle)

    def visit(task_id: str) -> None:
        if state.get(task_id) == "visited":
            return
        state[task_id] = "visiting"
        stack.append(task_id)
        for dependency_id in dependencies.get(task_id, []):
            if state.get(dependency_id) == "visiting":
                cycle_start = stack.index(dependency_id)
                record_cycle(stack[cycle_start:] + [dependency_id])
            else:
                visit(dependency_id)
        stack.pop()
        state[task_id] = "visited"

    for task_id in sorted(dependencies):
        visit(task_id)
    return sorted(cycles, key=lambda cycle: "->".join(cycle))


def collect_contract_required_findings(
    payload: object,
    *,
    max_tasks: int | None,
    objective: object | None = None,
    manifest: object | None = None,
) -> list[dict]:
    findings: list[dict] = []
    if not isinstance(payload, dict):
        return [_graph_finding("payload_invalid", "objective_coverage", "payload must be an object")]
    if payload.get("kind") != "decomposition_result":
        findings.append(_graph_finding("kind_invalid", "objective_coverage", "kind must be decomposition_result"))
    objective_owner = str(objective.get("owner") or "Bernard") if isinstance(objective, dict) else "Bernard"
    allowed_actors = {objective_owner, "Dolores", "Bernard"}
    if payload.get("actor") not in allowed_actors:
        findings.append(_graph_finding(
            "actor_invalid",
            "objective_coverage",
            f"actor must be one of {sorted(allowed_actors)}",
        ))
    is_amendment = payload.get("operation") == "amend"
    if is_amendment:
        if payload.get("requestReview") is not False:
            findings.append(_graph_finding("amendment_review_request_invalid", "objective_coverage", "amendment requestReview must be false"))
        if not isinstance(payload.get("decompositionContract"), dict):
            findings.append(_graph_finding("amendment_contract_missing", "objective_coverage", "amendment decompositionContract must be an object"))
        if isinstance(manifest, dict):
            if manifest.get("operation") != "amend":
                findings.append(_graph_finding("manifest_amendment_operation_missing", "objective_coverage", "amendment manifest operation must be amend"))
            if not isinstance(manifest.get("decompositionContractPatch"), dict):
                findings.append(_graph_finding("manifest_amendment_contract_patch_missing", "objective_coverage", "amendment manifest requires decompositionContractPatch"))
    elif payload.get("requestReview") is not True:
        findings.append(_graph_finding("review_request_missing", "objective_coverage", "requestReview must be true"))
    tasks = payload.get("tasks")
    if not isinstance(tasks, list) or not tasks:
        findings.append(_graph_finding("tasks_missing", "objective_coverage", "tasks must be a non-empty list"))
        return findings
    if max_tasks is not None and len(tasks) > max_tasks:
        findings.append(
            _graph_finding(
                "task_count_exceeded",
                "objective_coverage",
                f"task count {len(tasks)} exceeds max {max_tasks}",
            )
        )

    objective_contract = (
        objective.get("decompositionContract")
        if isinstance(objective, dict)
        else None
    )
    approved_slices = (
        objective_contract.get("approvedSlices")
        if isinstance(objective_contract, dict)
        else None
    )
    if isinstance(approved_slices, list) and approved_slices and len(tasks) != len(approved_slices):
        findings.append(
            _graph_finding(
                "task_count_mismatch_contract",
                "objective_coverage",
                (
                    f"task count {len(tasks)} must equal approved slice count "
                    f"{len(approved_slices)}"
                ),
            )
        )

    valid_tasks = [task for task in tasks if isinstance(task, dict)]
    if len(valid_tasks) != len(tasks):
        findings.append(_graph_finding("task_invalid", "task", "every task must be an object"))
    task_ids = [str(task.get("id") or "").strip() for task in valid_tasks]
    task_id_set = {task_id for task_id in task_ids if task_id}
    seen_ids: set[str] = set()
    providers: dict[str, list[str]] = {}
    output_artifact_owners: dict[str, list[str]] = {}
    root_usage: dict[str, dict[str, list[tuple[str, str]]]] = {
        "authorityRoot": {},
        "proofRoot": {},
    }
    for task, task_id in zip(valid_tasks, task_ids):
        if not task_id:
            findings.append(_graph_finding("task_id_missing", "task", "task id is required"))
            continue
        try:
            uuid.UUID(task_id)
        except Exception:
            findings.append(_graph_finding("task_id_invalid", "task", f"invalid UUID {task_id}", task_id=task_id))
        if task_id in seen_ids:
            findings.append(_graph_finding("task_id_duplicate", "dependency_graph", f"duplicate task id {task_id}", task_id=task_id))
        seen_ids.add(task_id)
        contract = task.get("taskContract")
        if isinstance(contract, dict):
            if task.get("taskType") == "execution":
                for token in normalized_string_list(contract.get("provides")):
                    providers.setdefault(token, []).append(task_id)
            for artifact in normalized_string_list(contract.get("outputArtifacts")):
                output_artifact_owners.setdefault(artifact, []).append(task_id)
            workflow_family = str(contract.get("workflowFamily") or "").strip()
            for field in root_usage:
                root = str(contract.get(field) or "").strip()
                if root:
                    root_usage[field].setdefault(root, []).append(
                        (task_id, workflow_family)
                    )

    for field, usages_by_root in root_usage.items():
        for root, usages in usages_by_root.items():
            workflow_families = {family for _task_id, family in usages if family}
            if _is_cross_family_root_overuse(usages):
                findings.append(
                    _graph_finding(
                        f"{field}_cross_family_reuse",
                        "objective_coverage",
                        (
                            f"taskContract.{field} is reused across unrelated workflow "
                            f"families for {root}: {sorted(workflow_families)}"
                        ),
                        paths=[root],
                        dependencies=[task_id for task_id, _family in usages],
                    )
                )

    for task, task_id in zip(valid_tasks, task_ids):
        contract = task.get("taskContract")
        if not isinstance(contract, dict):
            continue
        proof_root = str(contract.get("proofRoot") or "").strip()
        artifact_paths = [
            str(contract.get("authorityRoot") or "").strip(),
            *normalized_string_list(contract.get("readOnlyAnchors")),
            *normalized_string_list(contract.get("proofFiles")),
        ]
        for artifact_path in [path for path in artifact_paths if path]:
            if proof_root and _path_within_root(artifact_path, proof_root):
                continue
            sibling_owners = [
                owner
                for owner in output_artifact_owners.get(artifact_path, [])
                if owner != task_id
            ]
            if sibling_owners:
                findings.append(
                    _graph_finding(
                        "generic_proof_artifact_reused",
                        "dependency_graph",
                        (
                            f"task artifact authority reuses a sibling output outside "
                            f"its proofRoot: {artifact_path}"
                        ),
                        task_id=task_id,
                        paths=[artifact_path],
                        dependencies=sibling_owners,
                    )
                )

    objective_contract = (
        payload.get("decompositionContract")
        if is_amendment and isinstance(payload.get("decompositionContract"), dict)
        else objective.get("decompositionContract")
        if isinstance(objective, dict)
        and isinstance(objective.get("decompositionContract"), dict)
        else {}
    )
    objective_scope_clusters = _compact_scope_roots(
        normalized_string_list(objective_contract.get("allowedExpansionZone"))
        + normalized_string_list(objective_contract.get("sourceAnchors"))
    )
    artifact_delivery = (
        objective_contract.get("deliveryProfile") == "artifact_delivery"
        or (
            isinstance(objective, dict)
            and objective.get("deliveryProfile") == "artifact_delivery"
        )
    )
    documentation_surfaces = [
        surface
        for surface in normalized_string_list(objective_contract.get("touchedSurfaces"))
        if re.search(r"\b(documentation|docs)\b", surface, re.IGNORECASE)
    ]
    documentation_authorized = any(
        "docs" in zone.replace("**", "").strip("/").split("/")
        for zone in normalized_string_list(objective_contract.get("allowedExpansionZone"))
    )
    documentation_owners = [
        task
        for task in valid_tasks
        if isinstance(task.get("taskContract"), dict)
        and (
            task["taskContract"].get("primaryArtifactClass") == "docs"
            or str(task["taskContract"].get("mutationRoot") or "").endswith((".md", ".mdx"))
            or "/docs/" in str(task["taskContract"].get("mutationRoot") or "")
        )
    ]
    if documentation_authorized and documentation_surfaces and not documentation_owners:
        for surface in documentation_surfaces:
            findings.append(
                _graph_finding(
                    "touched_surface_owner_missing",
                    "objective_coverage",
                    f"touched surface has no bounded docs task owner: {surface}",
                    paths=[surface],
                )
            )
    review_tasks: list[dict] = []
    execution_ids: set[str] = set()
    for task, task_id in zip(valid_tasks, task_ids):
        for field in CONTRACT_MODE_REQUIRED_TASK_FIELDS:
            if field not in task:
                findings.append(
                    _graph_finding(
                        "task_field_missing",
                        "task",
                        f"task missing required field {field}",
                        task_id=task_id or None,
                    )
                )
        task_type = task.get("taskType")
        if task_type not in ("execution", "review"):
            findings.append(
                _graph_finding(
                    "task_type_invalid",
                    "task",
                    f"invalid taskType {task_type!r} for {task_id}",
                    task_id=task_id or None,
                )
            )
        elif task_type == "review":
            review_tasks.append(task)
        elif task_id:
            execution_ids.add(task_id)
        assignee = task.get("assignee")
        artifact_quality_assignment = is_artifact_delivery_maeve_quality_task(task, objective_contract)
        if (
            task_type in TASK_TYPE_ALLOWED_ASSIGNEES
            and canonical_agent(assignee) not in {
                canonical_agent(allowed) for allowed in TASK_TYPE_ALLOWED_ASSIGNEES[task_type]
            }
            and not artifact_quality_assignment
        ):
            findings.append(
                _graph_finding(
                    "task_assignee_incompatible",
                    "task",
                    f"assignee {assignee!r} cannot perform taskType {task_type!r} for {task_id}",
                    task_id=task_id or None,
                )
            )
        if task.get("priority") not in ("P1", "P2", "P3"):
            findings.append(
                _graph_finding(
                    "priority_invalid",
                    "task",
                    f"invalid priority {task.get('priority')!r} for {task_id}",
                    task_id=task_id or None,
                )
            )
        contract = task.get("taskContract")
        findings.extend(
            collect_task_contract_local_findings(
                contract,
                task_id or "<missing-id>",
                strict_plan=True,
                strict_graph=True,
                allow_read_only=task_type == "review" and task.get("reviewMode") == "gate_review",
            )
        )
        if artifact_delivery and task_type == "execution" and isinstance(contract, dict):
            quality_gates = normalized_string_list(
                contract.get("verification", {}).get("qualityGates")
                if isinstance(contract.get("verification"), dict)
                else []
            )
            for quality_gate in quality_gates:
                findings.append(
                    _graph_finding(
                        "quality_gate_unsupported",
                        "task",
                        f"artifact_delivery does not run software quality gate {quality_gate} for {task_id}",
                        task_id=task_id or None,
                    )
                )
            if contract.get("primaryArtifactClass") == "integration_proof":
                findings.append(
                    _graph_finding(
                        "primary_artifact_class_invalid",
                        "task",
                        f"artifact_delivery uses content evidence, not integration_proof, for {task_id}",
                        task_id=task_id or None,
                    )
                )
            if not normalized_string_list(contract.get("outputArtifacts")):
                findings.append(
                    _graph_finding(
                        "output_artifact_missing",
                        "task",
                        f"artifact_delivery task must declare an output artifact for {task_id}",
                        task_id=task_id or None,
                    )
                )
            if not normalized_string_list(contract.get("provides")):
                findings.append(
                    _graph_finding(
                        "evidence_provider_missing",
                        "task",
                        f"artifact_delivery task must provide phase-run evidence for {task_id}",
                        task_id=task_id or None,
                    )
                )
        dependency_ids = normalized_string_list(task.get("dependsOn"))
        missing_dependencies = [dep for dep in dependency_ids if dep not in task_id_set]
        for dependency in missing_dependencies:
            findings.append(
                _graph_finding(
                    "dependency_not_found",
                    "dependency_graph",
                    f"dependsOn {dependency} not found for task {task_id}",
                    task_id=task_id or None,
                    dependencies=[dependency],
                )
            )
        if not isinstance(contract, dict):
            continue
        writable_files = normalized_string_list(contract.get("writableFiles"))
        proof_files = normalized_string_list(contract.get("proofFiles"))
        created_files = normalized_string_list(contract.get("createdFileGlobs"))
        mutation_root = str(contract.get("mutationRoot") or "").strip()
        authority_root = str(contract.get("authorityRoot") or "").strip()
        proof_root = str(contract.get("proofRoot") or "").strip()
        if authority_root and any(
            _path_within_root(authority_root, created_file) for created_file in created_files
        ):
            findings.append(
                _graph_finding(
                    "authority_root_created_by_task",
                    "task",
                    f"authorityRoot cannot be created by the same task for {task_id}: {authority_root}",
                    task_id=task_id or None,
                    paths=[authority_root],
                )
            )
        docs_slice = (
            contract.get("primaryArtifactClass") == "docs"
            or mutation_root.endswith((".md", ".mdx"))
            or "/docs/" in mutation_root
        )
        verification = contract.get("verification")
        quality_gates = (
            normalized_string_list(verification.get("qualityGates"))
            if isinstance(verification, dict)
            else []
        )
        proof_only = (
            bool(proof_files)
            and mutation_root == proof_root
            and sorted(writable_files) == sorted(proof_files)
            and "software_test" in quality_gates
        )
        if proof_only and sorted(writable_files) != sorted(proof_files):
            findings.append(
                _graph_finding(
                    "proof_only_writable_mismatch",
                    "task",
                    f"proof-only writable scope must equal proofFiles for {task_id}",
                    task_id=task_id or None,
                    paths=sorted(set(writable_files + proof_files)),
                )
            )
        if task_type == "execution" and not proof_only and proof_files:
            findings.append(
                _graph_finding(
                    "implementation_owns_proof",
                    "task",
                    f"normal implementation task must not declare proofFiles for {task_id}",
                    task_id=task_id or None,
                    paths=proof_files,
                )
            )
        if task_type == "execution" and not proof_only:
            leaked_tests = [path for path in writable_files if "/__tests__/" in path]
            leaked_proof_creations = (
                []
                if docs_slice
                else [
                    path
                    for path in created_files
                    if proof_root and _path_within_root(path, proof_root)
                ]
            )
            if leaked_tests or leaked_proof_creations:
                findings.append(
                    _graph_finding(
                        "implementation_proof_scope_leak",
                        "task",
                        f"normal execution task owns proof scope for {task_id}",
                        task_id=task_id or None,
                        paths=sorted(set(leaked_tests + leaked_proof_creations)),
                    )
                )
        if objective_contract.get("taskContractRequired") is True:
            allowed_expansion = normalized_string_list(
                objective_contract.get("allowedExpansionZone")
            )
            for created_file in created_files:
                if not any(
                    _path_within_root(created_file, allowed_root)
                    for allowed_root in allowed_expansion
                ):
                    findings.append(
                        _graph_finding(
                            "unauthorized_created_file_glob",
                            "task",
                            (
                                "created-file scope is outside allowedExpansionZone "
                                f"for {task_id}: {created_file}"
                            ),
                            task_id=task_id or None,
                            paths=[created_file],
                        )
                    )
        leaked_manifests = [
            path for path in writable_files
            if path.endswith("package.json") or path.endswith("package-lock.json") or "node_modules" in path
        ]
        if leaked_manifests:
            findings.append(
                _graph_finding(
                    "manifest_or_dependency_residue_owned",
                    "task",
                    f"normal slice owns manifest or dependency residue for {task_id}",
                    task_id=task_id or None,
                    paths=leaked_manifests,
                )
            )
        production_created_files = [
            path
            for path in created_files
            if not (
                _is_exact_file_path(path)
                and proof_root
                and _path_within_root(path, proof_root)
                and path in proof_files
            )
        ]
        clusters = sorted(
            {
                cluster
                for cluster in (
                    classify_writable_cluster(path)
                    for path in writable_files + production_created_files
                )
                if cluster
            }
        )
        if task_type == "execution" and len(clusters) > 1:
            findings.append(
                _graph_finding(
                    "multiple_mutation_clusters",
                    "task",
                    f"execution writable scope spans multiple production clusters for {task_id}: {clusters}",
                    task_id=task_id or None,
                    paths=writable_files,
                )
            )
        if (
            task_type == "execution"
            and len(clusters) <= 1
            and len(objective_scope_clusters) > 1
        ):
            touched_clusters = sorted(
                {
                    cluster
                    for cluster in objective_scope_clusters
                    if any(
                        _path_within_root(path, cluster)
                        for path in writable_files + created_files
                    )
                }
            )
            if len(touched_clusters) > 1:
                findings.append(
                    _graph_finding(
                        "multiple_mutation_clusters",
                        "task",
                        f"execution writable scope spans multiple objective clusters for {task_id}: {touched_clusters}",
                        task_id=task_id or None,
                        paths=touched_clusters,
                    )
                )
        for token in normalized_string_list(contract.get("consumes")):
            provider_ids = [provider_id for provider_id in providers.get(token, []) if provider_id != task_id]
            linked = sorted(set(provider_ids).intersection(dependency_ids))
            if len(provider_ids) != 1 or len(linked) != 1:
                findings.append(
                    _graph_finding(
                        "evidence_dependency_invalid",
                        "dependency_graph",
                        f"consumed token {token} must have one explicit dependency provider for {task_id}",
                        task_id=task_id or None,
                        dependencies=provider_ids,
                    )
                )
        if contract.get("riskClass") == "exact_parity":
            writable_truth = [
                path
                for path in proof_files
                if path in writable_files
                or path == mutation_root
                or (mutation_root and path.startswith(mutation_root.rstrip("/") + "/"))
            ]
            if writable_truth:
                findings.append(
                    _graph_finding(
                        "parity_proof_uses_writable_truth",
                        "task",
                        f"exact-parity proof depends on local writable truth for {task_id}",
                        task_id=task_id or None,
                        paths=writable_truth,
                    )
                )

    for cycle in _find_dependency_cycles(valid_tasks):
        findings.append(
            _graph_finding(
                "dependency_cycle",
                "dependency_graph",
                f"task dependencies contain a cycle: {' -> '.join(cycle)}",
                task_id=cycle[0],
                dependencies=cycle,
            )
        )

    if len(review_tasks) != 1:
        findings.append(
            _graph_finding(
                "gate_review_count_invalid",
                "objective_coverage",
                f"expected exactly 1 review task, found {len(review_tasks)}",
            )
        )
    gate = review_tasks[0] if len(review_tasks) == 1 else None
    gate_deps = set(normalized_string_list(gate.get("dependsOn"))) if gate else set()
    if gate and gate.get("reviewMode") != "gate_review":
        findings.append(_graph_finding("gate_review_mode_invalid", "objective_coverage", "review task must use reviewMode=gate_review", task_id=str(gate.get("id") or "") or None))
    if gate:
        gate_contract = gate.get("taskContract") if isinstance(gate.get("taskContract"), dict) else {}
        gate_writable_paths = (
            normalized_string_list(gate_contract.get("writableFiles"))
            + normalized_string_list(gate_contract.get("createdFileGlobs"))
        )
        if gate_writable_paths:
            findings.append(
                _graph_finding(
                    "gate_review_not_read_only",
                    "task",
                    "gate_review must not declare writableFiles or createdFileGlobs",
                    task_id=str(gate.get("id") or "") or None,
                    paths=sorted(set(gate_writable_paths)),
                )
            )
        missing_gate_dependencies = sorted(execution_ids - gate_deps)
        if missing_gate_dependencies:
            findings.append(
                _graph_finding(
                    "gate_review_dependencies_missing",
                    "dependency_graph",
                    f"gate_review missing execution dependencies: {missing_gate_dependencies}",
                    task_id=str(gate.get("id") or "") or None,
                    dependencies=missing_gate_dependencies,
                )
            )
    required_production_evidence = set(
        normalized_string_list(objective_contract.get("requiredProductionEvidence"))
    )
    if required_production_evidence:
        evidence_owners: dict[str, list[str]] = {}
        for task, task_id in zip(valid_tasks, task_ids):
            contract = task.get("taskContract")
            if not isinstance(contract, dict):
                continue
            for declaration in contract.get("productionEvidence", []):
                if isinstance(declaration, dict):
                    category = str(declaration.get("category") or "").strip()
                    if category:
                        evidence_owners.setdefault(category, []).append(task_id)
        for category in sorted(required_production_evidence):
            if not evidence_owners.get(category):
                findings.append(
                    _graph_finding(
                        "production_evidence_missing",
                        "objective_coverage",
                        f"required production evidence has no owner: {category}",
                        requirement_id=f"productionEvidence:{category}",
                    )
                )
        expected_reviewer = str(objective_contract.get("productionGateReviewer") or "Dolores")
        if gate and gate.get("assignee") != expected_reviewer:
            findings.append(
                _graph_finding(
                    "production_gate_reviewer_invalid",
                    "objective_coverage",
                    f"production gate must be assigned to {expected_reviewer}",
                    task_id=str(gate.get("id") or "") or None,
                )
            )
    integration_tasks = [
        task
        for task in valid_tasks
        if task.get("taskType") == "execution"
        and isinstance(task.get("taskContract"), dict)
        and task["taskContract"].get("primaryArtifactClass") == "integration_proof"
    ]
    if artifact_delivery:
        if integration_tasks:
            findings.append(
                _graph_finding(
                    "integration_proof_count_invalid",
                    "objective_coverage",
                    "artifact_delivery must close through content evidence and review, not software integration_proof",
                )
            )
    elif len(integration_tasks) != 1:
        findings.append(
            _graph_finding(
                "integration_proof_count_invalid",
                "objective_coverage",
                f"contract-required graph must contain exactly one integration_proof task, found {len(integration_tasks)}",
            )
        )
    else:
        integration = integration_tasks[0]
        integration_id = str(integration.get("id") or "")
        integration_gates = normalized_string_list(
            integration["taskContract"].get("verification", {}).get("qualityGates")
        )
        if "software_build" not in integration_gates:
            findings.append(
                _graph_finding(
                    "quality_gate_build_ownership_invalid",
                    "task",
                    "final integration_proof must retain software_build",
                    task_id=integration_id or None,
                )
            )
        for task in valid_tasks:
            if task is integration or not isinstance(task.get("taskContract"), dict):
                continue
            task_gates = normalized_string_list(
                task["taskContract"].get("verification", {}).get("qualityGates")
            )
            if "software_build" in task_gates:
                findings.append(
                    _graph_finding(
                        "quality_gate_build_ownership_invalid",
                        "task",
                        "software_build is owned only by the final integration_proof task",
                        task_id=str(task.get("id") or "") or None,
                    )
                )
        integration_dependencies = set(normalized_string_list(integration.get("dependsOn")))
        missing_integration = sorted((execution_ids - {integration_id}) - integration_dependencies)
        if missing_integration:
            findings.append(
                _graph_finding(
                    "integration_proof_dependencies_missing",
                    "dependency_graph",
                    f"integration_proof missing execution dependencies: {missing_integration}",
                    task_id=integration_id or None,
                    dependencies=missing_integration,
                )
            )
        integration_contract = integration.get("taskContract")
        integration_consumes = set(
            normalized_string_list(
                integration_contract.get("consumes")
                if isinstance(integration_contract, dict)
                else []
            )
        )
        upstream_tokens = {
            token
            for task in valid_tasks
            if task.get("taskType") == "execution" and task is not integration
            for token in normalized_string_list(
                task["taskContract"].get("provides")
                if isinstance(task.get("taskContract"), dict)
                else []
            )
        }
        missing_integration_tokens = sorted(upstream_tokens - integration_consumes)
        if missing_integration_tokens:
            findings.append(
                _graph_finding(
                    "integration_proof_tokens_missing",
                    "dependency_graph",
                    f"integration_proof missing upstream tokens: {missing_integration_tokens}",
                    task_id=integration_id or None,
                )
            )
        if gate and integration_id not in gate_deps:
            findings.append(
                _graph_finding(
                    "gate_review_integration_dependency_missing",
                    "dependency_graph",
                    "gate_review must depend on the final integration_proof task",
                    task_id=str(gate.get("id") or "") or None,
                    dependencies=[integration_id],
                )
            )

    if isinstance(objective, dict):
        contract = (
            payload.get("decompositionContract")
            if is_amendment and isinstance(payload.get("decompositionContract"), dict)
            else objective.get("decompositionContract")
        )
        if isinstance(contract, dict):
            required_paths = normalized_string_list(contract.get("requiredOwnershipPaths"))
            for index, required_path in enumerate(required_paths):
                owners = [
                    task_id
                    for task, task_id in zip(valid_tasks, task_ids)
                    if isinstance(task.get("taskContract"), dict)
                    and required_path in normalized_string_list(task["taskContract"].get("writableFiles"))
                ]
                if len(owners) != 1:
                    findings.append(
                        _graph_finding(
                            "required_ownership_invalid",
                            "objective_coverage",
                            f"required ownership path must have exactly one owner: {required_path}; owners={owners}",
                            requirement_id=f"requiredOwnershipPaths[{index}]",
                            paths=[required_path],
                            dependencies=owners,
                        )
                    )
            if isinstance(manifest, dict):
                authority_impact = manifest.get("authorityImpact")
                if authority_impact is not None and not isinstance(authority_impact, list):
                    findings.append(
                        _graph_finding(
                            "authority_impact_invalid",
                            "objective_coverage",
                            "canonical manifest authorityImpact must be a list",
                        )
                    )
                elif isinstance(authority_impact, list):
                    for impact_index, impact in enumerate(authority_impact):
                        if not isinstance(impact, dict):
                            findings.append(
                                _graph_finding(
                                    "authority_impact_invalid",
                                    "objective_coverage",
                                    f"authorityImpact[{impact_index}] must be an object",
                                )
                            )
                            continue
                        authority_path = str(impact.get("authorityPath") or "").strip()
                        change_kind = str(impact.get("changeKind") or "").strip()
                        symbols = normalized_string_list(impact.get("symbols"))
                        candidate_paths = {
                            str(candidate.get("path") or "").strip()
                            for candidate in impact.get("candidates", [])
                            if isinstance(candidate, dict)
                        }
                        confirmed_roots = impact.get("confirmedRoots")
                        if not authority_path or not symbols:
                            findings.append(
                                _graph_finding(
                                    "authority_impact_invalid",
                                    "objective_coverage",
                                    f"authorityImpact[{impact_index}] requires authorityPath and symbols",
                                )
                            )
                        if not isinstance(confirmed_roots, list) or not confirmed_roots:
                            findings.append(
                                _graph_finding(
                                    "authority_impact_roots_missing",
                                    "objective_coverage",
                                    f"authorityImpact[{impact_index}] requires confirmedRoots",
                                    paths=[authority_path] if authority_path else None,
                                )
                            )
                            continue
                        confirmed_roles: set[str] = set()
                        composition_owner_ids: set[str] = set()
                        for root_index, root in enumerate(confirmed_roots):
                            if not isinstance(root, dict):
                                findings.append(
                                    _graph_finding(
                                        "authority_impact_root_invalid",
                                        "objective_coverage",
                                        f"authorityImpact[{impact_index}].confirmedRoots[{root_index}] must be an object",
                                    )
                                )
                                continue
                            path = str(root.get("path") or "").strip()
                            role = str(root.get("role") or "").strip()
                            confirmed_roles.add(role)
                            if not path or "*" in path or role not in AUTHORITY_IMPACT_ROLES:
                                findings.append(
                                    _graph_finding(
                                        "authority_impact_root_invalid",
                                        "objective_coverage",
                                        f"confirmed authority-impact root requires an exact path and supported role: {path or '<missing>'}",
                                        paths=[path] if path else None,
                                    )
                                )
                                continue
                            if path != authority_path and path not in candidate_paths:
                                findings.append(
                                    _graph_finding(
                                        "authority_impact_evidence_missing",
                                        "objective_coverage",
                                        f"confirmed root is not traceable to collected source-reference evidence: {path}",
                                        paths=[path],
                                    )
                                )
                            if path not in required_paths:
                                findings.append(
                                    _graph_finding(
                                        "authority_impact_ownership_requirement_missing",
                                        "objective_coverage",
                                        f"confirmed authority-impact root is absent from requiredOwnershipPaths: {path}",
                                        paths=[path],
                                    )
                                )
                            if (
                                change_kind == "shared_interface"
                                and role in {"composition", "export"}
                                and authority_path
                            ):
                                owners = [
                                    (task, task_id)
                                    for task, task_id in zip(valid_tasks, task_ids)
                                    if isinstance(task.get("taskContract"), dict)
                                    and path in normalized_string_list(
                                        task["taskContract"].get("writableFiles")
                                    )
                                ]
                                if len(owners) == 1:
                                    owner_task, owner_task_id = owners[0]
                                    if owner_task_id:
                                        composition_owner_ids.add(owner_task_id)
                                    owner_contract = owner_task["taskContract"]
                                    if owner_contract.get("authorityRoot") != authority_path:
                                        findings.append(
                                            _graph_finding(
                                                "authority_impact_owner_authority_invalid",
                                                "task",
                                                (
                                                    "shared-interface composition/export owner must "
                                                    f"use the originating authority path: {authority_path}"
                                                ),
                                                task_id=owner_task_id or None,
                                                paths=[authority_path, path],
                                            )
                                        )
                        if change_kind == "shared_interface" and not (
                            {"composition", "export"} & confirmed_roles
                        ):
                            findings.append(
                                _graph_finding(
                                    "shared_interface_composition_owner_missing",
                                    "objective_coverage",
                                    "shared interface change requires a confirmed composition or export root",
                                    paths=[authority_path] if authority_path else None,
                                )
                            )
                        if change_kind == "shared_interface":
                            authority_owner_ids = {
                                task_id
                                for task, task_id in zip(valid_tasks, task_ids)
                                if task_id
                                and isinstance(task.get("taskContract"), dict)
                                and authority_path in normalized_string_list(
                                    task["taskContract"].get("writableFiles")
                                )
                            }
                            for task, task_id in zip(valid_tasks, task_ids):
                                if task_id not in authority_owner_ids | composition_owner_ids:
                                    continue
                                quality_gates = normalized_string_list(
                                    task["taskContract"].get("verification", {}).get("qualityGates")
                                )
                                if "software_build" not in quality_gates:
                                    continue
                                missing_owners = sorted(
                                    composition_owner_ids
                                    - set(normalized_string_list(task.get("dependsOn")))
                                    - {task_id}
                                )
                                if missing_owners:
                                    findings.append(
                                        _graph_finding(
                                            "shared_interface_build_gate_premature",
                                            "dependency_graph",
                                            (
                                                "software_build cannot run before all confirmed "
                                                "shared-interface composition/export owners"
                                            ),
                                            task_id=task_id,
                                            paths=[authority_path],
                                            dependencies=missing_owners,
                                        )
                                    )
                            if len(integration_tasks) == 1:
                                integration_task = integration_tasks[0]
                                integration_id = str(integration_task.get("id") or "")
                                integration_gates = normalized_string_list(
                                    integration_task["taskContract"]
                                    .get("verification", {})
                                    .get("qualityGates")
                                )
                                if "software_build" not in integration_gates:
                                    findings.append(
                                        _graph_finding(
                                            "shared_interface_integration_build_missing",
                                            "objective_coverage",
                                            (
                                                "final integration_proof must own software_build "
                                                "for a shared-interface change"
                                            ),
                                            task_id=integration_id or None,
                                            paths=[authority_path],
                                        )
                                    )
                objective_id = str(objective.get("id") or payload.get("objectiveId") or "").strip()
                manifest_tasks = manifest.get("tasks")
                if not isinstance(manifest_tasks, list):
                    findings.append(
                        _graph_finding(
                            "manifest_tasks_missing",
                            "objective_coverage",
                            "canonical manifest tasks must be a list",
                        )
                    )
                else:
                    expected_requirements = {
                        **{
                            f"ownership:{path}": f"requiredOwnershipPaths[{index}]"
                            for index, path in enumerate(required_paths)
                        },
                        **{
                            f"proof:{index}": f"proofExpected[{index}]"
                            for index, _ in enumerate(normalized_string_list(contract.get("proofExpected")))
                        },
                    }
                    approved_slices_value = (
                        contract.get("approvedSlices")
                        or objective.get("approvedSlices")
                    )
                    # Mission Control stores approved slices as structured
                    # records, while legacy objectives may still use strings.
                    # Requirement identity is positional for both shapes.
                    approved_slices = (
                        approved_slices_value
                        if isinstance(approved_slices_value, list)
                        else []
                    )
                    expected_requirements.update(
                        {
                            f"slice:{index}": f"approvedSlices[{index}]"
                            for index, _ in enumerate(approved_slices)
                        }
                    )
                    assignments: dict[str, list[str]] = {}
                    manifest_task_ids: dict[str, str] = {}
                    try:
                        namespace = uuid.UUID(objective_id)
                    except Exception:
                        namespace = None
                    payload_ids = task_id_set
                    for manifest_task in manifest_tasks:
                        if not isinstance(manifest_task, dict):
                            continue
                        key = str(manifest_task.get("key") or "").strip()
                        if namespace and key:
                            persisted_task_id = manifest_task.get("persistedTaskId")
                            if persisted_task_id is None:
                                expected_id = str(uuid.uuid5(namespace, key))
                            else:
                                try:
                                    expected_id = str(uuid.UUID(str(persisted_task_id)))
                                except Exception:
                                    findings.append(
                                        _graph_finding(
                                            "manifest_persisted_task_id_invalid",
                                            "objective_coverage",
                                            f"manifest key {key} has an invalid persistedTaskId",
                                        )
                                    )
                                    continue
                            if expected_id not in payload_ids:
                                findings.append(
                                    _graph_finding(
                                        "manifest_task_identity_mismatch",
                                        "objective_coverage",
                                        f"manifest key {key} does not resolve to a persisted task id",
                                        task_id=expected_id,
                                    )
                                )
                            manifest_task_ids[key] = expected_id
                        requirements = manifest_task.get("requirements")
                        if not isinstance(requirements, list):
                            findings.append(
                                _graph_finding(
                                    "manifest_requirements_invalid",
                                    "objective_coverage",
                                    f"manifest task {key or '<missing-key>'} must declare requirements as a list",
                                )
                            )
                            continue
                        for requirement in normalized_string_list(requirements):
                            assignments.setdefault(requirement, []).append(key)
                    for requirement_id, source_id in expected_requirements.items():
                        owners = assignments.get(requirement_id, [])
                        if len(owners) != 1:
                            findings.append(
                                _graph_finding(
                                    "objective_requirement_coverage_invalid",
                                    "objective_coverage",
                                    f"objective requirement {requirement_id} must be represented exactly once; tasks={owners}",
                                    requirement_id=source_id,
                                    dependencies=owners,
                                )
                            )
                        elif requirement_id.startswith("ownership:"):
                            required_path = requirement_id.removeprefix("ownership:")
                            owner_key = owners[0]
                            owner_id = manifest_task_ids.get(owner_key)
                            owner_task = next(
                                (
                                    task
                                    for task in valid_tasks
                                    if str(task.get("id") or "").strip() == owner_id
                                ),
                                None,
                            )
                            owner_contract = (
                                owner_task.get("taskContract")
                                if isinstance(owner_task, dict)
                                else None
                            )
                            writable_scope = (
                                normalized_string_list(owner_contract.get("writableFiles"))
                                + normalized_string_list(owner_contract.get("createdFileGlobs"))
                                if isinstance(owner_contract, dict)
                                else []
                            )
                            if not any(
                                _path_within_root(required_path, scope_path)
                                for scope_path in writable_scope
                            ):
                                findings.append(
                                    _graph_finding(
                                        "objective_requirement_owner_scope_mismatch",
                                        "objective_coverage",
                                        (
                                            f"objective requirement {requirement_id} must be assigned "
                                            f"to a task that can write that path; task={owner_key}"
                                        ),
                                        task_id=owner_id,
                                        requirement_id=source_id,
                                        paths=[required_path, *writable_scope],
                                        dependencies=[owner_key],
                                    )
                                )
                    for requirement_id, owners in assignments.items():
                        if requirement_id not in expected_requirements:
                            findings.append(
                                _graph_finding(
                                    "objective_requirement_unknown",
                                    "objective_coverage",
                                    f"manifest assigns unknown objective requirement {requirement_id}",
                                    requirement_id=requirement_id,
                                    dependencies=owners,
                                )
                            )
    return findings


def emit_contract_required_report(
    payload: object,
    *,
    max_tasks: int | None,
    objective: object | None,
    manifest: object | None,
    amend_baseline: object | None,
    report_path: Path,
    workspace: Path,
) -> int:
    artifact_findings: list[dict] = []
    if isinstance(manifest, dict) and isinstance(objective, dict):
        try:
            from build_contract_decomposition import expand_manifest

            expected_payload = expand_manifest(manifest, objective)
            if expected_payload != payload:
                artifact_findings.append(
                    _graph_finding(
                        "manifest_payload_mismatch",
                        "objective_coverage",
                        "decomposition.json is not the deterministic expansion of the current manifest.json",
                    )
                )
        except (ImportError, TypeError, ValueError) as error:
            artifact_findings.append(
                _graph_finding(
                    "manifest_expansion_invalid",
                    "objective_coverage",
                    f"current manifest cannot be deterministically expanded: {error}",
                )
            )
    findings = artifact_findings + collect_contract_required_findings(
        payload,
        max_tasks=max_tasks,
        objective=objective,
        manifest=manifest,
    )
    grandfathered_findings: list[dict] = []
    if isinstance(amend_baseline, dict):
        baseline_tasks = amend_baseline.get("tasks")
        baseline_by_id = {
            str(task.get("id") or "").strip(): task
            for task in baseline_tasks
            if isinstance(task, dict) and str(task.get("id") or "").strip()
        } if isinstance(baseline_tasks, list) else {}
        proposed_tasks = payload.get("tasks") if isinstance(payload, dict) else None
        if isinstance(proposed_tasks, list):
            for proposed in proposed_tasks:
                if not isinstance(proposed, dict):
                    continue
                task_id = str(proposed.get("id") or "").strip()
                baseline_task = baseline_by_id.get(task_id)
                if not baseline_task:
                    continue
                baseline_contract = baseline_task.get("taskContract")
                proposed_contract = proposed.get("taskContract")
                if baseline_task.get("status") == "done":
                    contracts_match = baseline_contract == proposed_contract
                    finding_code = "amendment_completed_contract_changed"
                    message = (
                        "completed amendment child must preserve its accepted live "
                        f"taskContract exactly: {task_id}"
                    )
                else:
                    contracts_match = (
                        contract_without_additive_evidence(baseline_contract)
                        == contract_without_additive_evidence(proposed_contract)
                        or _is_safe_unreleased_narrowing(
                            baseline_task,
                            proposed,
                            objective_source_anchors=set(normalized_string_list(
                                objective.get("decompositionContract", {}).get("sourceAnchors")
                                if isinstance(objective, dict)
                                and isinstance(objective.get("decompositionContract"), dict)
                                else []
                            )),
                        )
                    )
                    finding_code = "amendment_incomplete_contract_changed"
                    message = (
                        "incomplete amendment child may change only consumed evidence, "
                        "or safely remove quality gates/read-only apply steps before release: "
                        f"{task_id}"
                    )
                if not contracts_match:
                    findings.append(
                        _graph_finding(
                            finding_code,
                            "task",
                            message,
                            task_id=task_id,
                        )
                    )
        baseline_task_ids = {
            str(task.get("id") or "").strip()
            for task in baseline_tasks
            if isinstance(task, dict)
        } if isinstance(baseline_tasks, list) else set()
        baseline_findings = collect_contract_required_findings(
            amend_baseline,
            max_tasks=max_tasks,
            objective=objective,
            manifest=None,
        )

        def finding_key(finding: dict) -> str:
            return json.dumps(
                {
                    key: finding.get(key)
                    for key in (
                        "code",
                        "group",
                        "taskId",
                        "requirementId",
                        "paths",
                        "dependencies",
                        "message",
                    )
                },
                sort_keys=True,
            )

        baseline_keys = {
            finding_key(finding)
            for finding in baseline_findings
            if finding.get("taskId") in baseline_task_ids
        }
        active_findings = []
        for finding in findings:
            if (
                finding.get("taskId") in baseline_task_ids
                and finding_key(finding) in baseline_keys
            ):
                grandfathered_findings.append(finding)
            else:
                active_findings.append(finding)
        findings = active_findings
    tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    report = {
        "version": "decomposition-validator-report.v1",
        "ok": not findings,
        "findingCount": len(findings),
        "findings": findings,
        "grandfatheredFindingCount": len(grandfathered_findings),
        "grandfatheredFindings": grandfathered_findings,
        "summary": {
            "taskCount": len(tasks) if isinstance(tasks, list) else 0,
            "taskFindings": sum(item["group"] == "task" for item in findings),
            "dependencyGraphFindings": sum(item["group"] == "dependency_graph" for item in findings),
            "objectiveCoverageFindings": sum(item["group"] == "objective_coverage" for item in findings),
        },
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    try:
        from decomposition_checkpoint import record_validation

        record_validation(report=report, workspace=workspace)
    except (OSError, ValueError) as error:
        if not any(item.get("code") == "build_artifact_mismatch" for item in findings):
            finding = _graph_finding(
                "build_artifact_mismatch",
                "objective_coverage",
                str(error),
            )
            findings.append(finding)
            report["ok"] = False
            report["findingCount"] = len(findings)
            report["findings"] = findings
            report["summary"]["objectiveCoverageFindings"] += 1
            report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    except ImportError:
        pass
    print(json.dumps(report))
    if findings:
        for finding in findings:
            print(f"INVALID [{finding['code']}]: {finding['message']}", file=sys.stderr)
        return 1
    return 0


def main() -> int:
    repair_mode = len(sys.argv) == 3 and sys.argv[1] == "--repair"
    contract_required = len(sys.argv) >= 3 and sys.argv[1] == "--contract-required"
    if not repair_mode and not contract_required and len(sys.argv) not in (2, 3):
        print(
            "usage: validate_decomposition_json.py <decomposition.json> [max_task_count]\n"
            "       validate_decomposition_json.py --contract-required <decomposition.json> [max_task_count]\n"
            "       validate_decomposition_json.py --repair <task-repair-result.json>",
            file=sys.stderr,
        )
        return 2

    path = Path(sys.argv[2] if (repair_mode or contract_required) else sys.argv[1])
    strict_args = sys.argv[3:] if contract_required else []
    max_arg = (
        strict_args[0]
        if strict_args and not strict_args[0].startswith("--")
        else None
    ) if contract_required else (
        sys.argv[2] if not contract_required and not repair_mode and len(sys.argv) == 3 else None
    )
    max_tasks = int(max_arg) if max_arg is not None else None

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if repair_mode:
        return validate_repair_payload(payload)
    if contract_required:
        objective_path: Path | None = None
        manifest_path: Path | None = None
        amend_baseline_path: Path | None = None
        report_path = path.parent / "decomposition-validator-report.json"
        option_args = strict_args[1:] if max_arg is not None else strict_args
        index = 0
        while index < len(option_args):
            option = option_args[index]
            if option == "--objective" and index + 1 < len(option_args):
                objective_path = Path(option_args[index + 1])
                index += 2
                continue
            if option == "--report" and index + 1 < len(option_args):
                report_path = Path(option_args[index + 1])
                index += 2
                continue
            if option == "--manifest" and index + 1 < len(option_args):
                manifest_path = Path(option_args[index + 1])
                index += 2
                continue
            if option == "--amend-baseline" and index + 1 < len(option_args):
                amend_baseline_path = Path(option_args[index + 1])
                index += 2
                continue
            print(f"unknown contract-required option: {option}", file=sys.stderr)
            return 2
        objective = None
        if objective_path:
            objective = json.loads(objective_path.read_text(encoding="utf-8"))
        manifest = None
        if manifest_path:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        amend_baseline = None
        if amend_baseline_path:
            amend_baseline = json.loads(amend_baseline_path.read_text(encoding="utf-8"))
        return emit_contract_required_report(
            payload,
            max_tasks=max_tasks,
            objective=objective,
            manifest=manifest,
            amend_baseline=amend_baseline,
            report_path=report_path,
            workspace=path.parent,
        )

    if payload.get("kind") != "decomposition_result":
        return fail("kind must be decomposition_result")
    objective_owner = str(objective.get("owner") or "Bernard") if isinstance(objective, dict) else "Bernard"
    if payload.get("actor") not in {objective_owner, "Dolores", "Bernard"}:
        return fail(f"actor is not authorized for objective owner {objective_owner}")
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
    tasks_by_id: dict[str, dict] = {}

    for task in tasks:
        tasks_by_id[task["id"]] = task
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
            mutation_root = str(task_contract.get("mutationRoot") or "").strip()
            authority_root = str(task_contract.get("authorityRoot") or "").strip()
            proof_root = str(task_contract.get("proofRoot") or "").strip()
            writable_files = list(task_contract.get("writableFiles", []))
            proof_files = list(task_contract.get("proofFiles", []))
            verification = task_contract.get("verification")
            quality_gates = (
                normalized_string_list(verification.get("qualityGates"))
                if isinstance(verification, dict)
                else []
            )
            read_only_anchors = list(task_contract.get("readOnlyAnchors", []))
            output_artifacts = list(task_contract.get("outputArtifacts", []))
            provides = list(task_contract.get("provides", []))
            consumes = list(task_contract.get("consumes", []))
            effective_authority_root = classify_authority_root(authority_root)
            effective_authority_roots = [effective_authority_root] if effective_authority_root else []
            title_lower = str(task.get("title", "")).lower()
            authority_extraction = title_lower.startswith("extract ") and " authority facts" in title_lower
            proof_only = authority_extraction or (
                mutation_root == proof_root
                and sorted(writable_files) == sorted(proof_files)
                and bool(proof_files)
                and "software_test" in quality_gates
            )
            if proof_only:
                if sorted(writable_files) != sorted(proof_files):
                    return fail(
                        f"authority-extraction task must keep writable scope equal to proof files for {task_id}: "
                        f"writable={writable_files} proof={proof_files}"
                    )
            elif task.get("taskType") == "execution":
                leaked_tests = [path for path in writable_files if "/__tests__/" in path]
                if leaked_tests:
                    return fail(f"execution writable scope must not include test globs/files for {task_id}: {leaked_tests}")
                proof_creations = [
                    path
                    for path in normalized_string_list(task_contract.get("createdFileGlobs"))
                    if _path_within_root(path, proof_root)
                ]
                if contract_required and proof_creations:
                    return fail(
                        f"normal execution task must not create proof files; split proof ownership for {task_id}: "
                        f"{proof_creations}"
                    )

            if (
                contract_required
                and task.get("taskType") == "execution"
                and not proof_only
                and proof_files
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

            leaked_manifests = [
                path for path in writable_files
                if path.endswith("package.json") or path.endswith("package-lock.json") or "node_modules" in path
            ]
            if leaked_manifests:
                return fail(f"normal slices must not own manifest or dependency residue paths for {task_id}: {leaked_manifests}")

            if task_contract.get("riskClass") == "exact_parity":
                for proof_file in proof_files:
                    if proof_file in writable_files or proof_file.startswith(mutation_root.rstrip("/") + "/") or proof_file == mutation_root:
                        return fail(
                            f"exact-parity proof cannot depend on local writable truth for {task_id}: {proof_file}"
                        )

            expected_authority_token = infer_expected_authority_token(task["title"])
            if authority_extraction:
                if expected_authority_token and expected_authority_token not in provides:
                    return fail(
                        f"authority-extraction task must provide {expected_authority_token} for {task_id}"
                    )
                if not any(str(item).endswith(".json") for item in output_artifacts):
                    return fail(f"authority-extraction task must emit a json authority artifact for {task_id}")
            if task_contract.get("riskClass") == "exact_parity" and mutation_root.endswith("/contracts"):
                if expected_authority_token and expected_authority_token not in consumes:
                    return fail(
                        f"exact-parity contract projection must consume {expected_authority_token} for {task_id}"
                    )
                if not derived_depends_on:
                    return fail(
                        f"exact-parity contract projection must depend on its upstream authority extraction task for {task_id}"
                    )
                verification = task_contract.get("verification", {})
                if not isinstance(verification, dict):
                    return fail(f"taskContract.verification must be an object for {task_id}")
                traceability = verification.get("traceability", {})
                if not isinstance(traceability, dict):
                    return fail(f"exact-parity contract projection must declare verification.traceability for {task_id}")
                if str(traceability.get("mode") or "").strip() != "contract_projection":
                    return fail(f"exact-parity contract projection traceability mode must be contract_projection for {task_id}")
                projected_members = normalized_string_list(traceability.get("projectedMembers"))
                if not projected_members:
                    return fail(f"exact-parity contract projection must declare projectedMembers for {task_id}")

                extraction_candidates: list[tuple[dict, dict]] = []
                for dep_id in derived_depends_on:
                    upstream = tasks_by_id.get(dep_id)
                    if not upstream:
                        continue
                    upstream_contract = upstream.get("taskContract")
                    if not isinstance(upstream_contract, dict):
                        continue
                    upstream_verification = upstream_contract.get("verification", {})
                    if not isinstance(upstream_verification, dict):
                        continue
                    upstream_traceability = upstream_verification.get("traceability", {})
                    if not isinstance(upstream_traceability, dict):
                        continue
                    if str(upstream_traceability.get("mode") or "").strip() != "authority_extraction":
                        continue
                    extraction_candidates.append((upstream, upstream_traceability))

                if len(extraction_candidates) != 1:
                    return fail(
                        f"exact-parity contract projection must resolve exactly one upstream authority extraction artifact for {task_id}"
                    )

                upstream_task, upstream_traceability = extraction_candidates[0]
                upstream_token = str(upstream_traceability.get("authorityToken") or "").strip()
                if expected_authority_token and upstream_token != expected_authority_token:
                    return fail(
                        f"exact-parity contract projection must trace to authority token {expected_authority_token} for {task_id}"
                    )
                evidence_members = normalized_string_list(upstream_traceability.get("evidenceMembers"))
                if not evidence_members:
                    return fail(
                        f"upstream authority extraction must declare evidenceMembers for {task_id} via {upstream_task['id']}"
                    )

                untraceable = sorted(set(projected_members) - set(evidence_members))
                if untraceable:
                    return fail(
                        f"exact-parity contract projection has untraceable projected members for {task_id}: {untraceable}"
                    )

            if task.get("taskType") == "execution":
                clusters = sorted(
                    {
                        cluster
                        for cluster in (classify_writable_cluster(path) for path in writable_files)
                        if cluster
                    }
                )
                if len(clusters) > 1:
                    return fail(
                        f"execution writable scope spans multiple production clusters for {task_id}: {clusters}"
                    )

                if (
                    title_lower.startswith("extract task api workflow authority facts")
                    or title_lower.startswith("author task api workflow parity")
                ) and effective_authority_roots != ["task_api"]:
                    return fail(
                        f"task API parity authority must stay on task_api only for {task_id}: {effective_authority_roots}"
                    )
                if (
                    title_lower.startswith("extract objective api workflow authority facts")
                    or title_lower.startswith("author objective api workflow parity")
                ) and effective_authority_roots != ["objective_api"]:
                    return fail(
                        f"objective API parity authority must stay on objective_api only for {task_id}: {effective_authority_roots}"
                    )
                if (
                    title_lower.startswith("extract worker-handler workflow authority facts")
                    or title_lower.startswith("author worker-handler workflow parity")
                ) and effective_authority_roots != ["worker_handler"]:
                    return fail(
                        f"worker-handler parity authority must stay on worker_handler only for {task_id}: {effective_authority_roots}"
                    )
                if (
                    title_lower.startswith("extract readiness/promotion workflow authority facts")
                    or title_lower.startswith("author readiness/promotion workflow parity")
                ) and effective_authority_roots != ["readiness_promotion"]:
                    return fail(
                        f"readiness/promotion parity authority must stay on readiness_promotion only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define shared task/objective workflow contract taxonomy" and read_only_anchors:
                    return fail(
                        f"shared taxonomy must consume prior proofs, not live sibling authority roots for {task_id}: {read_only_anchors}"
                    )
                if title_lower == "define ledgerevent repository boundary" and effective_authority_roots != ["prisma_schema"]:
                    return fail(
                        f"repository boundary authority must stay on prisma_schema only for {task_id}: {effective_authority_roots}"
                    )
                if (
                    title_lower.startswith("extract release workflow authority facts")
                    or title_lower.startswith("author release workflow parity contract taxonomy")
                ) and effective_authority_roots != ["release_runtime"]:
                    return fail(
                        f"release parity authority must stay on release_runtime only for {task_id}: {effective_authority_roots}"
                    )
                if title_lower == "define activation workflow contract taxonomy" and effective_authority_roots != ["activation_runtime"]:
                    return fail(
                        f"activation taxonomy authority must stay on activation_runtime only for {task_id}: {effective_authority_roots}"
                    )
                if (
                    title_lower.startswith("extract escalation workflow authority facts")
                    or title_lower.startswith("author escalation workflow parity contract taxonomy")
                ) and effective_authority_roots != ["escalation_runtime"]:
                    return fail(
                        f"escalation parity authority must stay on escalation_runtime only for {task_id}: {effective_authority_roots}"
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
