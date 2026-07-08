---
name: bernard-decompose
version: 2.0.0
author: Dolores
description: |
  Decompose a software/system objective into bounded child tasks that are
  directly usable by the current Mission Control workflow.
  Owner: Bernard, Department Head (Product & Systems).
trigger_conditions:
  - "Objective requires bounded decomposition for execution"
  - "Objective owner == 'Bernard' or Bernard is explicitly asked to decompose"
  - "Objective status == 'draft'"
---

# Bernard Decomposition Skill

## Mandatory fast path for 1A.1 canary

If the live objective id is `4009e581-7231-4930-9a0d-b2b56b281d9e`:

- do not freehand the decomposition
- do not compress or reinterpret the approved slice list
- do not emit a "close enough" variant
- do not merge the exact-parity slice with the task/objective taxonomy slice
- immediately use:
  1. `python3 scripts/build_1a1_decomposition.py objective.json decomposition.json`
  2. `python3 scripts/validate_decomposition_json.py decomposition.json 21`
  3. submit the validated payload once

For this objective, the helper script output is the authoritative decomposition shape unless the live
objective payload itself changes first.

If the helper path for this objective fails at any point:

- do not fall back to freehand decomposition
- do not patch in a smaller "close enough" graph
- do not reuse prior approved partial work to justify dropping a named slice
- classify the run as a decomposition/tooling defect
- block with the exact helper failure and stop

For `4009e581-7231-4930-9a0d-b2b56b281d9e`, an invalid helper run is safer than an improvised graph.

## Source of truth

Read these first when lifecycle or loop semantics matter:

1. `~/Documents/New project/apps/mission-control/docs/product-contract.md`
2. `~/Documents/New project/apps/mission-control/docs/README.md`

If decomposition guidance depends on release-sensitive baseline truth, require a fresh operator preflight instead of relying on memory or prior notes.

## Purpose

Break one objective into **3-7 bounded child tasks** that can be executed with minimal clarification turns and clean review scope.

Default target is 3-7 tasks, but a narrowly approved objective-specific exception may exceed 7 when preserving semantically bounded William tasks matters more than obeying the default cap.

Each task must represent **one bounded cognitive output**, not a string of micro-steps.

Optimize for:

- correctness first
- low-latency completion second
- minimal tool usage
- immediate termination once valid JSON is ready

## Current Workflow Contract

- Hermes Kanban is the execution inbox for agent work.
- Mission Control is the system of record.
- William executes implementation tasks.
- Bernard reviews implementation tasks.
- Deterministic release work belongs to machine jobs, not to William.
- Governed-workspace quality gates (`software_test`, `software_lint`, `software_build`) are local machine jobs that run after William execution and before Bernard approval.
- Normal quality-gate failures route back into William remediation, not operator inbox work.
- Mission Control now resolves each decompose trigger into one enforced runtime mode:
  - `payload_only`
  - `ambiguity_allowed`

Do not decompose agent tasks that ask William to:

- commit
- push
- open PRs
- merge PRs
- deploy

Those stay in the harness.

## Hard Constraints

1. Max 7 child tasks per objective unless an objective-specific exception is explicitly stated in the objective payload. Current approved exception: objective `4009e581-7231-4930-9a0d-b2b56b281d9e` may use **21** child tasks one time to keep exact-parity proof, separated contract families, schema foundation, repository boundary, storage exports, canonical writer, identity/correlation mapping, separated emitter families, readback query work, readback API/proof work, durable duplicate prevention, bounded backfill, docs, and gate review semantically bounded instead of rebundling known-risk surfaces.
   - count **all** emitted child tasks against this cap:
     - execution tasks
     - documentation tasks
     - gate review tasks
   - do not interpret the exception as "11 execution tasks plus review" unless the objective payload says so explicitly
   - if the cap is exceeded, merge or split differently before submission; do not emit an over-cap payload and then try to justify it afterward
   - a cap is a budget guard, not permission to rebundle semantic-risk work just to make the count fit
   - if the smallest coherent graph that satisfies the other hard rules exceeds the current cap, stop and return a decomposition repair result that names the cap conflict and the exact split surfaces driving it
   - do not satisfy the cap by dropping required docs/proof tasks, reusing prior-attempt approval as completion credit, or rebundling separate workflow families, readback, storage, or duplicate-prevention semantics
   - for objective `4009e581-7231-4930-9a0d-b2b56b281d9e`, decompose from the live objective payload only; do not inspect repo state, existing knowledge-plane files, prior approved reviews, or partial implementation artifacts to decide what work still remains
2. Every task must be completable by one agent in a focused pass, usually <=4 hours.
3. Every task must have:
   - `title`
   - `summary`
   - `assignee`
   - `priority`
   - `acceptanceCriteria`
   - `constraints`
   - `relatedFiles`
   - `nextAction`

Historical-task reuse rule:

- if the objective has been reset back to draft/decomposition with `childTaskIds=[]`, prior tasks, prior
  reviews, and prior approvals are evidence only, not reusable completion credit
- do not drop a required task from the new decomposition just because an older attempt once produced an
  approved review for a similar title
- only omit or collapse a task based on prior work when the live objective payload or direct operator
  instruction explicitly says that prior completed work should carry forward into the new decomposition

Objective-exception slice fidelity rule:

- if the live objective payload explicitly names the approved bounded slices for an exception graph,
  treat those named slices as part of the decomposition contract, not as optional examples
- do not silently merge, substitute, or reinterpret a named slice just to make the count fit; for
  example, do not replace a named `exact-parity proof` slice with a contract-definition task plus
  light tests, and do not collapse two separately named readback slices unless the objective or the
  operator is updated first
- if the named slice list and the current hard rules still conflict, stop and return a decomposition
  repair result that identifies the exact slice conflict instead of emitting a "close enough" graph

Objective-exception execution-order rule:

- when the objective payload provides an explicit approved slice list in order, start by mapping
  one task per named slice in that same order
- do not spend extra decomposition turns re-deriving whether a named slice "really belongs inside"
  a neighboring slice unless that mapping would violate a hard split rule or create an impossible
  scope/proof envelope
- do not inspect the repo or partial implementation state to decide that a named slice is already
  satisfied, unnecessary, or safe to collapse; that carry-forward decision belongs in the objective
  payload or direct operator instruction, not Bernard's decomposition turn
- if a neighboring pair still conflicts after the direct 1:1 mapping, identify the exact conflict
  and fix only that edge; do not reopen the whole exception graph conceptually
- for `4009e581-7231-4930-9a0d-b2b56b281d9e`, the approved 21-slice list is an execution-order
  contract, not a brainstorming prompt
- for `4009e581-7231-4930-9a0d-b2b56b281d9e`, once the objective payload is successfully read and no
  hard split-rule conflict is found, emit the task graph directly. Do not spend extra decomposition
  turns "thinking through" whether the named slices are still the right plan.
- for `4009e581-7231-4930-9a0d-b2b56b281d9e`, do not open a todo plan or freehand the payload once
  the objective is read. Use the deterministic helper path, validate once, and submit once.
- for `4009e581-7231-4930-9a0d-b2b56b281d9e`, the expected ordered slices are:
  1. exact-parity proof for task/objective workflow contract behavior
  2. task/objective workflow contract taxonomy
  3. release contract taxonomy
  4. activation contract taxonomy
  5. escalation contract taxonomy
  6. LedgerEvent Prisma schema foundation
  7. repository boundary
  8. storage exports
  9. canonical ledger writer
  10. stable identity/correlation mapping
  11. task/objective emitter wiring
  12. release-start emitter wiring
  13. merge/deploy/verify emitter wiring
  14. activation emitter wiring
  15. escalation emitter wiring
  16. deterministic readback query work
  17. readback API and proof
  18. durable duplicate prevention hardening
  19. bounded backfill
  20. docs
  21. gate review
- if one of those slices still cannot be emitted cleanly, stop and return the exact blocking slice
  conflict. Do not replace the list with a smaller "close enough" graph.
- for `4009e581-7231-4930-9a0d-b2b56b281d9e`, once the payload is read and the 21-slice list is
  confirmed, do not open a todo plan, do not perform extra repo discovery, and do not spend extra
  turns re-deriving the graph. Build the 21-task payload directly, validate it once, and submit it.
4. Every code/product-system task should assign to `William` or `Codex`.
5. Every documentation/research-only task should assign to `Librarian` if appropriate.
6. Priority should inherit from the objective unless there is a clear reason to lower urgency.
7. The first task must have a concrete `nextAction` that lets the assignee start immediately.
8. Every task must be compatible with the Mission Control objective decompose API.
9. Avoid decompositions where multiple `William` tasks substantially share the same primary files unless the overlap is truly unavoidable.
10. Assignee and `taskType` must be compatible:
   - `William`, `Codex`, and `Librarian` tasks should normally use `taskType: "execution"`
   - use `taskType: "review"` only when the assignee is the actual reviewer, usually `Bernard`
11. Every decomposed objective must include at least one dedicated standalone review task with `taskType: "review"` and `reviewMode: "gate_review"`.
12. The dedicated `gate_review` task should usually be the final parent review gate, assigned to the actual reviewer, usually `Bernard`, and should depend on the relevant execution tasks.
13. Do not use a legacy `phase_review` task as the objective-level gate review.
14. Do not continue exploring or self-auditing once a valid decomposition result can be emitted.
15. Do not hardcode internal implementation guesses such as table names, queue names, mapping-store names, or status keys unless they are explicitly named in the objective payload or confirmed by the minimal ambiguity-resolution inspection budget.
16. Do not make a normal execution task depend on a live hosted environment, production URL, or remote deployment unless the objective explicitly requires hosted proof or live-environment validation.
17. Do not model review-quality machine gates as separate decomposition tasks unless the objective explicitly requests a machine-only workflow design review; they are part of the execution-to-review contract.

## Runtime Discipline

Default to decomposing from the objective payload and already-known workflow contract.

Decomposition is a planning task, not an implementation task.
Bernard does not need to inspect code just to make the tasks feel more accurate.
William will inspect the code during execution.

### Runtime mode is authoritative

The Kanban card's `Decomposition Mode` is the source of truth for whether file discovery is allowed.

- `payload_only`
  - The objective payload is sufficient enough to require decomposition from the card alone.
  - Repo inspection is not allowed.
  - Do not inspect the repo to decide which approved slices "still remain" based on current partial
    code state, prior approved reviews, or leftover implementation artifacts. In payload-only mode,
    the live objective payload remains the decomposition contract unless the operator explicitly says
    prior completed work should carry forward.
  - Session archaeology is not allowed. Do not use `session_search`, prior rollout memory, chat
    history mining, or review-log lookup to decide what tasks should exist, what prior work can be
    reused, or what slices are still necessary.
  - In payload-only mode, the only valid inputs are:
    - the live objective payload
    - the runtime mode on the Kanban card
    - the hard workflow rules in this skill
  - If the payload is too vague to decompose safely, block the task and instruct the operator to reroute with `decompositionPolicy="ambiguity_allowed"`.
- `ambiguity_allowed`
  - Limited file discovery is allowed only to resolve genuine ambiguity.
  - This does not permit broad repo exploration, design review, shell exploration, or web research.

Do not decide unilaterally that a `payload_only` task should become an ambiguity task.
That reroute belongs to Mission Control via `decompositionPolicy`.

If the Kanban card does not expose an explicit decomposition mode but the live objective payload is
payload-complete and names an approved bounded slice list, treat that objective as payload-only for
this decomposition turn. Do not fall back to repo inspection just because the card omitted the mode
field.

### Objective Read and UUID Generation Discipline

Do not waste decomposition turns on brittle shell formatting or ad hoc terminal parsing when the
objective payload is already available.

Hard rules:

- fetch the objective once using the safest available path, then work from that local payload; do
  not bounce between repeated curl fetches, shell pretty-printers, and ad hoc re-reads of the same
  objective unless the local payload is provably missing or corrupt
- preferred read sequence for Mission Control objective decomposition:
  1. fetch the objective JSON to a local file once
  2. inspect that file with `read_file` or the bundled script `scripts/read_mission_control_objective.py`
  3. build the decomposition payload from that local source
  4. validate the payload locally with `scripts/validate_decomposition_json.py`
  5. submit only the final payload once it is validated
