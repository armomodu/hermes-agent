# Bernard Decompose Runtime Skill Mirror

This directory mirrors the live local Bernard Mission Control decomposition skill from:

- `~/.hermes/profiles/bernard/skills/bernard-decompose/`

It exists because the active runtime skill is currently profile-local and not tracked elsewhere in this repository.
The mirror is for source control, review, and sync only; the live Bernard gateway still reads the profile-local copy.

The compact manifest builder accepts either the concise `plan` input or a complete ordered
`executionPlan`. Explicit execution plans are preserved unchanged so correction rounds and
amendments do not lose Bernard's validated execution sequence.

The bounded `scripts/submit_decomposition.py` helper performs the single authenticated Mission
Control submission without shell file-to-network plumbing, so validated graphs are not stranded
behind terminal approval.
