# Local Agent Town - Taskboard

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

**Current focus:** The trader (crisis-line Slice 3) - deterministic trader +
`buy_good`, coin -> bread, optional local-LLM trader personality behind a hard
fallback. Now genuinely unblocked: physical sourcing gave grain a real 24h
growing season to price trader economics against.
**Owner:** Kayden and local coding agents
**Last updated:** 2026-07-03

This is the live work queue and proof ledger. Agents use it to decide what to
work on next. Keep strategy and long-term direction in `BLUEPRINT.md`; keep
commands and verification procedures in `RUNBOOK.md`.

## Executive Brief

- **Shipping now:** A deterministic build-1 civilization (~12 pawns) with both
  governors, the Pygame viewer, mood/hunger, the work-priority arbiter, water,
  storage caps, the first wage/market money loop, physical resource sourcing
  (real fields/nodes with growth time and depletion), visible storage,
  save/load persistence, and a spectator navigation/day-night/KPI-strip pass.
  All five confirmed Fable 5 peer-review findings are fixed.
- **Health:** green - full suite (385 tests as of this adoption, 2026-07-03;
  growing, do not hardcode a stale number) + smoke pass.
- **Decision needed:** none blocking (see Pending Decisions for the open,
  non-blocking LICENSE question).
- **Blocked on:** nothing (hosted AI, multiplayer, engine migration are
  intentionally gated, not blocked).
- **Next milestone:** the trader, then repair debt, then Paper 7 scale
  foundations.

## Pending Decisions

Decisions only the owner should make. Agents surface tradeoffs here as product
choices and do not decide them alone.

| ID | Decision | Options | Recommendation | Cost / impact | Owner | Status |
|---|---|---|---|---|---|---|
| D-001 | Add a `LICENSE` file? The project ships MIT-flavored tooling but never picked one. | MIT / other OSS / keep unlicensed | MIT if the repo stays public on GitHub | Licensing is hard to reverse once published | Kayden | open |

## How To Use This Board

1. Read `BLUEPRINT.md` for context.
2. Pick the highest-priority `ready` task that is in scope and unclaimed.
3. Move it to `claimed` or `in-progress` before editing.
4. Do the smallest correct change.
5. Run the task's required proof and the relevant `RUNBOOK.md` checks.
6. Move the task to `done`, `blocked`, `deferred`, or `needs-review`.
7. Append one proof row with the actual result. Do not rewrite existing proof
   rows.

## Status Values

| Status | Meaning |
|---|---|
| `ready` | Clear enough for the next agent to start. |
| `claimed` | An agent has picked it but has not edited yet. |
| `in-progress` | Work is underway. |
| `gated` | Implementation done, waiting on verification, review, or merge. |
| `needs-review` | Needs human/manager review before more work. |
| `blocked` | Cannot proceed until the blocker is resolved. |
| `deferred` | Valid work, intentionally not next. |
| `done` | Proof exists and docs impact is resolved. |

A `claimed`/`in-progress` task with no update for more than one working day may be
reclaimed per `AGENTS.md` -> Long Session Control.

## Ready