- after the local objective file exists, do not run terminal commands whose only purpose is to
  pretty-print the same JSON again
- if the objective has already been fetched into a local file such as `objective.json`, inspect it
  with `read_file` or a small deterministic script file, not `cat ... | python3 -c ...` or other
  inline shell pretty-printers
- do not use multiline shell heredocs collapsed into one terminal line for UUID generation,
  JSON printing, or payload assembly
- do not rely on shell one-liners that mix quoting, pipes, and embedded Python when a small script
  file or direct `read_file` call would be more reliable
- when UUIDs are needed, use one deterministic command shape only:
  - `python3 -c 'import uuid; [print(str(uuid.uuid4())) for _ in range(N)]'`
  - or generate them inside the structured Python builder that emits `decomposition.json`
- when parsing API responses or local JSON, prefer:
  - `read_file` for inspection, or
  - the bundled `scripts/read_mission_control_objective.py`, or
  - a dedicated short script file checked into the temporary workspace for deterministic parsing
- keep terminal commands single-purpose; do not chain `curl ... + 1 command`, combined echo/debug
  probes, or multi-action shell lines when one deterministic step at a time is available
- do not probe Mission Control write endpoints with fake, partial, or test decomposition payloads
  just to see whether the route is alive; the live `/decompose` POST is the final submit step, not
  a scratchpad
- if endpoint liveness or auth is genuinely uncertain, verify it with the safest non-mutating check
  available, or inspect the route contract locally; do not send `tasks: []`, placeholder
  `statusNote`, or other synthetic writes into the live objective flow

Known bad patterns:

- `curl ... | python3 -m json.tool`
- `curl ... | python3 -c "import sys,json; ..."`
- `cat objective.json | python3 -c "..."`
- `python3 - <<'PY' ...` collapsed into a single terminal line
- repeated shell retries just to pretty-print JSON already available on disk
- fetching `objective.json`, then dumping the whole file again through `python3 -c` instead of
  reading it directly
- combined terminal lines whose only effect is extra debug text rather than decomposition progress
- POSTing a fake or empty `decomposition_result` body to the live `/decompose` route as a test

Preferred Mission Control helper scripts:

- `scripts/read_mission_control_objective.py objective.json`
  - prints the stable fields and full description from a fetched objective JSON
  - use this instead of inventing a new `parse_objective.py` every run
- `scripts/validate_decomposition_json.py decomposition.json <max_task_count>`
  - validates the final `decomposition_result` payload before the live POST
  - checks required fields, UUIDs, dependency references, gate-review count, gate-review coverage,
    and escaped globs
  - for objective `4009e581-7231-4930-9a0d-b2b56b281d9e`, use max task count `19`
- `scripts/build_1a1_decomposition.py objective.json decomposition.json`
  - deterministic builder for objective `4009e581-7231-4930-9a0d-b2b56b281d9e`
  - emits the approved 19-task graph directly from the live objective payload
  - when the objective id matches `4009e581-7231-4930-9a0d-b2b56b281d9e`, use this builder instead
    of freehand payload construction
  - preferred path for this canary:
    1. fetch objective payload to `objective.json`
    2. run `python3 scripts/build_1a1_decomposition.py objective.json decomposition.json`
    3. run `python3 scripts/validate_decomposition_json.py decomposition.json 19`
    4. submit the validated payload once

Reason:

- these patterns trigger `pending_approval`, quoting errors, or hung shell commands
- they waste Bernard turns without improving decomposition quality
- decomposition should spend turns on graph quality, not shell repair

### When file discovery is allowed

Only in `ambiguity_allowed` mode may you inspect the repo, and only if the objective is ambiguous about one of these:

- subsystem boundaries
- likely owner files
- verification surface
- task ownership

If limited inspection is necessary:

- keep the budget to at most 4 tool actions total
- prefer the highest-signal files first
- stop as soon as the ambiguity is resolved
- do not read broad directories or unrelated docs
- do not use `execute_code` for decomposition discovery or payload shaping
- do not dump full objective JSON, full task lists, or whole API bodies when a narrow field read is sufficient
- prefer narrow `terminal` reads with `curl | jq` field selection or `rg` over ad hoc scripts

If the objective already names the relevant workflow area, do not broaden inspection just to be thorough.

If the objective already contains:

- purpose
- scope
- required deliverables
- out of scope
- success evidence

then assume that is enough to decompose unless a specific ambiguity blocks task boundaries.

If that condition is met, broad repo inspection is not optional refinement.
It is a decomposition error.

Do not inspect implementation files merely to:

- "shape tasks accurately"
- confirm obvious machine-job names already stated in the objective
- hunt for every possible related file
- turn planning into design review
- dump whole objective/task API records when only lifecycle flags, current child tasks, or task-field subsets are needed

Bounded inspection exception:

- Bernard may inspect the minimum live implementation files needed to prove the execution envelope
  when objective text alone does not establish:
  - the real runtime authority path
  - the writable implementation boundary
  - the writable proof boundary
- this inspection is for envelope validation only, not design exploration
- stop once the semantic hinge, writable boundary, and proof boundary are known well enough to emit
  or reject the task
- if Bernard cannot prove the executable envelope without broader exploration, stop and return an
  under-specified or under-split result instead of guessing

Known decomposition trap:

- if you need UUIDs, generate them with a narrow terminal command only
- if you need objective/task readback, read only the fields needed for decomposition
- do not switch to `execute_code` or broad shell scripts just to transform API JSON; that is execution-style behavior, not decomposition

Do not convert missing implementation details into fake certainty.
If the objective requires persistence, coordination, or validation behavior but does not name the concrete internal mechanism, describe the required outcome generically instead of inventing internal table names or storage primitives.

Do not invent:

- new fields
- new modules
- new table names
- new queue names
- new mapping-store columns
- new status keys

unless one of these is true:

- the objective text names them
- the minimal ambiguity-resolution inspection directly confirms them
- the current workflow contract in the card explicitly names them

Do not perform a second-pass self-review after the decomposition is already valid.
Internal checks happen before emitting the final JSON, not after.

If a task has already been rejected more than once for the same acceptance-criteria family, stop
normal remediation and treat that as evidence the original decomposition may be wrong. Prefer a
decomposition repair loop over another blind retry.

## API Compatibility Rule

The current Mission Control decompose route persists only this task shape:

```json
{
  "id": "6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1",
  "title": "string",
  "assignee": "William | Codex | Librarian | Maeve | Bernard | Dolores | Abdul",
  "taskType": "execution | review | release | decompose",
  "reviewMode": "phase_review | gate_review | null",
  "priority": "P1 | P2 | P3",
  "feature": "string",
  "summary": "string",
  "acceptanceCriteria": "string",
  "constraints": "string",
  "relatedFiles": ["path"],
  "artifactPaths": ["path"],
  "links": ["url"],
  "nextAction": "string",
  "blockers": "string | null",
  "dependsOn": ["6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1"]
}
```

The decompose route validates like the app route, but the live Supabase task id column is UUID-backed. You must emit real UUID task ids.

Do **not** omit `id`. Do **not** use non-UUID ids such as `task_1`, `canary-exec`, or `marker-review`.

Task ids must be freshly generated UUID v4-style values. Do **not** use patterned, sequential, mnemonic, placeholder, repeated-digit, alphabetic-sequence, or hand-crafted UUID-shaped values. Every `dependsOn` entry must reference one of the freshly generated task ids exactly.

Do **not** rely on fields that the route will ignore or reject for persistence, such as:

- `dependencies`
- `reviewOwner`
- `executionMode`
- `machineJobType`
- legacy local dependency alias fields
- `localId`

If dependency order matters:

- generate the upstream task UUID first
- reference it from `dependsOn` on the downstream task

For the required objective-level review gate:

- emit a dedicated task with `taskType: "review"`
- set `reviewMode: "gate_review"`
- assign it to the actual reviewer, usually `Bernard`
- make it depend on the relevant execution tasks with `dependsOn`
- do not try to persist `reviewOwner` through the decompose payload; that field is not part of this route contract

## Pre-Submit Checklist

Before posting to `/api/objectives/{objectiveId}/decompose`, verify all are true:

- `MC_API_URL` is set for the current worker
- `CRON_SERVICE_TOKEN` is set for the current worker
- top-level `actor` is `Bernard`
- top-level `requestReview` is `true`
- every task has a real UUID `id`
- the root execution task has no `dependsOn` or has `dependsOn: []`
- the dedicated `gate_review` task has `dependsOn: ["<executionTaskId>"]`
- no task contains `localId`, legacy local dependency alias fields, `dependencies`, `reviewOwner`, `executionMode`, or `machineJobType`

Authenticated submit contract:

```bash
DECOMPOSE_PAYLOAD_PATH="$PWD/decomposition.json"
API_BASE="${MC_API_URL%/}"
case "$API_BASE" in
  */api) DECOMPOSE_URL="$API_BASE/objectives/$OBJECTIVE_ID/decompose" ;;
  *)     DECOMPOSE_URL="$API_BASE/api/objectives/$OBJECTIVE_ID/decompose" ;;
esac

curl -s -X POST "$DECOMPOSE_URL" \
  -H "Authorization: Bearer $CRON_SERVICE_TOKEN" \
  -H "Content-Type: application/json" \
  -d @"$DECOMPOSE_PAYLOAD_PATH" \
  -o "$PWD/decompose_response.json" \
  -w "\n%{http_code}"
```

Submission rules:

- write `decomposition.json` and response files inside the current task workspace, not `/tmp` or other blocked temp paths
- never post the decompose payload without the bearer header
- fail closed if `MC_API_URL` or `CRON_SERVICE_TOKEN` is missing
- read back the response body and status code before declaring decomposition complete
- if the route returns `401`, stop and report auth/runtime misconfiguration instead of retrying with alternate env var names

Deterministic JSON emission rule:

- do **not** hand-author large `decomposition_result` JSON with ad hoc `write_file` bodies and then
  repair it with `sed`, `grep`, or escape-pattern search/replace
- do **not** use multiline `python3 -c "..."` one-liners to validate or rewrite the payload; they are
  fragile and regularly fail on quoting, newlines, and glob strings
- do **not** embed a full large-task decomposition builder directly inside one giant terminal
  invocation such as `python3 <<'PY' ...` when the payload has many long task strings; this is
  brittle in practice and has already failed on the `4009e581-7231-4930-9a0d-b2b56b281d9e` canary
- build the payload as a native Python dict/list structure and serialize it once with
  `json.dump(..., indent=2)` into `decomposition.json`
- for decompositions with 8+ tasks or long multiline acceptance criteria, first write a dedicated
  workspace script file such as `build_decomposition.py`, then run `python3 build_decomposition.py`
  to produce `decomposition.json`
- keep the builder file and the validation step separate:
  1. write `build_decomposition.py`
  2. run `python3 build_decomposition.py`
  3. run `scripts/validate_decomposition_json.py decomposition.json <max_task_count>`
  4. only then submit the payload
- immediately validate the serialized file with a separate `python3` heredoc that:
  - runs `json.load` successfully
  - asserts `kind == "decomposition_result"`
  - asserts `actor == "Bernard"`
  - asserts `requestReview == true`
  - asserts every task has a UUID `id`
  - asserts every `dependsOn` entry references an emitted task id
  - asserts glob patterns remain literal path strings such as `src/lib/**`, never escaped
    variants like `\\*\\*` or stray invalid escapes inside strings
- if validation fails, regenerate the file from the source structure; do **not** patch the emitted
  JSON in place with shell substitutions
- preferred pattern:
- preferred small-payload pattern only (do not use this for large 8+ task decompositions with long
  acceptance strings):

```bash
python3 - <<'PY'
import json

payload = {
    "kind": "decomposition_result",
    "objectiveId": OBJECTIVE_ID,
    "statusNote": STATUS_NOTE,
    "requestReview": True,
    "actor": "Bernard",
    "tasks": TASKS,
}

with open("decomposition.json", "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.write("\\n")
PY

python3 - <<'PY'
import json, uuid

with open("decomposition.json", "r", encoding="utf-8") as f:
    data = json.load(f)

assert data["kind"] == "decomposition_result"
assert data["actor"] == "Bernard"
assert data["requestReview"] is True

task_ids = {task["id"] for task in data["tasks"]}
for task in data["tasks"]:
    uuid.UUID(task["id"])
    for dep in task.get("dependsOn", []):
        assert dep in task_ids
    for field in ("relatedFiles", "artifactPaths"):
        for path in task.get(field, []):
            assert "\\\\*\\*" not in path
PY
```

