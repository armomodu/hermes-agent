---
name: mission-control-operator-manual
description: |
  Operator manual for Mission Control. Use when the work involves live Mission Control health checks,
  objective and task administration, release actions, workflow regression canaries, cleanup, and
  escalation across Mission Control, Hermes Kanban, and machine release flow.
---

# Mission Control Operator Manual

Use this skill as the top-level operator manual for Mission Control.

This is not the deep implementation reference. It is the live operating contract:

- what Mission Control owns
- what Hermes owns
- what machine release flow owns
- what the operator should do directly
- which specialist skill to invoke for each class of operation
- when to stop and escalate

## Read order

Read these in order:

1. `~/Documents/New project/apps/mission-control/docs/product-contract.md`
2. `~/Documents/New project/apps/mission-control/docs/README.md`
3. `~/Documents/New project/apps/mission-control/DEPLOY.md`
4. `references/operations-matrix.md`

There is no repo-local `manual-handoff-mc-work-lifecycle.md` anymore. Treat any reference to it as stale.

Use these specialist skills instead of improvising:

- `mission-control-records`
  - create, update, decompose, verify objectives/tasks through the live API
- `mission-control-e2e-canary`
  - disposable full workflow regression canary
- `mission-control-railway-deploy`
  - release/deploy procedure and manual fallback inspection
- `task-handoff`
  - structured delegation and board-anchored assignments

## System ownership

### Mission Control

Mission Control is the source of truth for:

- objectives
- tasks
- release state
- review state
- commit / PR / deploy evidence
- closeout

### Hermes Kanban

Hermes is the live agent execution plane:

- William executes
- Bernard reviews
- Bernard decompose tasks may run there

### Machine release flow

Machine jobs own deterministic release work:

- `ensure_objective_branch`
- `git_commit`
- `git_push`
- `create_pr`
- `merge_pr`
- `deploy_railway`
- `release_verify`

Important rule:

- the operator manages and verifies the flow
- the operator does not manually impersonate William or Bernard work

## Daily operator baseline

Before changing workflow state, check factory status from fresh reads.

Recommended read set:

```bash
curl -sS https://app.maroncorp.com/api/health
curl -sS https://app.maroncorp.com/api/hermes/health
curl -sS https://app.maroncorp.com/api/overview
curl -sS https://app.maroncorp.com/api/queue/dashboard
curl -sS https://app.maroncorp.com/api/inbox
```

What to verify:

- `GET /api/health`
  - `status=ok`
  - `dirty=false`
  - deployed `commitSha` known
- `GET /api/hermes/health`
  - `status=healthy`
  - `mappingCount=0`
  - `syncErrorCount=0`
  - adapter lease `active=true`
- `GET /api/overview`
  - runtime components healthy
  - reconciliation `clean`
- `GET /api/queue/dashboard`
  - queue state and worker status are current
- `GET /api/inbox`
  - active operator attention is understood before intervention
- local repo truth:
  - `git fetch origin main --prune`
  - `git rev-parse origin/main`
  - local target branch SHA or release worktree SHA when relevant
  - release-sensitive readiness uses fresh SHA checks plus the reconciliation verifier, not raw exact-SHA parity assumptions

If repo truth and deployed truth diverge, do not start a canary or release workflow until aligned.

## Mutation auth rule

All Mission Control mutation endpoints require authentication.

Accepted auth paths:

- browser admin session
- `Authorization: Bearer <CRON_SERVICE_TOKEN>`

Anonymous mutation success is a product defect.

## Release-main reconciliation rule

For keeper changes to the deployable app source:

1. commit the keeper change in `release-main`
2. reconcile that change into `main` in the same work session
3. push `main` to `origin/main`
4. run the pipeline reconciliation verifier
5. publish the fresh verifier result to Mission Control immediately
6. call the pipeline clean only if the verifier reports `clean` and the publish step succeeds

Important:

- verify content parity, not exact commit-SHA parity
- reconciliation may use cherry-pick or a follow-up reconciliation commit
- `release-main` is deploy authority, not a long-lived divergent branch
- the Overview page displays the published verifier result in `Release provenance > Build identity`; it does not compute the result itself and should not wait for the periodic bridge tick after deploy closeout
- Dashboard and Overview must treat missing published reconciliation as `unknown` / `awaiting snapshot`, not as release drift; drift is only when the published verifier result is actually `out_of_sync`
- when work touches Mission Control `Dashboard`, `Overview`, or shared frontend shell behavior, use `apps/mission-control/docs/mission-control-design-contract.md` as the frontend contract before changing the UI

## Canonical Railway deploy rule

For Mission Control product deploys, the default operator path is the canonical wrapper from `release-main`:

```bash
RAILWAY_CONFIRM=1 ~/.hermes/scripts/railway-deploy.sh production
```

Required behavior:

- deploy source must be `release-main`
- use the wrapper, not ad hoc `railway link`, raw `railway up`, or local linked-project state as the normal path
- let the wrapper handle:
  - Hermes env loading
  - Railway token injection
  - staged deploy context
  - per-service deploy submission
  - deployment polling
  - live `/api/health` verification

Required verification before continuing canary or release-sensitive work:

- wrapper finishes without error
- `GET https://app.maroncorp.com/api/health` reports the expected deployed SHA
- only then reconcile/sync branches and continue the workflow

Operator stop rule:

- if the current Hermes/TUI session is already carrying long-running background pollers, repeated websocket stalls, or detached deploy processes, do not stack more ad hoc deploy commands into the same session
- stop, start a clean turn or shell, and run the canonical wrapper once

## Stale-truth guard

No release-sensitive blocker claim may be made from memory, stale snapshots, prior rollout notes, or old task context.

Before claiming any of these:

- live is behind
- baseline is blocked
- canary cannot start
- deploy must happen first
- Git and cloud are diverged

you must run fresh checks in the same turn and report the exact observed values:

- `GET https://app.maroncorp.com/api/health`
- `git fetch origin main --prune`
- `git rev-parse origin/main`
- local target branch SHA or release worktree SHA when relevant

Required behavior:

- print the exact SHAs you observed before concluding there is drift
- if current-turn checks were not run yet, say `unverified, need fresh preflight`
- do not say `blocked` until the fresh checks prove the mismatch

## Normal operating modes

### 1. Objective and task administration

Use `mission-control-records`.

Do:

- create objectives
- update objectives
- trigger decomposition
- create or update tasks through the live API
- verify persisted state by reading it back
- ensure decomposed objectives include at least one dedicated `gate_review` review task
- set explicit `reviewMode` on standalone review tasks

Do not:

- write directly to storage
- fake task lifecycle jumps without verifying records
- create standalone review tasks with implicit or missing `reviewMode`
- use `blockedBy` in API calls; the canonical field is `dependsOn`

Objective creation guardrails:

- create decomposition objectives with a decomposition-eligible owner such as `Bernard`
- do not use `owner=Dolores` when `needsDecomposition=true`
- objective `description` is required on create
- if `reviewReady` remains `true` after decomposition approval, clear it before `draft -> ready`
- if an objective needs decomposition, do not set `approved=true` before Bernard completes the decomposition and the `review-objective` item exists
- if that approval happened too early, reset `approved=false` while preserving the decomposition review state so the review handoff can surface again
- do not pre-decide task counts in the objective brief; Bernard owns task granularity during decomposition
- if the objective implies extraction, modularization, new files, or multiple operator surfaces, the objective description plus `artifactPaths` or `links` must name the allowed expansion zones and implementation boundaries up front so Bernard can shape `relatedFiles` correctly
- if the objective targets a large file cluster or 3+ distinct architectural concerns, expect split-by-concern decomposition and flag under-decomposition during review instead of approving one broad William task

### 2. Delegation and assignment shaping

Use `task-handoff`.

Do:

- define clear scope
- anchor work to `objectiveId` / `taskId`
- state evidence expectations
- define escalation rules

Quality-gate rule:

- normal code-quality failures (`software_test`, `software_lint`, `software_build`) stay inside the William/Bernard task loop
- they are not operator inbox exceptions
- operator intervention is for runtime, release, decomposition review, or real system blockers

Inbox-native execution rule:

- assignment can mean `ownership only` or `auto-run`
- current spawn-eligible operator exception items are:
  - `review-objective` when assigned to a decomposition-approval-authorized agent; currently `Dolores` only
  - `objective-pr-open`
  - `objective-deploy-verify`
  - `escalated-objective`
  - some `escalated-task` items when they are runtime or release-operation blockers
- every inbox-native spawned run must end by emitting one exact machine-readable line:
  - `MC_INBOX_RESULT={...}`
- if that line is missing or malformed, the bridge marks the inbox work failed even if the agent did useful repo or browser work
- the failure is expected to include actionable runner context from stdout/stderr tail so operators can diagnose runner-contract misses directly from Mission Control
- ordinary William execution, Bernard review, Bernard decomposition, and William remediation must remain task-native

### 3. Release progression

Use `mission-control-railway-deploy` for the release contract and CLI fallback details.

Normal release shape:

1. objective is `active`
2. reviewed work is committed locally
3. objective release flow opens PR
4. merge is the intended manual release action
5. deploy and verify are automatic

Do not:

- treat task `done` as released
- treat merged PR as verified deployment
- trust a green build alone without live-route verification

Release verification rule:

- `release_verify` passes on exact match or ancestor inclusion
- do not treat an earlier objective as failed only because a newer deploy advanced the live SHA
- the verify verdict is tri-state:
  - `deployed`
  - `not_deployed`
  - `unknown`
- when verify fails, distinguish a real `not_deployed` release problem from an `unknown` repo/fetch/ref-state problem before escalating

