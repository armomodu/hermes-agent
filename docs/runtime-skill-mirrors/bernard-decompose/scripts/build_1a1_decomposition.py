#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path


SLICE_TITLES = [
    "Prove task/objective workflow parity against the live route contract",
    "Define task/objective workflow contract taxonomy",
    "Define release workflow contract taxonomy",
    "Define activation workflow contract taxonomy",
    "Define escalation workflow contract taxonomy",
    "Establish LedgerEvent Prisma schema foundation",
    "Define LedgerEvent repository boundary and storage exports",
    "Implement canonical ledger writer with stable identity mapping",
    "Wire task/objective emitters to the canonical ledger path",
    "Wire release-start emitters to the canonical ledger path",
    "Wire merge/deploy/verify emitters to the canonical ledger path",
    "Wire activation emitters to the canonical ledger path",
    "Wire escalation emitters to the canonical ledger path",
    "Implement deterministic ledger readback queries",
    "Expose ledger readback API and proof",
    "Harden replay/remediation duplicate prevention for ledger writes",
    "Backfill a bounded recent slice into the ledger",
    "Document the workflow-ledger contract and operator proof path",
]


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
        title = task["title"]

        if len(families) != 1:
            errors.append(f"{title}: expected exactly 1 workflow family, found {families}")
        if len(abstractions) != 1:
            errors.append(f"{title}: expected exactly 1 abstraction class, found {abstractions}")
        if not primary_artifact:
            errors.append(f"{title}: missing primary artifact class")
        if not distinct_delta:
            errors.append(f"{title}: downstream task lacks a distinct substantive delta")

        if "readback" in title.lower() and len(task.get("dependsOn", [])) > 3:
            errors.append(f"{title}: readback task depends on too many upstream slices")
        if "duplicate prevention" in title.lower() and len(task.get("dependsOn", [])) > 3:
            errors.append(f"{title}: duplicate-prevention task depends on too many upstream slices")

    if errors:
        raise SystemExit("bounded-graph validation failed:\n- " + "\n- ".join(errors))


