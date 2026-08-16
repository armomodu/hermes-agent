#!/usr/bin/env python3
"""Expand a compact contract slice manifest into a decomposition_result payload."""

from __future__ import annotations

import json
import re
import sys
import uuid
from pathlib import Path

from decomposition_checkpoint import load_checkpoint, record_build


LIST_FIELDS = (
    "writableFiles",
    "createdFileGlobs",
    "proofFiles",
    "readOnlyAnchors",
    "outputArtifacts",
    "provides",
    "consumes",
)


def semantic_key(value: str, index: int) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or f"slice-{index}"


def canonical_task_template() -> dict:
    return {
        "key": "",
        "requirements": [],
        "title": "",
        "assignee": "William",
        "taskType": "execution",
        "priority": "P1",
        "nextAction": "",
        "dependsOn": [],
        "reviewMode": None,
        "contract": {
            "semanticHinge": "",
            "workflowFamily": "",
            "mutationRoot": "",
            "authorityRoot": "",
            "proofRoot": "",
            "acceptanceHinge": "",
            "writableFiles": [],
            "createdFileGlobs": [],
            "proofFiles": [],
            "readOnlyAnchors": [],
            "outputArtifacts": [],
            "provides": [],
            "consumes": [],
            "verification": {"focusedTests": [], "qualityGates": []},
            "productionEvidence": [],
            "primaryArtifactClass": "code",
            "plan": {
                "outcome": "",
                "inspect": "",
                "derive": "",
                "apply": "",
                "verify": "",
                "operation": "modify",
                "symbols": [],
                "invariant": "",
                "completionChecks": [],
            },
        },
    }