| ID | Priority | Task | Source / why now | Touches | Proof required | Docs impact | Owner | Status | Last update |
|---|---:|---|---|---|---|---|---|---|---|
| T-101 | 1 | The trader (crisis-line Slice 3): deterministic trader core + `buy_good` (coin -> bread), optional local-LLM trader personality behind a hard fallback | Design already specified in `BLUEPRINT.md` "Crisis, response, consequence"; physical sourcing gave grain a real lead time to price against; recorded as "the natural next code task" 2026-07-02 | `src/agent_town/economy.py`, `governor.py`, `civilization_view.py`, `tests/` | red/green: new `tests/test_trader.py`; full suite + smoke; watchable proof frame of a trade happening | `BLUEPRINT.md` (crisis line, governor interface), `RUNBOOK.md` (manual check) | agent | gated | 2026-07-03 - PR #42 open |
| T-102 | 2 | Repair debt: building condition degrades into output/service penalties before catastrophic failure; planks/stone + labour repair sink | Paper 4 economy; stated "next code task" across the Research Paper Implementation Queue | `src/agent_town/economy.py`, `buildings.py`, `engine.py`, `telemetry.py`, `civilization_view.py`, `tests/` | red/green: new `tests/test_repair.py` for decay, penalty, repair job, telemetry; full suite + smoke | `BLUEPRINT.md` (money loop, invariants), `RUNBOOK.md` (manual check) | agent | gated | 2026-07-03 - PR #43 open |
| T-103 | 3 | Paper 7 scale foundation: reachability-region rejection (`region_id` per walkable tile, dirty recompute) so impossible jobs are rejected before pathfinding | Paper 7/8 build order; first scale foundation after the truth loop and crisis line | `src/agent_town/world.py`, `work.py`, `engine.py`, `tests/` | red/green tests for region assignment + impossible-job rejection; determinism preserved; full suite | `BLUEPRINT.md` (Scale architecture) | agent | gated | 2026-07-03 - PR #44 open |
| T-104 | 3 | Paper 7 scale foundation: deterministic command/update phases (stable ordered job claims, reservations, path requests, movement, production, needs, tax) | Paper 7; pairs with T-103 before raising population | `src/agent_town/engine.py`, `work.py`, `tests/` | determinism + phase-order tests; I1 3-day survival + LLM==fallback oracles stay green | `BLUEPRINT.md` | agent | gated | 2026-07-03 - PR #45 open |
| T-105 | 4 | Manual LM Studio/Ollama model tuning pass: run Gemma 4 E4B-it, Qwen3.5-4B, Phi-4-mini-instruct locally; record best speed/personality balance | Never completed; operator task carried since the I2 bridge milestone | `docs/run_reports/` | run report per model with analyzer verdict + timing | `RUNBOOK.md` (record chosen default) | Kayden | ready | 2026-07-02 |

## In Progress

| ID | Priority | Task | Owner | Started | Touches | Current note | Proof required | Status |
|---|---:|---|---|---|---|---|---|---|
| _(none)_ | | | | | | | | |

## Blocked

Roadblocks, slowdowns, and risks affecting current or near-term work. Stable
architectural risks are summarized in `BLUEPRINT.md` -> Known Risks.

| ID | Task / area | Blocked on | Evidence | Next action | Owner | Status |
|---|---|---|---|---|---|---|
| _(none)_ | | | | | | |

## Deferred

Valid work that should not be started yet.

| ID | Task | Deferred until | Why it matters | Revisit trigger |
|---|---|---|---|---|
| DEF-01 | Lethal starvation (72h-since-meal death, `Pawn.hours_since_meal`, `starving_pawn` exception, food-first fallback, viewer badge + death event, RUNBOOK manual check) | The visible autonomy/readability loop is satisfying | Gives the food chain lethal stakes; conservation-real | When the malnutrition/death timing slice can ship status + exceptions + viewer + urgency together |
| DEF-02 | Era ladder: stone -> farming (current) -> castle -> city-state -> full civilization, gated by upgrading old buildings (not just unlocking new ones) | Owner is researching the specifics | Reshapes/absorbs the current minimal research spine once scoped; do not design a deep tech tree ahead of the owner's research | Owner provides era/tech-tree specifics |
| DEF-03 | News/alert scaling for multi-civilization spectating | Build 4 (two Governor agents, one map) | The macro strip's `News` chip is one-civ shaped today; needs a design decision on aggregation before it becomes noise | Build 4 scoping begins |
| DEF-04 | Log-as-source-of-truth narration (an always-on digest/summary UI) | Deliberately not built | Owner direction: keep the JSONL run log rich and answer "what happened while I was away" by writing the story from the log on request, not an always-on feature | Do not build without revisiting this framing first |
| DEF-05 | Ambient/compact desktop-pet mode | Project is ready to package | Explicitly deprioritized: simulation depth (era ladder, trader, multi-civ) beats presentation modes | Do not pick up unless asked |
| DEF-06 | Hosted AI providers as default | Explicit user approval | Avoids accidental paid/network-dependent behavior | Owner opts in |
| DEF-07 | Human multiplayer / remote viewing | Explicit product direction change | Local-only; AI-vs-AI multi-civilization is build 4, not web | Build 4 |
| DEF-08 | Large map editor | Stable core loop | Editing tools are less useful before agent behavior is interesting | Core loop stable |
| DEF-09 | Engine migration off Pygame | Benchmark evidence that Pygame rendering/editor tooling is the blocker | Current measured risk is sim scale/persistence/pathfinding, not rendering | `scripts/benchmark_scaling.py` shows rendering as the cap |
| DEF-10 | Clothes/beauty chain, full needs set, building-quality-to-mood, revolution meter + keep, healthcare, Church, disasters, pets | Their build-2 prerequisites (see `BLUEPRINT.md` build arc) | Build-2 depth | Trader + repair debt land first |
| DEF-11 | Build 3 (pawn lifecycle, birth, soldier pipeline, ore->metal->tools chain, Police/Firehouse) | Build 2 depth complete | The people become real | Build 2 done |

