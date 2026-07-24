#!/usr/bin/env python3
"""Expand a compact contract slice manifest into a decomposition_result payload."""

from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

from decomposition_checkpoint import record_build


LIST_FIELDS = (
    "writableFiles",
    "createdFileGlobs",
    "proofFiles",
    "readOnlyAnchors",
    "outputArtifacts",
    "provides",
    "consumes",
)


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


def build_execution_plan(contract: dict, plan: dict, task_key: str) -> dict:
    consumes = require_string_list(contract.get("consumes", []), "contract.consumes", task_key)
    derive_references = ["authorityRoot", "mutationRoot"]
    derive_references.extend(f"consumedToken:{token}" for token in consumes)
    return {
        "version": "task-execution-plan.v1",
        "outcome": require_text(plan.get("outcome"), "contract.plan.outcome", task_key),
        "steps": [
            {"kind": "inspect_authority", "instruction": require_text(plan.get("inspect"), "contract.plan.inspect", task_key), "references": ["authorityRoot"]},
            {"kind": "derive_delta", "instruction": require_text(plan.get("derive"), "contract.plan.derive", task_key), "references": derive_references},
            {"kind": "apply_change", "instruction": require_text(plan.get("apply"), "contract.plan.apply", task_key), "references": ["mutationRoot"]},
            {"kind": "verify", "instruction": require_text(plan.get("verify"), "contract.plan.verify", task_key), "references": ["proofRoot"]},
        ],
        "expectedChanges": [{
            "target": "mutationRoot",
            "operation": require_text(plan.get("operation"), "contract.plan.operation", task_key),
            "symbols": require_string_list(plan.get("symbols"), "contract.plan.symbols", task_key),
            "invariant": require_text(plan.get("invariant"), "contract.plan.invariant", task_key),
        }],
        "completionChecks": require_string_list(plan.get("completionChecks"), "contract.plan.completionChecks", task_key),
    }


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
        verification = contract_input.get("verification", {})
        if not isinstance(verification, dict):
            raise ValueError(f"contract.verification must be an object for {key}")
        contract["verification"] = {
            "focusedTests": require_string_list(verification.get("focusedTests", []), "contract.verification.focusedTests", key),
            "qualityGates": require_string_list(verification.get("qualityGates", []), "contract.verification.qualityGates", key),
        }
        if "primaryArtifactClass" in contract_input:
            contract["primaryArtifactClass"] = require_text(contract_input["primaryArtifactClass"], "contract.primaryArtifactClass", key)
        execution_plan = contract_input.get("executionPlan")
        if execution_plan is not None:
            if not isinstance(execution_plan, dict):
                raise ValueError(f"contract.executionPlan must be an object for {key}")
            contract["executionPlan"] = execution_plan
        else:
            plan = contract_input.get("plan")
            if not isinstance(plan, dict):
                raise ValueError(f"contract.plan is required for {key}")
            contract["executionPlan"] = build_execution_plan(contract, plan, key)
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
        "actor": "Bernard",
        "tasks": tasks,
    }
    amended_contract = build_amended_contract(manifest, objective)
    if amended_contract is not None:
        payload["operation"] = "amend"
        payload["requestReview"] = False
        payload["decompositionContract"] = amended_contract
    return payload


def main() -> int:
    if len(sys.argv) not in (3, 5) or (len(sys.argv) == 5 and sys.argv[3] != "--objective"):
        print(
            "usage: build_contract_decomposition.py <manifest.json> <decomposition.json> "
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