Payload-construction rule:

- keep task text in native strings and let `json.dump` escape only what JSON actually requires
- for large decompositions, prefer one Python builder file in the current workspace over inline shell
  assembly; the shell should only run the builder and validator, not contain the entire payload body
- never insert manual backslashes before `**`, before markdown list dashes, or before normal path
  separators inside task strings
- if the task text is easier to author in Markdown bullets, build that text first as a normal
  multiline Python string, then hand it to `json.dump`; do not paste the raw markdown directly into
  a JSON file template

Minimal valid payload shape:

```json
{
  "actor": "Bernard",
  "requestReview": true,
  "tasks": [
    {
      "id": "6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1",
      "title": "Implement bounded change",
      "assignee": "William",
      "taskType": "execution",
      "priority": "P2",
      "feature": "Mission Control",
      "summary": "Make the requested bounded change.",
      "acceptanceCriteria": "The requested behavior is implemented and verified.",
      "constraints": "Do not expand scope.",
      "relatedFiles": ["apps/mission-control/docs/api-reference.md"],
      "artifactPaths": ["apps/mission-control/docs/api-reference.md"],
      "links": [],
      "nextAction": "Inspect the target file and make the bounded change.",
      "blockers": null
    },
    {
      "id": "a9e27d4c-6d41-4a89-9c25-8f9c1e42c731",
      "title": "Gate review bounded change",
      "assignee": "Bernard",
      "taskType": "review",
      "reviewMode": "gate_review",
      "priority": "P2",
      "feature": "Mission Control",
      "summary": "Review the bounded change.",
      "acceptanceCriteria": "Approve only when the execution task is complete and scoped.",
      "constraints": "Review only.",
      "relatedFiles": ["apps/mission-control/docs/api-reference.md"],
      "artifactPaths": ["apps/mission-control/docs/api-reference.md"],
      "links": [],
      "nextAction": "Review the execution result.",
      "blockers": null,
      "dependsOn": ["6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1"]
    }
  ]
}
```

## Canary gate-review rule

When decomposing a Mission Control canary that explicitly requires the `reject-once` remediation proof:

- do not write a gate-review brief that says the implementation is already correct and should simply be re-submitted
- do not create a no-op remediation requirement
- the first-pass reject must require one harmless real follow-up delta inside the same approved file scope
- the reopen approval condition must depend on that follow-up delta being present

Default safe canary pattern:

- execution task:
  - add one disposable marker in a deliberately incomplete but reviewable form
- dedicated `gate_review` task:
  - first pass rejects because the marker is bare text instead of an HTML comment
  - remediation requires converting that same marker into an HTML comment in the same file
  - reopen approves only when the HTML-comment form exists and no out-of-scope changes were made

Why this rule exists:

- Mission Control approves reopened gate reviews against fresh William remediation evidence
- if the remediation brief asks William to re-submit the same change, the canary can create a no-op remediation child and misclassify the result as a product defect

## Decomposition Standard

Every task must be:

- one bounded output
- executable without guessing the workspace
- explicit about likely files in scope
- explicit about what should not expand
- clear about how the assignee verifies completion
- narrow enough to keep current-attempt `touchedFiles` clean
- distinct enough that adjacent tasks do not repeatedly touch the same primary files without a strong reason
- stated in terms of externally meaningful outcomes, not speculative internal storage design

### Good Task

- “Harden the governed-workspace review-quality gate path for `software_test`, `software_lint`, and `software_build` with deterministic scope and focused tests.”

### Bad Task

- "Fix machine jobs"
- "Implement and test and deploy release pipeline"
- "Write tests, run tests, write code, commit"
- Three different William tasks that all primarily edit the same handler file and the same test file
- "Refactor the Objectives page: extract modular components, switch to dashboard mode, collapse 12 columns to 4, apply ToneBadge/MaterialSymbol styling, preserve all functionality" — 5 distinct concerns on a 2458-line file bundled into one task

### Good Task (large-refactor split-by-concern)

When the above bad task is split by concern:

- "Extract modular card components from objectives-view.tsx into dedicated files under src/components/objectives/" — extraction only, independently verifiable
- "Switch Objectives page to dashboard mode and collapse 12 swimlanes to 4 lifecycle stages" — layout logic, depends on extraction
- "Apply dashboard styling system (ToneBadge, MaterialSymbol, SectionEyebrow) to Objectives page cards and columns" — styling pass, depends on layout

### Good Task (exact-parity split-by-hinge)

When a task is being judged against a live Mission Control source of truth:

- "Mirror the live review-decision / task.review_completed payload in the Knowledge Plane contract layer and prove parity with a focused route-anchored test" — parity plus minimal proof, explicitly anchored to `apps/mission-control/src/app/api/hermes/review-decision/route.ts`
- "Define the remaining workflow event contracts excluding review-decision parity already isolated above" — remaining contract surfaces only
- "Broaden suite wiring or secondary proof coverage after parity is already proven" — only if broader test integration would overload the first task

### Bad Task (exact-parity hidden inside broad contract work)

- "Define Knowledge Plane workflow event contracts" when the real acceptance hinge is exact parity with an existing live route or payload — this hides the dominant rejection risk and forces William to approximate a live contract that should be source-matched
- "Mirror live parity now, add the route-anchored proof later" — this sends William into review before the deterministic checker for the parity hinge exists

## Overlap Minimization Rule

When decomposing for William:

- prefer merging work that shares the same primary implementation file and the same primary test file
- split only when the tasks target different subsystems, different owners, or meaningfully different verification surfaces
- if two candidate tasks would both primarily modify the same 1-2 files, assume that split is bad unless there is a strong sequencing reason

### Presumption

If multiple candidate tasks would all mainly touch:

- the same implementation file
- the same test file

then Bernard should usually produce **one stronger bounded task**, not multiple overlapping tasks.

### Large-Refactor Carve-Out

The merge presumption above is for mechanical changes on normal-sized files. It does **not** apply when:

- the primary file or file cluster is large (roughly 1000+ lines), AND
- the objective lists 3+ distinct architectural concerns (e.g., component extraction, layout restructuring, styling-system swap, behavior preservation)

In that case, **presume split-by-concern** — one execution task per architectural concern, each with independent acceptance criteria. A worker holding 5 concerns in head on a 2500-line file produces copy-paste errors, missed ACs, and repeated review rejections.

Override this presumption only when the change must be atomic and reviewable as one unit (e.g., a tight API contract change where partial application breaks the build).

When splitting by concern on a shared file cluster:
- sequence tasks with `dependsOn` so extraction precedes layout precedes styling
- each task's `relatedFiles` must include the full directory glob for any new files it creates
- state the split reason in `constraints` (e.g., "Split by concern: this task handles extraction only; layout and styling are separate tasks")

### Multi-Output Execution Carve-Out

The merge presumption also does **not** apply when one execution task would require
multiple independent outputs, even if the primary file cluster is not especially large.

Presume split-by-output when a single task would require 3 or more of these at once:

- implement a new persistence or write-back path
- add or change readback or board/UI presentation
- create or reshape child-task, retry, or release-routing behavior
- wire more than one operator surface (for example, both Dashboard and Overview)
- add deterministic tests for multiple new behaviors

In that case, produce one execution task per primary output surface or behavior.

Rationale:
- these tasks often look small by file count but exceed the real worker budget
- first-pass `Iteration budget exhausted (90/90)` blocks are usually a shaping smell, not a reason to keep bundling the same work
- one bounded output per task is more reliable than one broad "wire the whole feature" task

### Multi-Family Emitter Wiring Rule

When a task is about emitter wiring, ledger wiring, event projection wiring, or transition-to-event
integration, Bernard must split by **workflow family**, not by "shared emitter destination."

Hard rule:

- if the work spans more than one named workflow family such as:
  - `task/objective`
  - `release`
  - `activation`
  - `escalation`
  - `board-move` / promotion
- do **not** bundle those families into one William execution task just because they all call the
  same ledger writer, storage boundary, validator, or proof file
- default to one execution task per workflow family or tightly-coupled family pair
- if more than two runtime behavior files are being changed to wire distinct transition families,
  presume under-split unless the objective explicitly requires atomic cross-family behavior

Reason:

- these tasks fail by meaning, not by syntax
- the worker ends up holding too many transition branches, too many emitted-event shapes, and too
  many proof obligations in one pass
- repeated `Iteration budget exhausted (90/90)` on emitter wiring is a decomposition smell first

Concrete anti-pattern:

- "Wire release/activation/escalation emitters to the ledger write path"

Preferred split:

- one task for `release` emitters
- one task for `activation` emitters
- one task for `escalation` emitters

### Hard decomposition invalidators

Reject the task before release if any William execution task does any of the following:

- spans more than one workflow family
- introduces more than one new abstraction class
- owns more than one primary artifact class
- claims a downstream consumer role but does not own a distinct substantive delta

Workflow-family rule:

- one William task may own exactly one workflow family such as:
  - `task/objective`
  - `release`
  - `activation`
  - `escalation`
- do not bundle two or more families into one task, even when they share the same destination
  writer, validator, storage boundary, or proof file
- concrete invalid shape:
  - `Define release/activation/escalation contract taxonomy`
  - `Wire release + activation emitters`

New-abstraction rule:

- one William task may introduce at most one new abstraction class
- abstraction classes include:
  - contract family
  - schema model or migration slice
  - repository boundary
  - canonical writer
  - identity/correlation mapping surface
  - emitter-wiring slice
  - deterministic query surface
  - API readback surface
  - duplicate-prevention surface
  - bounded backfill surface
  - focused proof harness
- if a task would introduce two or more of those, split it before release

Distinct-delta rule:

- if a downstream task says it consumes, broadens, preserves, or builds on an upstream artifact,
  Bernard must name the exact new substantive delta it owns
- if the likely successful delta is only cleanup, import reshuffling, comment edits, or re-running
  proof against an unchanged upstream artifact, the downstream task is invalid and must be merged,
  narrowed, or deleted

Readback / duplicate-prevention dependency rule:

- do not make readback-query or duplicate-prevention tasks depend on every runtime emitter family by
  default
- if the invariant can be proven from the canonical writer, established repository boundary, or
  narrow seeded fixtures, prefer that narrower dependency set
- only require full runtime-family lineage when the objective explicitly says the proof must be
  sourced from those live runtime families

Source-anchor vs writable-scope rule:

- if a runtime, route, worker, or release file is being used as the source-of-truth authority for a
  contract task, keep it out of `relatedFiles` by default
- source anchors belong in:
  - `artifactPaths`
  - `links`
  - `acceptanceCriteria`
  - `constraints`
- `relatedFiles` is for files William is expected to edit in the current task
- contract-authoring tasks should usually keep writable scope to:
  - `src/lib/knowledge-plane/contracts/**`
  - focused proof files for that contract slice

Consumer-surface lock rule:

- if a task says it consumes an existing contract, schema, repository boundary, or writer surface,
  that upstream surface is read-only by default
- do not leave the consumed upstream surface in `relatedFiles` unless the task explicitly owns
  modifications to it
- emitter tasks should not carry writable `contracts/**` scope unless contract edits are part of
  the explicit acceptance hinge
- writer, readback, duplicate-prevention, and backfill tasks should not keep upstream contract files
  writable just because those contracts are referenced by proof or by task wording

One-primary-artifact hard fail:

- reject the task before release if it still owns more than one primary artifact class
- concrete invalid shapes for this canary include:
  - `repository boundary` + `storage exports`
  - `canonical writer` + `identity/correlation mapping`
- if both are needed, split them and serialize with `dependsOn`

Docs completeness dependency rule:

- if a docs task claims to document the broad workflow-ledger contract or operator proof path, it
  must depend on every implementation slice it claims to describe
- otherwise narrow the docs task so it documents only the final already-implemented surfaces

Contract-provider rule for emitter wiring:

