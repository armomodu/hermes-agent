---
name: bernard-decompose
version: 4.0.0
author: Dolores
description: |
  Produce bounded Mission Control decomposition and task-repair contracts.
  Mission Control remains the authoritative compiler and full-graph linter.
trigger_conditions:
  - "Objective requires bounded decomposition"
  - "Bernard is assigned a decompose or task-repair card"
---

# Bernard Decomposition

## Outcome

Return one locally validated structured result:

- `decomposition_result` for an objective decomposition; or
- `task_repair_result` for a task-level contract repair.

Do not execute implementation work, approve the objective, activate it, or release William.

## Authority-First Method

1. Read the live Mission Control objective or repair card.
2. Inventory objective requirements, required ownership paths, and live authority roots.
3. Assign each requirement exactly once before designing task prose.
4. Slice by one mutation root, one authority root, one proof root, and one acceptance hinge.
5. Add explicit evidence providers, consumers, and dependency edges.
6. Put the final integration proof and gate review last.
7. Use the existing Python validator for mechanical feedback.
8. Treat Mission Control's compiler/linter response as final authority.

Do not encode objective-specific policy in this skill. Do not use prior graphs, memory, or nearby
files as authority when the live objective provides a contract.

### Authority Impact

Before shaping tasks for a changed shared interface:

1. Write `authority-impact-request.json` with the changed authority path, exported symbols, and
   `changeKind="shared_interface"`.
2. Collect source-reference candidates:

```bash
python3 scripts/collect_authority_impact.py \
  --repo "$REPO_ROOT" \
  --request authority-impact-request.json \
  --output authority-impact.json
```

3. Inspect the candidates and confirm only semantically required implementation, export,
   composition, persistence, API, and integration-proof roots.
4. Copy the collector result into manifest `authorityImpact`, add exact `confirmedRoots` with one
   supported role each, and add every confirmed path to `requiredOwnershipPaths`.
5. Assign each confirmed path to exactly one task. Search candidates are evidence, not automatic
   tasks.

For a shared interface, at least one confirmed composition or export root is mandatory. Never infer
impact from prose alone or omit a confirmed root because another task owns the interface definition.
Each composition or export owner must use the changed interface path as its primary `authorityRoot`.
When that owner changes executable source, require `software_build` so type-level composition is proved
before review.

## Contract-Required Decomposition

When `decompositionContract.taskContractRequired=true`, every child uses
`task-contract.v1`. Legacy-only tasks are forbidden.

Each execution task declares:

- one exact or creation-bounded `mutationRoot`;
- one narrow `authorityRoot`;
- one exact `proofRoot`;
- one `acceptanceHinge`;
- bounded `writableFiles`, `createdFileGlobs`, `proofFiles`, and `readOnlyAnchors`;
- explicit `provides`, `consumes`, and `dependsOn` where evidence crosses slices;
- an ordered `executionPlan`: inspect authority, derive delta, apply change, verify;
- expected symbols/invariants and executable completion checks.

Hard boundaries:

- One task owns one independently mutable production root.
- Exact existing files are enumerated. A recursive writable glob is only for genuinely new files.
- Normal implementation tasks do not write proof files and use `proofFiles=[]`.
- Documentation slices are normal implementation tasks for this rule; a writable document cannot
  prove itself.
- A task with `proofFiles=[]` must not request `software_test`. Put executable tests and that gate on a
  separate proof-only task, and keep every `focusedTests` path inside its declared `proofFiles`.
- `verification.qualityGates` uses only `software_test`, `software_lint`, and `software_build`.
  Do not invent aliases such as `mission_control_build`; the validator rejects unknown gate names.
- New or changed proof belongs to a proof-only task whose mutation and proof root are the exact proof
  file.
- `readOnlyAnchors` never overlap writable or created scope. An exact preserve-only file may be a
  sibling of the primary `authorityRoot` when it is necessary to retain canonical implementation
  semantics; directory and glob expansion outside the primary authority root remain forbidden.
- Schema and migration ownership are separate tasks.
- Shared interface, file adapter, hosted adapter, hybrid adapter, and export surfaces are separate
  owners when the objective requires them.
- A consumed token has one provider and a dependency edge to that provider.
- Generic proof tasks do not invent authority JSON. Only real authority extraction produces a named
  evidence artifact.
- One final `integration_proof` execution task depends on every preceding execution slice.
- One final read-only `gate_review` depends on the integration proof and all required execution work.

Start from `requiredOwnershipPaths`. Every listed path must have exactly one explicit writable owner.
Do not hide existing ownership behind a parent `/**` glob.

## Canonical Manifest Workflow

Use this workflow for every contract-required graph:

