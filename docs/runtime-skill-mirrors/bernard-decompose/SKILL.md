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
For a changed shared interface, write `authority-impact-request.json` with its path, exported
symbols, and `changeKind="shared_interface"`, then run `python3
scripts/collect_authority_impact.py --repo "$REPO_ROOT" --request authority-impact-request.json
--output authority-impact.json`.
Confirm only necessary implementation/export/composition/persistence/API/integration roots, record
them in manifest `authorityImpact.confirmedRoots` and `requiredOwnershipPaths`, and give each one
owner. Search candidates are evidence, not automatic tasks. A shared interface requires a confirmed
composition/export owner using that interface as `authorityRoot`; run `software_build` only after
all confirmed owners converge and on the final integration proof.
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

Execution-plan policy is task-type specific:
- execution and proof tasks use `inspect_authority → derive_delta → apply_change → verify`
  with non-empty `expectedChanges`;
- read-only `gate_review` tasks use `inspect_authority → derive_delta → verify`,
  omit `apply_change`, and set `expectedChanges=[]`.

Hard boundaries:
- Objective `artifactPaths` and governed design documents are rationale evidence. Keep them in
  `readOnlyAnchors`; never use them as an implementation task's `authorityRoot` or `proofRoot`.
  Select the nearest pre-existing source owner from `sourceAnchors` or `requiredOwnershipPaths` as
  implementation authority.
- Home-directory and installed runtime paths such as `~/.hermes/**` are rollout evidence, not
  governed task mutation scope. Do not create an execution slice for profile installation unless
  the objective explicitly authorizes a tracked repository mirror and its existing runtime-action
  installation path.
- When `approvedSlices` is present, emit exactly one task per approved slice. Map ownership and
  proof requirements into those slices; do not silently split or merge them.
- One task owns one independently mutable production root.
- Route list and dynamic-detail pages are separate mutation slices when their writable files have
  different parent roots; do not combine them under a broad page-directory mutation root.
- `authorityRoot` must identify pre-existing external truth. It may never sit inside the task's own
  `createdFileGlobs`; integration proof must read authority provided by earlier slices.
- Exact existing files are enumerated. A recursive writable glob is only for genuinely new files.
- `createdFileGlobs` participate in the same mutation-cluster check as `writableFiles`; when exact
  new files are known, enumerate them instead of pairing exact files with a broader directory glob.
- When one-file executable scope equals `mutationRoot`, include that exact path in
  `createdFileGlobs` even when the file may already exist. This authorizes creation without widening
  scope and prevents new-file slices from failing only at workspace preflight.
- Normal implementation tasks do not write proof files and use `proofFiles=[]`.
- Documentation slices are normal implementation tasks for this rule; a writable document cannot
  prove itself.
- Documentation readback is the authored document itself: set `proofRoot=mutationRoot` and keep
  `proofFiles=[]`; never invent a sibling `src/docs` proof path.
- If `touchedSurfaces` explicitly names documentation and a docs expansion zone exists, assign one
  bounded docs task; prior validator failures are not authority to omit the current requirement.
- A task with `proofFiles=[]` must not request `software_test`. Put executable tests and that gate on a
  separate proof-only task, and keep every `focusedTests` path inside its declared `proofFiles`.
- `verification.qualityGates` uses only `software_test`, `software_lint`, and `software_build`.
  Do not invent aliases such as `mission_control_build`; the validator rejects unknown gate names.
- New proof uses exact equal mutation/proof roots and writable/proof files; the builder emits
  `focused_proof`. Other classes are `code` for generic implementation, `integration_proof` for
  final proof, and `review_gate` for final review; never emit legacy values.
- `readOnlyAnchors` never overlap writable or created scope. An exact preserve-only file may be a
  sibling of the primary `authorityRoot` when it is necessary to retain canonical implementation
  semantics; directory and glob expansion outside the primary authority root remain forbidden.
- Schema and migration ownership are separate tasks.
- Shared interface, file adapter, hosted adapter, hybrid adapter, and export surfaces are separate
  owners when the objective requires them.
- A consumed token has one provider and a dependency edge to that provider.
- Consumer completeness is semantic: any page, composition, export, or wrapper that uses a sibling
  output consumes its token and depends on its provider; final integration cannot replace that edge.
- Documentation of newly implemented behavior consumes and depends on the bounded implementation
  or proof owners it describes; authority anchors alone do not represent the new behavior.
- Consume sibling outputs through tokens; never mass-reuse an unrelated generic authority or proof.
- Generic proof tasks do not invent authority JSON. Only real authority extraction produces a named
  evidence artifact.