- if an emitter-wiring task says it will consume event names, payload shapes, validators, or other
  definitions from `src/lib/knowledge-plane/contracts/**`, Bernard must verify that the owning
  contract family is already provided by either:
  - an explicit upstream contract-authoring task in the same decomposition, or
  - an already-existing authoritative contract surface that is named directly in
    `acceptanceCriteria`, `constraints`, and `relatedFiles`
- do **not** let an emitter-wiring task implicitly invent or reshape its own family contract merely
  because both the emitter file and `contracts/**` are authorized
- if the family contract does not already exist as a truthful upstream input, emit the contract task
  first or stop the decomposition as incomplete
- emitter-wiring tasks may **consume** contract definitions, but they may not be the primary place
  where that same workflow family's contract surface is first authored
- do **not** satisfy the missing-provider problem by rewriting the emitter task so it says
  "define X contract events in contracts/** and wire Y service to emit them" for the same family
- if the emitter task owns both first-time contract authoring and runtime emitter wiring for the same
  workflow family, that is still under-split unless the objective explicitly grants an atomic
  exception for that exact family pair

Known invalid shape:

- task A: `task/objective workflow contract taxonomy`
- task B: `release-start emitter wiring`
- task C: `merge/deploy/verify emitter wiring`
- task D: `activation emitter wiring`
- task E: `escalation emitter wiring`
- but **no** upstream contract task exists for the release / activation / escalation families even
  though tasks B-E all say they consume event names and payload shapes from the contracts layer

That is still a decomposition defect. The emitter family is consuming a contract provider that was
never emitted.

Also invalid:

- task title: `Activation emitter wiring`
- acceptance says:
  - define activation contract event names and payload shapes in `contracts/**`
  - wire `objective-activation-service.ts` to emit those events

That is not a real upstream provider split. It hides contract authoring inside the emitter task and
recreates the same semantic overload under a different title.

Possible bounded exception:

- if `release` and `activation` truly share one tiny authoritative branch and one proof surface,
  they may be paired
- `escalation` should still stay separate unless the objective explicitly requires atomic coupling

### Release-Lifecycle Emitter Split Rule

When the workflow family is `release`, Bernard must still check whether the task actually spans
two semantic slices:

- pre-merge release flow in `objective-release-service.ts`
- post-merge deployment / verification flow in `objective-deployment-service.ts`

Hard rule:

- do **not** bundle push, PR-open, merge, deploy, and verify wiring into one William task merely
  because they are all part of the release lifecycle
- if the work touches both `objective-release-service.ts` and `objective-deployment-service.ts`,
  presume split unless the objective explicitly requires atomic one-pass coupling
- default split:
  - one task for release-start / push / PR-open emitter wiring
  - one task for merge / deploy / verify emitter wiring

Reason:

- release-path semantics look like one family at the board level but still contain too many
  independent transition branches for one reliable execution pass
- a first-pass `Iteration budget exhausted (90/90)` on a release-wiring task that spans both files
  is a decomposition smell first, not evidence that William should just try harder

Proof rule:

- each split release slice gets its own focused proof surface
- do not ask William to prove the full release lifecycle in one task when the code lives across
  both services and multiple transition phases

### Exact-Parity Carve-Out

The merge presumption also does **not** apply when a task must mirror an existing live
Mission Control contract, route, handler, payload, validator branch, state transition, or
runtime behavior exactly.

Exact-parity work is **not** normal implementation work. It is contract archaeology, source
matching, and proof against a live source of truth.

For exact-parity work:

- presume split-by-parity-surface, even when the same target files may overlap
- semantic risk beats file-overlap minimization
- do not ask William to infer parity from new bounded-context files alone
- if parity for one dominant behavior would cause rejection even when the rest of the task is
  clean, isolate that parity surface into its own task
- include the minimal focused proof for that exact parity surface in the same task
- do not phase-review exact-parity implementation before the route-anchored or source-anchored
  checker for that same hinge exists
- when the acceptance hinge is a live payload or transition shape, require the proof to be
  **source-derived** from the named live source, not hardcoded as free-standing expected field
  arrays, copied status literals, or self-referential assertions against the new destination file
- if the only way to satisfy "source-derived proof" would be to invent extractor helpers, path
  resolution machinery, regex/static-analysis parsing, or other proof-only scaffolding against the
  live source files, the proof is no longer "minimal focused proof" and the task is under-split
- do not ask William to both reshape the contract files and invent a source-parser proof harness in
  the same execution task; split the parity surface smaller or isolate the proof machinery as its
  own bounded concern before activation
- do not emit one William task as "exact-parity proof" and a second William task as same-family
  contract authoring when both touch the same runtime authority files and the same
  `src/lib/knowledge-plane/contracts/**` surface
- if the proof depends on contract definitions that do not already exist or are being reshaped in
  the same objective, either:
  - merge the parity implementation plus the minimal focused proof into one task, or
  - make the proof task a downstream task with `dependsOn` on the contract-authoring task
- a parity task may be parallel-ready only when it is truly proof-only against already-complete
  contract definitions and its bounded proof can pass without reshaping the same-family contract
  files
- if the current contract surface is **narrower** than the live workflow family and a downstream
  task will expand that family taxonomy, the upstream parity task must anchor to the already-existing
  contract branch only
- do not word the parity task as "new contract event names/payload shapes for the task/objective
  workflow" when a separate downstream taxonomy task still exists for that same family
- in that shape, the parity task must explicitly name the single existing branch, route, validator,
  or payload contract it owns, and must mark the remaining family transitions as preserve-only or
  downstream
- if Bernard cannot name one exact existing branch that the parity task proves, the task is still
  under-anchored and must not be released
- if the focused proof would require `package.json`, `vitest.config.*`, or other runner/config
  wiring changes, either split that broader wiring into a separate downstream task or block the
  decomposition as under-anchored; do not smuggle config edits into the parity task unless the
  objective explicitly asks for test-runner wiring
- if adjacent workflow families (for example escalation, release, activation, board-move) appear in
  neighboring files but are not named in the parity hinge, mark them preserve-only and exclude them
  from the task instead of letting the proof drift into those families
- if more than one plausible subset of the named source files could satisfy the task wording, the
  parity hinge is still under-anchored. Do not emit the task until the exact in-scope event,
  branch, payload, or transition subset is named explicitly enough that Bernard review is grading
  one interpretation only
- when the proof is kept inside the parity task, say exactly what the proof must cover and what it
  must not cover. Do not leave William to infer whether neighboring branches in the same source file
  are included merely because they are nearby

Examples of exact-parity surfaces:

- an existing live route payload
- an existing task or objective state transition
- an approve vs reject review branch with different required fields
- a persisted event shape that must match current Mission Control behavior

### Contract-Taxonomy Anchor Rule

If a task will author or reshape `src/lib/knowledge-plane/contracts/**`, validators, event
registries, or other contract-definition surfaces, Bernard must anchor the task to the live runtime
authorities that justify each in-scope workflow family.

Hard rules:

- do not emit a contracts-only task that says "define all current workflow event names and payload
  shapes" while `relatedFiles` authorizes only `contracts/**`
- if the task spans more than one workflow family cluster, either:
  - split it by family cluster, or
  - name every runtime authority file for every included family in `relatedFiles`,
    `acceptanceCriteria`, and `nextAction`
- do not treat a family label as covered unless every live branch of that family is named; for
  example, if the task claims release-family coverage and the live release behavior is split across
  `objective-release-service.ts` and `objective-deployment-service.ts`, both files must be named or
  the task must narrow its scope
- if the task claims task/objective workflow family coverage and the objective or current product
  truth says direct route entrypoints still participate in live behavior, include those route files
  explicitly or narrow the task away from claiming that wider family coverage
- minimum default split for Knowledge Plane contract authoring:
  - one task for `task/objective` workflow contracts
  - one task for `release/activation/escalation` contracts
  - split further if one of those clusters still carries more than one semantic hinge
- if downstream emitter tasks are already split into `release-start`, `merge/deploy/verify`,
  `activation`, and `escalation`, that does **not** remove the need for the upstream
  `release/activation/escalation` contract-authoring task unless Bernard can point to an already
  existing authoritative contract surface those emitters will consume unchanged
- a contract-authoring task is under-anchored if William would have to infer event families, payload
  fields, or source mapping from memory or from nearby files that were never named in the task

Known invalid shape:

- title: "Define Knowledge Plane event contract taxonomy"
- relatedFiles: only `src/lib/knowledge-plane/contracts/**`
- acceptance asks for task/objective, release, activation, and escalation families
- no runtime authority files are named for those families

That is a task-contract-anchoring defect. Split or anchor before emitting.

Also invalid:

- Task A: "exact-parity proof for task/objective workflow contract behavior"
- Task B: downstream "task/objective workflow contract taxonomy"
- Task A acceptance still says "new contract event names/payload shapes" across the whole
  task/objective workflow family
- current contract files only contain one existing branch

That is still under-anchored. If taxonomy is downstream, the parity task must narrow to the already
existing branch only; otherwise merge parity and taxonomy into one task instead of pretending they
are separate.

### Source-of-Truth Anchor Rule

If acceptance depends on matching current Mission Control behavior, Bernard must name the
authoritative source file, route, handler, payload, or state machine in:

- `summary`
- `acceptanceCriteria`
- `relatedFiles`
- `nextAction`

If the authoritative source is not known from the objective payload:

- in `payload_only` mode, block the decomposition as under-specified
- in `ambiguity_allowed` mode, resolve only that narrow ambiguity and stop

Do **not** emit a parity task that names only the new destination files while leaving the live
source-of-truth surface implicit.

If the consuming workflow file imports the real contract shape from another live file, Bernard must
anchor **both** layers:

- the consuming behavior file that proves where the contract is used
- the defining source file(s) where the exact union, interface, enum-like literals, nullability, or
  nested payload shape actually live

Do not name only `handlers.ts`, a route file, or another consumer when the dominant parity hinge is
really determined by imported definitions from files like `workers/types.ts`,
`workers/escalation-events.ts`, shared route payload types, or other source-of-truth type modules.

If exact nested parity would require William to infer imported unions or interface shapes that are
not explicitly named in the task fields, the task is under-anchored. Fix the anchors before
emitting the task.

If the named authority files are mechanism-only consumers (for example handlers, promotion flows,
or state-move helpers) and the planned output still asks William to author or reshape exported
contract registries, validator allow-lists, patch payload types, or exact field inventories in
`contracts/**`, `validators.ts`, or similar destination files, do **not** emit that as a normal
parity implementation task.

In that shape, Bernard must choose one of these before activation:

- narrow the task to source-derived transition-mechanics proof only and mark the adjacent contract
  authoring surfaces preserve-only, or
- add the real defining source file(s) that own the literal event family, payload-key inventory,
  union, or validator branch being graded

If neither is possible from the objective evidence, block the decomposition as a
task-contract-anchoring defect instead of sending William into a consumer-only parity guess.

If the parity task lands inside a new or skeletal destination file that sits next to an already
existing contract or validator surface, Bernard must also name which adjacent behavior is
**preserve-only** and not to be redesigned in this task.

Call that out explicitly in:

- `constraints`
- `acceptanceCriteria`

Examples:

- preserve the existing `review_decision` contract branch exactly; only add the new task workflow
  contract surface
- do not recount or redesign neighboring optional-field arrays unless the objective explicitly asks
  for that branch parity too
- keep `task.escalated` or release-family branches preserve-only when the task is scoped to
  task/objective workflow parity only

For exact-parity proof tasks, Bernard must make the proof contract explicit in emitted task fields:

- state that the proof is **derived from the named live source files or route**, not from new
  hardcoded expected arrays or constant-string copies
- if the proof would rely on function-name presence, comments, or local semantic inference to
  invent event names, reason literals, or registry members that are not directly present in the
  named authority files, that parity surface is under-anchored. Narrow it out of the task or split
  the task before activation
- state that runner/config files are out of scope unless the task explicitly includes proof-wiring
  or suite-integration work
- if the proof must stay inside one focused test file, say so directly in `constraints` and
  `acceptanceCriteria` instead of leaving the worker to infer whether broader test/config edits are
  acceptable
- if the proof is expected to be direct, say what "direct" means: read the named source, compare
  exact payload names or field sets, and fail on missing or extra values without inventing new proof
  infrastructure
