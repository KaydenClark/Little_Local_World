# Local Agent Town - Unattended Work Policy

Use this policy when an agent is allowed to work without immediate human supervision.

## Runtime Limits

- Default maximum unattended runtime: 60 minutes.
- Stop sooner if the agent reaches a stop condition, repeated failure, unclear verification, or scope expansion.
- For longer work, create a checkpoint and ask for approval before continuing.

## Checkpoints

Create a checkpoint:

- before broad edits;
- before dependency changes;
- after 30 minutes of work;
- after verification passes;
- before handoff.

Each checkpoint should record:

- current goal;
- files changed;
- verification run;
- known risks;
- next action.

## Branch Rules

- Create a dedicated branch for non-trivial work when the project is in git.
- Do not overwrite, reset, discard, or force-push user work unless explicitly asked.
- Inspect git state before editing when git metadata exists.
- Keep unrelated dirty files untouched.
- Do not commit secrets, local databases, generated dumps, `.venv`, or private exports.

## Stop Conditions

Stop and ask before:

- destructive filesystem actions;
- production data access or mutation;
- paid service creation;
- external deployment;
- auth, permission, or secret changes;
- database migrations;
- large dependency upgrades;
- architecture rewrites;
- continuing after repeated verification failures.

## Final Audit

Before handoff, verify:

- required files are present;
- placeholders are removed from adopted docs;
- changed files are scoped to the task;
- verification evidence is recorded;
- risks and blocked items are explicit;
- commands for inspection are provided.
