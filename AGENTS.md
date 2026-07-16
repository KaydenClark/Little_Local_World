# Local Agent Town - Agent Instructions

> Generated from LLM Workbench v2.1. To pull later harness improvements into this
> project, see `RUNBOOK.md` -> Upgrading The Harness.

This file controls how agents behave in this project. It answers four questions:
what can the agent read, what can it edit, how does it choose work, and where is
the proof that the work is done.

## Authority Order

When instructions conflict, use this order:

1. Current user request.
2. This `AGENTS.md`.
3. Source code and tests, verified live.
4. `BLUEPRINT.md`.
5. `TASKBOARD.md`.
6. `RUNBOOK.md`.
7. `README.md` and older handoff notes.

If docs and code disagree, trust verified code, flag the drift, and update the
stale doc when the task touches that area.

## Read Scope

The agent may read:

- this project root;
- source, tests, configs, scripts, docs, and logs needed for the current task;
- dependency manifests and lockfiles (`pyproject.toml`, `requirements.txt`);
- `research_papers/` when a task depends on a paper's design input;
- generated output only when debugging build, runtime, or verification behavior;
- external paths only when the user request or project docs explicitly reference
  them.

The agent must not read secrets, credentials, tokens, local databases, raw
personal data, or unrelated projects unless the current task requires it and the
source is explicitly in scope.

## Edit Scope

The agent may edit:

- `src/agent_town/` (the deterministic engine, governor, and viewer);
- `tests/`;
- `scripts/`;
- `docs/screenshots/` when updating checked-in visual proof, and
  `docs/run_reports/` when recording run gates;
- control docs: `AGENTS.md`, `BLUEPRINT.md`, `TASKBOARD.md`, `RUNBOOK.md`,
  `README.md`, `HARNESS_FEEDBACK.md`, `VISUAL_DESIGN.md`;
- dependency manifests (`pyproject.toml`, `requirements.txt`) only when a
  dependency change is necessary and explained.

Edit only on explicit user request:

- `research_papers/` (add, rename, or organize research files) - otherwise treat
  the raw papers as read-only design input;
- `src/agent_town/core.py` - the frozen contract. Changes go through the
  documented one-file-PR process (a small PR both build tracks rebase on), never
  a unilateral edit.

The agent must not edit:

- `.venv/`, `__pycache__/`, `*.egg-info/`, build output, or generated `logs/`;
- original downloaded asset files or source zips under `src/agent_town/assets/`
  (derive runtime sheets/sprites from them; keep originals untouched);
- secrets, credentials, OAuth tokens, local databases, raw personal data, or
  unrelated projects;
- the persistence model, LLM provider model, or external integrations unless the
  user asks for that or the current approach is blocking correctness.

If the correct change requires leaving scope, stop and explain the smallest
needed scope expansion.

## Work Selection

Default loop:

1. Read `BLUEPRINT.md` for purpose, constraints, and direction.
2. Read `TASKBOARD.md` to choose the next concrete task.
3. Pick the highest-priority `ready` task that is in scope and unclaimed.
4. Mark it `claimed` or `in-progress` before editing.
5. Do the smallest correct change.
6. Verify it with the proof required by the task and `RUNBOOK.md`.
7. Update `TASKBOARD.md` with the result, documentation status, and gaps.

Do not invent a different next task while `TASKBOARD.md` has a valid `ready` item
unless the user redirects you. If a task is blocked, move it to the `Blocked`
lane with the concrete blocker and next action; if a blocker becomes a stable
architectural risk, summarize it in `BLUEPRINT.md` -> Known Risks.

## Agent Job

Maintain and improve this local desktop civilization simulation without changing
its purpose.

Default responsibilities:

- restate the selected task goal in one sentence;
- read relevant docs and code before editing;
- when a task depends on a `research_papers/` paper, read it first and translate
  it into project decisions, tests, and explicit deferrals before touching code;
- make the smallest correct change;
- preserve existing architecture, naming, and style;
- validate inputs at boundaries; use explicit error handling and visible
  degraded states;
- update any project docs that would become stale because of the change;
- leave the project easier for the next agent to verify.

## Documentation Ownership

Documentation is part of the work, not a follow-up role. Unless the task assigns
a separate documentation owner, the agent making the change owns its docs.

| Change type | Documentation to check |
|---|---|
| Purpose, product behavior, architecture, data model, contracts, invariants, safety boundary | `BLUEPRINT.md` |
| Current work queue, blockers, deferred work, task proof, handoff state | `TASKBOARD.md` |
| Setup, install, run, test, build, recovery, environment, operations, evaluation | `RUNBOOK.md` |
| User-facing setup, usage, demo, public instructions | `README.md` |
| Agent rules, scope, authority, verification contract | `AGENTS.md` |
| Visual style, map/UI readability, asset direction | `VISUAL_DESIGN.md` |

If no docs need edits, record `Docs checked; no update needed` in the final
response and in the relevant `TASKBOARD.md` proof row, with a short reason.

## Verification And Proof

For behavior changes, use red/green/refactor:

1. Define the expected behavior.
2. Add or update a failing test.
3. Run the test and confirm it fails for the expected reason.
4. Implement the smallest change.
5. Run the targeted test.
6. Run the full verification suite from `RUNBOOK.md` when the task is complete.

