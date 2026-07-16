# Local Agent Town - Taskboard

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

**Current focus:** Repair debt - the first material/coin maintenance sink (building condition degrades into output penalties before failure), before further Paper 7 scale work.
**Owner:** Kayden and local coding agents
**Last updated:** 2026-07-02

This is the live work queue and proof ledger. Keep strategy and long-term
direction in `BLUEPRINT.md`; keep commands and verification procedures in
`RUNBOOK.md`.

## Executive Brief

- **Shipping now:** A deterministic build-1 civilization with ~12 pawns, both
  governors, the Pygame viewer, mood/hunger, work-priority arbiter, water,
  storage caps, and the first wage/market money loop.
- **Health:** green - full suite (262 tests) + smoke pass; latest Mac/hosted LM
  gates returned GREEN.
- **Decision needed:** none open (see Pending Decisions).
- **Blocked on:** nothing (hosted AI, multiplayer, engine migration are
  intentionally gated, not blocked).
- **Next milestone:** repair debt slice, then Paper 7 scale foundations
  (reachability regions + deterministic phases).

## Pending Decisions

Decisions only the owner should make. Agents surface tradeoffs here as product
choices and do not decide them alone.

| ID | Decision | Options | Recommendation | Cost / impact | Owner | Status |
|---|---|---|---|---|---|---|
| D-001 | Add a `LICENSE` file? The harness ships MIT but LLW never had one. | MIT / other OSS / keep unlicensed | MIT if the repo stays public on GitHub | Licensing is hard to reverse once published | Kayden | open |

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
| T-101 | 1 | Repair debt: building condition degrades into output/service penalties before catastrophic failure; planks/stone + labour repair sink | Paper 4 economy; stated "next code task" across ROADMAP truth-loop queue | `src/agent_town/economy.py`, `buildings.py`, `engine.py`, `telemetry.py`, `civilization_view.py`, `tests/` | red/green: new `tests/test_repair.py` for decay, penalty, repair job, telemetry; full suite + smoke | `BLUEPRINT.md` (money loop, invariants), `RUNBOOK.md` (manual check) | agent | ready | 2026-07-02 |
| T-102 | 2 | Paper 7 scale foundation: reachability-region rejection (`region_id` per walkable tile, dirty recompute) so impossible jobs are rejected before pathfinding | Paper 7 / Paper 8 build order; first scale foundation after the truth loop | `src/agent_town/world.py`, `work.py`, `engine.py`, `tests/` | red/green tests for region assignment + impossible-job rejection; determinism preserved; full suite | `BLUEPRINT.md` (Scale architecture) | agent | ready | 2026-07-02 |
| T-103 | 2 | Paper 7 scale foundation: deterministic command/update phases (stable ordered job claims, reservations, path requests, movement, production, needs, tax) | Paper 7; pairs with T-102 before raising population | `src/agent_town/engine.py`, `work.py`, `tests/` | determinism + phase-order tests; I1 3-day survival + LLM==fallback oracles stay green | `BLUEPRINT.md` | agent | ready | 2026-07-02 |
| T-104 | 3 | Manual LM Studio/Ollama model tuning pass: run Gemma 4 E4B-it, Qwen3.5-4B, Phi-4-mini-instruct locally; record best speed/personality balance | ROADMAP Next Tasks item 4 (never completed); operator task | `docs/run_reports/` | run report per model with analyzer verdict + timing | `RUNBOOK.md` (record chosen default) | Kayden | ready | 2026-07-02 |

## In Progress

| ID | Priority | Task | Owner | Started | Touches | Current note | Proof required | Status |
|---|---:|---|---|---|---|---|---|---|
| _(none)_ | | | | | | | | |

## Blocked

Roadblocks, slowdowns, and risks affecting current or near-term work. Stable
architectural risks are summarized in `BLUEPRINT.md` -> Known Risks.

| ID | Task / area | Blocked on | Evidence | Next action | Owner | Status |
|---|---|---|---|---|---|---|
| B-001 | Sandbox git write operations in this repo | Mount blocks `unlink` inside `.git`, so git cannot clear its own `index.lock` | `rm .git/index.lock` -> "Operation not permitted"; `git status` re-creates a lock it cannot remove | On a real machine, run `rm -f .git/index.lock` then commit the adoption normally | Kayden | blocked |

## Deferred

Valid work that should not be started yet.

