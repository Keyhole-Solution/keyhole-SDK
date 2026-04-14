# Context

This directory supports governed context lifecycle workflows.

## Structure

- `requests/` — Local staging area for context request artifacts
- `resolved/` — Resolved context references or summaries

## Important

Governed execution requires explicit governed context. This directory
prepares the repo for later context-bound runs.

This scaffold does **not** perform context compilation. Context will be
compiled through `keyhole context compile` in a later workflow.