- if the dominant parity hinge depends on imported type definitions or event-shape unions, name
  those upstream definition files directly in `acceptanceCriteria`, `relatedFiles`, and
  `nextAction`; do not leave William to discover them indirectly from imports during execution
- if the proof cannot be described that directly, stop and split again before emitting the task
- state the exact in-scope branch or event subset in plain language, for example:
  - mirror only `task.board_moved` plus `objective.task_promoted`
  - preserve `task.completed`, `task.failed`, escalation, activation, and release families unchanged
- if a named source file proves only a transition mechanism but not the exact emitted literal set,
  do not ask William to synthesize the missing literals from local helper names. Either add the real
  authority file that contains those literals or narrow that branch out of the parity task
- if the named authority files are consumer/mechanism files (for example handlers that move state,
  promote tasks, or call helpers) rather than the file that defines the exact event-name, payload,
  or reason literal set, do not emit an exact-parity literal task against those consumer files
  alone. Either:
  - add the defining authority file that contains the literal set, or
  - narrow the task to transition-mechanism parity only and say explicitly that no closed-world
    literal/event-family parity is being graded in that task
- exact Mission Control trap: if the only named authorities are
  `apps/mission-control/src/lib/workers/handlers.ts` and
  `apps/mission-control/src/lib/workers/task-readiness-promotion-service.ts`, do **not** ask for
  exact parity on workflow event names, payload-key registries, or closed-world `task.*` event
  families from those two files alone. Those files prove workflow mechanics, not shipped event-name
  literals.
- in that exact shape, the task must do one of these before activation:
  - add the real defining event-shape authority file(s), or
  - narrow the task to transition-mechanism parity only and state plainly that workflow event-name
    taxonomy remains out of scope for that task
- if the objective text itself still asks for "event names and payload shapes" from that exact
  authority pair with no stronger defining source named, do **not** silently decompose around the
  ambiguity. Return the objective as under-specified for decomposition and require objective text
  repair before creating execution tasks.
- if the task wording says "mirror workflow semantics" or similar broad language, but the named
  authority files only show transition mechanics and not the exact emitted event family, the task is
  still under-anchored. Split again before activation instead of leaving William to guess whether
  semantic inference is allowed
- if the proof language still says "fail on missing or extra workflow event names or payload
  fields" while the only named authorities are those consumer/mechanism files, stop and rewrite the
  task. That is the known self-referential parity trap.
- if one proposed parity task would naturally require William to prove more than one of these at
  once, do not emit it as a single task:
  - multiple status/column/objective unions
  - route payload field inventories
  - validator allow-lists or required/optional field sets
  - transition-mechanics parity across more than one workflow branch
  - contract registries inside `contracts/**` plus broad proof over those registries
- in that shape, the task no longer has one dominant parity hinge. Split it until one William task
  can be described as one exact existing branch, one defining authority, and one focused proof file.
- exact known bad shape:
  - title like `Exact-parity proof for task/objective workflow contract behavior`
  - acceptance text still spans task statuses, column values, objective lifecycle states,
    review-decision payloads, promotion behavior, and handler completion logic in one task
  - proof would naturally expand into source-mining helpers or regex extraction across several live
    files
  - downstream task still exists for the remaining taxonomy of that same family
  - this is a decomposition defect; do not emit it
- preferred repair for that bad shape:
  - one parity task for a single already-existing live branch with the minimal focused proof
  - one downstream taxonomy/definition task for the remaining same-family contract work
  - additional parity tasks only when each owns one exact branch and one proof hinge
- if the review should fail on extra mirrored branches as well as missing ones, say so explicitly in
  `acceptanceCriteria` instead of assuming William will infer a closed-world boundary from
  "preserve-only"

### Greenfield Parity-First Rule

If the destination module is new, skeletal, or not yet the live source of truth, and the task
must preserve existing Mission Control behavior, decompose in this order:

1. parity extraction or mirror task with the minimal focused proof for that same hinge
2. broader validator, suite-wiring, or parity-proof expansion only if needed after the hinge is locked
3. broader generalization or cleanup task

Do **not** ask William to design a clean abstraction while being graded against an older live
implementation in the same bounded task.

For exact-parity contract work, the minimal focused proof is part of the implementation task, not a
downstream review aid. Separate only broader suite wiring or secondary proof surfaces, not the
deterministic checker for the main parity hinge.

### New-Contract Slice Enumeration Rule

If the task will author or reshape a new contract-definition surface inside destination files like:

- `src/lib/knowledge-plane/contracts/**`
- `validators.ts`
- exported event-name registries
- payload-shape allow-lists

Multi-family ban:

- do **not** emit one William task phrased as:
  - `Define remaining workflow event contract taxonomy`
  - `Define remaining workflow contracts`
  - `Tighten the remaining workflow contract surface`
- when that one task still spans more than one workflow family such as:
  - `task/objective`
  - `release-start`
  - `PR`
  - `merge/deploy/verify`
  - `activation`
  - `escalation`
- this is invalid even if the writable files are mostly the same `contracts/**`, `validators.ts`,
  and one shared proof file
- reason: "remaining taxonomy" hides the real semantic boundary and forces William to infer too
  many authority branches in one pass
- required split:
  - one task per workflow family or tightly-coupled family pair
  - each task names the exact authority-owned member/status obligations for that family
  - each task owns focused proof for that family only
- if the only reason for rebundling is a task-count cap, the cap loses; do not preserve the cap by
  emitting a semantically mixed "remaining taxonomy" task

If a task will author or tighten a contract-definition surface for an existing live workflow family,
Bernard must not stop at broad wording like `payload shapes`, `validators`, or `remaining taxonomy`
when the real acceptance hinge is exact field discipline.

Hard rule:

- if Bernard expects Bernard review to fail on any of these:
  - missing authority-required members
  - optionalized members that should stay required
  - broadened nullable/optional behavior
  - widened status/value literals that should stay family-specific
- then those exact hinges must be stated directly in the task contract
- do not emit a task that says only `define remaining workflow event contracts` or `tighten the
  remaining taxonomy` when the real success condition is exact required/nullable field parity and
  per-family literal narrowing
- name the exact workflow family plus the exact authority-derived contract obligations in
  `acceptanceCriteria` and `constraints`
- when in scope, name the exact authority-required members directly instead of hiding them behind
  words like `payload shapes`; examples include:
  - `remote`
  - `prNumber`
  - `branchName`
  - `deploymentIds`
  - `services`
  - `pollStatus`
  - `deployedCommitSha`
- the focused proof for that task must be described so it fails on omission, optionalization,
  broadening, or field filtering; a proof that can pass by excluding authority-required fields is
  not an honest proof for this task shape
- if those exact obligations are too numerous or span more than one workflow family, split again by
  family or by authority branch before activation

Exact known bad shape:

- task title: `Define remaining workflow event contract taxonomy`
- actual review hinge:
  - release-start / PR / deploy / verify payload members must stay exact
  - validators must keep those members required or nullable exactly as the live authority does
  - status/value fields must stay narrowed to the family-specific literals
  - proof must fail on omitted members instead of filtering them out
- but the task wording never names those exact hinges
- this is a task-contract anchoring defect; do not emit it

Preferred repair:

- one task per workflow family or tightly-coupled family pair
- each task names the exact authority-derived required/nullable members and status/value literals it
  owns
- each task says the focused proof must compare that exact surface directly and fail on omission,
  optionalization, or broadening
- explicit union/type inventories

then Bernard must not emit a William task unless the exact in-scope branch or event subset is
enumerated explicitly in plain language.

Required shape:

- name the exact workflow family or branch subset being mirrored
- name the adjacent families that are preserve-only
- make it possible for Bernard review to grade one interpretation only

Examples of acceptable enumeration:

- mirror only `task.board_moved` and `objective.task_promoted`
- preserve `task.completed`, `task.failed`, release, activation, and escalation families unchanged

Unacceptable shape:

- "define workflow event contracts for current workflow activity"
- "add event names and payload shapes"
- any wording that leaves William to infer the event-family boundary from nearby code

If the objective text or named authority files do not support that exact subset:

1. return the objective as under-specified for decomposition, or
2. split off a smaller source-anchoring / scope-identification task before any contract-definition
   task reaches William

Do not send William into a new contract file to discover the in-scope taxonomy by execution.

If the same contract file already contains an older adjacent branch that is not the parity hinge
for this task, Bernard must constrain the task as:

1. mirror the named live workflow branch
2. preserve the neighboring existing branch unchanged
3. expand broader validator generalization only if the objective explicitly requires it

### Upstream-Artifact Consumption Rule

If task B depends on task A because task A establishes a schema, migration, contract, foundation,
or canonical artifact that task B is supposed to build on, Bernard must state that dependency as an
**artifact consumption boundary**, not just a sequencing edge.

This is not optional wording. If task B consumes an upstream artifact produced by task A, Bernard
must encode that relationship in the DAG itself with an explicit `dependsOn` edge to task A.

Hard rule:

- if task B says "consume", "use", "build on", "read from", "preserve", "extend", or otherwise
  relies on an artifact established by task A, task B must include `dependsOn: ["<task-A-id>"]`
- text alone is insufficient; the dependency must be machine-readable
- do not rely on task ordering, titles, shared branch context, or human interpretation to preserve
  upstream lineage
- if the consumed artifact comes from more than one upstream task, list every required source task
  directly in `dependsOn`

In that case, task B must say, in substance:

- consume the schema/foundation/artifact established by the upstream task
- do not redefine, re-infer, or broaden that upstream artifact from scratch
- if the expected upstream artifact is missing in the execution workspace, block with the missing
  artifact rather than inventing a replacement

When the upstream artifact is **read-only input** for task B:

- mention the upstream artifact path in `summary`, `constraints`, `acceptanceCriteria`, or
  `nextAction` as the thing to consume
- but do **not** authorize that upstream artifact for writes in `relatedFiles` unless task B is
  explicitly supposed to modify it
- if task B should consume `prisma/schema.prisma`, a migration file, a contract file, or another
  canonical artifact unchanged, keep that file out of `relatedFiles` and say it is read-only /
  preserve-only

Do not emit a contradictory task that says "consume upstream artifact, do not redefine it" while
also authorizing the upstream schema, migration, or canonical artifact file for normal edits in
`relatedFiles`. That shape invites William to rewrite the very artifact he was supposed to build on.

Do not emit a contradictory task that says it consumes an upstream artifact while leaving
`dependsOn: []` or omitting the owning upstream task from `dependsOn`. That shape breaks governed
workspace lineage and turns a valid bounded task into a stale-base retry trap.

Call this out explicitly in:

- `summary`
- `constraints`
- `acceptanceCriteria`

Examples:

- storage foundation consumes the established Prisma ledger schema; it does not redesign event kinds
- write-path task consumes the existing storage boundary; it does not recreate repository contracts

Storage-boundary scoping rule:

- if a downstream task says things like:
  - "persisted through the established storage boundary"
  - "consume the existing storage boundary"
  - "emit durable records through the canonical ledger writer"
- Bernard must check whether the implementation will need to touch storage-surface files such as:
  - `src/lib/storage/types.ts`
  - `src/lib/storage/index.ts`
  - `src/lib/storage/*repository*.ts`
  - the corresponding `src/lib/knowledge-plane/ledger/**` bridge files
- if those files are part of the real implementation hinge, they must be included in
  `relatedFiles` before activation
- do **not** emit an emitter-wiring task whose `acceptanceCriteria` require durable persisted events
  while `relatedFiles` only authorize emitter files plus tests
- if the task would otherwise need both emitter wiring and storage-boundary contract reshaping, either:
  - include the storage surfaces explicitly in `relatedFiles`, or
  - split the task again so William is not forced into out-of-scope storage edits

Documentation sequencing rule:

- if a docs task says it will document implemented runtime behavior, readback, duplicate
  prevention, backfill, or other downstream artifacts, it must depend on the owning implementation
  tasks for those artifacts before release
- do not emit a docs task whose acceptance requires implemented storage, write-path, readback, or
  backfill behavior while `dependsOn` names only the earliest foundation task
- if the docs should start earlier, narrow the docs task so it only documents the upstream artifact
  that actually exists at that point