| ID | Task | Deferred until | Why it matters | Revisit trigger |
|---|---|---|---|---|
| DEF-01 | Lethal starvation (72h-since-meal death, `Pawn.hours_since_meal`, `starving_pawn` exception, food-first fallback, viewer badge + death event, RUNBOOK manual check) | The visible autonomy/readability loop is satisfying | Gives the food chain lethal stakes; conservation-real | When the malnutrition/death timing slice can ship status + exceptions + viewer + urgency together |
| DEF-02 | Hosted AI providers as default | Explicit user approval | Avoids accidental paid/network-dependent behavior | Owner opts in |
| DEF-03 | Human multiplayer / remote viewing | Explicit product direction change | Local-only; AI-vs-AI multi-civilization is build 4, not web | Build 4 |
| DEF-04 | Large map editor | Stable core loop | Editing tools are less useful before agent behavior is interesting | Core loop stable |
| DEF-05 | Engine migration off Pygame | Benchmark evidence that Pygame rendering/editor tooling is the blocker | Current measured risk is sim scale/persistence/pathfinding, not rendering | `scripts/benchmark_scaling.py` shows rendering as the cap |
| DEF-06 | Clothes/beauty chain, full needs set, building-quality-to-mood, revolution meter + keep, save state, healthcare, Church, disasters, pets | Their build-2 prerequisites (see `BLUEPRINT.md` build arc) | Build-2 depth | Repair debt + district logistics land first |
| DEF-07 | Build 3 (pawn lifecycle, birth, soldier pipeline, ore->metal->tools chain, Police/Firehouse) | Build 2 depth complete | The people become real | Build 2 done |

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
evidence. Milestone rows fill the Demo column. Full pre-v2 history is preserved
in `archive/legacy-harness/ROADMAP.md` (Verification Log); the most recent slices
are carried here.

**Archival policy.** Append-only. When this passes ~30 rows, move the oldest
(keep the most recent ~30) into `TASKBOARD_ARCHIVE.md` verbatim under a dated
heading.

