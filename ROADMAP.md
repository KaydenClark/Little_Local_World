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
colony modules exist (world, economy, buildings, construction, pawns, mood,
schedule, governor), and the `effective_work` cross-track seam is defined in
`mood.py`.

Track A is complete against the current PC contract (A1 to A4): stockpile
operations, deterministic map and resource nodes, build-1 building definitions,
production through the real `effective_work` seam, construction sites with
delivery/work/completion, affordability, multi-chain production, and daily tax
income.

Track B is complete (B1 to B4): schedule templates and clock rollover in
`schedule.py`; need decay/restoration and the break state machine in `pawns.py`;
the real `effective_work` seam plus trait/want mood modifiers in `mood.py`; and
the exception queue, context builders, action validation/application, and the
deterministic `FallbackGovernor` in `governor.py`. The fallback now also emits
the next missing build-1 chain building as a `place_building` action while
leaving construction-site realization to Track A.

Integration I1 has its first headless regression: a seeded 12-pawn colony runs
for three simulated days under the fallback governor with production, needs,
mood, bread meals, and daily tax staying above the asserted floors. This is
still a test harness over the colony modules, not a reusable engine loop.

Important drift or uncertainty:

- The legacy social-sim (`Agent`, `Simulation`, `Location` in `core.py`, plus
  the current `app.py`, `persistence.py`, `spatial.py`) is intentionally kept
  importable and green so the existing Pygame viewer keeps working. It is
  retired when the viewer is rewritten to render colony state at milestone I3.
- I1 is not yet a reusable engine object/function. The proof lives in
  `tests/test_integration_i1.py`, which is enough to protect the seam but should
  be extracted into a real headless stepper before viewer work.
- Local LLM planning remains an optional local OpenAI-compatible adapter in
  `llm.py`, to be extended into the LLM governor at milestone I2.

## Current Goal

Turn the passing Track A + Track B module set into a reusable deterministic
colony stepper, then extend it through I2/I3 so the local LLM governor and
viewer run against real colony state.

Done when:

- a reusable headless engine step replaces the I1 test harness while preserving
  the three-day fallback survival proof;
- the LLM governor can drop in behind the fallback interface without blocking
  the sim loop;
- the viewer renders colony state instead of the legacy social-sim state;
- the smoke test still exits successfully and workbench validation passes.

## Next Tasks

1. **Extract the I1 headless stepper** - move the test-harness loop into a
   reusable colony engine function that applies fallback actions, realizes
   construction, advances production/needs/mood/tax, and preserves the
   three-day survival test.
2. **LLM governor I2** - add the local LLM governor behind the fallback
   interface with schema validation and hard fallback. Proof: manual Gemma 4
   E4B run log plus deterministic fallback tests still green.
3. **Viewer I3** - render colony buildings, pawns, stockpile, mood, and
   construction state in `app.py`, then retire the legacy social-sim only after
   the new viewer smoke test is green.
4. **Manual LM Studio/Ollama tuning pass** - run Gemma 4 E4B-it, Qwen3.5-4B,
   and Phi-4-mini-instruct locally and record which model gives the best
   speed/personality balance.

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
| 2026-06-27 | Track B B1: pawn needs, schedules, clock, and base mood | `.\.venv\Scripts\python.exe -m unittest tests.test_track_b_b1`; `.\.venv\Scripts\python.exe -m unittest tests.test_colony_contract tests.test_track_b_b1`; `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added 11 B1 tests. Implemented default/night/rest schedules, clock rollover, build-1 need decay/restoration, schedule-block restoration, and base mood from need satisfaction. B2 effective-work factors, B3 breaks/exceptions, and B4 governor remain pending |
| 2026-06-27 | Track B B2 to B4: effective_work, breaks/exceptions, fallback governor | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added 18 tests (94 total, was 76). Implemented the real `effective_work` seam (skill/mood/trait/schedule factors), trait/want mood modifiers, the break state machine, the governor exception queue, faction/roster/buildings context, action validate/apply, and the deterministic `FallbackGovernor`. Repointed the contract stub test at the remaining Track A stubs. Remaining gap: `place_building` is emitted but realised by Track A construction at integration I1 |
| 2026-06-28 | Port Track A into current Track B contract and add I1 regression | `.\.venv\Scripts\python.exe -m unittest tests.test_track_a_current_contract tests.test_track_b_b4 tests.test_integration_i1 tests.test_colony_contract`; `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --agents 100 500 1000` | pass | Ported PR #5 Track A behavior into the current dict-based PC contract instead of merging old files. Added stockpile/world/building/economy/construction tests, updated the Track B fallback place-building handoff, and added a seeded three-day I1 survival regression. Remaining gap: I1 is still a test harness, not a reusable headless engine stepper |
| 2026-06-28 | Add in-game LM Studio connect/disconnect toggle | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added runtime scheduler reconnect/disable support and a Pygame `L` key toggle with panel guidance. Already-running game windows must be relaunched to pick up this code change |
| 2026-06-28 | Make the LM Studio toggle visible and clickable | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added a high-visibility `LM Studio` panel control near the selected pawn header and made it clickable, while keeping `L` as the shortcut |
| 2026-06-28 | Document visible-controls-first feature rule | `.\scripts\validate-workbench.ps1` | pass | Updated `BLUEPRINT.md` so future user-facing features prioritize visible buttons, toggles, icon/state indicators, and color cues over keypress-only controls |
| 2026-06-28 | Convert side-panel runtime controls to visible UI buttons and LM switch | `python3 -m py_compile src/agent_town/app.py`; `python3 -m unittest tests.test_app` (blocked: pygame missing); `python3 -m pip install -e .` (blocked: package index 403 for setuptools build dependency) | partial | Code compiles; runtime/unit verification needs the project Python environment with pygame available |
