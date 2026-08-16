# Bernard Decompose Runtime Skill Mirror

This directory is the tracked source mirror for the Mission Control decomposition skill installed
for every profile authorized to own decomposition, including Bernard and Maeve:

- `~/.hermes/profiles/{bernard,maeve}/skills/bernard-decompose/`

It exists because the active runtime skill is currently profile-local and not tracked elsewhere in this repository.
The mirror is for source control, review, and sync only; live workers read their profile-local copy.

The compact manifest builder accepts canonical `plan` input and generates the ordered
`executionPlan`. The validator re-expands the current manifest and rejects stale generated output,
so correction rounds cannot certify a graph from a different manifest revision.

The bounded `scripts/submit_decomposition.py` helper performs the single authenticated Mission
Control submission without shell file-to-network plumbing. The normal live path invokes it through
`complete_decomposition.py`, which verifies checkpointed artifact digests and performs submission,
acceptance, and Hermes completion as one idempotent final action.
