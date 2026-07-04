# Local Agent Town - Runbook

> Generated from LLM Workbench v2.1. See Upgrading The Harness below.

**Last reviewed:** 2026-07-03
**Runtime owner:** Kayden
**Environment:** local desktop (developed on Windows; Mac/Linux gates verified
separately, see Evaluation And Benchmarking)

This file explains how to operate, verify, recover, and evaluate the project.
It is boring, exact, and executable.

## Prerequisites

Required tools:

- Windows PowerShell, or a POSIX shell on macOS/Linux.
- Python 3.11 or newer (Mac/hosted gates have used 3.12; avoid a system Python
  3.9).

Required accounts or services:

- None for the base prototype.
- Optional: a local OpenAI-compatible LLM server such as LM Studio or Ollama.

Required local files:

- None before setup. `setup.ps1` (Windows) creates `.venv`; on macOS/Linux, use
  the manual venv steps below.

## Environment Configuration

No `.env` file is required for the base prototype.

| Variable | Purpose | Secret? | Example / Notes |
|---|---|---|---|
| `SDL_VIDEODRIVER` | Headless Pygame smoke/test override | no | `dummy`, set automatically by `--smoke-test`; set manually for headless test runs |
| `AGENT_TOWN_LLM_MODEL` | Explicit model override | no | `google/gemma-4-e4b`, or the exact id loaded in LM Studio/Ollama |
| `AGENT_TOWN_LLM_BASE_URL` | OpenAI-compatible local endpoint | no | `http://localhost:1234/v1` for LM Studio, `http://localhost:11434/v1` for Ollama |
| `AGENT_TOWN_LLM_TIMEOUT` | Per-request timeout in seconds | no | default `4.0` |
| `AGENT_TOWN_LLM_MAX_TOKENS` | Max tokens for compact decision JSON | no | default `180` |
| `AGENT_TOWN_LLM_AUTO_DISCOVER` | Controls startup model discovery when no model is set | no | default `1`; set `0` to keep the local model disabled unless `AGENT_TOWN_LLM_MODEL` is set |

Rules:

- Do not commit real `.env` files, tokens, local databases, logs, or private
  data.
- Keep future LLM provider credentials local-only.
- Prefer a visible degraded state over fake external data when a future
  provider is unavailable.
- If no model variable is set, the app briefly checks the configured `/models`
  endpoint and selects the first non-embedding local model it finds.

## Install

Windows:

```powershell
.\setup.ps1
```

macOS/Linux (manual venv):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
```

Expected result: `.venv` exists, the package installs editable, Pygame is
available inside `.venv`.

## Asset Preparation

The civilization viewer uses runtime sprites under `src\agent_town\assets\colony`.

When adding a new free asset:

- Verify the source URL, license, author, and attribution requirements before
  download.
- Prefer CC0 or public domain. Use CC-BY only when attribution is recorded next
  to the imported files.
- Keep the original download or source zip untouched and generate runtime
  files from it.
- Update nearby asset notes and asset tests when the runtime asset set changes.
- If no license-safe asset fits, use the smallest temporary placeholder and
  record that it should be replaced.

## Run Locally

Windows:

```powershell
.\run.ps1
```

Double-click launcher:

```text
Launch Local Agent Town.cmd
```

macOS/Linux:

```bash
.venv/bin/python -m agent_town
```

Open: a local Pygame desktop window titled `Local Agent Town`.

Expected result:

- A civilization map appears with a day/night light overlay (dawn/dusk/night).
- The engine advances simulated hours over time.
- Civilization sprites appear for terrain, buildings, resources, and pawns;
  fields show their lifecycle (bare / growing % / ripe), depleted tree stands
  fade, mined-out stone reads crossed-out, and the Storehouse renders real held
  stock.
- The top KPI strip shows Day, Pop, Idle, Mood, Coin, Food-days, Storage, and
  News (trimmed to the Paper 6 budget; per-good stock/flow detail moved to a
  Goods drill-down panel).
- A top pawn roster shows colonist portraits, names, mood dots (hover/select to
  decode), and selection; clicking a roster portrait or an exception-stack row
  jumps the camera to that pawn/building.
- Mouse wheel, `+`, and `-` zoom. `WASD`/arrows pan continuously while held.
  `F` toggles a follow camera on the selected pawn (any manual pan hands the
  camera back).
- Clicking a pawn, or pressing `Tab`, updates the pawn sheet with status,
  assignment, needs, skills, traits, and a "Why this job" trace. Clicking a
  building (when no pawn is under the cursor) opens a derived building card:
  staffing, recipe I/O, banked cycle progress, production targets, the
  building's located source state (field growth/hours-to-ripe, node amounts,
  regrow status), and active exceptions.
- Pressing `L` connects to or disconnects from LM Studio/Ollama while the game
  is running; the HUD shows local model state (disabled/idle/thinking/offline/
  invalid).
- The right column lists active governor exceptions by severity and age (a
  chronic 5-day warning reads differently from a fresh one), then shows the
  selected pawn/building inspector.
- Every bottom command (`Architect`, `Work`, `Assign`, `Research`, `History`,
  `Menu`) opens a real docked panel; clicking the same button closes it, and
  opening another closes the previous one. `Esc` closes an open panel before
  quitting.
- The civilization autosaves daily and on exit to `saves/autosave.json`
  (git-ignored) and resumes on boot; pass `--new-world` to start fresh.

## Test And Build

Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m agent_town --smoke-test
.\scripts\validate-workbench.ps1
```