## Documentation Check

Before marking a task complete, check:

| If the task changed... | Update or confirm |
|---|---|
| Product purpose, workflows, contracts, data model, architecture, invariants, privacy/safety | `BLUEPRINT.md` |
| Task queue, blockers, deferred work, proof of completed work | `TASKBOARD.md` |
| Setup, install, run, test, build, recovery, environment, operations, evaluation | `RUNBOOK.md` |
| User-facing setup, usage, demo, handoff, public instructions | `README.md` |
| Agent rules, scope, authority, verification policy | `AGENTS.md` |

If no docs need edits, record `Docs checked; no update needed` in the final
response and in the proof row's `Docs` field.

## Proof Log

Append a row when a task changes durable state or produces durable verification
evidence. Milestone rows fill the Demo column. The full pre-v2.1 verification
history (2026-06-26 through 2026-06-30, 57 rows) is preserved verbatim in
`archive/legacy-harness/ROADMAP.md` and in git history; the rows below carry
forward from the 2026-07-01 crisis/review line onward.

**Archival policy.** Append-only. When this passes ~30 rows, move the oldest
(keep the most recent ~30) into `TASKBOARD_ARCHIVE.md` verbatim under a dated
heading.

| Date | Task ID | Agent | Proof | Demo | Result | Docs | Remaining gap |
|---|---|---|---|---|---|---|---|
| 2026-07-01 | (ui-nav-baseline) | codex | `unittest tests.test_civilization_view` (40) + full discover (267) + smoke + validate; rendered `docs/proof/ui_navigation/*.png` | `docs/proof/ui_navigation/default.png` + 6 panel proofs | pass | BLUEPRINT/ROADMAP/RUNBOOK | Architect/Assign/Research/Menu show truthful state; deeper mechanics remain future systems |
| 2026-07-01 | (inspector-assign-interactive) | codex | `unittest tests.test_civilization_view` (44) + full discover (271) + smoke + validate; rendered assign/inspector proof PNGs | `docs/proof/ui_navigation/assign.png` + inspector tab PNGs | pass | RUNBOOK | Gear/social/health show honest gaps until inventory/relationships/injuries exist |
| 2026-07-01 | (governor-decision-audit) | codex | `unittest tests.test_civilization_view tests.test_telemetry` (62) + full discover (277) + smoke + validate; rendered `docs/proof/governor_decision_audit/*.png` | `history_decision_detail.png`, `crisis_20x_history.png` (20x speed) | pass | RUNBOOK (watch-speed check) | Full timeline scrubber and policy editor remain deferred |
| 2026-07-01 | (fable5-review-harness-update) | claude | full discover (277) + smoke + validate (docs-only change) | n/a | pass | AGENTS/BLUEPRINT/ROADMAP | Implementation of Slices A-E still pending at this point |
| 2026-07-01 | (review-slice-a-one-pawn-one-job) | codex | RED targeted tests failed on stale `staffed_by`; GREEN same tests + affected set (54) + full discover (279) + smoke; rendered `docs/proof/review_labor/01_reassigned_pawn_single_building.png` | same PNG | pass | BLUEPRINT (invariants) | Slices B-E still open at this point |
| 2026-07-01 | (review-slice-b-model-guard) | opus | RED model-origin `assign_pawn`/`set_production_target(bread,0)` passed the old fall-through; GREEN `tests.test_llm_governor.ModelGuardTests` (4) + affected set + full discover (283) + smoke; rendered `docs/proof/slice_guard/01_audit_rejected_model_action.png` | same PNG | pass | BLUEPRINT (governor interface) | Slices C-E still open at this point |
| 2026-07-02 | (review-slice-c-executable-conservation) | fable | RED direct `counts` mutation passed silently; GREEN `tests.test_conservation` (6) + full discover (315) + smoke; rendered `docs/proof/slice_ledger/01_health_zero_violations_day10.png` + `02_tamper_invariant_critical.png` | both PNGs | pass | BLUEPRINT (conservation law) | Slices D-E still open at this point |
| 2026-07-02 | (review-slice-d-analyzer-honesty) | fable | RED a pipeline-only run stamped GREEN; GREEN `tests.test_analyzer_honesty` (8) + full discover (323) + smoke; re-analyzed the same log -> AMBER "pipeline-only" | n/a | pass | BLUEPRINT (Governor interface / model efficacy) | Slice E still open at this point |
| 2026-07-02 | (review-slice-e-watchability-refresh) | fable | RED five named visibility gaps (no age tags, bread-from-nothing chips, no mood chip, truncated attribution, false badges); GREEN `tests.test_watchability` (14) + full discover (337) + smoke; rendered `docs/proof/watchability_refresh/01_crisis_visible.png` + `02_recovery_flow.png` + `03_menu_speed_buttons.png` | all 3 PNGs | pass | BLUEPRINT | All five Fable review slices (A-E) now closed |
| 2026-07-02 | (physical-sourcing-plan) | sonnet | Planning only; no code change | n/a | pass | n/a (plan doc) | 6-slice implementation plan recorded before code started |
| 2026-07-02 | (physical-sourcing-tier0) | fable | `tests/test_sourcing.py` (15, incl. "grain cannot outrun the season"); 240h conservation oracle stays green; full discover (352) | n/a | pass | BLUEPRINT (physical sourcing), ROADMAP | Crisis-line retiming (day-4 recovery) verified in the same slice |
| 2026-07-02 | (physical-sourcing-viewer-p2) | (unattributed) | Watchability suite grows to 24 (attention label, state label, pressures, node visuals, storehouse lines, seed chip) | field/node map rendering | pass | BLUEPRINT (viewer P2 batch) | n/a |
| 2026-07-02 | (building-click-inspection) | fable | `building_card_lines` unit tests + hit-test + click wiring + render smoke (367 total); proof frames in `docs/proof/physical_sourcing/` | `01_fields_growing_visible_storage.png`, `02_building_card_growing_farm.png` | pass | BLUEPRINT | n/a |
| 2026-07-02 | (physical-sourcing-docs) | fable | `.\scripts\validate-workbench.ps1` (docs-only) | n/a | pass | BLUEPRINT, ROADMAP marked SHIPPED | n/a |
| 2026-07-02 | (spectator-navigation) | fable | `SpectatorNavigationTests` (6: chip layout/click, alert-row click, follow toggle, pan-breaks-follow, clamped centering); full discover (373) | held-key WASD pan, follow cam | pass | BLUEPRINT (spectator UI) | n/a |
| 2026-07-02 | (save-load-kpi-daynight) | fable | `tests/test_save.py` (10, incl. determinism oracle: saved-then-reloaded civ steps 48h identically to one that never stopped); goods panel + KPI budget + day/night curve in `test_watchability`; full discover (393), smoke exit 0 | autosave/resume round-trip | pass | BLUEPRINT (save/load, spectator UI) | n/a |
| 2026-07-02 | (lmstudio-log-cleanup) | fable | `.\scripts\validate-workbench.ps1`; `.gitignore` updated | n/a | pass | n/a | Accidentally committed log removed; `docs/lmstudio_logs/` gitignored |
| 2026-07-02 | (next-up-notes) | fable | docs-only; `.\scripts\validate-workbench.ps1` | n/a | pass | ROADMAP ("Next up" section) | Recorded trader/era-ladder/news-scaling/log-narration/no-ambient-mode context for the next session |
| 2026-07-03 | (harness-adoption-v2.1-redo) | sonnet | Adopted AGENTS/BLUEPRINT/TASKBOARD/RUNBOOK/README v2.1 against current `integration` tip (19b0586); `ROADMAP.md`/`BOOTSTRAP_CHECKLIST.md`/`UNATTENDED_WORK_POLICY.md` retired to `archive/legacy-harness/`; `BRANCHING.md`/`VISUAL_DESIGN.md` kept as project-local docs; post-migration verification: `SDL_VIDEODRIVER=dummy PYTHONPATH=src .venv/Scripts/python.exe -m unittest discover -s tests` -> 385 OK; `python -m agent_town --smoke-test` exit 0; `.\scripts\validate-workbench.ps1` (retargeted at the v2.1 doc set) -> passed | n/a | pass | AGENTS/BLUEPRINT/TASKBOARD/RUNBOOK/README adopted; archive/legacy-harness/README.md records disposition | Supersedes the stale PR #40 draft, which was forked before physical sourcing/save-load/spectator-UI shipped and would have lost that content on merge |
| 2026-07-03 | AFK task runner | codex | Selected no new code slice: `gh pr list --state open --json number,title,headRefName,baseRefName,mergeStateStatus,statusCheckRollup` showed T-101/102/103/104 already represented by open CLEAN PRs #42/#43/#44/#45 into `integration`; T-105 remains Kayden-owned manual model tuning. Updated T-101/T-102/T-103/T-104 status cells to `gated` with their PR numbers so the next AFK run does not duplicate live branches. Verification: `.\scripts\validate-workbench.ps1` and `git diff --check`. | n/a | skipped - no safe unclaimed agent-ready item | TASKBOARD updated; Docs checked; no code/runbook/blueprint update needed because this only corrected queue state | Review/merge PRs #42-#45, then choose the next unblocked agent task; Kayden-owned T-105 is still manual |
| 2026-07-03 | AFK task runner | codex | Selected no new code slice: live PR check showed T-101/102/103/104 still covered by open CLEAN PRs #42/#43/#44/#45 into `integration`, queue-gating PR #46 is open CLEAN, and T-105 remains Kayden-owned manual model tuning. Verification: `.\scripts\validate-workbench.ps1` and `git diff --check`. | n/a | skipped - no unclaimed agent-ready item | TASKBOARD updated with this proof row; Docs checked; no code/runbook/blueprint update needed because no product behavior changed | Review/merge PRs #42-#46, then choose the next unblocked agent task; Kayden-owned T-105 is still manual |
| 2026-07-03 11:01Z | AFK task runner | codex | Selected no new code slice on branch `codex/taskboard-pr-gates`: live PR check showed T-101/102/103/104 still covered by open CLEAN PRs #42/#43/#44/#45 into `integration`, queue-gating PR #46 is open CLEAN, and T-105 remains Kayden-owned manual model tuning. Verification: `.\scripts\validate-workbench.ps1` and `git diff --check`. Commit/PR: update to PR #46. | n/a | skipped - no safe unclaimed agent-ready item | TASKBOARD updated with this proof row; Docs checked; no code/runbook/blueprint update needed because no product behavior changed | Review/merge PRs #42-#46, then choose the next unblocked agent task; Kayden-owned T-105 is still manual |
| 2026-07-03 11:31Z | AFK task runner | codex | Selected no new code slice on branch `codex/taskboard-pr-gates`: live PR check showed T-101/102/103/104 still covered by open CLEAN PRs #42/#43/#44/#45 into `integration`, queue-gating PR #46 is open CLEAN, and T-105 remains Kayden-owned manual model tuning. Verification: `.\scripts\validate-workbench.ps1` and `git diff --check`. Commit/PR: update to PR #46. | n/a | skipped - no safe unclaimed agent-ready item | TASKBOARD updated with this proof row; Docs checked; no code/runbook/blueprint update needed because no product behavior changed | Review/merge PRs #42-#46, then choose the next unblocked agent task; Kayden-owned T-105 is still manual |