def initialize_manifest(objective: dict) -> dict:
    objective_id = require_text(objective.get("id"), "id", "objective")
    uuid.UUID(objective_id)
    contract = objective.get("decompositionContract")
    if not isinstance(contract, dict):
        raise ValueError("objective decompositionContract is required")
    approved_slices = contract.get("approvedSlices")
    if approved_slices is None:
        approved_slices = []
    if not isinstance(approved_slices, list):
        raise ValueError("objective decompositionContract.approvedSlices must be a list when present")

    tasks: list[dict] = []
    used_keys: set[str] = set()
    reviewer = objective.get("productionGateReviewer") or contract.get("productionGateReviewer")
    for index, approved_slice in enumerate(approved_slices):
        if isinstance(approved_slice, str):
            title = require_text(approved_slice, f"approvedSlices[{index}]", "objective")
            workflow_family = ""
            artifact_class = ""
        elif isinstance(approved_slice, dict):
            title = require_text(
                approved_slice.get("name"),
                f"approvedSlices[{index}].name",
                "objective",
            )
            workflow_family = str(approved_slice.get("workflowFamily") or "")
            artifact_class = str(approved_slice.get("primaryArtifactClass") or "")
        else:
            raise ValueError(f"approvedSlices[{index}] must be a string or object")

        base_key = semantic_key(title, index)
        key = base_key
        suffix = 2
        while key in used_keys:
            key = f"{base_key}-{suffix}"
            suffix += 1
        used_keys.add(key)
        is_gate_review = artifact_class == "review_gate"
        task = {
            "key": key,
            "requirements": [f"slice:{index}"],
            "title": title,
            "assignee": reviewer if is_gate_review and isinstance(reviewer, str) else "William",
            "taskType": "review" if is_gate_review else "execution",
            "priority": "P1",
            "nextAction": "",
            "dependsOn": [],
            "contract": {
                "semanticHinge": "",
                "workflowFamily": workflow_family,
                "mutationRoot": "",
                "authorityRoot": "",
                "proofRoot": "",
                "acceptanceHinge": "",
                "writableFiles": [],
                "createdFileGlobs": [],
                "proofFiles": [],
                "readOnlyAnchors": [],
                "outputArtifacts": [],
                "provides": [],
                "consumes": [],
                "verification": {"focusedTests": [], "qualityGates": []},
                "productionEvidence": [],
                "primaryArtifactClass": artifact_class,
                "plan": {
                    "outcome": "",
                    "inspect": "",
                    "derive": "",
                    "apply": "",
                    "verify": "",
                    "operation": "modify",
                    "symbols": [],
                    "invariant": "",
                    "completionChecks": [],
                },
            },
        }
        if is_gate_review:
            task["reviewMode"] = "gate_review"
        tasks.append(task)

    return {
        "kind": "contract-decomposition-manifest.v1",
        "objectiveId": objective_id,
        "statusNote": "",
        "contractGuide": {
            "sliceSource": "objective_approved" if approved_slices else "bernard_authored",
            "planOperations": ["add", "modify", "remove"],
            "taskTemplate": canonical_task_template(),
            "specialTaskShapes": {
                "documentation": {
                    "taskType": "execution",
                    "primaryArtifactClass": "docs",
                    "proofRoot": "mutationRoot",
                    "proofFiles": [],
                },
                "integrationProof": {
                    "taskType": "execution",
                    "primaryArtifactClass": "integration_proof",
                    "qualityGates": ["software_test", "software_build"],
                    "scopeRule": (
                        "Own one exact proof file: mutationRoot=proofRoot and "
                        "writableFiles=proofFiles=createdFileGlobs=[that exact file]. "
                        "Keep authorityRoot and readOnlyAnchors outside writable scope."
                    ),
                },
                "gateReview": {
                    "taskType": "review",
                    "reviewMode": "gate_review",
                    "primaryArtifactClass": "review_gate",
                },
                "artifactDelivery": {
                    "softwareQualityGates": [],
                    "forbiddenArtifactClass": "integration_proof",
                    "executionRequirement": "Each execution slice declares outputArtifacts and provides evidence.",
                    "closure": "Evidence-producing quality execution followed by one read-only operator gate_review.",
                },
            },
            "unassignedRequirements": [
                *[
                    f"ownership:{path}"
                    for path in contract.get("requiredOwnershipPaths", [])
                    if isinstance(path, str) and path.strip()
                ],
                *[
                    f"proof:{index}"
                    for index, _proof in enumerate(contract.get("proofExpected", []))
                ],
            ],
            "requiredProductionEvidence": [
                category
                for category in contract.get("requiredProductionEvidence", [])
                if isinstance(category, str) and category.strip()
            ],
            "rootRules": [
                "Assign every contractGuide.unassignedRequirements entry exactly once.",
                "Use an exact file mutationRoot when writableFiles contains one exact file.",
                "Keep createdFileGlobs equal to or below mutationRoot; use an exact new file path when known.",
                "Implementation proofRoot is read-only and must not overlap writable or created scope.",
                "The final integration proof depends on every preceding execution task.",
                "The gate review is read-only and depends on every execution task.",
                "Copy contractGuide.taskTemplate for each Bernard-authored task, then replace every placeholder.",
            ],
        },
        "tasks": tasks,
    }


def fail(message: str) -> int:
    print(f"INVALID MANIFEST: {message}", file=sys.stderr)
    return 1


def require_text(value: object, field: str, task_key: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} is required for {task_key}")
    return value.strip()


def require_string_list(value: object, field: str, task_key: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field} must be a string list for {task_key}")
    return [item.strip() for item in value]