macOS/Linux:

```bash
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
PYTHONPATH=src .venv/bin/python -m agent_town --smoke-test
pwsh -NoProfile -File scripts/validate-workbench.ps1
```

Expected result:

- Core tests pass (385 as of this adoption, 2026-07-03; the count grows with
  new slices - do not hardcode a stale number in a claim, re-run and confirm).
- Smoke test exits without import or display errors.
- Workbench validation passes. `validate-workbench.ps1` requires `pwsh`; if
  unavailable, treat the check as skipped and record that in the proof row.
- Asset checks prove the civilization runtime sprites and provenance notes
  exist.

### Test Coverage Policy

Treat tests as the project specification, not as a comfort signal. The suite
should be strong enough that if someone accidentally deletes a meaningful line,
branch, route, data contract, workflow step, validation rule, or bug fix, at
least one test or documented manual check fails.

Coverage rules:

- Prefer red/green TDD: write or update the failing test first, confirm the
  expected failure, then implement the smallest fix.
- Run every relevant existing test before judging the suite.
- Keep tests that prove behavior a user, API consumer, operator, or future
  maintainer depends on.
- Improve tests that assert the wrong level, hide real failures, rely on stale
  fixtures, overuse snapshots, or pass without checking meaningful behavior.
- Remove tests that are stale, duplicated without adding a boundary, or pure
  bloat.
- If behavior cannot be tested in the current harness, record the exact reason
  and use the strongest concrete manual check available.

Watchable proof (required for any behavior slice with a visible consequence):