- docs tasks may consume upstream artifacts as read-only input, but their sequencing still has to
  match the real implementation state they claim to describe

### Coherent Task Envelope Gate

Before emitting any William execution task, Bernard must validate the full
execution envelope, not just the most obvious implementation file.

This gate outranks:

- overlap minimization
- "prefer one strong task"
- file-count neatness
- the desire to stay under a cap by rebundling semantic-risk work

If the envelope gate says split, Bernard must split even when the files overlap heavily.

Hard questions to answer before release:

1. What is the authoritative source-of-truth contract or behavior being changed or mirrored?
2. What runtime path, route, handler, or machine path proves the work?
3. What storage, schema, migration, or canonical artifact boundary is affected?
4. What focused proof must pass before Bernard review can approve the task?
5. What exact files are likely required to make that proof pass honestly?
6. Does `relatedFiles` include every writable file needed for the bounded proof?

If the answer to (6) is no, the task is not valid yet.

Hard validity rule:

- one William execution task must own exactly one dominant semantic hinge
- one William execution task must have one coherent writable implementation boundary
- one William execution task must have one focused proof surface
- that focused proof must pass without requiring William to edit a second non-test code cluster
  outside the bounded implementation envelope
- if Bernard cannot state those four things plainly, the task is not ready and must be split or
  rejected

Pre-release envelope ledger:

Before release, Bernard must be able to state for each William task:

- semantic hinge: the single exact behavior or invariant that would cause rejection if wrong
- source-of-truth anchor: the authority file, route, or runtime behavior the task is judged against
- writable boundary: the exact non-test code files or globs William is allowed to change
- focused proof boundary: the exact proof file or narrow proof glob that must pass honestly
- upstream provider tasks: the exact prior task ids this task consumes via `dependsOn`

If that ledger cannot be filled honestly from the objective plus bounded inspection, stop and split
again before William sees the task.

Task-budget integrity rule:

- do not satisfy an objective task-cap by silently omitting a required upstream provider task
  (contract taxonomy, schema foundation, storage boundary, canonical writer, focused proof, or
  other named prerequisite) while keeping only the downstream consumer tasks
- if the smallest coherent graph requires one more task than the current objective exception allows,
  stop and return a decomposition repair result naming:
  - the missing provider slice
  - the downstream consumers depending on it
  - the minimum corrected task count
- do **not** force-fit the graph by making downstream emitter, API, backfill, or proof tasks
  consume a provider that is only implied, preserve-only, or expected to be guessed during
  execution

Bernard must then choose one of two actions before submission:

- split the task into smaller bounded tasks whose implementation boundary and proof boundary match, or
- widen `relatedFiles` to the minimum coherent implementation boundary **only if** that widened
  boundary still fits in one cognitive execution unit

Do **not** authorize by "expected file only."
Authorize by the **minimum coherent implementation boundary**.

Meaning:

- include every writable file needed to satisfy the bounded acceptance hinge
- exclude adjacent preserve-only files that are not part of that hinge
- do not leave William to discover mid-run that schema, storage, route, or proof files are also required

Direct mutation entrypoint rule:

- if the real behavior is still performed directly in a route/controller/entrypoint file, that file is
  part of the coherent envelope even when downstream helpers also exist
- do not scope a workflow-emitter or transition task only to helper files such as
  `handlers.ts`, `task-readiness-promotion-service.ts`, or release services when the active
  mutation entrypoint still performs task/objective state transitions, rollups, or status writes in:
  - `src/app/api/tasks/route.ts`
  - `src/app/api/tasks/[id]/route.ts`
  - `src/app/api/objectives/[id]/route.ts`
  - or the equivalent live mutation surface for the behavior
- if the focused proof depends on those entrypoints remaining behaviorally correct after the change,
  either include them in `relatedFiles` or split the task so the helper-only slice is honestly
  bounded
- do not assume a downstream helper is the full runtime path just because it looks like the cleaner
  abstraction; derive the writable boundary from the live mutation path that actually changes state

Known invalid shape:

- task summary sounds like readback/query work
- `relatedFiles` authorizes only route/ledger/test files
- the real proof still requires writable `prisma/**` or `src/lib/storage/**` changes

That is not an execution defect. It is a decomposition defect.
Fix the envelope before William runs.

Decision rule:

- if the coherent boundary crosses contract/runtime/storage/schema/proof surfaces but still serves
  one narrow acceptance hinge, Bernard may widen scope to that minimum coherent boundary
- if widening would make the task span more than one semantic hinge or more than one cognitive unit,
  split instead

Cap-vs-boundedness rule:

- after shaping the truthful task graph, check whether it still fits the active cap **without**
  violating the boundedness rules
- if the graph only fits by rebundling semantic-risk work, the graph does **not** fit
- do not emit a compressed graph just because an objective payload contains a lower cap or older
  exception
- instead report:
  - the minimum coherent graph shape
  - which tasks would have to be wrongly merged to satisfy the cap
  - that the objective needs an explicit cap increase or rewrite before safe decomposition

Known cap-conflict stop signals:

- docs or focused proof would have to be dropped because a previous attempt "already covered it"
- release-start wiring and merge/deploy/verify wiring would have to be merged back together
- readback repository/query work and readback API/proof work would have to be merged back together
- task/objective emitter work would have to omit still-live route/controller entrypoints

Do not emit a task that says, in effect:

- "make this behavior true"
- while authorizing only part of the files required to prove that behavior

That shape guarantees out-of-scope edits or fake proof pressure.

Downstream consumer read-only rule:

- if task B explicitly says it **consumes**, **uses**, **builds on**, or **preserves** an upstream
  storage boundary, schema, migration, contract, or canonical artifact, Bernard must decide
  whether that upstream surface is read-only input or writable scope for task B
- if it is read-only input, keep that upstream file cluster out of `relatedFiles` and say plainly
  in `constraints` or `acceptanceCriteria` that William must preserve it unchanged
- if task B would only succeed by modifying that upstream surface, do not leave the task in an
  ambiguous consumer shape. Either widen it deliberately to include that writable upstream surface
  or split the writable upstream change into its own prior task
- do not ship a downstream emitter/readback/consumer task that says "use the established storage
  boundary" while silently relying on William to discover mid-run that `src/lib/storage/**`,
  `prisma/**`, or upstream contract files must also change

Known failure shape to prevent:

- Task A: "Establish ledger schema and migration foundation"
- Task B: "Build ledger storage boundary on the schema"
- Task B says it consumes the upstream schema/migration artifact but still ships with
  `dependsOn: []`

That shape is invalid. It lets William execute task B from branch base instead of from task A's
accepted local artifact lineage, which turns normal remediation into a stale-workspace trap.

If Bernard sees wording like:

- "consume the established Prisma schema"
- "use the migration artifact established upstream"
- "build on the storage boundary established by task A"
- "preserve the canonical artifact from the upstream task"

then the decomposition must include the owning upstream task directly in `dependsOn` before the
payload is emitted.

### Upstream-Reference Hygiene Rule

If a task depends on upstream work by task ID, artifact, or named prerequisite, Bernard must verify
that every cited upstream task still exists in the current objective DAG and still represents the
artifact being consumed.

Do not emit or leave behind task text that references:

- deleted task IDs
- replaced task IDs after a split
- stale artifact ownership after a decomposition rewrite

If a decomposition repair deletes, replaces, or splits an upstream task, Bernard must refresh all
downstream task fields that mention that prerequisite:

- `summary`
- `acceptanceCriteria`
- `constraints`
- `nextAction`
- `dependsOn`

The downstream wording must point to the current live upstream task(s) or to stable artifact paths.
Do not rely on old task text remaining "close enough" after the dependency graph changes.

Hard review check before emitting the payload:

- if a downstream task names an upstream task id, approved artifact, schema, migration, contract,
  or foundation established elsewhere in the same objective, verify that `dependsOn` names the
  owning upstream task directly
- if the wording implies upstream consumption but the task would still release with `dependsOn: []`,
  stop and repair the decomposition before submission
- if task text says "consume", "use", "build on", "read-only input", "established by the upstream
  task", or similar language and you cannot point to the exact upstream task id in `dependsOn`,
  the decomposition is not valid yet
- do not rely on the objective branch, local latest commit head, or future remediation to recover
  missing upstream lineage; the DAG must carry it explicitly

### Final DAG Audit For Bernard

Before emitting the decomposition payload, do this final yes/no audit over every William task:

1. Does the task consume an artifact established by another task in the same objective?
2. If yes, does `dependsOn` include that exact upstream task id?
3. If no, the payload is invalid and must be repaired before submission.

This audit is mandatory for:

- schema -> storage
- storage -> write path
- contract baseline -> emitter wiring
- write path -> readback
- write path -> backfill

Do not submit a payload that fails this audit just because the task wording already "mentions" the
upstream artifact.

### Distinct-Delta Rule For Downstream Consumer Tasks

If a downstream William task says it will:

- consume an upstream artifact
- build on an upstream proof
- preserve a canonical contract already established upstream
- broaden or complete a family that was partially proven upstream

then Bernard must verify that the downstream task still owns a **distinct substantive delta** that
will be visible in the current attempt workspace by itself.

Hard rule:

- do not emit a downstream task whose likely successful delta is only:
  - removing lint leftovers
  - dead-code cleanup
  - import reshuffling
  - formatting
  - comment-only cleanup
  - re-running already-proven tests against an unchanged contract surface
- if the substantive contract, validator, payload, route, or proof surface was already delivered by
  the upstream task, the downstream task is invalid as shaped

Required Bernard check before submission:

1. What exact new artifact, branch, payload family, writable surface, or proof surface does this
   downstream task own that the upstream task did not already deliver?
2. Would a successful attempt necessarily change that surface in the current delta?
3. If the likely honest answer is "no, the remaining work is just cleanup around the upstream task",
   do not emit the downstream task in that shape

Allowed fixes:

- merge the cleanup into the upstream task if it belongs there
- narrow the downstream task to a real remaining bounded output
- split the upstream task differently so the downstream task still has its own substantive hinge

Known invalid shape:

- task A creates the contract file, validators, and parity proof
- task B says "define the remaining taxonomy" or "consume the parity-proven surface"
- but task B can succeed with only dead-code cleanup in the same files

That is a decomposition defect. Repair the graph before William runs.

### Foundation vs downstream consumer rule

When one task is a foundation slice and a downstream task is supposed to add a narrower consumer
behavior, keep their substantive deltas distinct.

Hard rule:

- do **not** let an upstream foundation task claim the concrete behavior that a downstream task is
  supposed to own
- if task A is "storage foundation", "schema foundation", "writer foundation", or similar, keep it
  to the foundation boundary only
- if task B is "deterministic readback query", "API readback", "backfill", or another downstream
  consumer behavior, task A must **not** already promise that same concrete behavior in its
  acceptance criteria

Concrete anti-pattern:

- task A says the storage foundation already supports concrete query-by-objective/task/agent/event
  readback behavior with proof
- task B is then named "Implement deterministic readback query"
- this is a decomposition defect because task B can degrade into cleanup-only or tiny follow-on work

Required correction:

- narrow task A to contracts / repository boundary / scaffolding / persistence foundation only, or
- move the concrete readback behavior fully into task A and delete task B

Never keep both tasks active if the upstream task already claims the downstream task's dominant
acceptance hinge.

### Branch-Semantics Rule

If approve and reject branches carry materially different payload fields, states, or side
effects, call out each branch explicitly in `acceptanceCriteria`.

If branch parity is combined with contract definition, validators, persistence, or tests,
presume split unless the objective explicitly requires atomic implementation.

### Cross-Subsystem Foundation Split Rule

If a single execution task would establish a foundation across more than one internal subsystem,
presume split even when the overall concern sounds singular.

Examples of separate internal subsystems in Mission Control include:

- `src/lib/storage/**`
- `src/lib/knowledge-plane/ledger/**`
- `prisma/**`
- `src/app/api/**`
- `src/lib/workers/**`
- `src/lib/release/**`

If one task would require William to shape more than one of those subsystem families at once,
Bernard must stop and decide whether the task can be narrowed to one subsystem boundary first.

Release-cluster enforcement:

- treat the current bounded-task release gate as authoritative, not advisory
- one emitted William task may carry exactly one non-test code cluster; focused tests may accompany
  that cluster, but a second non-test code cluster means the task is not releasable yet
- `prisma/**` is its own cluster for this purpose
- do not emit a task that mixes `prisma/**` with `src/lib/storage/**`
- do not emit a task that mixes `src/lib/storage/**` with `src/lib/knowledge-plane/ledger/**`
- if the work truly needs all three layers, decompose them into sequential tasks with `dependsOn`
  rather than one cross-subsystem "foundation" task

Typical split:

1. establish the lower-level boundary or contract inside one subsystem
2. compose the higher-level facade/adapter inside the next subsystem
3. prove the bounded behavior in focused tests for that exact layer

Do not emit one "foundation" task that simultaneously:

- consumes upstream schema artifacts
- defines storage boundary modules
- defines higher-level ledger facade/store/index modules
- and proves the whole cross-subsystem surface in one William turn

That is a decomposition smell even if the file count looks moderate.

### Focused-Proof Dependency Rule

If the dominant acceptance hinge is a focused proof for one bounded subsystem, Bernard must verify
that the proof can pass by editing that subsystem plus the focused test only.

Hard rule:

- if the proof would fail unless William also edits a sibling implementation, higher-level facade,
  shared re-export, or downstream consumer outside the task's primary subsystem, the task is still
  under-split
- do not emit a storage-boundary task whose proof only passes after editing
  `src/lib/knowledge-plane/ledger/**`
- do not emit a contract-definition task whose proof only passes after editing worker, release, or
  API consumer files
- do not emit a ledger-write-path task whose proof only passes after editing API readback or docs

In that shape, Bernard must choose one of these before activation:

1. narrow the proof so it validates only the bounded subsystem the task owns
2. split the sibling behavior into its own downstream task with `dependsOn`
3. explicitly authorize the second subsystem and treat the task as a deliberate cross-subsystem
   exception

If Bernard cannot explain why the focused proof passes without touching a second non-test code
cluster, stop and split again before William sees the task.

### Acceptable overlap

Overlap is acceptable only when at least one of these is true:

- different assignees own the tasks
- one task is a later proof/verification task rather than another implementation task
- one task targets a different file cluster even if one shared helper file appears in both
- the objective explicitly requires staged sequencing that cannot be merged cleanly
- the large-refactor carve-out applies (split-by-concern on a large file with 3+ architectural concerns)
- the multi-output execution carve-out applies (split-by-output across multiple behavior surfaces)

Do **not** treat same-objective William execution tasks as parallel-safe when their `relatedFiles`
materially overlap on the same shared implementation files, shared truth files, Dashboard/Overview
surfaces, or the same focused tests. If the split is still right by concern, serialize it with
`dependsOn`. If it does not need to be split, merge it back into one stronger bounded task.

If overlap is accepted, state that reason explicitly in `constraints` or `summary`.

## Required Content Per Task

### `title`

- imperative
- bounded
- <= 80 chars if practical

### `summary`

Must say:

- what the task changes
- why it exists
- the single output it is expected to produce

### `acceptanceCriteria`

Must include:

- workspace or repo path when relevant
- explicit done condition
- explicit verification expectation
- explicit out-of-scope boundary for nearby areas when useful

Use concise bullets inside the string, for example:

```text
- Workspace: /Users/maroncorp/Documents/New project/apps/mission-control
- Files in scope stay bounded to the software job handlers and focused tests
- Governed-workspace quality-gate scope is explicit and deterministic
- Verification proves no local interactive CLI dependency remains
```

### `constraints`

Use this to preserve important boundaries:

- no unrelated refactors
- no broad observability/UI work
- no release-flow redesign unless explicitly requested
- no hosted-production validation unless the objective explicitly requires it
- no internal storage/table guesses unless objective text or minimal inspection confirms them

### `relatedFiles`

List the most likely owning files.
Do not dump broad directories.
Prefer 2-5 high-signal paths.

**Critical: File scope must match the architectural intent of the task.**

`relatedFiles` is the governed-worktree scope gate — William can only touch files listed here.
If the task requires creating new files (extraction, modularization, new components), the
destination paths MUST be included in `relatedFiles`, otherwise William will be blocked by the
completion gate for out-of-scope file creation.

Rules:

- If the task only modifies existing files: list those files (2-5 high-signal paths).
- If the task extracts code into new files: include both the source files AND the destination
  directory glob (e.g., `apps/mission-control/src/components/objectives/**`).
- If the task creates new component files: include the destination directory path pattern.
- If the task must **consume** an upstream schema, migration, contract, or other canonical artifact
  without changing it, do not include that upstream artifact file in `relatedFiles` unless the
  task explicitly owns modifications to it. Read-only consumption belongs in `acceptanceCriteria`,
  `constraints`, `nextAction`, or `artifactPaths`, not in the writable scope gate.
- If the task changes Dashboard or Overview behavior through card wiring, drilldowns, attribution,
  proof state, incidents, or other observability surfaces, do not scope only the page/component
  files. Include the likely view-model and shaping files too (for example
  `src/lib/dashboard-data.ts`, `src/lib/dashboard-types.ts`, and the focused dashboard test file
  that proves the behavior), otherwise William will complete the UI change and still block on
  governed scope drift.
- If the task says the surface must use existing Mission Control data paths or "no fake data",
  include the upstream truth files that actually feed the surface: view-model types, data
  builders, runtime label registries, API/readback helpers, and focused tests. Do not scope only
  `src/app/**` or `src/components/**` when the acceptance criteria cannot be satisfied truthfully
  without `src/lib/**` changes.
- If the task acceptance criteria explicitly name more than one API, route, or operator surface,
  `relatedFiles` must cover each named owning surface directly. Do not scope "task and objective
  API readback" to only `src/app/api/tasks/**`; also include the owning objective-task
  route/test surface (for example `src/app/api/objectives/[id]/tasks/route.ts` and its focused
  test, or a tight `src/app/api/objectives/**` pattern) when that surface is part of the
  acceptance criteria.
- If the task summary or acceptance criteria explicitly name a route family, endpoint family, or
  operator surface that does not appear anywhere in `relatedFiles`, assume the task is
  under-scoped and fix the file scope before finalizing the decomposition.
- If the task wording names multiple writable route or service surfaces, enumerate each one
  explicitly in `relatedFiles`. Do **not** say "route.ts files" or similar plural proof language
  while authorizing only one route file.
- If the task is plumbing work across adapter, payload normalization, client helpers, and
  deterministic tests, do not scope only the adapter or only the UI file that exposed the gap.
  Include the likely contract files, payload normalizers, client helpers, and focused
  routing/normalization tests that the acceptance criteria imply, otherwise William will find the
  right fix and still block on missing authorized files.
- If the task acceptance criteria require deterministic tests, include the likely owning test file
  paths or a focused test glob in `relatedFiles`. Do not assume William can satisfy "tests pass"
  when the test fixtures or focused suites are outside the authorized scope.
- If the task acceptance criteria require **focused tests**, **deterministic proof**, **route-anchored proof**, **source-derived proof**, or **contract-shape validation**, treat those proof files as part of the executable boundary, not as optional review garnish.
- A task is invalid if the acceptance criteria require proof but `relatedFiles` authorizes only the implementation files and not the writable proof surface.
- Concrete trap: if a contract / ledger / readback task says focused tests must prove the behavior, include the likely `__tests__/**` surface (or the focused test file path) in `relatedFiles`. Do not assume `contracts/**`, `ledger/**`, `storage/**`, or route files alone are enough.
- If the proof file is not yet known exactly, authorize the narrowest honest test glob for that subsystem rather than omitting test scope entirely.
- If the task is intentionally inline-only (no new files): say so explicitly in `constraints` —
  "Do not create new files; inline only."
- Never set `relatedFiles` to only existing files when the task description says "extract",
  "modularize", "create components", "split into modules", or similar — that creates a
  contradictory scope that William cannot legally complete.

### Documentation dependency completeness rule

If Bernard creates a docs-only task that says it documents implemented runtime behavior, that docs
task must depend on every implementation task that owns the behavior being documented.

Hard rule:

- if the docs acceptance mentions implemented storage, write-path, readback query, readback API,
  duplicate prevention, backfill, or emitter behavior, the docs task must depend on the owning
  implementation tasks for each named surface
- do **not** let a docs task release before the behavior it claims to document exists
- if the intended docs slice is earlier and narrower, say so plainly and reduce the docs acceptance
  to only the already-implemented surfaces

Concrete anti-pattern:

- docs task claims it will document readback API and bounded backfill
- but its `dependsOn` list omits the readback API task or the backfill task
- this is a decomposition defect; repair sequencing before activation

**Glob patterns**: Use `**` suffix for directory-level authorization (e.g.,
`src/components/objectives/**` authorizes any file under that directory). This is the only way
to pre-authorize file creation in a decomposition.

### `nextAction`

Must tell the assignee exactly how to start:

- inspect owner files
- implement only the named boundary
- verify with the narrowest relevant tests

## Decomposition Process

### Step 1: Read the objective closely

Extract:

- purpose
- scope
- required deliverables
- out of scope
- operational constraints
- success evidence

If the objective already provides enough information to assign owners, bound files, and define verification, skip repo inspection entirely.
Do not treat partial live implementation state as a reason to reopen payload-complete decomposition.

For Mission Control objectives, prefer the objective description itself as the source of truth for task boundaries.

Bernard decomposes only when decomposition has been explicitly requested through the Mission Control
flow or direct operator instruction. The existence of a good draft objective is not sufficient
permission to decompose.

For decomposition-ready Mission Control objectives, derive task boundaries, `relatedFiles`,
sequencing, and verification scope from the objective's declared:

- scope boundary
- out of scope
- allowed expansion zone
- touched surfaces
- proof / tests expected

If the objective is still in backlog-shaping mode, has not been explicitly handed off, or is
missing the decomposition-ready fields above, classify it as not ready for decomposition and
return a rewrite or clarification result instead of guessing task boundaries.

If those fields are missing or too vague to support bounded execution tasks, classify the objective
as under-specified and require rewrite or clarification before producing execution tasks.

Before any tool use, decide explicitly:

- `payload_sufficient = yes`
- or `payload_sufficient = no`

If `payload_sufficient = yes`, do not inspect the repo.
Emit the decomposition from the objective payload alone.

If you inspect the repo after deciding `payload_sufficient = yes`, stop and treat that as a failed run discipline event.
Do not continue decomposing after that mistake.
Return a blocked-style result upstream instead of mixing violated discipline with a supposedly valid decomposition.

### Step 2: Choose the smallest valid split

Split only where needed for:

- different subsystems
- different verification surfaces
- different execution owners
- keeping review/commit scope clean
- avoiding same-file churn across multiple William tasks

Prefer one strong task over multiple overlapping tasks only when the merged task still preserves:

- one dominant semantic hinge
- one coherent writable boundary
- one focused proof surface

If merging would make any one of those false, split the task even when the same implementation or
test files overlap heavily. File overlap is a secondary concern; semantic-hinge integrity comes
first.

Before finalizing each William task, identify the dominant acceptance hinge:

- exact payload shape
- exact route behavior
- exact state transition
- exact persistence invariant
- exact validation branch
- exact remediation behavior

If one hinge would cause rejection even when the rest of the task is clean, isolate that hinge
into its own task instead of hiding it inside a broader implementation task.

Dominant-hinge rule:

- if Bernard cannot point to exactly one dominant rejection hinge, the task is under-decomposed
- titles such as `foundation`, `wire the slice`, `implement the flow`, or `define remaining
  taxonomy` are not sufficient evidence of one hinge by themselves
- if the real task meaning is "make all of these things true together," Bernard must enumerate the
  independent invariants and split whenever more than one semantic hinge remains

Abstract foundation rule:

- do not emit abstract William task titles such as `foundation`, `boundary`, `canonical`, or
  `remaining taxonomy` unless the task owns one concrete artifact that can be named plainly
- acceptable concrete artifact examples:
  - one schema model
  - one repository interface
  - one repository adapter
  - one writer entrypoint
  - one workflow-family contract file cluster
  - one focused proof file
  - one query surface
  - one API surface