- One final `integration_proof` depends on every preceding execution slice and consumes every token they provide.
- Only the final `integration_proof` owns `software_build`; it must retain that gate.
- One final read-only `gate_review` depends on all required execution work and declares no writable or created-file scope.
Start from `requiredOwnershipPaths`. Assign each requirement to its one actual writable owner.
Do not hide existing ownership behind a parent `/**` glob.
### Production Delivery Profiles
For `production_component` or `production_release`, give every `requiredProductionEvidence`
category an exact proof owner with
`productionEvidence=[{"category":"...","evidenceToken":"..."}]`, the same token in `provides`, and
an executable existing quality gate. The integration task provides `final_integration_proof`; assign
the final gate to `productionGateReviewer` (normally Dolores); when it is `operator`, use lowercase `operator`, which is review-capable only for the read-only production gate. Never assign that gate to William or Bernard; execution slices stay with a worker/enricher and changing the assignee never bypasses a required root-bounded task split.
During semantic correction, the current objective's `productionGateReviewer` remains authoritative.
Actor identity is case-insensitive, so `Operator` and `operator` are equivalent. Never replace an
operator gate with Dolores because of stale compiler history or a finding that conflicts with the
current objective contract; preserve the required reviewer and resubmit the otherwise corrected,
locally validated manifest.
`production_component` excludes cloud load/network/backup/restore/DR certification. Bernard selects
semantic slices, the validator checks mechanics, and Mission Control remains final authority.

## Canonical Manifest Workflow
Use this workflow for every contract-required graph:
1. Fetch the governed objective with `python3 scripts/fetch_objective.py <objective-id> objective.json`,
   then run `python3 scripts/decomposition_checkpoint.py resume`.
   Reuse the checkpoint manifest when present. Otherwise immediately create the canonical skeleton:
   `python3 scripts/build_contract_decomposition.py --init-manifest objective.json manifest.json`
   The manifest must exist within five non-write tool calls after fetching the objective. Do not read
   builder, validator, checkpoint, or submitter implementation source during normal decomposition;
   their documented CLI and validator report are the complete operational interface. If bootstrap
   fails, block with its error instead of reverse-engineering the tools.
   `sliceSource=bernard_authored` means add stable semantic tasks without `slice:N`; `objective_approved` means keep generated tasks and their `slice:N`.
   If the objective exposes `lastDecompositionCandidate` and lint or semantic-grade errors, preserve
   its candidate digest, correction round, task IDs, and slices in this same manifest and correct only
   reported findings. A semantic correction is never a fresh decomposition: retain every valid task
   identity, add only genuinely missing ownership, and submit the complete corrected candidate.
   The canonical manifest contains compact `contract.plan` instructions only. Never author, copy,
   or preserve `contract.executionPlan`; it is generated output owned exclusively by the builder.
2. Give every slice a stable semantic `key`. Never change a key during correction.
   The checkpoint rejects a correction that replaces every existing key for an unchanged objective;
   edit the canonical manifest in place and preserve the task identities that remain semantically
   valid. The checkpoint helper journals in-progress continuity outside the task workspace and
   restores a missing or altered workspace copy. Never delete or manually rewrite
   `.mc-decomposition-checkpoint.json`.
   For a live graph amendment only, copy each existing child's authoritative ID into
   `persistedTaskId` and copy its accepted live `taskContract` exactly; omit the ID only for a
   genuinely new slice so the builder derives a new stable ID. An incomplete downstream slice may
   add `dependsOn`, `consumes`, and builder-derived `consumedToken:` plan references. Before any
   child is released, it may also remove quality gates or normalize a gate review to the read-only
   plan above. A structured semantic finding may add an exact objective `sourceAnchor` to an
   unreleased task's `readOnlyAnchors`; it may not widen writable or proof scope. Never add or broaden
   a quality gate during amendment. Started, released, reviewed,
   completed, or phase-run-backed task contracts are immutable.
   Also set manifest `operation="amend"` and `decompositionContractPatch` to the smallest
   objective-contract update. The builder merges that patch with `--objective` and emits
   `requestReview=false`, `operation="amend"`, and the complete amended contract.
3. Assign objective requirements with stable IDs:
   - `ownership:<exact required path>`;
   - `proof:<zero-based proofExpected index>`;
   - `slice:<zero-based approvedSlices index>` only for `sliceSource=objective_approved`.
