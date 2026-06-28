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

Integration I1 is complete: the test-harness loop is extracted into a reusable
deterministic stepper in `engine.py` (`step_hour` / `run` / `run_days`). It
applies governor actions, realizes affordable `place_building` actions into
construction (haul -> work -> built), advances per-pawn needs/mood/breaks, runs
production through the `effective_work` seam, and collects daily tax on
rollover. The seeded 12-pawn three-day fallback-survival regression now runs
through the engine, and `test_engine.py` covers construction completion,
unaffordable-placement skipping, and determinism.

Important drift or uncertainty:

- The legacy social-sim (`Agent`, `Simulation`, `Location` in `core.py`, plus
  the current `app.py`, `persistence.py`, `spatial.py`) is intentionally kept
  importable and green so the existing Pygame viewer keeps working. It is
  retired when the viewer is rewritten to render colony state at milestone I3.
- The default `python -m agent_town` view is now the colony viewer
  (`colony_view.py`), which renders the colony `FactionState` and steps the
  engine. The legacy social-sim (`app.py`, `create_default_simulation`) is still
  importable and tested; it is retired once the colony viewer reaches parity
  (camera, pawn-selection panel, LLM toggle).
- The LLM governor (I2) exists headless: `governor.LLMGovernor` implements the
  same `decide(context)` interface backed by `LocalLLMClient.complete_json` with
  a JSON-schema action list and a hard fallback to `FallbackGovernor` on any
  error. It is proven faithful (an always-failing LLM governor drives the colony
  identically to the fallback over three days). Remaining for the bridge: a
  live-model run log (needs LM Studio/Gemma; `scripts/llm_governor_run.py`) and
  wiring it into the real-time viewer **without blocking** the sim loop (reuse
  the `LLMDecisionScheduler` async pattern), after which the legacy social-sim
  retires.

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

## Build arc (the long road)

The immediate goal above finishes build 1. The product then grows in builds,
each gated on the prior. Conservation ("nothing from nothing", `BLUEPRINT.md`)
governs every system. The full content design lives in `BLUEPRINT.md`'s "Target
content design"; this is the sequencing.

- **Build 1 - one colony works (current).** About 12 pawns, 3 chains (wood,
  food, stone), construction, needs/mood/breaks, happiness-to-tax, deterministic
  fallback Governor then the LLM Governor, viewer renders colony state.
- **Build 2 - depth and the spectator.** Water and clothes/beauty chains; the
  full needs set (water, shelter, clothes, beauty); building quality to
  happiness; decay + repair as a material/coin sink; the wage money loop
  (wages -> spend -> tax) with the Market and Tavern; storage caps and a
  "storage full %" readout; RimWorld work priorities (`set_work_priority`) and
  the per-colony spectator view; skill-based healthcare (Infirmary + optional
  medicine); the Church as recreation/mood; operator-triggered disasters; the
  revolution meter plus the keep and fail state; pets as decor; save state.
- **Build 3 - the people are real.** Pawn lifecycle: aging, productivity bands,
  death; birth from two parent pawns with lineage; the home -> barracks ->
  trained -> deployable soldier pipeline; Watch Tower soldier slots; Police and
  Firehouse; the ore -> metal -> tools/parts chain; cooking and meat. Soldiers
  want beer + meat.
- **Build 4 - competition and the Space Age.** Two Governor agents, one shared
  map, finite contested resources, rivals unaware at first. The research spine
  to the industrial tier (components) and the space-program endgame: the first
  colony to launch wins, and outlasting the rival is the implied secondary win.
  Scale target up to about 1000 pawns per colony.

## Next Tasks

The bridge order is I1 -> I3 -> I2 (see the colony render before adding the LLM).

1. **(done) Extract the I1 headless stepper** - `engine.py` is the reusable
   colony engine; the three-day survival test runs through it. See the current
   state above.
