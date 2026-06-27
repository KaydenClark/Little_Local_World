# Local Agent Town - Roadmap

**Current phase:** prototype  
**Owner:** Kayden and local coding agents

This is the active work plan. Keep it forward-looking and proof-oriented.

## Current State

The project has a local Python desktop slice: a Pygame town viewer, ten autonomous NPCs, selectable inspection state, suggestion input, Kenney sprites/emotes, event feed, spatial-indexed social checks, SQLite snapshot/replay helpers, a scaling benchmark script, and unit-tested simulation core.

Important drift or uncertainty:

- Pygame was not installed globally when the project was created; local `.venv` setup is required.
- LLM-backed planning is implemented as an optional local OpenAI-compatible adapter. It uses `AGENT_TOWN_LLM_MODEL` when set, otherwise it quickly discovers a local non-embedding model from the configured `/models` endpoint when LM Studio/Ollama is already running.
- Persistence exists as an explicit SQLite helper for snapshots and event-log replay. The viewer does not autosave or expose load UI yet.

## Current Goal

Stabilize the first local LLM-backed desktop prototype while keeping the non-LLM town loop reliable and measuring scale before broad feature work.

Done when:

- core and LLM adapter tests pass;
- the Pygame smoke test opens, draws assets briefly, and exits;
- the scaling benchmark can be run for 100, 500, and 1,000 synthetic agents;
- workbench validation passes.

## Next Tasks

1. **Run and record scale baselines** - run `scripts\benchmark_scaling.py` after each major simulation change and compare 100, 500, and 1,000 agent results. Proof: benchmark output copied into the relevant task notes or verification row.
2. **Manual LM Studio/Ollama tuning pass** - run Gemma 4 E4B-it, Qwen3.5-4B, and Phi-4-mini-instruct locally and record which model gives the best speed/personality balance. Proof: manual notes with model status and responsiveness.
3. **Viewer save/load command** - wire the tested SQLite helper into an explicit local save/load path. Proof: manual viewer check plus persistence tests.
4. **Deeper objects and places** - add usable objects and location-specific tasks. Proof: deterministic simulation tests and viewer smoke test.

## Blocked Or Deferred

Do not start these until their prerequisite is met.

| Item | Blocked on | Why it matters |
|---|---|---|
| Hosted AI providers | explicit user approval | Avoids accidental paid or network-dependent behavior |
| Multiplayer or remote viewing | explicit product direction change | Current requirement is local and not web based |
| Large map editor | stable core loop | Editing tools are less useful before agent behavior is interesting |
| Engine migration | benchmark evidence that Pygame rendering or editor tooling is the blocker | Current measured risk is simulation scale, persistence, and future pathfinding before rendering |

## Backlog

- Add event feed and time controls.
- Add places with objects and tasks.
- Add agent-to-agent message summaries.
- Add screenshots or GIF capture for quick review.
- Add pathfinding benchmark before implementing obstacles or large maps.

## Release Checks

Verification commands live in `RUNBOOK.md` Test And Build.

Project-specific release and checkpoint checks:

- Confirm no `.venv`, logs, databases, private exports, or generated dumps are included.
- Confirm no web server or browser runtime was introduced.
- Confirm `ROADMAP.md` Verification Log has a current row for durable state changes.

## Verification Log

Append a row when a task changes durable project state. Use actual results, not stale claims.

| Date | Task | Proof | Result | Remaining gap |
|---|---|---|---|---|
| 2026-06-26 | Add double-click desktop launcher | `& '.\Launch Local Agent Town.ps1' -SmokeTest`; `.\scripts\validate-workbench.ps1` | pass | `.cmd` wrapper is intended for File Explorer double-click; smoke test verified the PowerShell launch path |
| 2026-06-26 | Bootstrap prototype and adopt workbench structure | `.\setup.ps1`; `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | LLM-backed planning and persistence remain deferred |
| 2026-06-26 | Add optional local LLM planning and Kenney sprite viewer slice | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Manual LM Studio/Ollama model tuning remains next |
| 2026-06-26 | Prepare main branch publish to GitHub | `gh repo view KaydenClark/Little_Local_World --json nameWithOwner,defaultBranchRef,isPrivate,isArchived,url`; `.\scripts\validate-workbench.ps1` | pass | GitHub push performed after this row |
| 2026-06-26 | Fix LM Studio local planning startup | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; live `LocalLLMClient.from_env()` request against `http://localhost:1234/v1` auto-selected `google/gemma-4-e4b` | pass | Already-running game windows must be closed and relaunched to pick up the fix |
| 2026-06-26 | Fix wrong character sprite indices and expand test coverage for agents/buildings/app rendering | `python3 -m unittest discover -s tests` (46 tests, was 17) | pass | `characters.png` column 0 holds full single-tile characters; the old `sprite_index` values (4,8,...,40) pointed into cape/hood/hat layering columns instead, so 9 of 10 agents rendered as clothing fragments and Pax (index 32) rendered fully blank; reassigned all 10 agents to distinct non-blank column-0 indices and added regression tests asserting every agent sprite is non-blank and unique |
| 2026-06-26 | Reset visual design around Kenney assets and colony/RTS readability | `.\scripts\prepare-kenney-assets.ps1`; `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Next step is implementing the tile-cluster map and HUD changes described in `VISUAL_DESIGN.md` |
| 2026-06-26 | Replace circle-style map markers with tile-based colony visuals | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; temp rendered frame inspected at `C:\Users\kayde\AppData\Local\Temp\local-agent-town-visual-final.png` | pass | Still uses the bundled Kenney sheet only; future polish can add more varied authored tile clusters |
| 2026-06-26 | Shift visual direction toward Age of Empires settlement readability | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; temp rendered frame inspected at `C:\Users\kayde\AppData\Local\Temp\local-agent-town-aoe-rimworld-final.png` | pass | Uses existing Kenney sheets; true AoE-style isometric buildings would require a richer building asset pass |
| 2026-06-27 | Document free-asset-first sourcing rule | `.\scripts\validate-workbench.ps1` | pass | No new asset was imported; future asset work still needs per-asset license verification |
| 2026-06-27 | Implement scale boundary slice | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000` | pass | Benchmark result: 1,000 synthetic agents measured 4.862 ms core step, 2.420 ms LLM context build, and 13.744 ms dummy draw frame; viewer save/load UI remains future work |
| 2026-06-27 | Merge current `main` test coverage into scale boundary branch | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000` | pass | Latest merged benchmark result: 1,000 synthetic agents measured 4.617 ms core step, 2.399 ms LLM context build, and 12.477 ms dummy draw frame |