4. Express dependencies by key.
5. Put all task-specific contract truth in each `contract`, including a compact `plan`.
   For Bernard-authored slices, copy `contractGuide.taskTemplate` for every task and replace every
   placeholder before the first build. Do not discover required fields by reading implementation
   source, searching old sessions, or repeatedly invoking the builder with incomplete tasks.
   Apply `contractGuide.specialTaskShapes` exactly: integration proof remains task type `execution`
   with artifact class `integration_proof`; gate review remains task type `review` with
   `reviewMode=gate_review`; documentation uses artifact class `docs`, empty `proofFiles`, and its
   mutation root as non-executable readback.
   Assign every `contractGuide.unassignedRequirements` entry exactly once. Plan `operation` is only
   `add`, `modify`, or `remove`; created paths remain equal to or below their exact mutation root.
6. Expand and checkpoint with `python3 scripts/build_contract_decomposition.py manifest.json
   decomposition.json --objective objective.json`.
7. Validate the whole graph with `python3 scripts/validate_decomposition_json.py
   --contract-required decomposition.json <maxTaskCount> --objective objective.json --manifest
   manifest.json --report decomposition-validator-report.json`.

For a live amendment, also pass `--amend-baseline current-decomposition.json`. Only exact task-scoped
findings already present on persisted children are reported as grandfathered. Graph findings and every
new or changed task finding remain blocking. Validation uses the builder-emitted amended contract, so
new ownership paths cannot pass by being absent from the original objective file. The baseline also
rejects stale completed contracts and non-evidence changes to incomplete contracts before submission.

8. If invalid, read the complete report once, edit the existing `manifest.json` in place, rebuild,
   and revalidate. Every correction must reduce the finding count without introducing a new finding
   fingerprint; `correction_rejected` means use the remaining bounded round or stop. Never patch
   generated JSON and never regenerate the manifest.
   When narrowing a mutation root, atomically align `writableFiles` and `createdFileGlobs` to the same
   exact scope in that correction. On `TERMINAL_DECOMPOSITION_FAILURE`, call `kanban_block` with the
   final report immediately and make no further tool calls.
9. Complete within one initial draft plus at most two correction rounds. If still invalid, block with
   the final report.
10. Before retrying after timeout, run `python3 scripts/decomposition_checkpoint.py resume`.
Resume the recorded manifest and correction round. The helper restores the workspace checkpoint from
its in-progress journal when possible. If both copies are missing or invalid, continuity is blocked;
do not reconstruct from memory.
Correction rounds are consumed only by completed validator results. A timeout after building a
corrected manifest must resume and validate that same digest; rebuilding the unchanged digest does
not consume another correction round.
11. After validation succeeds, record the bounded-run metrics with
    `python3 scripts/decomposition_checkpoint.py metrics`. Do not edit `manifest.json` or
    `decomposition.json`. As the final tool call, run
    `python3 scripts/complete_decomposition.py`. It verifies both artifact digests,
    submits the exact graph once, reconciles an ambiguous timeout against the live objective, marks
    the checkpoint accepted, and terminally completes the card. Make no further tool calls, workspace
    reads, or native `kanban_complete` calls; immediately end the session.
12. Do not replace this helper with ad hoc shell data plumbing. The legacy submit and checkpoint
    commands remain available for compatibility, but normal live decomposition uses the atomic finalizer.
13. On any rejection, report the exact finding rather than improvising a
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
- every assembly and implementation-derived documentation task has direct consumer edges;
- final integration proof consumes all required outputs;
- gate review is last and read-only;
- every required production evidence category has a token-bearing proof owner;
- the production gate is assigned to the objective's independent reviewer;
- task count is within the live cap.

## Task Repair
For a marked `task_repair_result` card:
1. Preserve source task ID and attempt number.
2. Repair only the defect; one exact writable file requires that exact `mutationRoot`.
4. Include a complete ordered `executionPlan`.
5. Write the exact result to `task-repair-result.json`.
6. Run `python3 scripts/validate_decomposition_json.py --repair task-repair-result.json`.
7. Return the exact validated JSON. Mission Control performs full-graph validation.

Do not call Mission Control mutation endpoints during task repair. In particular, do not PATCH the
source task, repair task, contract, blocker, status, attempt, or dispatch fields, and do not search for
an endpoint that applies the repair. Hermes submits the returned `task_repair_result` through the
governed evidence route after completion.

Never complete a marked repair card with prose, null output, or an unvalidated contract.

## Submission Safety
- Write only in the task workspace; fail closed when required Mission Control URLs or credentials are missing.
- Never submit twice after a timeout, and never create, approve, activate, or release execution tasks directly.
- If local validation cannot pass, block with the exact validator output.

## On-Demand Reference
Load only a named section of `references/decomposition-policy-archive.md` when this contract cannot resolve a validator finding.
