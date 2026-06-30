# Local Agent Town - Runbook

**Last reviewed:** 2026-06-28
**Runtime owner:** Kayden  
**Environment:** local desktop

This file explains how to operate the project.

## Prerequisites

Required tools:

- Windows PowerShell.
- Python 3.11 or newer.

Required accounts or services:

- None for the base prototype.
- Optional: a local OpenAI-compatible LLM server such as LM Studio or Ollama.

Required local files:

- None before setup. `setup.ps1` creates `.venv`.

## Environment Configuration

No `.env` file is required for the base prototype.

Required variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `SDL_VIDEODRIVER` | Optional Pygame smoke-test override | no | `dummy`, set automatically by `--smoke-test` |

Optional local model variables:

| Variable | Purpose | Secret | Example or notes |
|---|---|---|---|
| `AGENT_TOWN_LLM_MODEL` | Optional explicit model override | no | `google/gemma-4-e4b`, or the exact model id loaded in LM Studio/Ollama |
| `AGENT_TOWN_LLM_BASE_URL` | OpenAI-compatible local endpoint | no | `http://localhost:1234/v1` for LM Studio, `http://localhost:11434/v1` for Ollama |
| `AGENT_TOWN_LLM_TIMEOUT` | Per-request timeout in seconds | no | default `4.0` |
| `AGENT_TOWN_LLM_MAX_TOKENS` | Max tokens for compact decision JSON | no | default `180` |
| `AGENT_TOWN_LLM_AUTO_DISCOVER` | Controls startup model discovery when no model is set | no | default `1`; set `0` to keep local model disabled unless `AGENT_TOWN_LLM_MODEL` is set |

Rules:

- Do not commit real `.env` files, tokens, local databases, logs, or private data.
- Keep future LLM provider credentials local-only.
- Prefer a visible degraded state over fake external data when a future provider is unavailable.
- If no model variable is set, the app briefly checks the configured `/models` endpoint and selects the first non-embedding local model it finds.

## Install

```powershell
.\setup.ps1
```

Expected result:

- `.venv` exists.
- The package installs editable into `.venv`.
- Pygame is available inside `.venv`.

## Asset Preparation

The civilization viewer uses runtime sprites under `src\agent_town\assets\colony`.

When adding a new free asset:

- Verify the source URL, license, author, and attribution requirements before download.
- Prefer CC0 or public domain. Use CC-BY only when attribution is recorded next to the imported files.
- Keep the original download or source zip untouched and generate runtime files from it.
- Update nearby asset notes and asset tests when the runtime asset set changes.
- If no license-safe asset fits, use the smallest temporary placeholder and record that it should be replaced.

## Run Locally

```powershell
.\run.ps1
```

Double-click launcher:

```text
Launch Local Agent Town.cmd
```

Open:

- A local Pygame desktop window titled `Local Agent Town`.

Expected result:

- A civilization map appears.
- The engine advances simulated hours over time.
- Civilization sprites appear for terrain, buildings, resources, and pawns.
- A top pawn roster shows colonist portraits, names, mood dots, and selection.
- Mouse wheel, `+`, and `-` zoom.
- `WASD` or arrow keys pan.
- Clicking a pawn, or pressing `Tab`, updates the pawn sheet with status,
  assignment, needs, skills, and traits, plus a "Why this job" trace: the winning
  decision lane, the reason, and the top job the pawn passed over.
- The HUD shows an `Idle N` count (pawns with no work the arbiter could give)
  and stockpile chips including Bread and Water; idle pawns also get a small
  overhead `!` badge after the arbiter marks them idle.
- Hovering a pawn shows a lighter world outline than selection; selected pawns
  keep a double outline, and break/stress danger rings draw above selection.
- Active construction sites render as translucent building ghosts with a
  footprint outline and progress bar.
- The Civ stats panel shows Mood, Food, Water, Recreation, and Rest.
- Pressing `L` connects to or disconnects from LM Studio/Ollama while the game is running.
- The HUD shows local model state: disabled, idle, thinking, offline, or invalid.
- A bottom-left Governor card stays visible with the current plan, phase,
  bottleneck, confidence, last policy change, and top exception.
