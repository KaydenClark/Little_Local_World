# Legacy harness (pre-v2.1) - archived 2026-07-02

Before this commit, Local Agent Town used a different control/policy doc set. When
it adopted the LLM Workbench v2.1 harness (four control docs: `AGENTS.md`,
`BLUEPRINT.md`, `TASKBOARD.md`, `RUNBOOK.md`), the pre-v2 docs were retired. They
are history, not a competing rulebook - do not follow them. The live docs at the
repo root govern.

The retired docs were `ROADMAP.md`, `UNATTENDED_WORK_POLICY.md`, and
`BOOTSTRAP_CHECKLIST.md`. Their full content is preserved in git history at the
pre-adoption commit `db890c29` (and in the local working tree copies under this
directory). Where their content went during adoption:

| Retired doc | Disposition |
|---|---|
| `ROADMAP.md` | Split: stable direction -> `BLUEPRINT.md` (Direction And Build Order); live queue, blockers, deferred work -> `TASKBOARD.md`; the most recent slices were carried into the `TASKBOARD.md` Proof Log. Full Verification Log remains in git history. |
| `UNATTENDED_WORK_POLICY.md` | Folded into `AGENTS.md` (Long Session Control, Stop And Ask). |
| `BOOTSTRAP_CHECKLIST.md` | Retired - superseded by the harness ADOPTION/GENESIS protocol. |

The former root `AGENTS.md` and `README.md` were rewritten in place into their v2
forms; their prior content is recoverable from git history at `db890c29`.