def build_execution_plan(
    contract: dict,
    plan: dict,
    task_key: str,
    *,
    read_only: bool = False,
) -> dict:
    consumes = require_string_list(contract.get("consumes", []), "contract.consumes", task_key)
    derive_references = ["authorityRoot", "mutationRoot"]
    derive_references.extend(f"consumedToken:{token}" for token in consumes)
    steps = [
        {"kind": "inspect_authority", "instruction": require_text(plan.get("inspect"), "contract.plan.inspect", task_key), "references": ["authorityRoot"]},
        {"kind": "derive_delta", "instruction": require_text(plan.get("derive"), "contract.plan.derive", task_key), "references": derive_references},
    ]
    if not read_only:
        steps.append(
            {"kind": "apply_change", "instruction": require_text(plan.get("apply"), "contract.plan.apply", task_key), "references": ["mutationRoot"]}
        )
    steps.append(
        {"kind": "verify", "instruction": require_text(plan.get("verify"), "contract.plan.verify", task_key), "references": ["proofRoot"]}
    )
    expected_changes = []
    if not read_only:
        expected_changes.append({
            "target": "mutationRoot",
            "operation": require_text(plan.get("operation"), "contract.plan.operation", task_key),
            "symbols": require_string_list(plan.get("symbols"), "contract.plan.symbols", task_key),
            "invariant": require_text(plan.get("invariant"), "contract.plan.invariant", task_key),
        })
    return {
        "version": "task-execution-plan.v1",
        "outcome": require_text(plan.get("outcome"), "contract.plan.outcome", task_key),
        "steps": steps,
        "expectedChanges": expected_changes,
        "completionChecks": require_string_list(plan.get("completionChecks"), "contract.plan.completionChecks", task_key),
    }


def canonical_artifact_class(contract_input: dict, task_key: str) -> str | None:
    artifact_class = (
        require_text(
            contract_input["primaryArtifactClass"],
            "contract.primaryArtifactClass",
            task_key,
        )
        if "primaryArtifactClass" in contract_input
        else None
    )
    writable_files = require_string_list(
        contract_input.get("writableFiles", []),
        "contract.writableFiles",
        task_key,
    )
    proof_files = require_string_list(
        contract_input.get("proofFiles", []),
        "contract.proofFiles",
        task_key,
    )
    created_files = require_string_list(
        contract_input.get("createdFileGlobs", []),
        "contract.createdFileGlobs",
        task_key,
    )
    mutation_root = str(contract_input.get("mutationRoot") or "").strip()
    docs_slice = mutation_root.endswith((".md", ".mdx")) or "/docs/" in mutation_root
    if docs_slice:
        return "docs"
    proof_only = (
        bool(proof_files)
        and set(writable_files) == set(proof_files)
        and set(created_files).issubset(set(proof_files))
        and contract_input.get("mutationRoot") == contract_input.get("proofRoot")
    )
    generic_implementation_classes = {None, "code", "implementation", "writer"}
    if proof_only and artifact_class in generic_implementation_classes:
        return "focused_proof"
    if artifact_class in {None, "implementation"}:
        return "code"
    return artifact_class


def canonical_plan_input(contract_input: dict, task_key: str) -> dict:
    if "executionPlan" in contract_input:
        raise ValueError(
            f"contract.executionPlan is generated output and must not appear in canonical manifest for {task_key}; "
            "author contract.plan instead"
        )
    plan = contract_input.get("plan")
    if not isinstance(plan, dict):
        raise ValueError(f"contract.plan is required for {task_key}")
    return plan


def canonical_proof_root(contract: dict, artifact_class: str | None) -> str:
    return contract["mutationRoot"] if artifact_class == "docs" else contract["proofRoot"]


def build_amended_contract(manifest: dict, objective: object | None) -> dict | None:
    operation = manifest.get("operation")
    if operation is None:
        return None
    if operation != "amend":
        raise ValueError("manifest operation must be amend when present")
    if not isinstance(objective, dict):
        raise ValueError("amendment manifest requires --objective")
    objective_contract = objective.get("decompositionContract")
    if not isinstance(objective_contract, dict):
        raise ValueError("amendment objective requires decompositionContract")
    patch = manifest.get("decompositionContractPatch")
    if not isinstance(patch, dict) or not patch:
        raise ValueError("amendment manifest requires decompositionContractPatch")
    return {**objective_contract, **patch}