- A right-edge exception stack lists the active governor exceptions by severity,
  including the likely cause for the highest-priority problems.
- The `Work` button opens the work-priority grid; the `History` button opens a
  live run-event feed. The remaining command buttons (`Architect`, `Assign`,
  `Research`, `Menu`) are still placeholders.

Work-priority arbiter manual check (build-2 step 1):

- Click the bottom-strip `Work` button (or press `Esc` to close it). A grid of
  pawns (rows) by work types (columns) appears, each cell showing the effective
  priority `1`-`4` (blank = disabled), brightest at `1`.
- Click a cell to cycle its priority (`1` highest .. `4` lowest .. blank off).
  Within a second or two the pawn re-routes: disable a baker's `Bake` and set its
  `Farm` to `1`, and watch it leave the Bakery and walk to a Farm.
- Confirm no two pawns occupy the same single-slot building, and that the `Idle`
  count rises if you disable a work type that leaves a pawn with nothing legal.
- Select that pawn and read the inspector's "Why this job" trace to see the lane
  it won under and the job it rejected (e.g. `Passed over Bakery: reserved/full`).
- `Research` appears as a work type once Laboratory work exists; the bottom-strip
  `Research` button is still a placeholder until a research panel is built.

Research spine manual check (truth-loop slice):

- A `Laboratory` is buildable after the essential build order. The fallback
  Governor then selects the first tech, `efficient_baking`.
- A staffed Laboratory advances `research_points`; when the tech completes,
  Bakery output rises from 4 bread per cycle to 5.
- For a headless proof, run
  `.\.venv\Scripts\python.exe -m unittest tests.test_research_spine`.

Water essential manual check (build-2 water slice):

- Start the viewer and confirm the default civilization has a Water Well,
  Water in the HUD stockpile chips, and a Water row in the Civ stats panel.
- Open the `Work` grid and confirm `Water` is a work type. A water-skilled pawn
  should staff the Water Well under the arbiter.
- For a headless proof, run `.\.venv\Scripts\python.exe -m unittest tests.test_water`.
  It covers Water Well production, drinking, days of cover, and the `low_water`
  governor exception.

Map readability manual check (Paper 5 current-systems slice):

- Move the mouse across pawns and confirm hover uses a thin amber outline while
  the selected pawn keeps the stronger double outline.
- Temporarily remove or disable one work slot in a test state, step one hour,
  and confirm the idle pawn has an overhead `!` badge matching the HUD `Idle N`.
- Create or observe an active construction site and confirm it shows a ghost,
  footprint outline, and progress bar before completion.
- Storage pressure badges are intentionally deferred until stockpile capacity
  exists; do not fake 80/95% storage warnings from uncapped stockpile totals.

## Monitoring A Run

Live viewer monitoring:

- Run the app and click `History` in the bottom strip (or press `Esc` to close).
  The panel shows recent structured events newest-first from an in-memory ring:
  completed buildings, the food staple depleting, sustained supply stalls, pawn
  breaks, mass idle, mood dips/collapse, LLM dropped decisions, and invariant
  violations.
- When warn/critical events occur the HUD shows a coloured alert chip with a
  count and the `History` button glows; opening the feed acknowledges them.
- The Governor card and exception stack are live observer surfaces, not command
  editors; use them to diagnose whether the current bottleneck is supply,
  staffing, mood, model availability, or construction.
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
  staple depletion, mood collapse, or a high dropped-decision rate). An
  interrupted log with no `run_end` is summarized over completed hours and noted
  as incomplete rather than failing.
- A run with no local model loaded logs cleanly as deterministic fallback and is
  **not** counted as dropped LLM decisions.

## Test And Build

Workbench validation:

```powershell
.\scripts\validate-workbench.ps1
```