If tests are impractical, run a concrete manual check and name the specific
reason (for example "no test harness for this Pygame interaction").

Every completed task leaves proof in two places:

- Final response: what changed, why, risks, and how verified.
- `TASKBOARD.md` proof log: one row with actual results, not stale claims.

Do not claim work is complete unless verification ran. Milestone tasks also
require a demo artifact the owner can check in under a minute (a screenshot, a
short recording, or a one-command demo) recorded in the proof log's Demo column.

For scale, pathfinding, large-population, or performance work, read
`research_papers/7.scalable-sim-report.md`, run `scripts/benchmark_scaling.py`
when practical, and preserve exact simulation for player-visible truth before
adding approximation.

## Long Session Control

Long sessions drift; counter it deliberately (folds in the former unattended-work
policy):

- Re-read `BLUEPRINT.md` and `TASKBOARD.md` after any context summary or long
  interruption.
- Keep task statuses current; tick or move a task only once its proof exists.
- Append proof rows; do not rewrite existing proof history.
- If the same verification fails twice and the next step is not clearly safe,
  stop, record the blocker, and surface the decision needed.
- Create a dedicated branch for non-trivial work when the project is in git. Do
  not overwrite, reset, discard, or force-push user work unless explicitly asked.
  Inspect git state before editing; keep unrelated dirty files untouched.
- Do not commit secrets, local databases, generated dumps, `.venv`, or private
  exports.
- Create a checkpoint before broad edits, before dependency changes, after
  verification passes, and before handoff. Each checkpoint records: current goal,
  files changed, verification run, known risks, and next action.

**Reclaiming stale claims.** A `claimed`/`in-progress` task whose last update is
older than one working day with no committed progress may be reclaimed: confirm
no branch or commit is advancing it, note the reclaim in the task with the date,
then take it over or move it back to `ready`. Never silently discard a prior
agent's committed work.

## Stop And Ask

Stop and ask before:

- destructive filesystem actions (recursive delete, reset, clean, overwrite);
- touching production data, private exports, secrets, credentials, tokens, or
  local databases;
- creating paid services, changing billing, or enabling external integrations
  (including hosted AI as a default);
- changing authentication, authorization, permission, or encryption behavior;
- deploying externally or changing deployment configuration;
- broad dependency upgrades or architecture rewrites;
- editing `core.py`'s frozen contract outside the one-file-PR process;
- continuing after repeated verification failures when the next step is not
  clearly safe.

Escalations to the owner are phrased as product tradeoffs, not tool- or
code-level failures: give the options, a recommendation, and the cost of each
path, and record the open decision in `TASKBOARD.md` -> Pending Decisions.

## Harness Feedback

These control docs came from a reusable harness (LLM Workbench v2.1). When a
harness rule itself is unclear, wrong, missing, or slows the work down, do not
silently work around it: log it in `HARNESS_FEEDBACK.md` (append-only) with the
doc, section, and a proposed change. Keep it separate from `TASKBOARD.md`, which
tracks this project's own work.

## Visual And Asset Work

Local visual style is owned by `VISUAL_DESIGN.md`, not this template. Use the
project prompt, that design doc, screenshots, and audience context.

When visual work needs a new asset:

- search for a license-safe free asset before drawing or kitbashing one locally;
- prefer CC0 or public domain; CC-BY is acceptable only when attribution is
  recorded near the imported files;
- verify the source URL, license, author, and attribution before adding files;
- keep original downloaded assets/zips untouched and derive runtime sheets from
  them;
- match the target mood (medieval fantasy village; default to Age-of-Empires-style
  readable RTS buildings/terrain when uncertain);
- avoid emoji as interface icons when a real icon, symbol, or text label can do
  the job.

For visual changes to the viewer: render and inspect a fresh screenshot after the
change, replace `docs/screenshots/current-state.png` when the visible state
changed, and keep the README caption honest about what is current, mocked, or
placeholder.

## Day-One Checklist

Load only what the task requires:

- Quick task: read `BLUEPRINT.md` summary and the relevant `TASKBOARD.md` item.
- Feature, refactor, or unknown-scope bug: read `BLUEPRINT.md`, `TASKBOARD.md`,
  and the relevant code/tests.
- Onboarding, setup, or operations work: also read `RUNBOOK.md`.
- Any task that runs verification: also open `RUNBOOK.md` -> Test And Build.
- Any UI or visual work: read `VISUAL_DESIGN.md`.

Then for every task: inspect the relevant files, check version-control status,
run baseline verification when practical, implement with tests or a named manual
check, and append a `TASKBOARD.md` proof row if durable state changed.

## Output Format

For all task completions, report: (1) what changed, (2) why, (3) risks or side
effects, (4) how it was verified. Keep it concise; flag uncertainty instead of
hiding it.

## What Not To Do

- Do not invent APIs, files, functions, behavior, or test results.
- Do not rewrite working systems just to make them cleaner.
- Do not broaden scope without a concrete reason.
- Do not add paid services unless the user explicitly approves them.
- Do not leave unexplained placeholder logic.
- Do not treat prior session notes or taskboard history as current truth without
  verifying source state.
- Do not rewrite existing `TASKBOARD.md` proof rows; append only.
- Do not treat `research_papers/` as already-implemented code truth; conflicts
  become `TASKBOARD.md` tasks.