def expand_manifest(manifest: dict, objective: object | None = None) -> dict:
    if manifest.get("kind") != "contract-decomposition-manifest.v1":
        raise ValueError("kind must be contract-decomposition-manifest.v1")
    objective_id = require_text(manifest.get("objectiveId"), "objectiveId", "manifest")
    namespace = uuid.UUID(objective_id)
    slices = manifest.get("tasks")
    if not isinstance(slices, list) or not slices:
        raise ValueError("tasks must be a non-empty list")
    keys = [require_text(item.get("key"), "key", "task") for item in slices if isinstance(item, dict)]
    if len(keys) != len(slices) or len(set(keys)) != len(keys):
        raise ValueError("every task key must be unique")
    ids: dict[str, str] = {}
    for item in slices:
        key = item["key"]
        persisted_task_id = item.get("persistedTaskId")
        if persisted_task_id is None:
            ids[key] = str(uuid.uuid5(namespace, key))
            continue
        persisted_id = require_text(persisted_task_id, "persistedTaskId", key)
        uuid.UUID(persisted_id)
        ids[key] = persisted_id
    if len(set(ids.values())) != len(ids):
        raise ValueError("every task id must be unique")
    tasks: list[dict] = []
    for item in slices:
        key = item["key"]
        require_string_list(item.get("requirements", []), "requirements", key)
        contract_input = item.get("contract")
        if not isinstance(contract_input, dict):
            raise ValueError(f"contract is required for {key}")
        contract = {
            "version": "task-contract.v1",
            "semanticHinge": require_text(contract_input.get("semanticHinge"), "contract.semanticHinge", key),
            "workflowFamily": require_text(contract_input.get("workflowFamily"), "contract.workflowFamily", key),
            "mutationRoot": require_text(contract_input.get("mutationRoot"), "contract.mutationRoot", key),
            "authorityRoot": require_text(contract_input.get("authorityRoot"), "contract.authorityRoot", key),
            "proofRoot": require_text(contract_input.get("proofRoot"), "contract.proofRoot", key),
            "acceptanceHinge": require_text(contract_input.get("acceptanceHinge"), "contract.acceptanceHinge", key),
        }
        for field in LIST_FIELDS:
            contract[field] = require_string_list(contract_input.get(field, []), f"contract.{field}", key)
        if (
            item.get("taskType") != "review"
            and len(contract["writableFiles"]) == 1
            and not any(marker in contract["writableFiles"][0] for marker in ("*", "?", "[", "]", "{", "}"))
            and contract["mutationRoot"] == contract["writableFiles"][0]
            and contract["writableFiles"][0] not in contract["createdFileGlobs"]
        ):
            contract["createdFileGlobs"].append(contract["writableFiles"][0])
        verification = contract_input.get("verification", {})
        if not isinstance(verification, dict):
            raise ValueError(f"contract.verification must be an object for {key}")
        contract["verification"] = {
            "focusedTests": require_string_list(verification.get("focusedTests", []), "contract.verification.focusedTests", key),
            "qualityGates": require_string_list(verification.get("qualityGates", []), "contract.verification.qualityGates", key),
        }
        production_evidence = contract_input.get("productionEvidence", [])
        if not isinstance(production_evidence, list):
            raise ValueError(f"contract.productionEvidence must be a list for {key}")
        contract["productionEvidence"] = []
        for index, declaration in enumerate(production_evidence):
            if not isinstance(declaration, dict):
                raise ValueError(f"contract.productionEvidence[{index}] must be an object for {key}")
            contract["productionEvidence"].append({
                "category": require_text(
                    declaration.get("category"),
                    f"contract.productionEvidence[{index}].category",
                    key,
                ),
                "evidenceToken": require_text(
                    declaration.get("evidenceToken"),
                    f"contract.productionEvidence[{index}].evidenceToken",
                    key,
                ),
            })
        artifact_class = canonical_artifact_class(contract_input, key)
        if artifact_class is not None:
            contract["primaryArtifactClass"] = artifact_class
        contract["proofRoot"] = canonical_proof_root(contract, artifact_class)
        if artifact_class == "docs":
            contract["proofFiles"] = []
            contract["verification"]["focusedTests"] = []
        plan = canonical_plan_input(contract_input, key)
        contract["executionPlan"] = build_execution_plan(
            contract,
            plan,
            key,
            read_only=(
                item.get("taskType") == "review"
                and item.get("reviewMode") == "gate_review"
            ),
        )
        dependency_keys = require_string_list(item.get("dependsOn", []), "dependsOn", key)
        unknown = [dependency for dependency in dependency_keys if dependency not in ids]
        if unknown:
            raise ValueError(f"unknown dependsOn keys for {key}: {', '.join(unknown)}")
        task = {
            "id": ids[key],
            "title": require_text(item.get("title"), "title", key),
            "assignee": require_text(item.get("assignee"), "assignee", key),
            "taskType": require_text(item.get("taskType"), "taskType", key),
            "priority": require_text(item.get("priority"), "priority", key),
            "nextAction": require_text(item.get("nextAction"), "nextAction", key),
            "dependsOn": [ids[dependency] for dependency in dependency_keys],
            "taskContract": contract,
        }
        if item.get("reviewMode"):
            task["reviewMode"] = require_text(item["reviewMode"], "reviewMode", key)
        tasks.append(task)
    payload = {
        "kind": "decomposition_result",
        "objectiveId": objective_id,
        "statusNote": require_text(manifest.get("statusNote"), "statusNote", "manifest"),
        "requestReview": True,
        "actor": str(objective.get("owner") or "Bernard"),
        "tasks": tasks,
    }
    amended_contract = build_amended_contract(manifest, objective)
    if amended_contract is not None:
        payload["operation"] = "amend"
        payload["requestReview"] = False
        payload["decompositionContract"] = amended_contract
    return payload