Deploy-timeout rule:

- a Railway submission timeout is not automatic proof that deploy failed
- if an objective is still `deploying`, check whether `deploy_railway` recovered by finding and polling the real Railway deployment
- only escalate after checking the actual deploy task result and whether `release_verify` was created

Merge-conflict rule:

- same-file merge conflicts are normal Git conflicts, not inbox-runner failures
- keep the resolution inside the existing reviewed remediation and retry path
- do not invent a parallel merge-conflict execution loop

### 4. End-to-end regression proof

Use `mission-control-e2e-canary`.

Use it when:

- validating workflow readiness
- checking zero-touch release behavior
- proving a fix across the three planes

Current coverage:

- live-proof checkpoints:
  - decomposition pickup and review handoff
  - activation and promotion
  - execution and review loops
  - `gate_review` remediation loop
  - release handoff and machine release chain
- healthy/clean validation only:
  - runtime preflight truth
  - sync-error cleanliness
  - pipeline reconciliation
  - cleanup residue closeout

Do not use an ad hoc canary procedure when the skill already covers it.

## Runtime observability and recovery

Sync errors:

- use `GET /api/hermes/sync-errors` for active recoverable failures
- operator actions are `retry`, `reset`, and `dismiss`
- the control-plane route is `POST /api/hermes/sync-errors`
- required body fields are:
  - `action`
  - `phaseRunId`
  - `actor`
- use `dismiss` only for stale residue that should leave active surfaces without replay
- stale orphan residue may auto-retire through the adapter sweep
- `review_decision_rejected` usually means MC rejected the review-decision POST because matching remediation evidence was not available yet or the remediation was a no-op
- deleting the underlying stale canary tasks/objectives retires the associated sync residue
- deleting or archiving an objective should also retire linked machine/release tasks when those tasks are attached through `machinePayload.sourceObjectiveId`, not just direct `task.objectiveId`

Active mappings:

- `mappingCount > 0` is not automatically a bug
- use the Overview active-mapping drilldown to identify the exact MC task and Hermes task still mapped
- treat the Overview drilldown as evidence/observability and Dashboard as the command cockpit; do not redesign those surfaces without first checking the design contract
- the operator action paths are:
  - `Open Task`
  - `Open Inbox` when the mapping points to operator attention
- the drilldown is observability, not Inbox

Phase review retries:

- same-task `phase_review` rejection stays inside the same task lineage
- reject 1-2 resets the execution task to a fresh William retry attempt with Bernard's review feedback attached
- reject 3 stops the retry loop and escalates through the blocked/escalated path
- do not treat reject 1-2 as an operator Inbox exception unless current truth shows the retry path itself failed

## Objective lifecycle rules

Key statuses:

- objective work lifecycle:
  - `draft`
  - `ready`
  - `activating`
  - `active`
  - `completed`
  - `archived`
- release lifecycle:
  - `not_started`
  - `in_build`
  - `pr_open`
  - `deploying`
  - `released`
  - `blocked`

Important distinctions:

- task `done` is not release completion
- PR merged is not deploy verification
- objective `completed` is only valid after deployment verification passes

Activation sequence:

1. set `approved=true`
2. move objective `draft -> ready`
3. move objective `ready -> active`

Do not skip `ready`. The API enforces that `active` may only come from `ready` or `activating`.

## Stop and escalate conditions

Stop and treat the issue as a workflow defect if any of these occur:

- `origin/main` does not match the deployed baseline before a release-sensitive workflow
- the pipeline reconciliation verifier reports `out_of_sync`
- code execution or review lands in `scratch`
- activation needs manual branch repair
- commit, PR, or deploy needs manual task re-arming during a zero-touch validation run
- deploy verification fails under the current exact-or-ancestor rule
- write succeeds but record readback is wrong
- Hermes health shows non-zero mapping/cleanup residue after a supposedly complete run

When you stop:

1. capture exact record ids
2. capture the observed state mismatch
3. do not paper over it with silent operator overrides

## Cleanup discipline

After any disposable proof run:

1. remove the disposable app change from `main`
2. deploy the cleaned commit
3. delete/archive matching Mission Control objective and tasks
4. purge matching Hermes task rows and governed workspace residue
5. verify public health and Hermes health are clean

Important:

- objective cleanup now covers linked machine/release tasks discovered through `machinePayload.sourceObjectiveId`
- completed or archived objectives should not leave residual active non-terminal child-task noise on board/read-model surfaces
- valid done/history task records remain legitimate evidence and should not be treated as cleanup drift
- if release or quality artifacts remain active after objective delete/archive, treat that as cleanup drift to investigate, not expected residue

Cleanup is part of the operator contract, not an optional extra.

## Output format

When acting as the operator, report in this order:

1. current verdict
2. exact ids
3. current state mismatch or success proof
4. whether manual intervention occurred
5. next operator action

Be blunt. Do not pad status reports.