def sanitize_tasks(tasks: list[dict]) -> list[dict]:
    return [{k: v for k, v in task.items() if k != "__meta"} for task in tasks]


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: build_1a1_decomposition.py <objective.json> <decomposition.json>", file=sys.stderr)
        return 2

    objective_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])
    objective = json.loads(objective_path.read_text(encoding="utf-8"))

    if objective.get("id") != "4009e581-7231-4930-9a0d-b2b56b281d9e":
        print("unexpected objective id", file=sys.stderr)
        return 2

    parity_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/app/api/tasks/route.ts",
        "apps/mission-control/src/app/api/tasks/[id]/route.ts",
        "apps/mission-control/src/app/api/objectives/[id]/route.ts",
        "apps/mission-control/src/lib/workers/handlers.ts",
        "apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts",
    ]
    task_objective_emitter_paths = parity_paths + [
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    release_contract_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/release/objective-release-service.ts",
        "apps/mission-control/src/lib/release/objective-deployment-service.ts",
    ]
    activation_contract_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/release/objective-activation-service.ts",
    ]
    escalation_contract_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/workers/escalation-events.ts",
    ]
    release_start_emitter_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/release/objective-release-service.ts",
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    merge_deploy_verify_emitter_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/release/objective-release-service.ts",
        "apps/mission-control/src/lib/release/objective-deployment-service.ts",
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    activation_emitter_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        "apps/mission-control/src/lib/release/objective-activation-service.ts",
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
    ]
    schema_paths = [
        "apps/mission-control/prisma/schema.prisma",
        "apps/mission-control/prisma/migrations/**",
    ]
    storage_foundation_paths = [
        "apps/mission-control/src/lib/storage/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
    ]
    ledger_write_paths = [
        "apps/mission-control/src/lib/knowledge-plane/contracts/**",
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
    ]
    readback_paths = [
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
    ]
    docs_paths = [
        "apps/mission-control/docs/knowledge-plane/**",
    ]
    api_paths = [
        "apps/mission-control/src/app/api/knowledge/ledger/**",
        "apps/mission-control/src/lib/knowledge-plane/ledger/**",
        "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
    ]

    tasks: list[dict] = []

    t1 = make_task(
        title=SLICE_TITLES[0],
        summary="Mirror the current task/objective workflow behavior into the knowledge-plane contract layer with exact-parity proof anchored to the live route surfaces.",
        acceptance=text(
            "The focused parity test proves the emitted task/objective workflow contract matches the live Mission Control behavior for the targeted route/transition surface.",
            "The parity task does not redefine broader release, activation, or escalation families.",
            "Mission Control typecheck and the focused parity proof pass.",
        ),
        constraints=text(
            "Exact-parity task only. Keep the minimal route-anchored proof inside this task.",
            "Do not broaden into general contract taxonomy for other workflow families.",
        ),
        related_files=parity_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Read the live task/objective transition authority surfaces and author the focused parity contract plus proof first.",
        workflow_families=["task/objective"],
        abstraction_classes=["focused proof slice"],
        primary_artifact_class="focused proof slice",
    )
    tasks.append(t1)

    t2 = make_task(
        title=SLICE_TITLES[1],
        summary="Define the remaining task/objective workflow event names and payload shapes outside the exact-parity slice already isolated above.",
        acceptance=text(
            "Task/objective workflow contract definitions exist under the knowledge-plane contracts layer.",
            "The taxonomy excludes release, activation, and escalation families.",
            "Focused tests or deterministic validation prove the task/objective family definitions load cleanly.",
        ),
        constraints=text(
            "Consume the parity slice from the prior task instead of redefining it.",
            "Do not wire runtime emitters in this task.",
        ),
        related_files=parity_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**"],
        next_action="Extend the task/objective contract family around the already-proven parity slice without wiring emitters yet.",
        depends_on=[t1["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t2)

    t3 = make_task(
        title=SLICE_TITLES[2],
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
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**"],
        next_action="Define the release workflow contract family as explicit upstream input for later release emitter tasks.",
        workflow_families=["release"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3)

    t3b = make_task(
        title=SLICE_TITLES[3],
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
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**"],
        next_action="Define the activation workflow contract family as explicit upstream input for later activation emitter tasks.",
        workflow_families=["activation"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3b)

    t3c = make_task(
        title=SLICE_TITLES[4],
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
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/contracts/**"],
        next_action="Define the escalation workflow contract family as explicit upstream input for later escalation emitter tasks.",
        workflow_families=["escalation"],
        abstraction_classes=["contract family"],
        primary_artifact_class="contract family",
    )
    tasks.append(t3c)

    t4 = make_task(
        title=SLICE_TITLES[5],
        summary="Lay down the LedgerEvent Prisma schema foundation for durable workflow event storage before any storage or ledger implementation begins.",
        acceptance=text(
            "The LedgerEvent schema foundation is defined in Prisma with migration-safe IDs and correlation fields.",
            "The schema does not bundle runtime write-path behavior or duplicate-prevention logic.",
            "Schema validation passes.",
        ),
        constraints=text(
            "Schema foundation only.",
            "Do not implement repository writes or readback queries here.",
        ),
        related_files=schema_paths,
        artifact_paths=["apps/mission-control/prisma/schema.prisma", "apps/mission-control/prisma/migrations/**"],
        next_action="Define the durable event schema and migration foundation before any write-path wiring.",
        workflow_families=["ledger-schema"],
        abstraction_classes=["schema model or migration slice"],
        primary_artifact_class="schema model or migration slice",
    )
    tasks.append(t4)

    t5 = make_task(
        title=SLICE_TITLES[6],
        summary="Define the concrete LedgerEvent repository boundary and storage export surface over the established schema without taking on writer or duplicate logic yet.",
        acceptance=text(
            "A concrete LedgerEvent repository boundary exists for ledger events and consumes the established Prisma LedgerEvent schema as read-only input.",
            "The storage export surface is explicit enough for later writer and readback tasks to consume without redesigning repository shape.",
            "Focused tests prove the repository boundary and storage exports load cleanly.",
        ),
        constraints=text(
            "Repository boundary and storage exports only.",
            "Consume the established Prisma schema as read-only input; do not redesign it here.",
            "Do not implement the canonical writer, emitter wiring, or duplicate prevention here.",
        ),
        related_files=storage_foundation_paths,
        artifact_paths=["apps/mission-control/src/lib/storage/**"],
        next_action="Define the concrete repository boundary and storage exports that later writer tasks will call.",
        depends_on=[t4["id"]],
        workflow_families=["ledger-storage"],
        abstraction_classes=["repository boundary"],
        primary_artifact_class="repository boundary",
    )
    tasks.append(t5)

    t6 = make_task(
        title=SLICE_TITLES[7],
        summary="Implement the canonical ledger writer over the existing repository boundary while preserving stable event identity and correlation mapping.",
        acceptance=text(
            "A single canonical ledger writer exists over the established repository boundary.",
            "Focused tests prove the writer persists valid events while preserving stable event identity and correlation mapping through the intended boundary.",
            "No workflow-family emitter wiring is bundled into this task.",
        ),
        constraints=text(
            "Canonical writer plus identity-mapping only.",
            "Do not implement replay/remediation duplicate prevention here.",
            "Do not redesign the repository boundary or schema in this task.",
        ),
        related_files=ledger_write_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Implement the canonical ledger writer over the existing repository boundary and lock the stable identity-mapping behavior before emitter tasks consume it.",
        depends_on=[t4["id"], t5["id"]],
        workflow_families=["ledger-writer"],
        abstraction_classes=["canonical writer"],
        primary_artifact_class="canonical writer",
    )
    tasks.append(t6)

    t7 = make_task(
        title=SLICE_TITLES[8],
        summary="Wire task/objective runtime transitions to the canonical ledger path using the already-authored task/objective contract family.",
        acceptance=text(
            "Task/objective runtime transitions emit through the canonical ledger path.",
            "Emitter wiring consumes the pre-authored contract family instead of inventing it inline.",
            "Focused tests prove the targeted task/objective transitions emit the expected events.",
        ),
        constraints=text(
            "Task/objective emitter family only.",
            "Do not wire release, activation, or escalation surfaces here.",
        ),
        related_files=task_objective_emitter_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Wire only the task/objective family to the canonical writer and prove it with focused tests.",
        depends_on=[t2["id"], t6["id"]],
        workflow_families=["task/objective"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t7)

    t8 = make_task(
        title=SLICE_TITLES[9],
        summary="Wire release-start events to the canonical ledger path using the already-authored release contract family.",
        acceptance=text(
            "Release-start runtime behavior emits the expected ledger events through the canonical writer.",
            "The task consumes the release contract family rather than authoring it inline.",
            "Focused tests prove release-start emission behavior.",
        ),
        constraints=text("Release-start emitter family only.", "Do not bundle merge/deploy/verify, activation, or escalation here."),
        related_files=release_start_emitter_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Wire only the release-start surfaces to the canonical ledger writer.",
        depends_on=[t3["id"], t6["id"]],
        workflow_families=["release"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t8)

    t9 = make_task(
        title=SLICE_TITLES[10],
        summary="Wire merge/deploy/verify runtime events to the canonical ledger path using the already-authored release contract family.",
        acceptance=text(
            "Merge, deploy, and verify runtime behavior emits through the canonical writer.",
            "The task consumes the release contract family rather than authoring it inline.",
            "Focused tests prove merge/deploy/verify emission behavior.",
        ),
        constraints=text("Merge/deploy/verify emitter family only.", "Do not bundle release-start, activation, or escalation here."),
        related_files=merge_deploy_verify_emitter_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Wire only merge/deploy/verify surfaces to the canonical ledger writer.",
        depends_on=[t3["id"], t6["id"]],
        workflow_families=["release"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t9)

    t10 = make_task(
        title=SLICE_TITLES[11],
        summary="Wire activation runtime events to the canonical ledger path using the already-authored activation contract family.",
        acceptance=text(
            "Activation runtime behavior emits through the canonical writer.",
            "The task consumes the activation contract family rather than authoring it inline.",
            "Focused tests prove activation emission behavior.",
        ),
        constraints=text("Activation emitter family only.", "Do not bundle release or escalation families here."),
        related_files=activation_emitter_paths,
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Wire only activation surfaces to the canonical ledger writer.",
        depends_on=[t3b["id"], t6["id"]],
        workflow_families=["activation"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t10)

    t11 = make_task(
        title=SLICE_TITLES[12],
        summary="Wire escalation runtime events to the canonical ledger path using the already-authored escalation contract family.",
        acceptance=text(
            "Escalation runtime behavior emits through the canonical writer.",
            "The task consumes the escalation contract family rather than authoring it inline.",
            "Focused tests prove escalation emission behavior.",
        ),
        constraints=text("Escalation emitter family only.", "Do not bundle task/objective, release, or activation families here."),
        related_files=[
            "apps/mission-control/src/lib/workers/escalation-events.ts",
            "apps/mission-control/src/lib/knowledge-plane/contracts/**",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Wire only escalation surfaces to the canonical ledger writer.",
        depends_on=[t3c["id"], t6["id"]],
        workflow_families=["escalation"],
        abstraction_classes=["emitter-wiring slice"],
        primary_artifact_class="emitter-wiring slice",
    )
    tasks.append(t11)

    t12 = make_task(
        title=SLICE_TITLES[13],
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
        depends_on=[t6["id"]],
        workflow_families=["readback"],
        abstraction_classes=["deterministic query surface"],
        primary_artifact_class="deterministic query surface",
    )
    tasks.append(t12)

    t13 = make_task(
        title=SLICE_TITLES[14],
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
        depends_on=[t12["id"]],
        workflow_families=["readback"],
        abstraction_classes=["API readback surface"],
        primary_artifact_class="API readback surface",
    )
    tasks.append(t13)

    t14 = make_task(
        title=SLICE_TITLES[15],
        summary="Harden replay/remediation duplicate prevention so retries, replay, remediation loops, and repeated writes do not create incorrect duplicate ledger writes.",
        acceptance=text(
            "Duplicate prevention is enforced on the ledger write path for the relevant retry/replay surfaces.",
            "Focused tests cover replay/retry/remediation duplicate-prevention invariants.",
            "The task does not widen into new workflow-family wiring.",
        ),
        constraints=text("Duplicate-prevention hardening only.", "Do not bundle backfill or readback API work here."),
        related_files=[
            "apps/mission-control/src/lib/workers/idempotency.ts",
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/__tests__/**"],
        next_action="Harden the write path against duplicate creation under replay and retry paths.",
        depends_on=[t6["id"]],
        workflow_families=["duplicate-prevention"],
        abstraction_classes=["duplicate-prevention surface"],
        primary_artifact_class="duplicate-prevention surface",
    )
    tasks.append(t14)

    t15 = make_task(
        title=SLICE_TITLES[16],
        summary="Backfill a bounded recent slice of factory workflow history into the ledger without expanding into full retrieval or synthesis work.",
        acceptance=text(
            "A bounded recent backfill path exists for the intended workflow slice.",
            "Backfill respects duplicate-prevention invariants and does not create incorrect duplicates.",
            "Focused proof shows the bounded backfill writes the intended history slice.",
        ),
        constraints=text("Bounded backfill only.", "Do not widen into long-term archaeology or semantic retrieval."),
        related_files=[
            "apps/mission-control/src/lib/knowledge-plane/ledger/**",
            "apps/mission-control/src/lib/knowledge-plane/__tests__/**",
        ],
        artifact_paths=["apps/mission-control/src/lib/knowledge-plane/ledger/**"],
        next_action="Implement the bounded workflow-history backfill over the hardened ledger write path.",
        depends_on=[t12["id"], t14["id"]],
        workflow_families=["backfill"],
        abstraction_classes=["bounded backfill surface"],
        primary_artifact_class="bounded backfill surface",
    )
    tasks.append(t15)

    t16 = make_task(
        title=SLICE_TITLES[17],
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
        depends_on=[t13["id"], t15["id"]],
        workflow_families=["docs"],
        abstraction_classes=["docs"],
        primary_artifact_class="docs",
    )
    tasks.append(t16)

    t17 = make_task(
        title="Gate review workflow-ledger canary",
        summary="Review the completed 1A.1 execution graph only after all bounded slices are done and the proof surfaces are present.",
        acceptance=text(
            "Approve only when all 16 upstream tasks are complete and their bounded outputs remain semantically separate.",
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
    tasks.append(t17)

    validate_bounded_graph(tasks)
    payload = {
        "kind": "decomposition_result",
        "objectiveId": objective["id"],
        "actor": "Bernard",
        "requestReview": True,
        "statusNote": "Decomposed 1A.1 into bounded single-family slices with dedicated gate review.",
        "tasks": sanitize_tasks(tasks),
    }

    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