- A green suite is not proof the slice is watchable. Render a real frame of the
  new behavior and inspect it before calling it done (see `AGENTS.md`
  "Watchability Is Part Of Done"). Save proof frames under `docs\proof\<slice>\`.
- Headless render recipe: `SDL_VIDEODRIVER=dummy`, build the state, call
  `render_civilization(...)`, `pygame.image.save(...)`, then open the PNG.
- If the slice touches the local model, confirm the model path actually ran (a
  model loaded in LM Studio, a non-fallback outcome). A fallback-only run uses
  no model and no GPU and proves nothing about the LLM behavior.
- For viewer navigation or placement work, render at least a default-state
  proof plus one panel proof per changed command panel, and refresh
  `docs\screenshots\current-state.png` when the default screen changes.

## Manual Checks (per shipped slice)

Run the viewer and confirm:

- **Work arbiter:** open the `Work` grid, click a cell to cycle a pawn's
  priority (`1` highest .. `4` lowest .. blank off); the pawn re-routes within
  a step or two. No two pawns occupy the same single-slot building; the
  `Idle N` KPI rises when a work type is disabled that leaves a pawn with
  nothing legal. Select that pawn and read the inspector's "Why this job"
  trace. Headless proof: `unittest tests.test_work`.
- **Research spine:** a staffed Laboratory advances `research_points`; when
  `efficient_baking` completes, Bakery output rises from 4 to 5 bread/cycle.
  Headless proof: `unittest tests.test_research_spine`.
- **UI navigation:** `Architect` shows build options, counts, slots, cost,
  missing materials, and construction blockers. `Assign` selects a pawn on the
  left and job slots on the right; open/current rows pin a forced override,
  occupied rows select the worker holding the slot. `Research` shows current
  research plus disabled future entries with reasons. `History` shows recent
  decisions and events; clicking a Governor decision opens
  proposed/applied/rejected policy details with after-state goods/needs and a
  causality map. `Menu` shows run controls, local model status, and
  `1x`/`8x`/`20x` watch-speed buttons (the `History` title reflects the active
  speed). Clicking a button twice closes its panel; `Esc` with a panel open
  closes it without quitting.
- **Water essential:** the default civilization has a Water Well, Water in the
  KPI/goods panel, and Water in the selected-pawn needs inspector; `Water` is
  a Work grid type. Headless proof: `unittest tests.test_water`.
- **Storage caps:** the goods panel/Storehouse badge turn amber at >=80% full,
  red at >=95%. Headless proof: `unittest tests.test_storage_caps`.
- **Repair debt:** damaged buildings show a warning badge and a building-card
  condition row; below 75% condition they lose efficiency, and a staffed damaged
  building spends repair labour plus 1 plank + 1 stone before producing again.
  Storehouse service capacity scales with condition. Headless proof:
  `unittest tests.test_repair`. Proof frame: `docs/proof/repair_debt/`.
- **Money loop:** day rollover pays assigned pawns from treasury; a staffed
  Market sells bread to pawn wallets above reserve, records sales tax, and
  exports only the remaining surplus; unmet buyers surface as
  `market_service_pressure`. Headless proof: `unittest tests.test_money_loop`.
- **Physical sourcing:** a Farm's field visibly cycles bare -> growing % ->
  ripe; a Quarry/Forester node depletes (Forester regrows, Quarry does not);
  clicking a building shows its located source state. Headless proof:
  `unittest tests.test_sourcing` (15 tests, incl. "grain cannot outrun the
  season"). Proof frames: `docs/proof/physical_sourcing/`.
- **Save/load:** quit and relaunch; the civilization resumes from
  `saves/autosave.json` instead of resetting. Headless proof:
  `unittest tests.test_save` (10 tests, incl. the determinism oracle: a
  saved-then-reloaded civ steps 48h identically to one that never stopped).
  `--new-world` starts fresh.
- **Conservation ledger:** `health.check_invariants` reports zero violations
  across a 10-day run; a direct-mutation tamper test surfaces a CRITICAL
  `invariant_violation` event. Headless proof: `unittest tests.test_conservation`.
- **Model safety guard:** a model-origin `assign_pawn` or a survival-good
  production cap (grain/flour/bread/water = 0) is rejected with a reason
  visible in the History decision audit. Headless proof:
  `unittest tests.test_llm_governor.ModelGuardTests`.
- **Analyzer honesty:** a healthy-pipeline run with zero model-origin actions
  applied reports AMBER ("pipeline-only"), never GREEN. Headless proof:
  `unittest tests.test_analyzer_honesty`.
- **The trader (crisis-line Slice 3):** during a `low_food` exception the
  fallback governor's decision includes a `buy_good` action alongside the
  dig-out's `place_building`; the `History` panel's decision detail shows
  "buy bread xN from the trader" under Applied, with coin dropping by the
  bought amount times the bread trade price in the after-state; the `Research` panel's Trade
  row reads "Live" instead of "Not implemented yet". Headless proof:
  `unittest tests.test_trader` (31 tests). Proof frames:
  `docs/proof/trader/`. The optional local-LLM trader personality
  (`governor.trader_quip`) is tested via an injected fake client only - it has
  not been exercised against a live loaded model and is not wired into the
  live viewer loop (see `BLUEPRINT.md` "Crisis, response, consequence").

Starvation-escapability manual check (crisis/response Slice 0):

- The default civilization must sustain under the fallback governor: step it
  many days (or run `unittest tests.test_food`) and confirm bread stays on
  hand and pawns stay fed - the old frozen death spiral is gone.
- A fail state must stay reachable: with the bakeries removed no bread can be
  made and the civ still starves toward empty.
- Storage-cap interaction: the default civ seeds surplus-producer ceilings
  (water, logs, planks, stone) so an uncapped producer cannot flood the finite
  stockpile and crowd the food chain out; `unittest tests.test_dig_out` proves
  the healthy civ never over-builds and a marginal civ digs out and recovers.

## Monitoring A Run

Live viewer monitoring:

- Run the app and click `History` in the bottom strip (or press `Esc` to
  close). The panel shows recent structured decisions and events newest-first.
  Click a Governor decision to inspect source/model state, proposed/applied/
  rejected payloads, completed buildings, after-state goods/needs, and the
  causality map.
- Event rows include completed buildings, staple depletion, sustained supply
  stalls, pawn breaks, mass idle, mood dips/collapse, LLM dropped decisions,
  and invariant violations.
- Use `Menu` to switch between `1x`, `8x`, and `20x` watch speed.
- When warn/critical events occur the KPI strip's News chip lights up with a
  count and the `History` button glows; opening the feed acknowledges them.
- The macro Governor summary and right-side exception stack are observer
  surfaces, not command editors.
- Live viewer runs also write a JSONL log under `logs\`; these are local proof
  artifacts and are git-ignored.

Headless run plus analyzer (post-run health gate):

```powershell
.\.venv\Scripts\python.exe scripts\llm_governor_run.py --hours 24
.\.venv\Scripts\python.exe scripts\analyze_run.py logs\run-YYYYMMDD-HHMMSS.jsonl --events
```

Expected result:

- The runner prints each hour's applied actions and the JSONL log path, then a
  one-line health verdict (`GREEN` / `AMBER` / `RED`).
- The analyzer prints run metadata (with `run_id`), the health summary, flagged
  events, and `RESULT: GREEN|AMBER|RED`.
- The analyzer exits non-zero on a red condition (invariant violation, food
  staple depletion, mood collapse, or a high dropped-decision rate).
- A healthy-pipeline run with zero model-origin actions applied is AMBER
  ("pipeline-only"), never GREEN (analyzer honesty; see Fable review Slice D in
  `BLUEPRINT.md`).
- A run with no local model loaded logs cleanly as deterministic fallback and
  is **not** counted as dropped LLM decisions.

## Evaluation And Benchmarking

Scaling benchmark:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000
```