2. **(done, cleanup pending) Viewer I3** - `colony_view.py` renders the colony
   `FactionState` (tiles, buildings with staffing, pawns by mood, HUD) with the
   authored `assets/colony` sprites and steps `engine.step_hour`; it is now the
   default `python -m agent_town` view and its smoke test is green. Remaining:
   retire the legacy social-sim once the colony viewer reaches parity (camera,
   pawn-selection panel, LLM toggle).
3. **(done headless) LLM governor I2** - `governor.LLMGovernor` is behind the
   fallback `decide` interface with JSON-schema output and a hard fallback;
   `test_llm_governor.py` is green and `scripts/llm_governor_run.py` is the live
   proof tool. Remaining: a live Gemma run log, then a non-blocking integration
   into the real-time viewer (async, reusing the `LLMDecisionScheduler`
   pattern), after which the legacy social-sim retires.
4. **Manual LM Studio/Ollama tuning pass** - run Gemma 4 E4B-it, Qwen3.5-4B,
   and Phi-4-mini-instruct locally and record which model gives the best
   speed/personality balance.

## Blocked Or Deferred

Do not start these until their prerequisite is met.

| Item | Blocked on | Why it matters |
|---|---|---|
| Hosted AI providers | explicit user approval | Avoids accidental paid or network-dependent behavior |
| Human multiplayer or remote viewing | explicit product direction change | Local-only, not web based; AI-vs-AI multi-colony is build 4, not this |
| Large map editor | stable core loop | Editing tools are less useful before agent behavior is interesting |
| Engine migration | benchmark evidence that Pygame rendering or editor tooling is the blocker | Current measured risk is simulation scale, persistence, and future pathfinding before rendering |

## Backlog

Tagged by the earliest build that needs them; see `BLUEPRINT.md` for the design.

Build 2 (depth and the spectator):

- Water chain (Water Well -> water need) and clothes/beauty chain (animals ->
  wool/hide -> Tailor -> cloth/clothes; furniture -> beauty).
- Full needs: water, shelter, clothes, beauty, wired to schedule restoration.
- Building quality -> happiness, plus decay + repair consuming planks/stone +
  labour (the missing material/coin sink).
- Wage money loop: pay pawns (treasury -> purse), pawns spend at Market/Tavern,
  tax the wages back; Market trades surplus with off-map caravans.
- Storage caps + "storage full %" readout; Storehouse raises capacity.
- `set_work_priority` action + RimWorld per-pawn work-priority model.
- Per-colony spectator view: open a colony and see assignments, priorities,
  stockpile, mood, construction live.
- Skill-based healthcare: doctoring priority, Infirmary, optional medicine,
  skill grows by treating.
- Operator-triggered disasters (fire, lightning, cold) via a deliberate UI
  action or a separate storyteller model - never the playing Governor.
- Revolution meter (mood -> revolt risk) + the keep avatar + fail state.
- Save state (wake the dormant SQLite scaffold for long games).
- Pets as decor once population passes a threshold.

Build 3 (the people are real):

- Pawn lifecycle: aging, productivity bands (productive ~16-60), death; 1 real
  hour ~= 1 game year.
- Birth from two parent pawns with lineage tracking; child -> adult.
- Soldier pipeline: home -> walk to barracks -> train -> deployable-anywhere
  soldier; Watch Tower soldier slots; soldiers want beer + meat.
- ore -> metal -> tools/parts chain (Mine, Smelter, Blacksmith); cooking/meat;
  Police House and Firehouse.

Build 4 (competition and the Space Age):

- Two Governor agents, one shared map, contested finite resources.
- Research spine to industrial components and the space-program launch victory.
- Scale to ~1000 pawns per colony (this is where spatial indexing/benchmarks
  earn their place).

Carried from the social-sim era (revisit when relevant):

