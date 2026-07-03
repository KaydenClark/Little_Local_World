# Local Agent Town - Bootstrap Checklist

Use this file when adopting or refreshing the workbench structure for this project.

## Before Editing

- Confirm the target project root is `E:\GPTCode\local-agent-town`.
- Check version-control status when the project is inside a git repo.
- Read `AGENTS.md`, `BLUEPRINT.md`, `ROADMAP.md`, and `RUNBOOK.md`.
- Identify files that may contain secrets, private data, local databases, dumps, or generated output.
- Decide whether the task is project bootstrap, feature work, or verification repair.

## Existing Project Path

Inventory before changing templates:

- Source layout and app entry points.
- Runtime and package metadata.
- Install, run, test, and smoke-check commands.
- Environment variables without exposing secret values.
- Current docs that appear stale or contradicted by code.
- Generated files and folders agents should not edit.
- Known fragile areas and likely verification gaps.

Then keep current:

- `AGENTS.md` read scope, edit scope, stop conditions, and proof rules.
- `BLUEPRINT.md` project identity, architecture, contracts, data model, invariants, and risks.
- `ROADMAP.md` current state, current goal, next tasks, blockers, and verification log.
- `RUNBOOK.md` exact setup, run, test, recovery, and troubleshooting commands.

## New Project Path

Define before scaffolding:

- MVP goal.
- Primary users.
- Non-goals.
- Stack choice and why it is the smallest reasonable option.
- Persistence needs.
- External service needs.
- Verification plan.
- Ownership and maintenance expectations.

Then create the smallest runnable vertical slice and document:

- setup command;
- local run command;
- test command;
- smoke check;
- known limitations.

## Completion Gate

Adoption is not complete until:

- required placeholders have been replaced or deleted;
- `AGENTS.md` has real read and edit scope;
- `RUNBOOK.md` has exact commands or named reasons commands do not exist;
- `ROADMAP.md` has a current verification log entry;
- `BLUEPRINT.md` reflects the actual project, not a desired future state;
- `scripts\validate-workbench.ps1` passes.
