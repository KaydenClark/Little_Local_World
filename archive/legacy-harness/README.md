# Legacy harness (pre-v2.1) - archived 2026-07-03

Before this commit, Local Agent Town used a different control/policy doc set.
When it adopted the LLM Workbench v2.1 harness (four control docs: `AGENTS.md`,
`BLUEPRINT.md`, `TASKBOARD.md`, `RUNBOOK.md`), the pre-v2 docs were retired.
They are history, not a competing rulebook - do not follow them. The live docs
at the repo root govern.

The retired docs were `ROADMAP.md`, `UNATTENDED_WORK_POLICY.md`, and
`BOOTSTRAP_CHECKLIST.md`. Their full content is preserved both as verbatim
copies in this directory and in git history at every commit before this one.
Where their content went during adoption:

| Retired doc | Disposition |
|---|---|
| `ROADMAP.md` | Split: stable direction -> `BLUEPRINT.md` (Direction And Build Order, the Physical sourcing and Crisis-response sections); live queue, blockers, deferred work -> `TASKBOARD.md`. The most recent slices (2026-07-01 onward) were carried into the `TASKBOARD.md` Proof Log in the new column format; the full original 87-row Verification Log (2026-06-26 through 2026-07-02) is preserved verbatim in `ROADMAP.md` in this directory. |
| `UNATTENDED_WORK_POLICY.md` | Folded into `AGENTS.md` (Long Session Control, Stop And Ask). |
| `BOOTSTRAP_CHECKLIST.md` | Retired - superseded by the harness ADOPTION/GENESIS protocol. |

`BRANCHING.md` and `VISUAL_DESIGN.md` were **not** retired: they are
project-local operational/design references the harness does not own, and are
referenced (not folded) from `AGENTS.md`, `BLUEPRINT.md`, and `RUNBOOK.md`.

Note on provenance: an earlier adoption attempt (PR #40,
`adopt/llm-workbench-v2.1`) forked from `main` before physical resource
sourcing, save/load, and the spectator UI batch shipped on `integration`, and
went stale - retargeting it to `integration` produced real merge conflicts,
including a modify/delete conflict on `ROADMAP.md` (the PR deleted it while
`integration` had kept extending it). This adoption was redone from scratch
against the current `integration` tip so that content was not lost.
