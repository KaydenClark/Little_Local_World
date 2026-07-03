# Local Agent Town - Harness Feedback

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

This is the return channel from this project back to the LLM Workbench harness.
When the control docs themselves (`AGENTS.md`, `BLUEPRINT.md`, `TASKBOARD.md`,
`RUNBOOK.md`, `GENESIS.md`, `ADOPTION.md`) are unclear, wrong, missing
guidance, or actively slow the work down, record it here instead of silently
working around it. The owner carries these lessons back to LLM Workbench,
where a change is validated against `evals/` before it ships as "better".

This log is append-only. Do not edit or delete prior rows; add a new one.

## How To Log

Add a row whenever the harness (not this project's own code or docs) caused
friction or could be improved. Name the doc and section, say what happened,
and propose a change if you have one.

| Date | Doc / section | What happened | Impact | Proposed change | Status |
|---|---|---|---|---|---|
| 2026-07-03 | ADOPTION.md -> Phase 3 (map the old harness) | A prior adoption attempt (this project's PR #40) forked from `main` instead of the actively-worked `integration` branch, and by the time it was reviewed, `integration` had moved ~19 commits further and edited the same docs being migrated (including ~496 new lines added to the doc being retired). The PR showed real merge conflicts, including a modify/delete conflict, when retargeted. | medium - required redoing the entire adoption from scratch against the current branch tip rather than reconciling the stale PR | Add explicit guidance to Phase 0: "branch from a clean commit" should say *which* branch to observe/branch from when the project uses a non-`main` integration/trunk branch (per this project's `BRANCHING.md`), not just "a clean commit." Also flag that a long-lived adoption PR should be re-verified against the current trunk tip before merge, not just at PR-open time. | new |
| 2026-07-03 | ADOPTION.md -> Phase 3 / Guardrails | This project has a project-specific `BRANCHING.md` (a three-tier branch model) that the harness template has no equivalent doc for. The protocol's "Port / Fold / Keep / Retire" classification doesn't have an explicit category for "a project-local operational policy doc that the harness should reference from `AGENTS.md`/`RUNBOOK.md` but not fold or retire." It was classified as "Keep" by analogy to `VISUAL_DESIGN.md`, but Keep's description ("the harness defers visual style to it") is worded narrowly around visual/design docs. | low - the classification worked once reasoned through, but the guardrail language could make this an easier default | Broaden "Keep" in Phase 0's classification list to cover any project-owned operational policy (branching, deployment, visual style) that the harness references but does not own, not only "a visual or design doc." | new |

## What Belongs Here vs. TASKBOARD

- This project's own work, bugs, and tasks -> `TASKBOARD.md`.
- Problems with the *harness rules themselves* -> here.

If a harness problem is also blocking this project right now, log it here
**and** open a `TASKBOARD.md` task for the local workaround, linking the two.
