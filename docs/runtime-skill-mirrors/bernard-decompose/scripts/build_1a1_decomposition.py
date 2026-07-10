#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path


SLICE_TITLES = [
    "Author task API workflow parity contract slice",
    "Prove task API workflow exact parity against the live route contract",
    "Author objective API workflow parity contract slice",
    "Prove objective API workflow exact parity against the live route contract",
    "Author worker-handler workflow parity contract slice",
    "Prove worker-handler workflow exact parity against the live route contract",
    "Author readiness/promotion workflow parity contract slice",
    "Prove readiness/promotion workflow exact parity against the live route contract",
    "Define shared task/objective workflow contract taxonomy",
    "Define release workflow contract taxonomy",
    "Define activation workflow contract taxonomy",
    "Define escalation workflow contract taxonomy",
    "Establish LedgerEvent Prisma schema model foundation",
    "Create LedgerEvent Prisma migration scaffold",
    "Define LedgerEvent repository boundary",
    "Wire LedgerEvent storage exports",
    "Implement canonical ledger writer",
    "Harden stable identity/correlation mapping for ledger writes",
    "Wire task API entrypoint emitters to the canonical ledger path",
    "Wire objective API entrypoint emitters to the canonical ledger path",
    "Wire worker handler transition emitters to the canonical ledger path",
    "Wire readiness/promotion transition emitters to the canonical ledger path",
    "Wire release-start emitters to the canonical ledger path",
    "Wire merge/runtime transition emitters to the canonical ledger path",
    "Wire deploy/verify emitters to the canonical ledger path",
    "Wire activation emitters to the canonical ledger path",
    "Wire escalation emitters to the canonical ledger path",
    "Implement deterministic ledger readback queries",
    "Expose ledger readback API and proof",
    "Harden replay/remediation duplicate prevention for ledger writes",
    "Backfill a bounded recent slice into the ledger",
    "Document the workflow-ledger contract and operator proof path",
]

APPROVED_EXECUTION_SLICE_COUNT = 32
APPROVED_MAX_TASK_COUNT = 33
CANARY_OBJECTIVE_ID = "4009e581-7231-4930-9a0d-b2b56b281d9e"


def new_id() -> str:
    return str(uuid.uuid4())


def text(*parts: str) -> str:
    return "\n".join([p.strip() for p in parts if p and p.strip()])


def make_task(
    *,
    title: str,
    summary: str,
    acceptance: str,
    constraints: str,
    related_files: list[str],
    artifact_paths: list[str],
    next_action: str,
    depends_on: list[str] | None = None,
    assignee: str = "William",
    task_type: str = "execution",
    review_mode: str | None = None,
    workflow_families: list[str] | None = None,
    abstraction_classes: list[str] | None = None,
    primary_artifact_class: str | None = None,
    distinct_delta: bool = True,
    parity_scope_mode: str | None = None,
    proof_required_scope: list[str] | None = None,
) -> dict:
    task = {
        "id": new_id(),
        "title": title,
        "assignee": assignee,
        "taskType": task_type,
        "priority": "P1",
        "feature": "Mission Control",
        "summary": summary,
        "acceptanceCriteria": acceptance,
        "constraints": constraints,
        "relatedFiles": related_files,
        "artifactPaths": artifact_paths,
        "links": [
            "https://app.maroncorp.com/api/objectives/4009e581-7231-4930-9a0d-b2b56b281d9e",
            "https://app.maroncorp.com/overview",
        ],
        "nextAction": next_action,
        "blockers": None,
        "__meta": {
            "workflow_families": workflow_families or [],
            "abstraction_classes": abstraction_classes or [],
            "primary_artifact_class": primary_artifact_class,
            "distinct_delta": distinct_delta,
            "parity_scope_mode": parity_scope_mode,
            "proof_required_scope": proof_required_scope or [],
        },
    }
    if depends_on:
        task["dependsOn"] = depends_on
    if review_mode is not None:
        task["reviewMode"] = review_mode
    return task