Fast check:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Full verification:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
.\.venv\Scripts\python.exe -m agent_town --smoke-test
.\scripts\validate-workbench.ps1
```

Expected result:

- Core tests pass.
- Smoke test exits without import or display errors.
- Workbench validation passes.
- Asset checks prove the civilization runtime sprites and provenance notes exist.

Scaling benchmark:

```powershell
.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000
```

Expected result:

- A CSV-style table reports engine step time, governor context build time, dummy draw time, final applied action count, and completed-building count.
- Use this before increasing default population size or deciding whether Pygame is the scaling blocker.

Scale interpretation from `research_papers/7.scalable-sim-report.md`:

- At about 12 pawns, keep player-visible truth exact.
- Before raising default population, add reachability-region rejection and
  deterministic update phases.
- Around 16 to 64 pawns, add job candidate indexes and cadence buckets.
- Around 64 to 150 pawns, add long-route abstraction or shared routes for common
  sinks before relying on exact per-pawn paths.
- Around 150 to 400 pawns, use district work packets and path budgets.
- Around 400 to 1000 pawns, use offscreen ETA movement, far-needs cadence, and
  strong visual/overlay LOD.

If a pawn is selected, visible, in conflict, touching scarce resources, or
transferring ownership of a good/building/job, force it into exact simulation.
Only approximate opportunity search and offscreen movement.

## Research Intake

Research papers live in `research_papers/`. They are design inputs and source
leads, not automatic proof that the current code behaves that way.

When adding or using a paper:

1. Keep the raw paper file intact unless the user explicitly asks to rename or
   reorganize it.
2. Read the relevant paper before editing active docs or code.
3. Extract only the project rule, affected files, tests, risks, and deferrals.
4. If the paper conflicts with current implementation, record the conflict in
   `ROADMAP.md` instead of silently changing the design.
5. If exact constants affect code behavior, verify the cited source or mark the
   value as research-derived in the test/doc note.

Workbench-only research integration check:

```powershell
.\scripts\validate-workbench.ps1
git diff --check
```

Use the full verification path when the research intake also changes runtime
code, tests, assets, or viewer behavior.

## Data Operations

There is no civilization save/load UI or persistence model yet.

Safety rules:

- Do not wire persistent local databases into automatic viewer behavior without updating `BLUEPRINT.md`, `RUNBOOK.md`, and tests.
- Do not store real private data in future pawn or governor memory unless the user explicitly approves that use.

## Deployment Or Startup

There is no deployment target. The project runs locally through PowerShell.

## Troubleshooting

| Symptom | Likely cause | Check | Fix |
|---|---|---|---|
| `ModuleNotFoundError: pygame` | Setup was not run or wrong Python is being used | `.\.venv\Scripts\python.exe -c "import pygame"` | Run `.\setup.ps1` |
| Double-click does nothing visible | Windows did not execute the PowerShell script directly | Open `Launch Local Agent Town.cmd` | Use the `.cmd` launcher, which calls the PowerShell launcher with the right policy |
| Window does not open | Display or Pygame issue | `.\.venv\Scripts\python.exe -m agent_town --smoke-test` | Reinstall through `.\setup.ps1`; check local graphics environment |
| Local model shows disabled | The in-game toggle is off, no local chat model was found, or `AGENT_TOWN_LLM_AUTO_DISCOVER=0` | Inspect the HUD governor row | Start LM Studio/Ollama, load a model, then press `L`; or set `AGENT_TOWN_LLM_MODEL` exactly as the local server expects it |
| Local model shows offline | LM Studio/Ollama server is not running or URL is wrong | Check `AGENT_TOWN_LLM_BASE_URL` | Start the local server or change the URL |
| Local model shows invalid reply | Model returned malformed JSON, unknown action, or the server rejected the request payload | Inspect the HUD governor row | Use a smaller/faster instruct model and keep max tokens low |
| Workbench validation fails | Required docs missing headings or unresolved placeholders | `.\scripts\validate-workbench.ps1` | Update the named doc and rerun validation |

## Recovery And Rollback

If a change fails:

1. Identify the touched files and the failing command.
2. Revert only the smallest change needed, preserving user work.
3. Rerun the failing verification command.
4. Append the result to `ROADMAP.md` if durable state changed.

Do not delete data, reset repositories, rewrite history, or rotate secrets unless the user explicitly approves that action.

## Operational Proof

If a command in this runbook changed durable project state, append a row to the `ROADMAP.md` Verification Log. For routine local runs that do not change state, a final response note is enough.
