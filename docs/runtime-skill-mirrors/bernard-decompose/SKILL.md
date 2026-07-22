---
name: bernard-decompose
version: 3.0.0
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

## Sources Of Truth

1. Read the live Mission Control objective or repair card.
2. Follow its `decompositionContract`, approved slices, allowed paths, required ownership paths,
   maximum task count, and completion marker literally.
3. Use this skill for shaping.
4. Use the existing Python validator for local mechanical feedback.
5. Treat Mission Control's compiler/linter response as final authority.

Do not read validator source to infer policy. Do not use prior graphs, memory, or nearby files as
authority when the live objective provides a contract.

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
- A task with `proofFiles=[]` must not request `software_test`. Put executable tests and that gate on a
  separate proof-only task, and keep every `focusedTests` path inside its declared `proofFiles`.
- New or changed proof belongs to a proof-only task whose mutation and proof root are the exact proof
  file.
- `readOnlyAnchors` never overlap writable or created scope.
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

## Manifest-First Workflow

For every non-1A.1 contract-required graph with eight or more tasks:

1. Write `manifest.json` with `kind="contract-decomposition-manifest.v1"`.
2. Give every slice a short unique `key`.
3. Express dependencies by key.
4. Put all task-specific contract truth in each `contract` object, including a compact `plan`.
5. Expand once:

```bash
python3 scripts/build_contract_decomposition.py manifest.json decomposition.json
```

6. Validate:

```bash
python3 scripts/validate_decomposition_json.py --contract-required decomposition.json <maxTaskCount>
```

7. If invalid, edit `manifest.json`, rebuild, and revalidate. Never patch generated JSON.
8. Submit the exact validated `decomposition.json` once to the live `/decompose` URL with
   `Authorization: Bearer $CRON_SERVICE_TOKEN`.
9. Read the response. Stop on any rejection; report the exact finding rather than improvising a
   legacy or smaller graph.

The expander creates deterministic UUIDs and repetitive plan structure only. It is not a second
compiler or validator.

For a smaller contract-required graph, the same manifest path is preferred.

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

## 1A.1 Deterministic Exception

For objective `4009e581-7231-4930-9a0d-b2b56b281d9e` only:

```bash
python3 scripts/build_1a1_decomposition.py objective.json decomposition.json
python3 scripts/validate_decomposition_json.py decomposition.json 35
```

Submit the exact output. Do not freehand or adapt this helper for any other objective.

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
- Fail closed if `MC_API_URL), the decompose URL, or `CRON_SERVICE_TOKEN` is missing.
- Never submit twice after a timeout without reading objective state.
- Never create, approve, activate, or release execution tasks directly.
- If local validation cannot pass, block with the exact validator output.

## On-Demand Reference

The archived historical guidance is in
`references/decomposition-policy-archive.md`. Do not load it during normal decomposition. Consult
only a specifically named section when a validator finding cannot be resolved from this concise
contract.