1. Write `manifest.json` with `kind="contract-decomposition-manifest.v1"`.
2. Give every slice a stable semantic `key`. Never change a key during correction.
   For a live graph amendment only, copy each existing child's authoritative ID into
   `persistedTaskId` and copy its accepted live `taskContract` exactly; omit the ID only for a
   genuinely new slice so the builder derives a new stable ID. An incomplete downstream slice may
   add only `dependsOn`, `consumes`, and builder-derived `consumedToken:` plan references.
   Also set manifest `operation="amend"` and `decompositionContractPatch` to the smallest
   objective-contract update. The builder merges that patch with `--objective` and emits
   `requestReview=false`, `operation="amend"`, and the complete amended contract.
3. Assign objective requirements with stable IDs:
   - `ownership:<exact required path>`;
   - `proof:<zero-based proofExpected index>`;
   - `slice:<zero-based approvedSlices index>`.
4. Express dependencies by key.
5. Put all task-specific contract truth in each `contract`, including a compact `plan`.
6. Expand and checkpoint:

```bash
python3 scripts/build_contract_decomposition.py \
  manifest.json decomposition.json --objective objective.json
```

7. Validate the whole graph and write one batch report:

```bash
python3 scripts/validate_decomposition_json.py \
  --contract-required decomposition.json <maxTaskCount> \
  --objective objective.json \
  --manifest manifest.json \
  --report decomposition-validator-report.json
```

For a live amendment, also pass `--amend-baseline current-decomposition.json`. Only exact task-scoped
findings already present on persisted children are reported as grandfathered. Graph findings and every
new or changed task finding remain blocking. Validation uses the builder-emitted amended contract, so
new ownership paths cannot pass by being absent from the original objective file. The baseline also
rejects stale completed contracts and non-evidence changes to incomplete contracts before submission.

8. If invalid, read the complete report once, edit the existing `manifest.json` in place, rebuild,
   and revalidate. Every correction must reduce the finding count without introducing a new finding
   fingerprint; `correction_rejected` means use the remaining bounded round or stop. Never patch
   generated JSON and never regenerate the manifest.
9. Complete within one initial draft plus at most two correction rounds. If still invalid, block with
   the final report.
10. Before retrying after timeout, run:

```bash
python3 scripts/decomposition_checkpoint.py resume
```

Resume the recorded manifest and correction round. A missing checkpoint is a continuity blocker; do
not reconstruct from memory.
11. Submit the exact validated `decomposition.json` once through the bounded helper. It reads
   `MC_API_URL` and `CRON_SERVICE_TOKEN` from the environment, performs one authenticated JSON POST,
   identifies itself as the Hermes Mission Control service at the public edge, and avoids shell
   pipes or `curl --data-binary` patterns that trigger terminal approval:

```bash
python3 scripts/submit_decomposition.py \
  decomposition.json \
  --response decomposition-response.json
```

Do not replace this helper with ad hoc shell data plumbing. On an ambiguous timeout, read the live
objective before deciding whether submission may be retried.
12. On HTTP success, mark the checkpoint accepted:

```bash
python3 scripts/decomposition_checkpoint.py mark accepted
```

This archives the canonical manifest, compiled decomposition, validator report, checkpoint, and
metrics outside the disposable task workspace.

13. Report convergence metrics:

```bash
python3 scripts/decomposition_checkpoint.py metrics
```

14. Read the response. Stop on any rejection; report the exact finding rather than improvising a
   legacy or smaller graph.

The expander creates deterministic UUIDs and plan structure only. The batch validator remains the
single Bernard-side mechanical authority.

## Slice Matrix Checklist

Before expansion, verify:

- every approved slice is represented;
- every required ownership path has one owner;
- every required documentation path has one exact `primaryArtifactClass=docs` owner without
  `software_test` unless that task also owns executable proof;
- storage persistence includes every named adapter and export surface;
- schema and migration are separate;
- proof tasks own only their exact proof file;
- authority roots are live, narrow, and not writable local truth;
- evidence providers precede consumers;
- final integration proof consumes all required outputs;
- gate review is last and read-only;
- task count is within the live cap.

## Task Repair

For a marked `task_repair_result` card:

1. Preserve source task ID and attempt number.
2. Repair only the contract defect and required read-only/created paths.
3. Include a complete ordered `executionPlan`.
4. Write the exact result to `task-repair-result.json`.
5. Run:

```bash
python3 scripts/validate_decomposition_json.py --repair task-repair-result.json
```

6. Return the exact validated JSON. Mission Control performs full-graph validation.

Never complete a marked repair card with prose, null output, or an unvalidated contract.

## Submission Safety

- Write files only in the task workspace.
- Fail closed if `MC_API_URL`, the decompose URL, or `CRON_SERVICE_TOKEN` is missing.
- Never submit twice after a timeout without reading objective state.
- Never create, approve, activate, or release execution tasks directly.
- If local validation cannot pass, block with the exact validator output.

## On-Demand Reference

The archived historical guidance is in
`references/decomposition-policy-archive.md`. Do not load it during normal decomposition. Consult
only a specifically named section when a validator finding cannot be resolved from this concise
contract.