def main() -> int:
    if len(sys.argv) == 4 and sys.argv[1] == "--init-manifest":
        try:
            existing = load_checkpoint(Path(sys.argv[3]).parent)
            if existing:
                if (
                    int(existing.get("correctionRound", 0)) >= 2
                    and int(existing.get("findingCount", 0)) > 0
                ):
                    raise ValueError(
                        "TERMINAL_DECOMPOSITION_FAILURE: bounded correction rounds are exhausted; "
                        "do not rebuild, regenerate, rewrite the checkpoint, or inspect tool source; "
                        "block the Hermes task with the final validator report now"
                    )
                raise ValueError(
                    "a decomposition checkpoint already exists; resume and edit its canonical "
                    "manifest instead of initializing another manifest"
                )
            objective = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
            if not isinstance(objective, dict):
                raise ValueError("objective must be an object")
            manifest = initialize_manifest(objective)
            Path(sys.argv[3]).write_text(
                json.dumps(manifest, indent=2) + "\n",
                encoding="utf-8",
            )
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            return fail(str(exc))
        print(json.dumps({
            "ok": True,
            "mode": "init_manifest",
            "taskCount": len(manifest["tasks"]),
            "output": sys.argv[3],
        }))
        return 0
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--objective"):
        print(
            "usage: build_contract_decomposition.py --init-manifest <objective.json> <manifest.json>\n"
            "   or: build_contract_decomposition.py <manifest.json> <decomposition.json> "
            "[--objective <objective.json>]",
            file=sys.stderr,
        )
        return 2
    try:
        manifest = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
        objective = (
            json.loads(Path(sys.argv[4]).read_text(encoding="utf-8"))
            if len(sys.argv) == 5
            else None
        )
        payload = expand_manifest(manifest, objective)
        Path(sys.argv[2]).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        checkpoint = record_build(
            objective_id=payload["objectiveId"],
            manifest_path=Path(sys.argv[1]),
            decomposition_path=Path(sys.argv[2]),
            objective_path=Path(sys.argv[4]) if len(sys.argv) == 5 else None,
            workspace=Path(sys.argv[1]).parent,
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return fail(str(exc))
    print(json.dumps({
        "ok": True,
        "taskCount": len(payload["tasks"]),
        "output": sys.argv[2],
        "correctionRound": checkpoint["correctionRound"],
        "manifestDigest": checkpoint["manifestDigest"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
