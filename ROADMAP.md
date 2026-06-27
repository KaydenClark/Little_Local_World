# Local Agent Town - Roadmap

**Current phase:** prototype  
**Owner:** Kayden and local coding agents

This is the active work plan. Keep it forward-looking and proof-oriented.

## Current State

The project is mid-refactor from the AI-Town social wander-sim into a
single-faction, LLM-governed colony builder. The authoritative build plan is
`Local_little_world_refactor1.md`; `BLUEPRINT.md` carries the stable summary.

Phase 0 is complete: the frozen colony contract lives in `core.py` (Good,
GridMap, ResourceNode, Stockpile, Recipe, Building, ConstructionSite, Pawn,
JobRef, ScheduleTemplate, FactionState, ColonyException, GovernorAction), eight
stubbed colony modules exist (world, economy, buildings, construction, pawns,
mood, schedule, governor), and the `effective_work` cross-track seam is defined
in `mood.py` (returns a 1.0 placeholder until milestone B2).

Important drift or uncertainty:

- The legacy social-sim (`Agent`, `Simulation`, `Location` in `core.py`, plus
  the current `app.py`, `persistence.py`, `spatial.py`) is intentionally kept
  importable and green so the existing Pygame viewer keeps working. It is
  retired when the viewer is rewritten to render colony state at milestone I3.
- Track A (world/economy/buildings/construction) and Track B (pawns/mood/
  schedule/governor) behavioural bodies are still stubs raising
  NotImplementedError.
- Local LLM planning remains an optional local OpenAI-compatible adapter in
  `llm.py`, to be extended into the LLM governor at milestone I2.

## Current Goal

Build the deterministic colony engine bottom-up under the Phase 0 contract:
Track A (economy and world) and Track B (pawns and governor), then integrate so
the fallback governor keeps about 12 pawns alive across simulated days headless.

Done when:

- Track A milestones A1 to A4 pass headless tests (map, one chain, construction,
  multi-chain plus tax loop);
- Track B milestones B1 to B4 pass headless tests (needs/schedule/mood,
  effective_work, traits/wants/breaks, context plus fallback governor);
- integration I1 shows the fallback governor sustaining the colony for N days
  with no death spiral;
- the smoke test still exits successfully and workbench validation passes.

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
| 2026-06-27 | Phase 0: freeze colony-builder contract and stub module skeletons | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added the frozen colony contract to `core.py`, eight stubbed colony modules (world, economy, buildings, construction, pawns, mood, schedule, governor), and contract tests (65 tests, was 55). Behavioural bodies are stubbed for Track A and Track B; the `effective_work` seam returns a 1.0 placeholder. Legacy social-sim kept importable until the viewer is rewritten at milestone I3 |