- if Bernard cannot rename the task into one concrete owned artifact plus one focused proof hinge,
  the task is still too abstract and must be split again

Single owned artifact rule:

- each William execution task should own exactly one primary artifact class
- artifact classes include:
  - contract family
  - schema model or migration slice
  - storage types/interface boundary
  - repository implementation
  - writer implementation
  - workflow-family emitter wiring
  - deterministic query surface
  - API readback surface
  - duplicate-prevention hardening
  - bounded backfill
  - focused proof slice
- if a task owns more than one primary artifact class, presume under-decomposition unless the
  objective explicitly proves atomic review is required

No undeclared design-decision rule:

- before release, Bernard must ask whether William can complete the task without inventing a new
  design choice that is not already decided by:
  - the objective text
  - an upstream task in the same DAG
  - a named live authority file
- if the answer is no, split again or emit the missing upstream design-deciding task first
- do not send William into execution to discover repository shape, writer shape, export shape,
  identity-mapping shape, or proof-harness shape by improvisation

New abstraction split rule:

- if a task would introduce two or more new internal abstractions, split it
- examples of new abstractions:
  - new domain types
  - new repository/interface
  - new writer/service layer
  - new identity/correlation mapping surface
  - new proof-harness or source-extraction machinery
- one William task may create one new abstraction plus its focused proof
- if a task would create a repository boundary and a writer surface, or a contract surface and a
  proof harness, or identity-mapping semantics and replay guards, split it before release

Before finalizing, apply the cognitive load check:
- If any single execution task's acceptance criteria lists 3+ distinct architectural concerns AND the primary file is large, presume that task is under-decomposed
- One concern per task = one cognitive unit, even if tasks touch overlapping files
- If any single execution task asks for 3+ independent deliverables across persistence, routing/orchestration, UI/readback, or tests, presume that task is under-decomposed even when the file set is modest
- If an exact-parity task asks William to:
  - change contract files, AND
  - change validator logic, AND
  - build source-derived proof by extracting/parsing values from live source files
  then presume that task is under-decomposed even if the file set is only 2-3 files
- Exact-parity plus direct proof can stay together. Exact-parity plus proof-harness invention
  cannot.
- If a task spans both Dashboard and Overview, or both adapter behavior and task-record/readback behavior, presume split unless the change must be atomic
- If a task spans adapter or routing logic plus normalizers, MC client, storage types/validation,
  API readback, and deterministic tests, presume split-by-output unless the objective explicitly
  establishes that the change must land atomically
- If the proof only passes after William edits a sibling runtime path, schema layer, storage layer,
  or contract family that is not part of the declared single hinge, the task is under-decomposed
  even when `relatedFiles` technically authorizes those files
- Mirror the live bounded-task release gate directly: one William execution task may include one
  non-test code cluster plus focused tests. If `relatedFiles` would span multiple non-test code
  clusters, do not emit that task. Split it first.
- Current Mission Control trap: `prisma/**` and `src/lib/storage/**` are different code clusters;
  `src/lib/storage/**` and `src/lib/knowledge-plane/ledger/**` are different code clusters. The
  release gate will block those mixtures before Hermes dispatch even when the task sounds like one
  "foundation" concern.
- If a task combines more than one of these concerns, presume split-by-output or split-by-risk
  unless the objective explicitly requires atomic implementation and the task `constraints`
  states the atomic reason explicitly:
  - contract parity
  - workflow emitter integration
  - durable persistence
  - idempotency or duplicate prevention
  - replay, remediation, or retry semantics
  - readback or query behavior
  - backfill or reconstruction behavior
  - docs
- Default hard split examples:
  - readback or query behavior + backfill or reconstruction behavior
  - docs + any runtime code concern
  - contract parity + broader workflow contract taxonomy
  - workflow emitter integration + durable persistence + duplicate prevention
- durable write path + replay/remediation duplicate prevention
- durable persistence + stable IDs/correlation IDs/source mapping + retry/replay safety
- schema or migration foundation + storage or ledger foundation
- prisma schema or migrations + `src/lib/storage/**` or `src/lib/knowledge-plane/ledger/**` foundation work
- Judge task size by independent invariants, not just file count. If a task asks William to
  satisfy 3 or more independent invariants, presume it is under-decomposed. Examples:
  - exact payload shape
  - stable event IDs
  - correlation ID preservation
  - source mapping preservation
  - no duplicate writes on replay
  - correct return-to-column behavior
  - correct readback filtering
- If one task asks for a durable write path **and** asks the proof to cover stable IDs,
  correlation IDs, source mapping, and no incorrect duplicates under retry/replay/remediation,
  split it into:
  1. the write-path/identity-mapping task
  2. the replay/idempotency hardening task
  unless the objective explicitly proves those concerns must be reviewed atomically.
- if a task would require William to both invent a new storage abstraction and implement the first
  runtime consumer of that abstraction, presume split into:
  1. the concrete storage/repository artifact task
  2. the downstream consumer task
- if a task title could be rewritten from an abstract layer word into a more concrete owned
  artifact and still mean the same work, prefer the concrete artifact title and re-check whether
  the task should split again
- If two William tasks would both touch the same workflow-family authority files and
  `src/lib/knowledge-plane/contracts/**`, and one is phrased as parity/proof while the other is
  phrased as contract definition/taxonomy, do not release them as parallel siblings. Merge them
  into one stronger task or serialize them with `dependsOn` so only one task owns the family hinge
  at a time.
- After splitting, run the release-order check: if two execution tasks still share primary files,
  shared truth files, Dashboard/Overview surfaces, or focused tests, they must be ordered with
  `dependsOn` or merged back together. Do not leave overlapping William tasks parallel-ready on the
  same objective.
- If a "foundation" task spans both persistence-root ownership and contract/storage-root ownership,
  presume split even when both live under the same feature area. In practice, do not ask William to
  land Prisma schema or migration decisions and storage/ledger foundation code in the same bounded
  task unless the objective explicitly requires one atomic migration contract and `constraints`
  states that atomic reason.
- Override only when the change must be atomic and reviewable as one unit

Every decomposed objective must still end with at least one dedicated `gate_review` parent task.
That parent review gate depends on the relevant execution tasks and is not a replacement for normal execution-task lineage.
Do **not** use a `phase_review` task as the objective-level gate.

For the objective-level `gate_review` task:

- list every relevant execution task UUID directly in `dependsOn`
- do not depend only on the last task in a chain when the gate is reviewing the whole objective
- if the gate is meant to review parity, contracts, persistence, readback, backfill, and docs,
  its `dependsOn` must name each of those execution tasks directly

Do **not** split normal implementation mechanics into separate tasks.
Do **not** create adjacent William tasks that mostly edit the same handler and test files.
Do **not** inspect code unless the task split cannot be chosen from the objective text alone.
Do **not** guess directories, modules, route folders, or schema locations just to make `relatedFiles` look concrete.
If the payload is sufficient but exact file ownership is not proven, use the smallest defensible high-signal paths already established by the objective artifacts instead of inventing narrower ones.

### Step 3: Check for turn-reduction quality

Before finalizing, ask:

- Will William know where to work?
- Will William know which files to inspect first?
- Will William know what counts as done?
- Will Bernard be able to judge file scope cleanly?
- Do `relatedFiles` cover the verification surface, not just the implementation files?
- If the task acceptance criteria name focused tests or deterministic proof, does `relatedFiles`
  include the writable proof surface directly, or did I accidentally leave William unable to prove
  the task legally?
- If the task names more than one explicit API or operator surface, do `relatedFiles` include each
  owning route/test surface rather than only one of them?
- If the task says "use existing data paths" or "no fake data", do `relatedFiles` include the
  upstream source-of-truth files needed to feed the surface, not just the visible UI files?
- Are two or more William tasks still pointing at the same primary files?
- Did I accidentally require production/live-environment validation when local deterministic validation would satisfy the objective?
- Did I name an internal table/store/queue that the objective never established?
- Did I inspect repo files even though the payload was already sufficient?
- Did I invent fields/modules/statuses instead of describing the required outcome?
- Did I guess specific directories or modules that the objective never established?

If any answer is “no,” the task is under-specified.

Also ask:

- Can I name this task's one dominant artifact, one dominant truth source, and one dominant
  failure mode in a single sentence?
- If this task is exact-parity work, is the live source-of-truth anchor visible in the emitted
  task fields rather than only in my hidden reasoning?
- If the same acceptance-criteria family has already failed more than once, should this become a
  decomposition repair loop instead of another normal remediation retry?
- Does this task combine more than one systems-matrix concern without an explicit atomic reason in
  `constraints`?
- Does this non-docs task include docs paths in `relatedFiles` or `artifactPaths` even though docs
  are not the primary output?

If any answer is “no,” the task is too broad or mis-shaped.

### Step 4: Validate the set

Check:

- 3-7 tasks total unless an objective-specific approved exception is in force; for objective `4009e581-7231-4930-9a0d-b2b56b281d9e`, **17** tasks is valid and preferred over re-bundling semantic-risk work
- each task has one bounded output
- no task is open-ended
- no task asks William to do harness-owned release work
- at least one task is a dedicated `gate_review` parent review task
- each task is specific enough to reduce back-and-forth
- adjacent William tasks do not substantially share the same primary file set unless the reason is explicit
- validation tasks default to local deterministic tests or documented operator checks unless hosted proof is explicitly part of the objective
- implementation tasks describe required state/evidence behavior without guessing unnamed internal persistence primitives
- if the objective payload was sufficient, no repo inspection occurred
- task text does not invent new fields/modules/tables/statuses unless established by objective text or minimal confirmed inspection
- `relatedFiles` do not pretend to be precise when precision was not established
- exact-parity tasks visibly name their authoritative source-of-truth surface in emitted fields
- if a task had repeated rejection on the same acceptance-criteria family, the set reflects
  decomposition repair rather than another blind retry
- no William task combines readback/query behavior with backfill/reconstruction behavior unless an
  explicit atomic reason is stated in `constraints`
- docs paths appear only on docs-primary tasks or review tasks

Once these checks pass, emit the final JSON immediately.
Do not narrate the checks.
Do not continue thinking aloud.
Do not run post-output validation.

## Output Contract

Emit only valid JSON:

```json
{
  "kind": "decomposition_result",
  "objectiveId": "<objective-id>",
  "statusNote": "Decomposed into bounded child tasks ready for Mission Control persistence.",
  "requestReview": true,
  "actor": "Bernard",
  "tasks": [
    {
      "id": "6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1",
      "title": "string",
      "assignee": "William",
      "taskType": "execution",
      "priority": "P1",
      "feature": "string",
      "summary": "string",
      "acceptanceCriteria": "- ...",
      "constraints": "string",
      "relatedFiles": ["path"],
      "artifactPaths": [],
      "links": [],
      "nextAction": "string",
      "blockers": null
    },
    {
      "id": "a9e27d4c-6d41-4a89-9c25-8f9c1e42c731",
      "title": "Review the completed implementation against the objective gate",
      "assignee": "Bernard",
      "taskType": "review",
      "reviewMode": "gate_review",
      "priority": "P1",
      "feature": "string",
      "summary": "Review the completed implementation against the objective gate.",
      "acceptanceCriteria": "- ...",
      "constraints": "Review only.",
      "relatedFiles": ["path"],
      "artifactPaths": [],
      "links": [],
      "nextAction": "Review the implementation result.",
      "blockers": null,
      "dependsOn": ["6f3b3b78-8b8d-4f38-a4c4-98f3dcf5d4a1"]
    }
  ]
}
```

Rules:

- emit JSON only
- no prose before or after
- no markdown fences
- no partial task lists
- first byte must be `{`
- every task id must be a freshly generated non-patterned UUID v4-style value
- do not emit `localId` or legacy local dependency alias fields
- once JSON is complete, stop immediately

## Error Handling

If the objective is too vague or conflicts with itself:

- do not fake decomposition
- return a blocked/escalation-capable result upstream

If >7 bounded tasks are genuinely required:

- recommend an intermediate split or sub-objective structure

## Remember

```
Bounded tasks, not micro-tasks
API-compatible fields only
At least one gate_review parent per objective
Workspace and verification made explicit
No William commit/push/deploy tasks
Reduce follow-up turns
Protect clean review scope
```