def validate_bounded_graph(tasks: list[dict]) -> None:
    errors: list[str] = []

    for task in tasks:
        if task.get("taskType") != "execution" or task.get("assignee") != "William":
            continue

        meta = task.get("__meta", {})
        families = meta.get("workflow_families", [])
        abstractions = meta.get("abstraction_classes", [])
        primary_artifact = meta.get("primary_artifact_class")
        distinct_delta = meta.get("distinct_delta", True)
        parity_scope_mode = meta.get("parity_scope_mode")
        proof_required_scope = meta.get("proof_required_scope", [])
        title = task["title"]

        if len(families) != 1:
            errors.append(f"{title}: expected exactly 1 workflow family, found {families}")
        if len(abstractions) != 1:
            errors.append(f"{title}: expected exactly 1 abstraction class, found {abstractions}")
        if not primary_artifact:
            errors.append(f"{title}: missing primary artifact class")
        if not distinct_delta:
            errors.append(f"{title}: downstream task lacks a distinct substantive delta")

        related_files = task.get("relatedFiles", [])
        artifact_paths = task.get("artifactPaths", [])
        title_lower = title.lower()
        authority_roots = sorted(
            {
                root
                for root in (classify_live_authority_root(path) for path in artifact_paths)
                if root
            }
        )

        if "parity" in title_lower:
            if parity_scope_mode not in {"proof_only", "contract_output"}:
                errors.append(f"{title}: parity task missing parity_scope_mode")
            if parity_scope_mode == "proof_only":
                invalid = [
                    path for path in related_files
                    if "/__tests__/" not in path
                ]
                if invalid:
                    errors.append(f"{title}: proof-only parity task includes non-proof writable scope {invalid}")
            if parity_scope_mode == "contract_output":
                if not any("/src/lib/knowledge-plane/contracts/" in path for path in related_files):
                    errors.append(f"{title}: contract-output parity task missing contracts writable scope")
                if "prove" in title_lower:
                    errors.append(f"{title}: contract-output parity task must not also be the proof task")
                if "contract" not in title_lower and "contract" not in task.get("summary", "").lower():
                    errors.append(f"{title}: contract-output parity task does not name the production contract output")
        if "task api workflow parity" in title_lower and authority_roots != ["task_api"]:
            errors.append(f"{title}: proof/read authority must stay on task_api only, found {authority_roots}")
        if "objective api workflow parity" in title_lower and authority_roots != ["objective_api"]:
            errors.append(f"{title}: proof/read authority must stay on objective_api only, found {authority_roots}")
        if "worker-handler workflow parity" in title_lower and authority_roots != ["worker_handler"]:
            errors.append(f"{title}: proof/read authority must stay on worker_handler only, found {authority_roots}")
        if "readiness/promotion workflow parity" in title_lower and authority_roots != ["readiness_promotion"]:
            errors.append(f"{title}: proof/read authority must stay on readiness_promotion only, found {authority_roots}")
        if title == "Define shared task/objective workflow contract taxonomy" and authority_roots:
            errors.append(f"{title}: shared taxonomy must consume proven parity slices, not live sibling roots {authority_roots}")
        if "task/objective" in title_lower and "emitters" in title_lower:
            has_api_entrypoints = any("/src/app/api/tasks/" in path or "/src/app/api/objectives/" in path for path in related_files)
            has_worker_files = any("/src/lib/workers/" in path for path in related_files)
            if has_api_entrypoints and has_worker_files:
                errors.append(f"{title}: task/objective emitter task mixes API entrypoints and worker transition files")
        if "wire task api entrypoint emitters" in title_lower and any("/src/app/api/objectives/" in path for path in related_files):
            errors.append(f"{title}: task API slice must not keep objective API writable")
        if "wire objective api entrypoint emitters" in title_lower and any("/src/app/api/tasks/" in path for path in related_files):
            errors.append(f"{title}: objective API slice must not keep task API writable")
        if "wire worker handler transition emitters" in title_lower and any("task-readiness-promotion-service.ts" in path for path in related_files):
            errors.append(f"{title}: worker handler slice must not keep readiness/promotion writable")
        if "wire readiness/promotion transition emitters" in title_lower and any("handlers.ts" in path for path in related_files):
            errors.append(f"{title}: readiness/promotion slice must not keep worker handler writable")

        if "contract taxonomy" in title.lower():
            invalid = [
                path for path in related_files
                if "/src/lib/knowledge-plane/contracts/" not in path
                and "/src/lib/knowledge-plane/__tests__/" not in path
            ]
            if invalid:
                errors.append(f"{title}: contract task includes non-contract writable scope {invalid}")

        if "emitters to the canonical ledger path" in title.lower():
            if any("/src/lib/knowledge-plane/contracts/" in path for path in related_files):
                errors.append(f"{title}: emitter task must not keep contracts/** writable")
            if authority_roots:
                errors.append(f"{title}: emitter task must not keep sibling live mutation roots in artifact authority {authority_roots}")
        if "repository boundary" in title.lower():
            invalid = [path for path in related_files if "/prisma/" in path]
            if invalid:
                errors.append(f"{title}: preserve-only Prisma authority must not stay writable {invalid}")
            if authority_roots != ["prisma_schema"]:
                errors.append(f"{title}: repository boundary must anchor only to prisma_schema, found {authority_roots}")
        if "merge/runtime transition emitters" in title.lower():
            if any("objective-deployment-service.ts" in path for path in related_files):
                errors.append(f"{title}: merge/runtime task must not include deployment-service writable scope")
        if "deploy/verify emitters" in title.lower():
            if any("objective-release-service.ts" in path for path in related_files):
                errors.append(f"{title}: deploy/verify task must not include release-service writable scope")
        if title == "Define release workflow contract taxonomy" and authority_roots != ["release_runtime"]:
            errors.append(f"{title}: release taxonomy must anchor only to release_runtime, found {authority_roots}")

        if "canonical ledger writer" in title.lower():
            if any("/src/lib/knowledge-plane/contracts/" in path for path in related_files):
                errors.append(f"{title}: writer task must not keep contracts/** writable")

        if "readback" in title.lower() and len(task.get("dependsOn", [])) > 3:
            errors.append(f"{title}: readback task depends on too many upstream slices")
        if "duplicate prevention" in title.lower() and len(task.get("dependsOn", [])) > 3:
            errors.append(f"{title}: duplicate-prevention task depends on too many upstream slices")

        missing_proof_scope = [
            path for path in proof_required_scope
            if path not in related_files
        ]
        if missing_proof_scope:
            errors.append(f"{title}: proof depends on upstream authority outside writable scope {missing_proof_scope}")

        candidate_writable_files = infer_writable_files(task, infer_proof_file(task))
        writable_clusters = sorted(
            {
                cluster
                for cluster in (classify_live_writable_cluster(path) for path in candidate_writable_files)
                if cluster
            }
        )
        if len(writable_clusters) > 1:
            errors.append(
                f"{title}: writable scope still spans multiple live writable clusters {writable_clusters}; "
                "narrow the writable scope or move preserve-only authority into read-only metadata"
            )

    if errors:
        raise SystemExit("bounded-graph validation failed:\n- " + "\n- ".join(errors))


def sanitize_tasks(tasks: list[dict]) -> list[dict]:
    return [to_contract_mode_task(task) for task in tasks]


