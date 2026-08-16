---
name: grade-mission-control-decomposition
description: Grade a persisted Mission Control decomposition for semantic execution safety after the mechanical validator passes. Use for objective-review inbox work, pre-approval audits, decomposition correction feedback, or whenever an operator asks whether a graph is A-grade and safe for William.
---

# Grade Mission Control Decomposition

## Purpose

Decide whether a staged or accepted decomposition is safe to approve. Bernard owns task design, the existing
validator owns mechanical correctness, Mission Control owns persistence, and this skill owns the
operator's semantic A-grade decision.

Never approve, activate, reset, or release execution while grading.

## Inputs

Read live, current records:

1. `GET /api/objectives/<id>`
2. `GET /api/tasks`, filtered to the objective's exact `childTaskIds`
3. `GET /api/hermes/health`
4. `GET /api/inbox`

Do not grade recovery, review-quality, release, or machine rows as decomposition children.

When `lastDecompositionCandidate.gradingState` is pending or grading, grade its exact `tasks` and
`candidateDigest`; do not require persisted child rows. Emit `decomposition_grade_result` version
`decomposition-grade.v1` with objective/task identity, candidate digest, correction round, grade,
verdict, authority evidence, and structured findings.

For a Mission Control grading card, complete Hermes with the exact report JSON as the
`kanban_complete(result=...)` value. A prose summary is not the result contract and must never be
submitted in its place. The shared completion guard rejects an invalid result in the same session.

For a repeatable audit, save the objective JSON and filtered child array, then run:

```bash
python3 scripts/grade_decomposition.py \
  --objective objective.json \
  --tasks child-tasks.json \
  --report decomposition-grade.json
```

The script complements, and never replaces, Bernard's validator or Mission Control's compiler.

The deterministic report is authoritative for mechanical and policy facts it evaluates. Grade only
the current objective and exact candidate digest. Do not use prior sessions, historical compiler
rejections, or stale inbox text to add a finding contradicted by the current report. Actor identity
is canonical and case-insensitive: `Operator` and `operator` are the same reviewer. A production
gate must match the objective's current `productionGateReviewer`; never replace an operator gate
with Dolores merely because an older attempt rejected differently cased text.

For a staged candidate, pass `--candidate candidate.json` instead of `--tasks child-tasks.json`.

## A-Grade Contract

Require all of the following:

- Every exact objective child has `taskContract.v1`.
- Every execution child has one mutation root, authority root, proof root, acceptance hinge, and
  ordered execution plan.
- Writable and created paths stay inside one mutation root.
- Proof-only work writes exactly its declared proof files.
- Bounded proof-only work uses `primaryArtifactClass=focused_proof`; persisted legacy `proof`
  remains readable but must be amended before execution.
- Normal implementation work does not write proof files.
- Read-only anchors do not overlap writable scope.
- Each consumed token has exactly one provider and an explicit dependency on that provider.
- For software delivery, exactly one final `integration_proof` depends on every preceding execution
  slice, consumes all preceding output tokens, and exclusively owns `software_build`.
- For `artifact_delivery`, accept content artifact classes, require declared output artifacts and
  evidence tokens on every execution slice, and forbid software integration/build proof.
- For `artifact_delivery`, the final operator gate depends on every execution slice and the named
  `maeve_quality_review` slice is assigned to Maeve.
- Exactly one final read-only gate review follows all execution work. Software review consumes the
  integration proof; artifact review consumes the bounded content-quality evidence.
- A gate review has no writable scope, no `apply_change` plan step, and no expected mutation.
- Persistence, API, schema, migration, export, and composition ownership is truthful when present.
- Trace trigger -> routing -> executor -> persistence -> proof. Every required invocation file has
  an exact task owner; otherwise report `invocation_chain_incomplete` with source evidence.
- Treat invocation-layer paths in the objective's `sourceAnchors` as semantic coverage requirements;
  `requiredOwnershipPaths` remains the mechanical writable-owner contract.
- No sibling authority spill, generic proof reuse, self-authored parity truth, or duplicate writable
  ownership exists.
- The objective is `reviewReady=true`, `approved=false`, and no William task has been released; or
  it is a blocked pre-approval correction graph with `needsDecomposition=false` whose canonical
  children are all unreleased `pending/ready` work. Do not force that correction graph through a
  destructive draft reset merely to set `reviewReady`.
- There is one objective-review inbox item and no duplicate trigger, recovery, or execution residue.

## Grade Decision

- **A**: zero blocking findings. Verdict: `A-grade and ready for approval`.
- **B**: mechanically valid but one or more semantic execution-safety findings. Verdict:
  `return to Bernard for bounded correction`.
- **C/D/F**: missing contracts, broken graph/evidence ownership, unsafe release, or widespread
  ambiguity. Verdict: `stop before William`.

Warnings never override a blocking finding.

## Correction Feedback

When below A, return structured findings:

```json
{
  "code": "quality_gate_build_ownership_invalid",
  "taskId": "<task-id>",
  "field": "taskContract.verification.qualityGates",
  "current": ["software_test", "software_build"],
  "required": "Keep software_build only on the final integration proof."
}
```

Each finding must include a stable code, task ID when applicable, exact field, current defect, and
required correction. Preserve task IDs and require Bernard to edit the canonical manifest in place.
Do not request full regeneration unless the objective contract changed.

Use these stable semantic codes:

- `quality_gate_build_ownership_invalid`
- `read_only_review_plan_invalid`
- `evidence_provider_missing`
- `evidence_dependency_missing`
- `integration_proof_incomplete`
- `gate_review_incomplete`
- `writable_ownership_overlap`
- `scope_root_invalid`
- `proof_scope_invalid`
- `execution_plan_incomplete`
- `execution_released_before_approval`
- `objective_review_state_invalid`
- `invocation_chain_incomplete`
- `artifact_delivery_software_proof_invalid`
- `artifact_evidence_incomplete`
- `artifact_quality_owner_invalid`

## Report

Report:

- grade and explicit verdict;
- findings ordered by severity;
- task count and task-type split;
- first validator findings and correction rounds when available;
- every A-grade bar as pass/fail;
- objective, inbox, Hermes health, and release state;
- whether Bernard should correct the existing manifest or the operator should stop.