| Date | Task ID | Agent | Proof | Demo | Result | Docs | Remaining gap |
|---|---|---|---|---|---|---|---|
| 2026-06-30 | (research-spine) | codex | `unittest tests.test_research_spine` (6) + full discover (240) + smoke + validate-workbench | Bakery output 4->5 on `efficient_baking` | pass | ROADMAP/BLUEPRINT/RUNBOOK | Space-Age spine, wages, scale deferred |
| 2026-06-30 | (storage-caps) | codex | `unittest tests.test_storage_caps` (6) + full discover (246) + smoke + validate + screenshot | HUD `Storage N%` | pass | ROADMAP/BLUEPRINT/RUNBOOK | Storehouse upgrades, district storage, badges (later shipped) |
| 2026-06-30 | (wage-market) | codex | `unittest tests.test_money_loop` (5) + full discover (251) + smoke + validate | Daily wages + Market bread export | pass | ROADMAP/BLUEPRINT/RUNBOOK | Household spending, reserve-aware trade deferred |
| 2026-06-30 | (storehouse-badges) | codex | affected set (58) + full discover (255) + smoke + validate + render proof | HUD/Storehouse badge amber@80/red@95% | pass | ROADMAP/BLUEPRINT/RUNBOOK | District storage/hauling deferred |
| 2026-06-30 | (household-spending) | codex | `unittest tests.test_money_loop` (7) + full discover (257) + smoke + validate | Sales tax collected from wallets | pass | ROADMAP/BLUEPRINT/RUNBOOK | District queues, Tavern comfort deferred |
| 2026-06-30 | (market-service-pressure) | codex | affected set (45) + full discover (260) + smoke + validate | `market_service_pressure` in exception stack | pass | ROADMAP/BLUEPRINT/RUNBOOK | Repair debt is next code task |
| 2026-06-30 | (pr29-mac-lm-gate) | mac-gate | install/smoke + full discover (260) + validate + LM ping + 96 viewer hours + analyzer GREEN | `docs/run_reports/2026-06-30-pr29-mac-lm-gate.md` | pass | run report | Post-run summary helper AttributeError (non-gating) |
| 2026-06-30 | (pr29-openai-gate) | mac-gate | hosted `gpt-5.4-mini` structured-output probe + 96 viewer hours + analyzer GREEN (~$0.20, 2m38s) | `docs/run_reports/2026-06-30-pr29-openai-gpt-5.4-mini-gate.md` | pass | run report | Provider token/cost not captured in telemetry |
| 2026-07-02 | (harness-adoption) | claude | Baseline before migration: pygame installed, `SDL_VIDEODRIVER=dummy PYTHONPATH=src python3 -m unittest discover -s tests` -> 262 OK; `python3 -m agent_town --smoke-test` exit 0 | n/a | pass | AGENTS/BLUEPRINT/TASKBOARD/RUNBOOK/README (adopted v2.1); ROADMAP/BOOTSTRAP_CHECKLIST/UNATTENDED_WORK_POLICY retired to archive | Git commit pending (sandbox cannot write git; see B-001) |
| 2026-07-03 | (pr43-mac-ui-lm-gate) | mac-gate | PR #43 head `5daf3a6c97464ad3c8dc7fda29db8528968c1cd0`; visible Pygame UI ~10.5 min against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1089 decisions, 58 model-origin hours, 0 dropped, 3 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr43-start.png`, `2026-07-03-pr43-mid.png`, `2026-07-03-pr43-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; log lacks `run_end` because macOS blocked synthetic quit keystroke and viewer was stopped by terminal interrupt |
| 2026-07-03 | (pr44-mac-ui-lm-gate) | mac-gate | PR #44 head `fd75521ab0fb14006b39356626cef000cb42b869`; visible Pygame UI ~10.5 min against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1046 decisions, 57 model-origin hours, 989 fallback-origin hours, 0 dropped, 29 `good_stalled` water warnings | `docs/proof/mac-ui-lm/2026-07-03-pr44-start.png`, `2026-07-03-pr44-mid.png`, `2026-07-03-pr44-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; repeated water supply stalls from day 12 through day 43 |
| 2026-07-03 | (pr46-mac-ui-lm-gate) | mac-gate | PR #46 head `3c6b1e10ab1796d7199a287866e9fb97f9ab0873`; visible Pygame UI ~11 min against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1093 decisions, 58 model-origin hours, 1035 fallback-origin hours, 0 dropped, 5 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-start.png`, `2026-07-03-pr46-mid.png`, `2026-07-03-pr46-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; logs/planks supply stalls remain |
| 2026-07-03 | (pr46-126f185-mac-ui-lm-gate) | mac-gate | PR #46 head `126f185266e500c4d88b8dedc1f0b1ab2542e940`; visible Pygame UI ~10m57s against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1094 simulated hours, 59 model-emission hours, 1035 fallback-origin hours, 0 dropped/invalid decisions, 4 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-126f185-start.png`, `2026-07-03-pr46-126f185-mid.png`, `2026-07-03-pr46-126f185-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; logs/planks supply stalls remain |
| 2026-07-03 | (pr46-ee919e3-mac-ui-lm-gate) | mac-gate | PR #46 head `ee919e3e726f9d983e49b6d0acf6f2388c3fbb1c`; visible Pygame UI ~10m33s against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1054 simulated hours, 57 model-emission hours, 997 fallback-origin hours, 0 dropped/invalid decisions, 2 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-ee919e3-start.png`, `2026-07-03-pr46-ee919e3-mid.png`, `2026-07-03-pr46-ee919e3-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; logs/planks supply stalls remain |
| 2026-07-03 | (pr46-fa5f601-mac-ui-lm-gate) | mac-gate | PR #46 head `fa5f6017717b8eff5e15fd13e1bf84796914d1fd`; visible Pygame UI ~10m against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1105 simulated hours, 60 model-emission hours, 1045 fallback-origin hours, 0 dropped/invalid decisions, 4 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-fa5f601-start.png`, `2026-07-03-pr46-fa5f601-mid.png`, `2026-07-03-pr46-fa5f601-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; logs/planks supply stalls remain; viewer stopped by terminal interrupt after final screenshot |
| 2026-07-03 | (pr46-5f51cc5-mac-ui-lm-gate) | mac-gate | PR #46 head `5f51cc52167c5ea72c36537f0af6c329b46b198e`; visible Pygame UI ~10m against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1125 simulated hours, 61 model-emission hours, 1064 fallback-origin hours, 0 dropped/invalid decisions, 2 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-5f51cc5-start.png`, `2026-07-03-pr46-5f51cc5-mid.png`, `2026-07-03-pr46-5f51cc5-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; logs/planks supply stalls remain; macOS blocked synthetic quit but terminal interrupt still wrote `run_end` |
| 2026-07-03 | (pr46-8fc3f23-mac-ui-lm-gate) | mac-gate | PR #46 head `8fc3f23397132f7119b575c0f0dedd0907bfc76e`; visible Pygame UI ~10m32s against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1060 simulated hours, 58 model-emission hours, 1002 fallback-origin hours, 0 dropped/invalid decisions, 7 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-8fc3f23-start.png`, `2026-07-03-pr46-8fc3f23-mid.png`, `2026-07-03-pr46-8fc3f23-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; late-run water stalls plus initial logs/planks stalls remain; viewer stopped by terminal interrupt after final screenshot but wrote `run_end` |
| 2026-07-03 | (pr46-f711f0a-mac-ui-lm-gate) | mac-gate | PR #46 head `f711f0a382ac6f0d416996cd1d59d1fe2e945e82`; visible Pygame UI ~10m against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1111 simulated hours, 61 model-emission hours, 1050 fallback-origin hours, 0 dropped/invalid decisions, 6 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-f711f0a-start.png`, `2026-07-03-pr46-f711f0a-mid.png`, `2026-07-03-pr46-f711f0a-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; initial logs/planks stall, day 31 planks stall, and late-run water stalls remain |
| 2026-07-03 | (pr46-f83a52b-mac-ui-lm-gate) | mac-gate | PR #46 head `f83a52bc41d129eb388a07d98143344e34d4d70c`; visible Pygame UI ~11m against LM Studio `google/gemma-4-e4b`; analyzer `RESULT: AMBER`; 1120 simulated hours, 61 model-emission hours, 1059 fallback-origin decisions, 0 dropped/invalid decisions, 4 `good_stalled` warnings | `docs/proof/mac-ui-lm/2026-07-03-pr46-f83a52b-start.png`, `2026-07-03-pr46-f83a52b-mid.png`, `2026-07-03-pr46-f83a52b-end.png`; report `docs/run_reports/2026-07-03-mac-ui-lm-gate.md` | pass-with-warnings | run report; Docs checked; no BLUEPRINT/RUNBOOK update needed because no behavior or operation contract changed | Not clean GREEN; initial logs/planks stalls plus day 26/day 33 planks stalls remain |