def slugify(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "task"


def normalize_family(value: str | None) -> str:
    mapping = {
        "task/objective": "task_objective",
        "release": "merge_deploy_verify",
        "activation": "activation",
        "escalation": "escalation",
        "ledger-schema": "storage",
        "ledger-storage": "storage",
        "ledger-writer": "storage",
        "readback": "storage",
        "duplicate-prevention": "storage",
        "backfill": "storage",
        "docs": "docs",
    }
    return mapping.get((value or "").strip(), "storage")


def normalize_primary_artifact(value: str | None, *, task_type: str, title: str) -> str:
    if task_type == "review":
        return "review_gate"
    title_lower = title.lower()
    mapping = {
        "contract parity slice": "contract_family",
        "focused proof slice": "contract_family",
        "contract family": "contract_family",
        "schema model or migration slice": "schema_model",
        "repository boundary": "repository_boundary",
        "storage export surface": "repository_boundary",
        "canonical writer": "writer",
        "identity/correlation mapping surface": "writer",
        "emitter-wiring slice": "emitter_wiring",
        "deterministic query surface": "readback_query",
        "api readback surface": "readback_api",
        "duplicate-prevention surface": "duplicate_prevention",
        "bounded backfill surface": "backfill",
        "docs": "docs",
    }
    if value and value.strip() in mapping:
        return mapping[value.strip()]
    if "schema" in title_lower:
        return "schema_model"
    if "review" in title_lower:
        return "review_gate"
    return "writer"


def normalize_risk_class(title: str, primary_artifact_class: str) -> str:
    title_lower = title.lower()
    if "exact parity" in title_lower or "parity contract" in title_lower:
        return "exact_parity"
    if primary_artifact_class in {"schema_model", "repository_boundary", "writer", "duplicate_prevention", "backfill"}:
        return "persistence"
    if primary_artifact_class in {"emitter_wiring", "readback_api"}:
        return "runtime_wiring"
    if primary_artifact_class == "review_gate":
        return "canary"
    return "normal"


def overlaps(left: str, right: str) -> bool:
    left_norm = left.replace("**", "").rstrip("/")
    right_norm = right.replace("**", "").rstrip("/")
    return left_norm == right_norm or left_norm.startswith(right_norm + "/") or right_norm.startswith(left_norm + "/")


def classify_live_writable_cluster(path: str) -> str | None:
    cleaned = path.replace("**", "").rstrip("/")
    if cleaned == "apps/mission-control/prisma/schema.prisma":
        return "apps/mission-control/prisma/schema.prisma"
    if cleaned.startswith("apps/mission-control/prisma/migrations"):
        return "apps/mission-control/prisma/migrations"
    if cleaned.startswith("apps/mission-control/src/app/api/tasks"):
        return "apps/mission-control/src/app/api/tasks"
    if cleaned.startswith("apps/mission-control/src/app/api/objectives"):
        return "apps/mission-control/src/app/api/objectives"
    if cleaned == "apps/mission-control/src/lib/workers/handlers.ts":
        return "apps/mission-control/src/lib/workers/handlers.ts"
    if cleaned == "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts":
        return "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts"
    return None


def classify_live_authority_root(path: str) -> str | None:
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


def infer_created_file_globs(task: dict, writable_files: list[str]) -> list[str]:
    return []


def infer_read_only_anchors(task: dict, writable_files: list[str], created_file_globs: list[str]) -> list[str]:
    artifact_paths = [entry for entry in task.get("artifactPaths", []) if isinstance(entry, str)]
    related_files = [entry for entry in task.get("relatedFiles", []) if isinstance(entry, str)]
    anchors: list[str] = []
    for path in artifact_paths:
        if path.endswith(".md") or "/__tests__/" in path or "/docs/" in path:
            continue
        if any(overlaps(path, writable_path) for writable_path in writable_files):
            continue
        if any(overlaps(path, created_glob) for created_glob in created_file_globs):
            continue
        anchors.append(path)
    for path in related_files:
        if any(overlaps(path, writable_path) for writable_path in writable_files):
            continue
        if any(overlaps(path, created_glob) for created_glob in created_file_globs):
            continue
        if "/__tests__/" in path:
            continue
        anchors.append(path)
    deduped: list[str] = []
    seen = set()
    for path in anchors:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def infer_proof_file(task: dict) -> str:
    slug = slugify(task["title"])
    if task.get("assignee") == "Librarian":
        return f"apps/mission-control/docs/knowledge-plane/proof/{slug}.md"
    return f"apps/mission-control/src/lib/knowledge-plane/__tests__/canary/{slug}.test.ts"


def infer_output_artifact(task: dict) -> str:
    slug = slugify(task["title"])
    return f"artifacts/decomposition/1a1/{slug}.md"


def infer_writable_files(task: dict, proof_file: str) -> list[str]:
    meta = task.get("__meta", {})
    parity_scope_mode = meta.get("parity_scope_mode")
    title = task.get("title", "")
    related_files = [entry for entry in task.get("relatedFiles", []) if isinstance(entry, str)]

    if parity_scope_mode == "proof_only":
        return [proof_file]

    scope_overrides = {
        "Establish LedgerEvent Prisma schema model foundation": [
            "apps/mission-control/prisma/schema.prisma",
        ],
        "Create LedgerEvent Prisma migration scaffold": [
            "apps/mission-control/prisma/migrations/**",
        ],
        "Wire task API entrypoint emitters to the canonical ledger path": [
            "apps/mission-control/src/app/api/tasks/route.ts",
            "apps/mission-control/src/app/api/tasks/[id]/route.ts",
        ],
        "Wire objective API entrypoint emitters to the canonical ledger path": [
            "apps/mission-control/src/app/api/objectives/[id]/route.ts",
        ],
        "Wire worker handler transition emitters to the canonical ledger path": [
            "apps/mission-control/src/lib/workers/handlers.ts",
        ],
        "Wire readiness/promotion transition emitters to the canonical ledger path": [
            "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts",
        ],
    }
    if title in scope_overrides:
        return list(scope_overrides[title])

    writable = [entry for entry in related_files if "/__tests__/" not in entry]
    deduped: list[str] = []
    seen = set()
    for path in writable:
        if path in seen:
            continue
        seen.add(path)
        deduped.append(path)
    return deduped


def to_contract_mode_task(task: dict) -> dict:
    meta = task.get("__meta", {})
    family = normalize_family((meta.get("workflow_families") or [None])[0])
    primary_artifact_class = normalize_primary_artifact(
        meta.get("primary_artifact_class"),
        task_type=task["taskType"],
        title=task["title"],
    )
    proof_file = infer_proof_file(task)
    writable_files = infer_writable_files(task, proof_file)
    created_file_globs = infer_created_file_globs(task, writable_files)
    task_contract = {
        "version": "task-contract.v1",
        "semanticHinge": task["title"],
        "workflowFamily": family,
        "primaryArtifactClass": primary_artifact_class,
        "riskClass": normalize_risk_class(task["title"], primary_artifact_class),
        "writableFiles": writable_files,
        "proofFiles": [proof_file],
        "createdFileGlobs": created_file_globs,
        "readOnlyAnchors": infer_read_only_anchors(task, writable_files, created_file_globs),
        "outputArtifacts": [infer_output_artifact(task)],
        "provides": [f"task:{task['id']}"],
        "consumes": [f"task:{dep}" for dep in task.get("dependsOn", [])],
        "outOfScope": [],
        "verification": {
            "focusedTests": [proof_file],
            "qualityGates": ["software_test"],
        },
    }
    payload = {
        "id": task["id"],
        "title": task["title"],
        "assignee": task["assignee"],
        "taskType": task["taskType"],
        "priority": task["priority"],
        "feature": task["feature"],
        "links": list(task.get("links", [])),
        "nextAction": task["nextAction"],
        "blockers": task.get("blockers"),
        "taskContract": task_contract,
    }
    if task.get("reviewMode") is not None:
        payload["reviewMode"] = task["reviewMode"]
    return payload


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: build_1a1_decomposition.py <objective.json> <decomposition.json>", file=sys.stderr)
        return 2

    if len(SLICE_TITLES) != APPROVED_EXECUTION_SLICE_COUNT:
        raise SystemExit(
            f"expected {APPROVED_EXECUTION_SLICE_COUNT} execution slices, found {len(SLICE_TITLES)}"
        )

    objective_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    objective = json.loads(objective_path.read_text(encoding="utf-8"))

    if objective.get("id") != CANARY_OBJECTIVE_ID:
        print("unexpected objective id", file=sys.stderr)
        return 2

    parity_writable_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
    ]
    task_api_authority_paths = [
        "apps/mission-control/src/app/api/tasks/route.ts",
        "apps/mission-control/src/app/api/tasks/[id]/route.ts",
    ]
    objective_api_authority_paths = [
        "apps/mission-control/src/app/api/objectives/[id]/route.ts",
    ]
    worker_handler_authority_paths = [
        "apps/mission-control/src/lib/workers/handlers.ts",
    ]
    readiness_authority_paths = [
        "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts",
    ]
    contract_scope_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
    ]
    release_contract_paths = contract_scope_paths
    activation_contract_paths = contract_scope_paths
    escalation_contract_paths = contract_scope_paths
    release_start_emitter_paths = [
        "apps/mission-control/src/lib/release/objective-release-service.ts",
    ]
    merge_runtime_emitter_paths = [
        "apps/mission-control/src/lib/release/objective-release-service.ts",
    ]
    deploy_verify_emitter_paths = [
        "apps/mission-control/src/lib/release/objective-deployment-service.ts",
    ]
    activation_emitter_paths = [
        "apps/mission-control/src/lib/release/objective-activation-service.ts",
    ]
    schema_model_paths = [
        "apps/mission-control/prisma/schema.prisma",
    ]
    schema_migration_paths = [
        "apps/mission-control/prisma/migrations/**",
    ]
    storage_foundation_paths = [
        "apps/mission-control/src/lib/storage/**",
    ]
    ledger_write_paths = [
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    readback_paths = [
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    docs_paths = [
        "apps/mission-control/docs/knowledge-plane/**",
    ]
    api_paths = [
        "apps/mission-control/src/app/api/knowledge/ledger/**",
    ]

    tasks: list[dict] = []

    t1 = make_task(
        title=SLICE_TITLES[0],
        summary="Author only the minimal task API production contract parity slice needed for the live task-route branch without widening into broader taxonomy.",
        acceptance=text(
            "A minimal task API production contract parity slice exists for the live task-route branch.",
            "The authored slice stays narrower than the downstream shared task/objective taxonomy task and does not broaden into adjacent workflow families.",
            "The contract slice loads cleanly without requiring broader taxonomy, validator invention, or runtime emitter wiring.",
        ),
        constraints=text(
            "Task API exact-parity contract-output task only.",
            "Author only the minimal task API contract parity slice; do not build the parity proof here.",
            "Do not widen into validators, broader taxonomy, or adjacent workflow families.",
        ),
        related_files=parity_writable_paths,
        artifact_paths=task_api_authority_paths,
        next_action="Read only the live task API authority surfaces, then author the minimal task API parity contract slice for that exact branch.",
        workflow_families=["task/objective"],
        abstraction_classes=["contract parity slice"],
        primary_artifact_class="contract parity slice",
        parity_scope_mode="contract_output",
    )
    tasks.append(t1)

    t1b = make_task(
        title=SLICE_TITLES[1],
        summary="Prove the authored minimal task API parity contract slice matches the live task-route surfaces exactly with proof-only writable scope.",
        acceptance=text(
            "A focused source-derived proof demonstrates the task API parity slice matches the live Mission Control task-route behavior exactly.",
            "The proof task stays proof-only and does not edit the production contract slice, validators, or broader taxonomy.",
            "Mission Control typecheck and the focused parity proof pass.",
        ),
        constraints=text(
            "Task API exact-parity proof-only task.",
            "Consume the authored minimal task API parity contract slice from the prior task without editing it.",
            "Do not widen into broader taxonomy, validators, or adjacent workflow families.",
        ),
        related_files=[],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**", *task_api_authority_paths],
        next_action="Write the task-route-anchored proof against the authored task API parity slice using only proof-file writable scope.",
        depends_on=[t1["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["focused proof slice"],
        primary_artifact_class="focused proof slice",
        parity_scope_mode="proof_only",
    )
    tasks.append(t1b)

    t1c = make_task(
        title=SLICE_TITLES[2],
        summary="Author only the minimal objective API production contract parity slice needed for the live objective-route branch without widening into broader taxonomy.",
        acceptance=text(
            "A minimal objective API production contract parity slice exists for the live objective-route branch.",
            "The authored slice stays narrower than the downstream shared task/objective taxonomy task and does not broaden into adjacent workflow families.",
            "The contract slice loads cleanly without requiring broader taxonomy, validator invention, or runtime emitter wiring.",
        ),
        constraints=text(
            "Objective API exact-parity contract-output task only.",
            "Author only the minimal objective API contract parity slice; do not build the parity proof here.",
            "Do not widen into validators, broader taxonomy, or adjacent workflow families.",
        ),
        related_files=parity_writable_paths,
        artifact_paths=objective_api_authority_paths,
        next_action="Read only the live objective API authority surface, then author the minimal objective API parity contract slice for that exact branch.",
        workflow_families=["task/objective"],
        abstraction_classes=["contract parity slice"],
        primary_artifact_class="contract parity slice",
        parity_scope_mode="contract_output",
    )
    tasks.append(t1c)

    t1d = make_task(
        title=SLICE_TITLES[3],
        summary="Prove the authored minimal objective API parity contract slice matches the live objective-route surface exactly with proof-only writable scope.",
        acceptance=text(
            "A focused source-derived proof demonstrates the objective API parity slice matches the live Mission Control objective-route behavior exactly.",
            "The proof task stays proof-only and does not edit the production contract slice, validators, or broader taxonomy.",
            "Mission Control typecheck and the focused parity proof pass.",
        ),
        constraints=text(
            "Objective API exact-parity proof-only task.",
            "Consume the authored minimal objective API parity contract slice from the prior task without editing it.",
            "Do not widen into broader taxonomy, validators, or adjacent workflow families.",
        ),
        related_files=[],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**", *objective_api_authority_paths],
        next_action="Write the objective-route-anchored proof against the authored objective API parity slice using only proof-file writable scope.",
        depends_on=[t1c["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["focused proof slice"],
        primary_artifact_class="focused proof slice",
        parity_scope_mode="proof_only",
    )
    tasks.append(t1d)

    t1e = make_task(
        title=SLICE_TITLES[4],
        summary="Author only the minimal worker-handler production contract parity slice needed for the live worker-handler branch without widening into broader taxonomy.",
        acceptance=text(
            "A minimal worker-handler production contract parity slice exists for the live worker-handler branch.",
            "The authored slice stays narrower than the downstream shared task/objective taxonomy task and does not broaden into adjacent workflow families.",
            "The contract slice loads cleanly without requiring broader taxonomy, validator invention, or runtime emitter wiring.",
        ),
        constraints=text(
            "Worker-handler exact-parity contract-output task only.",
            "Author only the minimal worker-handler contract parity slice; do not build the parity proof here.",
            "Do not widen into validators, broader taxonomy, or adjacent workflow families.",
        ),
        related_files=parity_writable_paths,
        artifact_paths=worker_handler_authority_paths,
        next_action="Read only the live worker-handler authority surface, then author the minimal worker-handler parity contract slice for that exact branch.",
        workflow_families=["task/objective"],
        abstraction_classes=["contract parity slice"],
        primary_artifact_class="contract parity slice",
        parity_scope_mode="contract_output",
    )
    tasks.append(t1e)

    t1f = make_task(
        title=SLICE_TITLES[5],
        summary="Prove the authored minimal worker-handler parity contract slice matches the live worker-handler surface exactly with proof-only writable scope.",
        acceptance=text(
            "A focused source-derived proof demonstrates the worker-handler parity slice matches the live Mission Control worker-handler behavior exactly.",
            "The proof task stays proof-only and does not edit the production contract slice, validators, or broader taxonomy.",
            "Mission Control typecheck and the focused parity proof pass.",
        ),
        constraints=text(
            "Worker-handler exact-parity proof-only task.",
            "Consume the authored minimal worker-handler parity contract slice from the prior task without editing it.",
            "Do not widen into broader taxonomy, validators, or adjacent workflow families.",
        ),
        related_files=[],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**", *worker_handler_authority_paths],
        next_action="Write the worker-handler-anchored proof against the authored parity slice using only proof-file writable scope.",
        depends_on=[t1e["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["focused proof slice"],
        primary_artifact_class="focused proof slice",
        parity_scope_mode="proof_only",
    )
    tasks.append(t1f)

    t1g = make_task(
        title=SLICE_TITLES[6],
        summary="Author only the minimal readiness/promotion production contract parity slice needed for the live readiness/promotion branch without widening into broader taxonomy.",
        acceptance=text(
            "A minimal readiness/promotion production contract parity slice exists for the live readiness/promotion branch.",
            "The authored slice stays narrower than the downstream shared task/objective taxonomy task and does not broaden into adjacent workflow families.",
            "The contract slice loads cleanly without requiring broader taxonomy, validator invention, or runtime emitter wiring.",
        ),
        constraints=text(
            "Readiness/promotion exact-parity contract-output task only.",
            "Author only the minimal readiness/promotion contract parity slice; do not build the parity proof here.",
            "Do not widen into validators, broader taxonomy, or adjacent workflow families.",
        ),
        related_files=parity_writable_paths,
        artifact_paths=readiness_authority_paths,
        next_action="Read only the live readiness/promotion authority surface, then author the minimal readiness/promotion parity contract slice for that exact branch.",
        workflow_families=["task/objective"],
        abstraction_classes=["contract parity slice"],
        primary_artifact_class="contract parity slice",
        parity_scope_mode="contract_output",
    )
    tasks.append(t1g)

    t1h = make_task(
        title=SLICE_TITLES[7],
        summary="Prove the authored minimal readiness/promotion parity contract slice matches the live readiness/promotion surface exactly with proof-only writable scope.",
        acceptance=text(
            "A focused source-derived proof demonstrates the readiness/promotion parity slice matches the live Mission Control readiness/promotion behavior exactly.",
            "The proof task stays proof-only and does not edit the production contract slice, validators, or broader taxonomy.",
            "Mission Control typecheck and the focused parity proof pass.",
        ),
        constraints=text(
            "Readiness/promotion exact-parity proof-only task.",
            "Consume the authored minimal readiness/promotion parity contract slice from the prior task without editing it.",
            "Do not widen into broader taxonomy, validators, or adjacent workflow families.",
        ),
        related_files=[],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**", *readiness_authority_paths],
        next_action="Write the readiness/promotion-anchored proof against the authored parity slice using only proof-file writable scope.",
        depends_on=[t1g["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["focused proof slice"],
        primary_artifact_class="focused proof slice",
        parity_scope_mode="proof_only",
    )
    tasks.append(t1h)

    t2 = make_task(
        title=SLICE_TITLES[8],
        summary="Define the shared task/objective workflow event names and payload shapes outside the already-authored and already-proven root-bounded parity slices.",
        acceptance=text(
            "Shared task/objective workflow contract definitions exist under the knowledge-plane contracts layer.",
            "The shared taxonomy consumes the proven root-bounded parity slices instead of rereading sibling runtime roots directly.",
            "The taxonomy excludes release, activation, and escalation families.",
        ),
        constraints=text(
            "Shared task/objective taxonomy only.",
            "Consume the four proven parity slices instead of rereading live route or worker roots directly.",
            "Do not wire runtime emitters in this task.",
        ),
        related_files=parity_writable_paths,
        artifact_paths=[],
        next_action="Extend the shared task/objective contract family around the four proven root-bounded parity slices without wiring emitters yet.",
        depends_on=[t1b["id"], t1d["id"], t1f["id"], t1h["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t2)

    t3 = make_task(
        title=SLICE_TITLES[9],
        summary="Author the release workflow contract family as an explicit contract input for later release emitter tasks.",
        acceptance=text(
            "Release event names and payload shapes are defined in the contracts layer.",
            "The release family boundary is explicit and not embedded inside emitter tasks.",
            "Focused validation proves the contract layer loads without runtime coupling.",
        ),
        constraints=text(
            "Contract-authoring only.",
            "Do not wire emitters or backfill in this task.",
        ),
        related_files=release_contract_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/release/objective-release-service.ts",
        ],
        next_action="Define the release workflow contract family as explicit upstream input for later release emitter tasks, using the live release runtime files as read-only authority only.",
        workflow_families=["release"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3)

    t3b = make_task(
        title=SLICE_TITLES[10],
        summary="Author the activation workflow contract family as an explicit contract input for later activation emitter tasks.",
        acceptance=text(
            "Activation event names and payload shapes are defined in the contracts layer.",
            "The activation family boundary is explicit and not embedded inside emitter tasks.",
            "Focused validation proves the contract layer loads without runtime coupling.",
        ),
        constraints=text(
            "Contract-authoring only.",
            "Do not wire emitters or backfill in this task.",
        ),
        related_files=activation_contract_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/release/objective-activation-service.ts",
        ],
        next_action="Define the activation workflow contract family as explicit upstream input for later activation emitter tasks, using the live activation runtime file as read-only authority only.",
        workflow_families=["activation"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3b)

    t3c = make_task(
        title=SLICE_TITLES[11],
        summary="Author the escalation workflow contract family as an explicit contract input for later escalation emitter tasks.",
        acceptance=text(
            "Escalation event names and payload shapes are defined in the contracts layer.",
            "The escalation family boundary is explicit and not embedded inside emitter tasks.",
            "Focused validation proves the contract layer loads without runtime coupling.",
        ),
        constraints=text(
            "Contract-authoring only.",
            "Do not wire emitters or backfill in this task.",
        ),
        related_files=escalation_contract_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/workers/escalation-events.ts",
        ],
        next_action="Define the escalation workflow contract family as explicit upstream input for later escalation emitter tasks, using the live escalation runtime file as read-only authority only.",
        workflow_families=["escalation"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3c)

    t4 = make_task(
        title=SLICE_TITLES[12],
        summary="Lay down the LedgerEvent Prisma schema model foundation for durable workflow event storage before any storage or ledger implementation begins.",
        acceptance=text(
            "The LedgerEvent schema model is defined in Prisma with migration-safe IDs and correlation fields.",
            "The schema does not bundle runtime write-path behavior or duplicate-prevention logic.",
            "Schema validation passes.",
        ),
        constraints=text(
            "Schema-model foundation only.",
            "Do not author migration files, repository writes, or readback queries here.",
        ),
        related_files=schema_model_paths,
        artifact_paths=["apps/mission-control/prisma/schema.prisma", *schema_migration_paths],
        next_action="Define the durable event schema model before any migration, repository, or write-path wiring.",
        workflow_families=["ledger-schema"],
        abstraction_classes=["schema model or migration slice"],
        primary_artifact_class="schema model or migration slice",
    )
    tasks.append(t4)

    t4b = make_task(
        title=SLICE_TITLES[13],
        summary="Create the LedgerEvent Prisma migration scaffold over the established schema model without expanding into repository or runtime behavior.",
        acceptance=text(
            "A bounded LedgerEvent migration scaffold exists for the approved schema model.",
            "The migration scaffold does not redesign the schema model or embed repository/runtime behavior.",
            "Migration generation or validation passes for the scoped change.",
        ),
        constraints=text(
            "Migration scaffold only.",
            "Consume the approved schema model as read-only authority.",
            "Do not implement repository writes or readback queries here.",
        ),
        related_files=schema_migration_paths,
        artifact_paths=["apps/mission-control/prisma/schema.prisma", *schema_migration_paths],
        next_action="Create the bounded LedgerEvent migration scaffold from the approved schema model.",
        workflow_families=["ledger-schema"],
        abstraction_classes=["schema model or migration slice"],
        primary_artifact_class="schema model or migration slice",
    )
    tasks.append(t4b)

    t5 = make_task(
        title=SLICE_TITLES[14],
        summary="Define the concrete LedgerEvent repository boundary over the established schema without taking on exports, writer logic, or duplicate handling yet.",
        acceptance=text(
            "A concrete LedgerEvent repository boundary exists for ledger events and consumes the established Prisma LedgerEvent schema as read-only input.",
            "The repository boundary is explicit enough for later export, writer, and readback tasks to consume without redesigning repository shape.",
            "Focused tests prove the repository boundary loads cleanly.",
        ),
        constraints=text(
            "Repository boundary only.",
            "Consume the established Prisma schema as upstream authority input; do not redesign it here.",
            "The Prisma schema and migration files are preserve-only authority for proof and must remain read-only input.",
            "Do not wire storage exports, implement the canonical writer, emitter wiring, or duplicate prevention here.",
        ),
        related_files=storage_foundation_paths,
        artifact_paths=[*schema_model_paths],
        next_action="Define the concrete repository boundary that later storage-export and writer tasks will call.",
        depends_on=[t4["id"], t4b["id"]],
        workflow_families=["ledger-storage"],
        abstraction_classes=["repository boundary"],
        primary_artifact_class="repository boundary",
    )
    tasks.append(t5)

    t5b = make_task(
        title=SLICE_TITLES[15],
        summary="Wire the LedgerEvent storage export surface over the established repository boundary without taking on writer logic or duplicate handling.",
        acceptance=text(
            "The LedgerEvent storage export surface is explicit and stable for downstream ledger tasks.",
            "Focused tests prove the storage exports load cleanly over the existing repository boundary.",
            "The task does not implement canonical writer behavior or workflow-family emitter wiring.",
        ),
        constraints=text(
            "Storage exports only.",
            "Do not redesign the repository boundary or schema in this task.",
            "Do not implement canonical writer behavior, emitter wiring, or duplicate prevention here.",
        ),
        related_files=[
            "apps/mission-control/src/lib/storage/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/storage/**"],
        next_action="Wire the stable storage export surface over the repository boundary before the canonical writer is introduced.",
        depends_on=[t5["id"]],
        workflow_families=["ledger-storage"],
        abstraction_classes=["storage export surface"],
        primary_artifact_class="storage export surface",
    )
    tasks.append(t5b)

    t6 = make_task(
        title=SLICE_TITLES[16],
        summary="Implement the canonical ledger writer over the existing storage export surface without taking on identity/correlation hardening or duplicate handling yet.",
        acceptance=text(
            "A single canonical ledger writer exists over the established storage export surface.",
            "Focused tests prove the writer persists valid events through the intended boundary.",
            "No workflow-family emitter wiring or identity/correlation hardening is bundled into this task.",
        ),
        constraints=text(
            "Canonical writer only.",
            "Do not implement stable identity/correlation hardening here.",
            "Do not redesign the repository boundary, storage exports, or schema in this task.",
        ),
        related_files=[
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Implement the canonical ledger writer over the established storage export surface before identity/correlation hardening and emitter tasks consume it.",
        depends_on=[t5["id"], t5b["id"]],
        workflow_families=["ledger-writer"],
        abstraction_classes=["canonical writer"],
        primary_artifact_class="canonical writer",
    )
    tasks.append(t6)

    t6b = make_task(
        title=SLICE_TITLES[17],
        summary="Harden stable event identity and correlation mapping for ledger writes over the existing canonical writer.",
        acceptance=text(
            "Stable event identity and correlation mapping is enforced on the ledger write path.",
            "Focused tests prove stable identity and correlation mapping without broadening into replay/remediation duplicate-prevention logic.",
            "The task does not redesign the canonical writer surface itself.",
        ),
        constraints=text(
            "Identity/correlation hardening only.",
            "Do not implement replay/remediation duplicate prevention here.",
            "Do not redesign the repository boundary, storage exports, or canonical writer surface in this task.",
        ),
        related_files=[
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Harden stable event identity and correlation mapping over the existing canonical writer before downstream runtime families consume it.",
        depends_on=[t6["id"]],
        workflow_families=["ledger-writer"],
        abstraction_classes=["identity/correlation mapping surface"],
        primary_artifact_class="identity/correlation mapping surface",
    )
    tasks.append(t6b)

    t7 = make_task(
        title=SLICE_TITLES[18],
        summary="Wire direct task API mutation entrypoints to the canonical ledger path using the already-authored task/objective contract family.",
        acceptance=text(
            "Direct task API mutation entrypoints emit through the canonical ledger path.",
            "Emitter wiring consumes the pre-authored contract family instead of inventing it inline.",
            "Focused tests prove the targeted task API-entrypoint transitions emit the expected events.",
        ),
        constraints=text(
            "Task API-entrypoint emitter slice only.",
            "Do not wire objective API routes, worker transition/promotion files, release, activation, or escalation surfaces here.",
        ),
        related_files=[
            "apps/mission-control/src/app/api/tasks/route.ts",
            "apps/mission-control/src/app/api/tasks/[id]/route.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only the direct task API mutation entrypoints to the canonical writer and prove them with focused tests.",
        depends_on=[t2["id"], t6["id"], t6b["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t7)

    t7b = make_task(
        title=SLICE_TITLES[19],
        summary="Wire direct objective API mutation entrypoints to the canonical ledger path using the already-authored task/objective contract family.",
        acceptance=text(
            "Direct objective API mutation entrypoints emit through the canonical ledger path.",
            "Emitter wiring consumes the pre-authored contract family instead of inventing it inline.",
            "Focused tests prove the targeted objective API-entrypoint transitions emit the expected events.",
        ),
        constraints=text(
            "Objective API-entrypoint emitter slice only.",
            "Do not wire task API routes, worker transition/promotion files, release, activation, or escalation surfaces here.",
        ),
        related_files=[
            "apps/mission-control/src/app/api/objectives/[id]/route.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only the direct objective API mutation entrypoints to the canonical writer and prove them with focused tests.",
        depends_on=[t2["id"], t6["id"], t6b["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t7b)

    t7c = make_task(
        title=SLICE_TITLES[20],
        summary="Wire worker handler task/objective transition paths to the canonical ledger path using the already-authored task/objective contract family.",
        acceptance=text(
            "Worker handler task/objective transition behavior emits through the canonical ledger path.",
            "Emitter wiring consumes the pre-authored contract family instead of inventing it inline.",
            "Focused tests prove the targeted worker-handler transition behavior emits the expected events.",
        ),
        constraints=text(
            "Worker handler emitter slice only.",
            "Do not wire readiness/promotion, direct API mutation entrypoints, release, activation, or escalation surfaces here.",
        ),
        related_files=[
            "apps/mission-control/src/lib/workers/handlers.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only the worker handler transition paths to the canonical writer and prove them with focused tests.",
        depends_on=[t2["id"], t6["id"], t6b["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t7c)

    t7d = make_task(
        title=SLICE_TITLES[21],
        summary="Wire readiness/promotion task progression paths to the canonical ledger path using the already-authored task/objective contract family.",
        acceptance=text(
            "Readiness and promotion task/objective transition behavior emits through the canonical ledger path.",
            "Emitter wiring consumes the pre-authored contract family instead of inventing it inline.",
            "Focused tests prove the targeted readiness/promotion transition behavior emits the expected events.",
        ),
        constraints=text(
            "Readiness/promotion emitter slice only.",
            "Do not wire worker handlers, direct API mutation entrypoints, release, activation, or escalation surfaces here.",
        ),
        related_files=[
            "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only the readiness/promotion transition paths to the canonical writer and prove them with focused tests.",
        depends_on=[t2["id"], t6["id"], t6b["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t7d)

    t8 = make_task(
        title=SLICE_TITLES[22],
        summary="Wire release-start events to the canonical ledger path using the already-authored release contract family.",
        acceptance=text(
            "Release-start runtime behavior emits the expected ledger events through the canonical writer.",
            "The task consumes the release contract family rather than authoring it inline.",
            "Focused tests prove release-start emission behavior.",
        ),
        constraints=text("Release-start emitter family only.", "Do not bundle merge/deploy/verify, activation, or escalation here."),
        related_files=release_start_emitter_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only the release-start surfaces to the canonical ledger writer.",
        depends_on=[t3["id"], t6["id"], t6b["id"]],
        workflow_families=["release"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t8)

    t9 = make_task(
        title=SLICE_TITLES[23],
        summary="Wire merge/runtime transition events to the canonical ledger path using the already-authored release contract family.",
        acceptance=text(
            "Merge/runtime transition behavior emits through the canonical writer.",
            "The task consumes the release contract family rather than authoring it inline.",
            "Focused tests prove merge/runtime transition emission behavior.",
        ),
        constraints=text("Merge/runtime transition emitter slice only.", "Do not bundle release-start, deploy/verify, activation, or escalation here."),
        related_files=merge_runtime_emitter_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only merge/runtime transition surfaces to the canonical ledger writer.",
        depends_on=[t3["id"], t6["id"], t6b["id"]],
        workflow_families=["release"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t9)

    t10 = make_task(
        title=SLICE_TITLES[24],
        summary="Wire deploy/verify runtime events to the canonical ledger path using the already-authored release contract family.",
        acceptance=text(
            "Deploy/verify runtime behavior emits through the canonical writer.",
            "The task consumes the release contract family rather than authoring it inline.",
            "Focused tests prove deploy/verify emission behavior.",
        ),
        constraints=text("Deploy/verify emitter slice only.", "Do not bundle release-start, merge/runtime transition, activation, or escalation here."),
        related_files=deploy_verify_emitter_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only deploy/verify surfaces to the canonical ledger writer.",
        depends_on=[t3["id"], t6["id"], t6b["id"]],
        workflow_families=["release"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t10)

    t11 = make_task(
        title=SLICE_TITLES[25],
        summary="Wire activation runtime events to the canonical ledger path using the already-authored activation contract family.",
        acceptance=text(
            "Activation runtime behavior emits through the canonical writer.",
            "The task consumes the activation contract family rather than authoring it inline.",
            "Focused tests prove activation emission behavior.",
        ),
        constraints=text("Activation emitter family only.", "Do not bundle release or escalation families here."),
        related_files=activation_emitter_paths,
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only activation surfaces to the canonical ledger writer.",
        depends_on=[t3b["id"], t6["id"], t6b["id"]],
        workflow_families=["activation"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t11)

    t12 = make_task(
        title=SLICE_TITLES[26],
        summary="Wire escalation runtime events to the canonical ledger path using the already-authored escalation contract family.",
        acceptance=text(
            "Escalation runtime behavior emits through the canonical writer.",
            "The task consumes the escalation contract family rather than authoring it inline.",
            "Focused tests prove escalation emission behavior.",
        ),
        constraints=text("Escalation emitter family only.", "Do not bundle task/objective, release, or activation families here."),
        related_files=[
            "apps/mission-control/src/lib/workers/escalation-events.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Wire only escalation surfaces to the canonical ledger writer.",
        depends_on=[t3c["id"], t6["id"], t6b["id"]],
        workflow_families=["escalation"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t12)

    t13 = make_task(
        title=SLICE_TITLES[27],
        summary="Implement the deterministic ledger readback query surface over the persisted ledger events.",
        acceptance=text(
            "Deterministic readback queries exist for objective, task, agent, and event-type access patterns.",
            "The query layer is separate from API projection and backfill logic.",
            "Focused tests prove the query surface returns deterministic results.",
        ),
        constraints=text("Query surface only.", "Do not expose API routes or backfill in this task."),
        related_files=readback_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Implement the deterministic readback query layer over the persisted ledger data.",
        depends_on=[t6["id"], t6b["id"]],
        workflow_families=["readback"],
        abstraction_classes=["deterministic query surface"],
        primary_artifact_class="deterministic query surface",
    )
    tasks.append(t13)

    t14 = make_task(
        title=SLICE_TITLES[28],
        summary="Expose ledger readback through the API surface and prove the readback contract end to end.",
        acceptance=text(
            "Ledger readback API routes exist and consume the deterministic query layer.",
            "Focused tests or deterministic readback proof cover the API surface.",
            "The task does not widen into semantic retrieval or wiki projection.",
        ),
        constraints=text("Readback API and proof only.", "Do not bundle backfill or duplicate-prevention changes here."),
        related_files=api_paths,
        artifact_paths=["apps/mission-control/src/app/api/knowledge/ledger/**"],
        next_action="Expose the deterministic ledger query surface through the API and prove the API contract.",
        depends_on=[t13["id"]],
        workflow_families=["readback"],
        abstraction_classes=["API readback surface"],
        primary_artifact_class="API readback surface",
    )
    tasks.append(t14)

    t15 = make_task(
        title=SLICE_TITLES[29],
        summary="Harden replay/remediation duplicate prevention so retries, replay, remediation loops, and repeated writes do not create incorrect duplicate ledger writes.",
        acceptance=text(
            "Duplicate prevention is enforced on the ledger write path for the relevant retry/replay surfaces.",
            "Focused tests cover replay/retry/remediation duplicate-prevention invariants.",
            "The task does not widen into new workflow-family wiring.",
        ),
        constraints=text("Duplicate-prevention hardening only.", "Do not bundle backfill or readback API work here."),
        related_files=[
            "apps/mission-control/src/lib/workers/idempotency.ts",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Harden the write path against duplicate creation under replay and retry paths.",
        depends_on=[t6["id"], t6b["id"]],
        workflow_families=["duplicate-prevention"],
        abstraction_classes=["duplicate-prevention surface"],
        primary_artifact_class="duplicate-prevention surface",
    )
    tasks.append(t15)

    t16 = make_task(
        title=SLICE_TITLES[30],
        summary="Backfill a bounded recent slice of factory workflow history into the ledger without expanding into full retrieval or synthesis work.",
        acceptance=text(
            "A bounded recent backfill path exists for the intended workflow slice.",
            "Backfill respects duplicate-prevention invariants and does not create incorrect duplicates.",
            "Focused proof shows the bounded backfill writes the intended history slice.",
        ),
        constraints=text("Bounded backfill only.", "Do not widen into long-term archaeology or semantic retrieval."),
        related_files=[
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Implement the bounded workflow-history backfill over the hardened ledger write path.",
        depends_on=[t13["id"], t15["id"]],
        workflow_families=["backfill"],
        abstraction_classes=["bounded backfill surface"],
        primary_artifact_class="bounded backfill surface",
    )
    tasks.append(t16)

    t17 = make_task(
        title=SLICE_TITLES[31],
        summary="Document the workflow-ledger contract, operator proof path, and objective-local scope boundaries for this phase.",
        acceptance=text(
            "Repo-local knowledge-plane documentation captures the workflow-ledger contract and proof surfaces introduced by this objective.",
            "The documentation stays scoped to 1A.1 and does not wander into retrieval or wiki projection.",
            "Referenced docs align with the implemented workflow-ledger surfaces.",
        ),
        constraints=text("Docs-primary task.", "Do not bundle runtime emitter or storage implementation here."),
        related_files=docs_paths + ["apps/mission-control/src/lib/knowledge-plane/contracts/**", "apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        artifact_paths=["apps/mission-control/docs/knowledge-plane/**"],
        next_action="Write the scoped workflow-ledger docs after the runtime surfaces are in place.",
        assignee="Librarian",
        depends_on=[
            t1["id"], t1b["id"], t1c["id"], t1d["id"], t1e["id"], t1f["id"], t1g["id"], t1h["id"], t2["id"], t3["id"], t3b["id"], t3c["id"], t4["id"], t4b["id"], t5["id"],
            t5b["id"], t6["id"], t6b["id"], t7["id"], t7b["id"], t7c["id"], t7d["id"], t8["id"], t9["id"], t10["id"],
            t11["id"], t12["id"], t13["id"], t14["id"], t15["id"], t16["id"],
        ],
        workflow_families=["docs"],
        abstraction_classes=["docs"],
        primary_artifact_class="docs",
    )
    tasks.append(t17)

    t18 = make_task(
        title="Gate review workflow-ledger canary",
        summary="Review the completed 1A.1 execution graph only after all bounded slices are done and the proof surfaces are present.",
        acceptance=text(
            f"Approve only when all {len(tasks)} upstream tasks are complete and their bounded outputs remain semantically separate.",
            "Reject if any workflow family was rebundled, if proof is missing from the parity slice, or if duplicate-prevention/readback/backfill surfaces were collapsed incorrectly.",
            "Review the implemented task graph against the live objective contract rather than prior attempt residue.",
        ),
        constraints=text("Gate-review only.", "Do not implement code or docs in this task."),
        related_files=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/storage/**",
            "apps/mission-control/src/app/api/knowledge/ledger/**",
            "apps/mission-control/docs/knowledge-plane/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
            "apps/mission-control/prisma/schema.prisma",
            "apps/mission-control/prisma/migrations/**",
        ],
        artifact_paths=[
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/app/api/knowledge/ledger/**",
            "apps/mission-control/docs/knowledge-plane/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        next_action="Review the completed bounded graph against the 1A.1 objective contract.",
        assignee="Bernard",
        task_type="review",
        review_mode="gate_review",
        depends_on=[task["id"] for task in tasks],
    )
    tasks.append(t18)

    if len(tasks) != APPROVED_MAX_TASK_COUNT:
        raise SystemExit(
            f"expected {APPROVED_MAX_TASK_COUNT} total tasks (32 execution slices + 1 gate review), found {len(tasks)}"
        )

    validate_bounded_graph(tasks)
    payload = {
        "kind": "decomposition_result",
        "objectiveId": objective["id"],
        "actor": "Bernard",
        "requestReview": True,
        "statusNote": "Decomposed 1A.1 into 33 root-bounded contract-mode slices with dedicated gate review.",
        "tasks": sanitize_tasks(tasks),
    }

    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
