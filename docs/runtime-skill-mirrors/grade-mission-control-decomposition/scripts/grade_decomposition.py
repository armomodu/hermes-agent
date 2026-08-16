#!/usr/bin/env python3
"""Semantic execution-safety grader for persisted or staged Mission Control decompositions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

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

ARTIFACT_DELIVERY_CLASSES = {"research_evidence", "content_draft", "content_package"}


def delivery_profile(objective: dict[str, Any]) -> str:
    decomposition_contract = objective.get("decompositionContract")
    contract_profile = (
        decomposition_contract.get("deliveryProfile")
        if isinstance(decomposition_contract, dict)
        else None
    )
    return str(objective.get("deliveryProfile") or contract_profile or "").strip().lower()


def load_json(path: str) -> Any:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        return json.load(handle)


def strings(value: Any) -> list[str]:
    return [entry for entry in value if isinstance(entry, str) and entry] if isinstance(value, list) else []


def contract(task: dict[str, Any]) -> dict[str, Any]:
    value = task.get("taskContract")
    return value if isinstance(value, dict) else {}


def canonical_actor(value: Any) -> str:
    return str(value or "").strip().lower()


def canonical_label(value: Any) -> str:
    return canonical_actor(value).replace("-", "_").replace(" ", "_")


def inside(path: str, root: str) -> bool:
    clean_path = path.rstrip("/")
    clean_root = root.rstrip("/")
    if clean_root.endswith("/**"):
        clean_root = clean_root[:-3].rstrip("/")
    return clean_path == clean_root or clean_path.startswith(f"{clean_root}/")


def task_owns_path(task: dict[str, Any], required_path: str) -> bool:
    tc = contract(task)
    exact_declared = (
        strings(task.get("relatedFiles"))
        + strings(tc.get("writableFiles"))
        + strings(tc.get("proofFiles"))
        + strings(tc.get("readOnlyAnchors"))
    )
    if required_path in exact_declared:
        return True
    return any(inside(required_path, glob) for glob in strings(tc.get("createdFileGlobs")))


def is_invocation_anchor(path: str) -> bool:
    normalized = path.lower()
    return any(
        marker in normalized
        for marker in (
            "/route.ts",
            "routing",
            "worker",
            "catalog",
            "persistence",
            "projector",
            "orchestrat",
            "scheduler",
            "dispatcher",
            "executor",
        )
    )


def finding(
    findings: list[dict[str, Any]],
    code: str,
    message: str,
    task: dict[str, Any] | None = None,
    field: str | None = None,
) -> None:
    findings.append(
        {
            "severity": "blocking",
            "code": code,
            "taskId": task.get("id") if task else None,
            "title": task.get("title") if task else None,
            "field": field,
            "message": message,
        }
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--objective", required=True)
    parser.add_argument("--tasks")
    parser.add_argument("--candidate")
    parser.add_argument("--report")
    args = parser.parse_args()

    objective = load_json(args.objective)
    if not args.tasks and not args.candidate:
        parser.error("one of --tasks or --candidate is required")
    candidate = load_json(args.candidate) if args.candidate else None
    raw_tasks = candidate.get("tasks", []) if isinstance(candidate, dict) else load_json(args.tasks)
    if isinstance(raw_tasks, dict):
        raw_tasks = raw_tasks.get("tasks", [])
    if not isinstance(raw_tasks, list):
        raise SystemExit("tasks input must be an array or an object with tasks[]")

    by_id = {task.get("id"): task for task in raw_tasks if isinstance(task, dict) and task.get("id")}
    staged = isinstance(candidate, dict)
    child_ids = [task_id for task_id in by_id] if staged else strings(objective.get("childTaskIds"))
    tasks = [by_id[task_id] for task_id in child_ids if task_id in by_id]
    findings: list[dict[str, Any]] = []
    authority_evidence: list[dict[str, Any]] = []

    missing_children = [task_id for task_id in child_ids if task_id not in by_id]
    if missing_children:
        finding(findings, "objective_review_state_invalid", f"Missing persisted children: {missing_children}")

    decomposition_contract = objective.get("decompositionContract")
    artifact_delivery = delivery_profile(objective) == "artifact_delivery"
    mechanically_required_paths = strings(
        decomposition_contract.get("requiredOwnershipPaths")
        if isinstance(decomposition_contract, dict)
        else []
    )
    semantic_invocation_paths = [
        path
        for path in strings(
            decomposition_contract.get("sourceAnchors")
            if isinstance(decomposition_contract, dict)
            else []
        )
        if is_invocation_anchor(path)
    ]
    required_paths = list(dict.fromkeys(mechanically_required_paths + semantic_invocation_paths))
    for required_path in required_paths:
        owners = [task for task in tasks if task_owns_path(task, required_path)]
        if not owners:
            finding(
                findings,
                "invocation_chain_incomplete",
                f"Required invocation-chain authority {required_path} has no truthful task owner.",
                field=(
                    "decompositionContract.requiredOwnershipPaths"
                    if required_path in mechanically_required_paths
                    else "decompositionContract.sourceAnchors"
                ),
            )
        else:
            authority_evidence.extend(
                {
                    "path": required_path,
                    "taskId": owner.get("id"),
                    "claim": "required invocation-chain authority is owned by this task",
                }
                for owner in owners
            )

    execution = [task for task in tasks if task.get("taskType") == "execution"]
    reviews = [task for task in tasks if task.get("taskType") == "review"]
    writable_owners: dict[str, list[dict[str, Any]]] = {}
    token_providers: dict[str, list[dict[str, Any]]] = {}

    for task in tasks:
        tc = contract(task)
        if tc.get("version") != "task-contract.v1":
            finding(findings, "scope_root_invalid", "Missing task-contract.v1.", task, "taskContract.version")
            continue
        artifact_class = tc.get("primaryArtifactClass")
        if artifact_class == "proof":
            finding(
                findings,
                "legacy_primary_artifact_class",
                "Legacy primaryArtifactClass 'proof' must be amended to 'focused_proof' before execution.",
                task,
                "taskContract.primaryArtifactClass",
            )
        elif artifact_class not in PRIMARY_ARTIFACT_CLASSES:
            finding(
                findings,
                "invalid_primary_artifact_class",
                f"Unsupported primaryArtifactClass: {artifact_class!r}.",
                task,
                "taskContract.primaryArtifactClass",
            )

        for token in strings(tc.get("provides")):
            token_providers.setdefault(token, []).append(task)
        for path in strings(tc.get("writableFiles")) + strings(tc.get("createdFileGlobs")):
            writable_owners.setdefault(path, []).append(task)

        if task.get("taskType") != "execution":
            continue

        for field_name in ("mutationRoot", "authorityRoot", "proofRoot", "acceptanceHinge"):
            if not isinstance(tc.get(field_name), str) or not tc[field_name].strip():
                finding(findings, "scope_root_invalid", f"Missing {field_name}.", task, f"taskContract.{field_name}")

        mutation_root = tc.get("mutationRoot", "")
        proof_root = tc.get("proofRoot", "")
        writable = strings(tc.get("writableFiles"))
        created = strings(tc.get("createdFileGlobs"))
        proof_files = strings(tc.get("proofFiles"))
        read_only = set(strings(tc.get("readOnlyAnchors")))

        for path in writable + created:
            if mutation_root and not inside(path, mutation_root):
                finding(findings, "scope_root_invalid", f"{path} escapes mutationRoot {mutation_root}.", task)
        for path in proof_files:
            if proof_root and not inside(path, proof_root):
                finding(findings, "proof_scope_invalid", f"{path} escapes proofRoot {proof_root}.", task)
        if read_only.intersection(set(writable + created)):
            finding(findings, "scope_root_invalid", "Read-only anchors overlap writable scope.", task)

        if artifact_class in {"proof", "focused_proof", "integration_proof"} and sorted(writable) != sorted(proof_files):
            finding(findings, "proof_scope_invalid", "Proof-only writable scope must equal proofFiles.", task)
        if artifact_class not in {"proof", "focused_proof", "integration_proof"} and proof_files:
            finding(findings, "proof_scope_invalid", "Normal implementation task owns proof files.", task)

        plan = tc.get("executionPlan") if isinstance(tc.get("executionPlan"), dict) else {}
        steps = plan.get("steps") if isinstance(plan.get("steps"), list) else []
        kinds = [step.get("kind") for step in steps if isinstance(step, dict)]
        expected = ["inspect_authority", "derive_delta", "apply_change", "verify"]
        if kinds[:4] != expected:
            finding(findings, "execution_plan_incomplete", f"Expected ordered plan {expected}; got {kinds}.", task)

        gates = strings((tc.get("verification") or {}).get("qualityGates"))
        if artifact_delivery and ("software_build" in gates or artifact_class == "integration_proof"):
            finding(
                findings,
                "artifact_delivery_software_proof_invalid",
                "Artifact delivery cannot use software integration or build proof.",
                task,
                "taskContract.verification.qualityGates",
            )
        elif "software_build" in gates and artifact_class != "integration_proof":
            finding(
                findings,
                "quality_gate_build_ownership_invalid",
                "software_build belongs only to the final integration proof.",
                task,
                "taskContract.verification.qualityGates",
            )

        if task.get("releasedToHermes") is True or task.get("hermesDispatchStatus") in {"released", "running"}:
            finding(findings, "execution_released_before_approval", "Execution was released before approval.", task)

    for path, owners in writable_owners.items():
        unique = {owner.get("id") for owner in owners}
        if len(unique) > 1:
            finding(findings, "writable_ownership_overlap", f"Writable path {path} has owners {sorted(unique)}.")

    for task in tasks:
        tc = contract(task)
        dependencies = set(strings(task.get("dependsOn")))
        for token in strings(tc.get("consumes")):
            providers = token_providers.get(token, [])
            if len(providers) != 1:
                finding(findings, "evidence_provider_missing", f"Token {token} has {len(providers)} providers.", task)
            elif providers[0].get("id") not in dependencies:
                finding(findings, "evidence_dependency_missing", f"Token {token} provider is not a dependency.", task)

    integrations = [task for task in execution if contract(task).get("primaryArtifactClass") == "integration_proof"]
    if artifact_delivery:
        for task in execution:
            tc = contract(task)
            if not strings(tc.get("outputArtifacts")):
                finding(findings, "artifact_evidence_incomplete", "Artifact execution must declare outputArtifacts.", task)
            if not strings(tc.get("provides")):
                finding(findings, "artifact_evidence_incomplete", "Artifact execution must provide evidence tokens.", task)

        approved_slices = (
            decomposition_contract.get("approvedSlices")
            if isinstance(decomposition_contract, dict)
            else []
        )
        maeve_slice_names = {
            canonical_label(entry.get("name"))
            for entry in approved_slices
            if isinstance(entry, dict)
            and canonical_label(entry.get("name")) == "maeve_quality_review"
        }
        maeve_quality = [
            task
            for task in execution
            if canonical_label(task.get("sliceName") or task.get("approvedSlice")) in maeve_slice_names
            or canonical_label(task.get("title")) == "maeve_quality_review"
        ]
        if len(maeve_quality) != 1 or canonical_actor(maeve_quality[0].get("assignee")) != "maeve":
            finding(
                findings,
                "artifact_quality_owner_invalid",
                "Artifact delivery requires exactly one Maeve-owned maeve_quality_review execution slice.",
                maeve_quality[0] if len(maeve_quality) == 1 else None,
                "assignee",
            )
    elif len(integrations) != 1:
        finding(findings, "integration_proof_incomplete", f"Expected one integration proof; found {len(integrations)}.")
    else:
        integration = integrations[0]
        preceding = {task.get("id") for task in execution if task.get("id") != integration.get("id")}
        dependencies = set(strings(integration.get("dependsOn")))
        prior_tokens = {
            token
            for task in execution
            if task.get("id") != integration.get("id")
            for token in strings(contract(task).get("provides"))
        }
        consumed = set(strings(contract(integration).get("consumes")))
        if not preceding.issubset(dependencies) or not prior_tokens.issubset(consumed):
            finding(findings, "integration_proof_incomplete", "Integration proof does not depend on and consume all prior work.", integration)

    if len(reviews) != 1:
        finding(findings, "gate_review_incomplete", f"Expected one gate review; found {len(reviews)}.")
    else:
        review = reviews[0]
        tc = contract(review)
        expected_reviewer = canonical_actor(
            decomposition_contract.get("productionGateReviewer")
            if isinstance(decomposition_contract, dict)
            else None
        )
        actual_reviewer = canonical_actor(review.get("assignee"))
        if expected_reviewer and actual_reviewer != expected_reviewer:
            finding(
                findings,
                "gate_review_incomplete",
                (
                    f"Gate review assignee {review.get('assignee')!r} does not match "
                    f"productionGateReviewer {decomposition_contract.get('productionGateReviewer')!r}."
                ),
                review,
                "assignee",
            )
        if strings(tc.get("writableFiles")) or strings(tc.get("createdFileGlobs")):
            finding(findings, "gate_review_incomplete", "Gate review must be read-only.", review)
        plan = tc.get("executionPlan") if isinstance(tc.get("executionPlan"), dict) else {}
        kinds = [step.get("kind") for step in plan.get("steps", []) if isinstance(step, dict)]
        expected_changes = plan.get("expectedChanges", [])
        if "apply_change" in kinds or expected_changes:
            finding(
                findings,
                "read_only_review_plan_invalid",
                "Read-only gate review cannot apply or expect mutations.",
                review,
                "taskContract.executionPlan",
            )
        if not {task.get("id") for task in execution}.issubset(set(strings(review.get("dependsOn")))):
            finding(findings, "gate_review_incomplete", "Gate review does not depend on every execution task.", review)
        if integrations:
            integration_tokens = set(strings(contract(integrations[0]).get("provides")))
            if not integration_tokens.intersection(strings(tc.get("consumes"))):
                finding(findings, "gate_review_incomplete", "Gate review does not consume integration proof.", review)

    all_children_unreleased = all(
        task.get("status") in ("pending", "ready")
        and task.get("releasedToHermes") is not True
        and task.get("hermesDispatchStatus") not in ("released", "running")
        for task in tasks
    )
    standard_review_state = (
        objective.get("reviewReady") is True
        and objective.get("approved") is not True
    )
    blocked_correction_review_state = (
        objective.get("status") == "blocked"
        and objective.get("approved") is not True
        and objective.get("needsDecomposition") is False
        and all_children_unreleased
    )
    if not staged and not standard_review_state and not blocked_correction_review_state:
        finding(
            findings,
            "objective_review_state_invalid",
            (
                "Expected reviewReady=true and approved=false, or a blocked pre-approval "
                "correction graph whose canonical children are entirely unreleased pending/ready work."
            ),
        )

    grade = "A" if not findings else "B"
    verdict = "A-grade and ready for approval" if not findings else "return to Bernard for bounded correction"
    report = {
        "kind": "decomposition_grade_result",
        "version": "decomposition-grade.v1",
        "objectiveId": objective.get("id"),
        "decompositionTaskId": candidate.get("decompositionTaskId") if staged else None,
        "candidateDigest": candidate.get("candidateDigest") if staged else None,
        "correctionRound": candidate.get("correctionRound", 0) if staged else 0,
        "grade": grade,
        "verdict": verdict,
        "authorityEvidence": authority_evidence,
        "taskCount": len(tasks),
        "executionTaskCount": len(execution),
        "reviewTaskCount": len(reviews),
        "blockingFindingCount": len(findings),
        "findings": findings,
    }
    rendered = json.dumps(report, indent=2)
    if args.report:
        Path(args.report).expanduser().write_text(f"{rendered}\n", encoding="utf-8")
    print(rendered)
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