Expected result: a CSV-style table reports engine step time, governor
context-build time, dummy draw time, final applied action count, and
completed-building count. Use this before increasing default population size
or deciding whether Pygame is the scaling blocker. Scale interpretation lives
in `BLUEPRINT.md` -> Scale architecture and
`research_papers/7.scalable-sim-report.md`.

Mac/hosted LM acceptance gate (main end-to-end evaluation before a slice is
"ready to merge"): install, smoke, full unit discovery, `validate-workbench.ps1`,
an LM Studio ping, a booted `CivilizationViewer` with a blocking `LLMGovernor`,
~96 simulated viewer hours, and `analyze_run.py` returning `RESULT: GREEN`, with
the run report saved under `docs/run_reports/`. AMBER/RED are not GREEN. Real
hosted-provider runs spend budget; record model, conditions, hours, cost, and
the result path before making claims (see `docs/run_reports/` for the existing
pattern).

## Research Intake

Research papers live in `research_papers/`. They are design inputs and source
leads, not automatic proof that the current code behaves that way.

When adding or using a paper:

1. Keep the raw paper file intact unless the user explicitly asks to rename or
   reorganize it.
2. Read the relevant paper before editing active docs or code.
3. Extract only the project rule, affected files, tests, risks, and deferrals.
4. If the paper conflicts with current implementation, record the conflict in
   `TASKBOARD.md` instead of silently changing the design.
5. If exact constants affect code behavior, verify the cited source or mark
   the value as research-derived in the test/doc note.

Workbench-only research integration check:

```powershell
.\scripts\validate-workbench.ps1
git diff --check
```

Use the full verification path when the research intake also changes runtime
code, tests, assets, or viewer behavior.

## Data Operations

The civilization persists via `save.py`: a versioned JSON round-trip of the
full `FactionState` (pawns with thoughts/priorities, buildings with banked
cycles and owned fields, the conservation journal, nodes mid-growth, research,
clock). Static recipe data is rebuilt from the building catalogue on load so
rebalances apply to old saves. The viewer autosaves daily and on exit to
`saves/autosave.json` (git-ignored) and resumes on boot; `--new-world` starts
fresh.

Safety rules:

