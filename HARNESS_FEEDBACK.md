# Local Agent Town - Harness Feedback

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

This is the return channel from this project back to the LLM Workbench harness.
When the control docs themselves (`AGENTS.md`, `BLUEPRINT.md`, `TASKBOARD.md`,
`RUNBOOK.md`, `GENESIS.md`, `ADOPTION.md`) are unclear, wrong, missing guidance,
or actively slow the work down, record it here instead of silently working around
it. The owner carries these lessons back to LLM Workbench, where a change is
validated against `evals/` before it ships as "better".

This log is append-only. Do not edit or delete prior rows; add a new one.

## How To Log

Add a row whenever the harness (not this project's own code or docs) caused
friction or could be improved. Name the doc and section, say what happened, and
propose a change if you have one.

| Date | Doc / section | What happened | Impact | Proposed change | Status |
|---|---|---|---|---|---|
| 2026-07-02 | ADOPTION.md -> Phase 0 / Guardrails | "Never migrate on a dirty tree" and "branch from a clean commit" assume the agent can run git writes. In a sandbox whose mount blocks `unlink` inside `.git`, git cannot clear its own `index.lock`, so stash/commit/branch operations fail after the first one. | medium - the branch-and-stash step could not complete; adoption proceeded as file edits and the PR was pushed via the GitHub API | Add an ADOPTION note: if the environment cannot perform git writes, do the doc migration with plain file writes, verify with the test suite, and hand off git (or push via the platform API); record it as a blocker rather than forcing git. | new |
| 2026-07-02 | RUNBOOK.md template -> Evaluation And Benchmarking | The template's evaluation section hard-references `tools/` and `evals/` scripts that exist in the LLM Workbench repo itself, not in an adopted downstream project. During adoption these had to be replaced with the project's real gate (Mac/hosted LM acceptance gate + `analyze_run.py`). | low - one section needed rewriting rather than filling | Mark the `tools/`/`evals/` commands in the template as "workbench-repo only; replace with the project's real evaluation procedure during adoption." | new |

## What Belongs Here vs. TASKBOARD

- This project's own work, bugs, and tasks -> `TASKBOARD.md`.
- Problems with the *harness rules themselves* -> here.

If a harness problem is also blocking this project right now, log it here **and**
open a `TASKBOARD.md` task/blocker for the local workaround, linking the two (see
`TASKBOARD.md` B-001).