- Event feed and time controls; screenshots/GIF capture for quick review.
- Pathfinding benchmark before obstacles or large maps.

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
| 2026-06-28 | Rework BLUEPRINT/ROADMAP to the full game vision (autopilot+spectator, RimWorld priorities, multi-agent -> Space Age) | `.\scripts\validate-workbench.ps1` | pass | Docs only. Added long-term vision, conservation north star, full production-chain/needs/services design, money loop, healthcare-as-skill, and a build-1..4 arc. Refactor doc kept until the I1-I3 bridge is green; new goods/actions remain design targets, not yet in the frozen `core.py` contract |
| 2026-06-28 | Integration I1: extract reusable headless engine stepper | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (117 tests, was 113); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added `engine.py` (`step_hour`/`run`/`run_days`, `StepResult`) realizing governor actions, construction, per-pawn/production/tax. Repointed the three-day survival regression through the engine and added `test_engine.py` (construction completion, unaffordable-skip, determinism, whole-day stepping). Next bridge step is the I3 colony viewer |
| 2026-06-28 | Integration I3: colony viewer renders FactionState with authored sprites | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (126 tests, was 117); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; rendered frame inspected at `%TEMP%\colony_frame.png` | pass | Relocated the new authored sprites into `assets/colony/`, added `load_colony_manifest` (25px tiles), `colony.create_default_colony`, and `colony_view.py` (tiles/nodes/buildings-with-staffing/pawns-by-mood/HUD) stepping `engine.step_hour`; repointed `__main__` to it. Added `test_colony.py` + `test_colony_view.py`. Remaining: pawn movement to workplaces, camera/pan-zoom, pawn-selection panel, and retiring the legacy social-sim at parity. Authored sprites are stand-ins mapped by category (raw->house3, processing->house); per-kind art still pending |
| 2026-06-28 | Integrate CC0 pawn sprites and inventory new asset packs | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (126 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; rendered frame inspected at `%TEMP%\colony_frame.png` | pass | Sliced four front-facing pawn sprites (`pawn_a..d`) from the CC0 ansimuz `town_rpg_pack`, replacing the mood circles with style-matched townsfolk plus a mood dot. Repointed `test_assets.py` at the relocated Kenney source zips under `assets/`. Added `assets/colony/README.md` provenance. Held packs pending license: `32_Characters` (best pawn variety), `gfx` (possible rips), `FreePixelFood`. Unused CC0 adds still available: town well/bushes/fences (slice from `town_rpg_pack`), `trees_and_bushes_pack` |
| 2026-06-28 | Confirm asset licenses and swap pawns to the Tiny Characters Set | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (126 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; rendered frame inspected at `%TEMP%\colony_frame.png` | pass | Confirmed CC0 via source pages: Tiny Characters Set (Fleurman/GrafxKid, opengameart) and Free Pixel Food (Henry Software, itch). Sliced+trimmed all 24 characters from `32_Characters/All.png` into `pawn_00..23`, removed the four `pawn_a..d`, and load pawns by glob (each colonist now a distinct person). `gfx.zip` left unverified (possible rips). `FreePixelFood` now cleared for HUD good-icons. Updated `assets/colony/README.md` |
| 2026-06-28 | Integration I2: headless LLM governor with hard fallback | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (137 tests, was 126); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; offline `scripts\llm_governor_run.py --hours 6` (hard-fallback path) | pass | Added `LocalLLMClient.complete_json` (generic schema chat) and `governor.LLMGovernor` (JSON-schema action list, `action_from_dict`/`parse_action_list`, hard fallback on any error; empty result defers to fallback). `test_llm_governor.py` (11 tests) covers parsing, hard fallback, injected-http client path, and a 3-day determinism proof that an always-failing LLM governor == fallback. Remaining: live Gemma run log + non-blocking integration into the real-time viewer |
| 2026-06-28 | Bridge the LLM governor into the colony viewer without blocking | `.\.venv\Scripts\python.exe -m unittest tests.test_colony_governor tests.test_colony_view` (18 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (149 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added `ColonyDecisionScheduler`, wired the live colony viewer through it by default, kept smoke tests deterministic on fallback, added HUD status text plus the `L` connect/disconnect toggle, and covered offline/disabled/thinking behavior with injected-http tests. Remaining I3 work: camera/pan-zoom, pawn-selection panel, live Gemma run log, and legacy social-sim retirement after parity |