- Do not wire a second persistent local database into automatic viewer
  behavior without updating `BLUEPRINT.md`, `RUNBOOK.md`, and tests.
- Do not store real private data in future pawn or governor memory unless the
  user explicitly approves that use.
- Never commit `saves/` contents; they are git-ignored local run state.

## Deployment Or Startup

There is no deployment target. The project runs locally through PowerShell
(Windows) or the venv entry point (macOS/Linux).

## Version Control

This repo uses a three-tier branch model; full rules live in `BRANCHING.md`
(kept as a project-local reference, not folded away by this harness):

- Branch **from `integration`**, and open pull requests **into `integration`**,
  never into `main` directly. Branch names: `codex/<task>`, `claude/<task>`,
  `feat/<slice>`, `fix/<thing>`, `docs/<thing>` - short, kebab-case, specific.
- `integration` is the shared root every agent forks from and merges back
  into. `main` is human-owned; only Kayden promotes `integration -> main`, and
  only for states that have been watched running.
- Commit messages: imperative subject <= 72 chars, the why in the body; one
  logical change per commit. Run `git status` before committing.
- Merge feature branches into `integration` with a merge commit (do not
  squash); delete the feature branch after it merges.
- Never commit secrets, `.env` files, local databases, `logs/`, `saves/`,
  build output, or generated artifacts.
- Open a pull request with `gh` when the task is verified; the PR states what
  changed, why, risks, and how it was verified.
- Do not rewrite published history or force-push shared branches unless the
  user explicitly approves.

## Upgrading The Harness

These control docs were generated from a specific LLM Workbench version,
recorded in the `Generated from LLM Workbench v2.1` stamp at the top of each
doc. That stamp lets you tell when the project is running an older harness
than the current one.

To upgrade:

1. Check the LLM Workbench repo's releases/changelog for what changed since
   v2.1.
2. Re-copy only the changed template sections; keep this project's filled-in
   specifics. Never let unfilled template placeholder tokens leak back into
   filled docs.
3. Update each doc's version stamp to the new version.
4. Re-run the full verification suite (above) and record the upgrade as a
   proof-log row in `TASKBOARD.md`.

Treat a harness upgrade like any other change: smallest correct diff, verified,
with proof. If a downstream lesson should flow back to the harness, capture it
in `HARNESS_FEEDBACK.md`.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: pygame` | Setup was not run or wrong Python is being used | `.\.venv\Scripts\python.exe -c "import pygame"` | Run `.\setup.ps1` |
| Double-click does nothing visible | Windows did not execute the PowerShell script directly | Open `Launch Local Agent Town.cmd` | Use the `.cmd` launcher |
| Window does not open | Display or Pygame issue | `.\.venv\Scripts\python.exe -m agent_town --smoke-test` | Reinstall through `.\setup.ps1`; check local graphics environment |
| macOS picks Python 3.9 | System Python selected | `python3 --version` | Use `python3.12` explicitly for the venv |
| Local model shows disabled | Toggle is off, no local chat model was found, or `AGENT_TOWN_LLM_AUTO_DISCOVER=0` | Inspect the HUD governor row | Start LM Studio/Ollama, load a model, then press `L`; or set `AGENT_TOWN_LLM_MODEL` |
| Local model shows offline | LM Studio/Ollama server is not running or URL is wrong | Check `AGENT_TOWN_LLM_BASE_URL` | Start the local server or change the URL |
| Local model shows invalid reply | Model returned malformed JSON or an unknown action | Inspect the HUD governor row | Use a smaller/faster instruct model and keep max tokens low |
| `validate-workbench.ps1` fails | Required doc missing a heading, unresolved placeholder, or `pwsh` unavailable | `pwsh -File scripts/validate-workbench.ps1` | Update the named doc; install PowerShell or record the check as skipped |

## Recovery And Rollback

If a change fails:

1. Identify the touched files and failing command.
2. Revert only the smallest change needed, preserving user work.
3. Rerun the failing verification command.
4. Update `TASKBOARD.md` with the result and remaining gap.

Do not delete data, reset repositories, rewrite history, or rotate secrets
unless the user explicitly approves that action.

## Operational Proof

If a command in this runbook changed durable project state, append a row to
the `TASKBOARD.md` proof log. For routine local runs that do not change state,
a final response note is enough.
