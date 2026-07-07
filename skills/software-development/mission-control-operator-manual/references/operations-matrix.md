# Mission Control Operations Matrix

Use this matrix to choose the right tool or skill quickly.

## Health and baseline truth

- Check app health:
  - `GET /api/health`
- Check Hermes health:
  - `GET /api/hermes/health`
- Confirm repo truth:
  - `git fetch origin main --prune`
  - compare to deployed `commitSha`

## Record operations

Use `mission-control-records` for:

- create objective
- update objective
- create task
- update task
- decompose objective
- verify record persistence

## Delegation

Use `task-handoff` for:

- assignment shaping
- board-anchored delegation
- evidence requirements
- escalation rules

## Release / deploy

Use `mission-control-railway-deploy` for:

- objective release actions
- deploy investigation
- manual Railway inspection
- release verification expectations

## End-to-end regression

Use `mission-control-e2e-canary` for:

- disposable proof run
- zero-touch release validation
- Phase readiness checks

## Cleanup

After disposable runs, always remove:

- disposable app change from `main`
- MC objective/task residue
- Hermes task residue
- governed workspace residue

## Escalate immediately if

- repo truth and deployed truth differ for release-sensitive work
- any code task uses `scratch`
- merged SHA and deployed SHA differ
- operator had to re-arm a task in a workflow that should be zero-touch
- MC record write and readback disagree
