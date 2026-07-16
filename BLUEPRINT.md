# Local Agent Town - Blueprint

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

**Last reviewed:** 2026-07-02
**Status:** active
**Source root:** repo root of `Little_Local_World` (cross-platform: developed on
Windows and macOS; no absolute path is authoritative)

This is the stable reference for what the project is. The live work queue,
blockers, and proof history live in `TASKBOARD.md`; setup and verification
commands live in `RUNBOOK.md`.

Authoritative build plan for the refactor: `Local_little_world_refactor1.md`
(frozen historical artifact). This blueprint is the stable summary. Local visual
baseline: `VISUAL_DESIGN.md` (project-local reference; the harness defers visual
style to it).

## What This Project Is

Local Agent Town is a local desktop prototype for watching one LLM-governed
civilization run on autopilot. It is being refactored from an AI-Town social
wander-sim into a single-faction, LLM-governed civilization builder: a
Townsmen-style town economy staffed by about a dozen RimWorld-style pawns, run
by one Governor agent that sets policy and never micro-controls pawns.

Core promise:

> One Agent governs one town of about 12 Pawns by setting policy (assign,
> schedule, build, research) while a deterministic engine runs the pawns and
> economy. The operator watches; they do not play.

Primary users:

- Kayden, as the local operator and designer of the civilization.
- Future coding agents extending the engine, governor, and viewer.

### In scope (build 1)

- Single faction, one town, one map. No enemy, no PvP.
- About 12 Pawns with skills, traits, wants, needs, mood, schedule, and mental
  breaks.
- A real economy: 2-3 production chains, construction, distribution, and a
  happiness-to-tax loop.
- One Governor: a deterministic rule-based fallback first, a local LLM
  (Gemma 4 E4B) as a drop-in second.
- The Governor reads summaries plus an exception queue, never raw pawn state.
- The Pygame viewer renders civilization state and remains a smoke-test surface.

## Non-Goals

This project is not trying to:

- become a web app or multiplayer game, or require hosted infrastructure;
- require paid AI services for the base experience;
- add a second faction, contested map, crowns/objectives layer, or military in
  build 1;
- add spatial indexing, benchmarks, or performance optimization at 12 pawns;
- let the Governor micromanage pawns - it issues policy commands only.

"Multiplayer game" means human multiplayer. Multiple AI agents each running their
own civilization on one map is a planned later build (build 4), not a non-goal.

## Current Product Shape

When the project is working, the operator can:

- launch a Pygame desktop window that renders the civilization map, buildings,
  resources, and ~12 pawns coloured by mood;
- pan/zoom the camera, select a pawn, and read its needs, skills, traits, and a
  "Why this job" decision trace;
- open a RimWorld-style work-priority grid (the **Work** button) and re-route
  pawns by changing priorities, watching them re-path on the next step;
- read a Civ stats panel (Mood, Food, Water, Recreation, Rest), a resource HUD
  with storage fullness, a Governor observer card, and a right-edge exception
  stack;
- press `L` to hand policy to a local LLM (LM Studio/Ollama), with a hard
  fallback to the deterministic governor on any error;
- open a live **History** event feed of completed buildings, depletions, stalls,
  breaks, and dropped LLM decisions.

The most important quality bar is **correctness/determinism**: same seed plus
same policy equals same outcome, with the LLM as the only nondeterministic layer,
always swappable for the deterministic fallback.

## Design North Star: Conservation ("nothing from nothing")

Stated as a law because it governs every system: nothing is created from
nothing; everything traces to a source.

- Goods come from chains: bread is baked from flour milled from grain grown on a
  farm.
- Soldiers come from people: a soldier is a pawn who was born, grew up, walked to
  a barracks, and trained. The barracks never spawns a unit from nothing.
- Coin comes from circulation: taxes are collected from wages already paid out.
  The only external coin source/sink is trade.

When a new system is proposed, the test is: where does each thing come from, and
where does it go? If the answer is "nowhere," the design is wrong.

## Direction And Build Order

Stable product direction and sequencing. The current executable task queue lives
in `TASKBOARD.md`, not here.

**Current phase:** prototype, finishing build 1 and starting build 2 depth. Build
1's engine, both governors, the viewer, mood/hunger, work-priority arbiter,
water, storage caps, and the first wage/market loop are shipped. The next code
task is repair debt (the first material/coin maintenance sink), then Paper 7
scale foundations.

Build arc (each gated on the prior; conservation governs every system):

1. **Build 1 - one civilization works (current).** ~12 pawns, 3 chains (wood,
   food, stone), construction, needs/mood/breaks, happiness-to-tax, deterministic
   fallback Governor then the LLM Governor, viewer renders civilization state.
2. **Build 2 - depth and the spectator.** Water (done) and clothes/beauty chains;
   full needs set; building quality to happiness; decay + repair as a
   material/coin sink; the wage money loop (started); storage caps (started);
   RimWorld work priorities (done) and the per-civilization spectator view;
   skill-based healthcare; the Church; operator-triggered disasters; the
   revolution meter + keep + fail state; pets; save state.
3. **Build 3 - the people are real.** Pawn lifecycle (aging, productivity bands,
   death); birth with lineage; the home -> barracks -> soldier pipeline; Watch
   Tower, Police, Firehouse; the ore -> metal -> tools/parts chain; cooking/meat.
4. **Build 4 - competition and the Space Age.** Two Governor agents, one shared
   map, finite contested resources. The research spine to industrial components
   and the space-program launch victory. Scale target ~1000 pawns per civilization
   via the Paper 7 path.

### Long-term vision (marked direction, beyond build 1)

- **Pure autopilot, watched not played.** One Governor agent per civilization
  runs it end to end; the operator spectates to confirm the agent is managing
  well. Hands-off by design.
- **One voice per civilization.** The Governor is the civilization's single mind.
  Pawns have RimWorld-style free will; each autonomously picks its highest
  priority available job from a list the Governor tunes.
- **Scale arc:** 1 agent / ~12 pawns, then 1 agent / ~1000 pawns, then two agents
  each running their own civilization on one shared map, competing for finite
  resources. Contact is emergent.
- **Victory is the Space Age.** The primary win is technological (research and
  build a civilization able to leave the planet); outlasting the rival is the
  implied secondary win. Research is a core spine, not a stretch goal.
- **A player avatar / "the keep."** Each civilization has a seat of power; losing
  it is a fail state.
- **Immortal agents, mortal pawns.** ~1 real hour = 1 game year. The Governor is
  immortal; pawns age. The very old and very young are cared for, not worked.

## Architecture

Three layers, built bottom-up. The engine and pawns work and pass tests headless
before the Governor is wired on top. The fallback Governor is built before the
LLM Governor.

```text
Governor agent (LLM or rule-based fallback)
   reads:  faction summary + roster summary + exception queue
   emits:  policy commands (assign, schedule, build, research)
        |
        v
Policy layer  ->  Deterministic simulation engine
                    production, hauling, construction, needs, mood, tax
        |
        v
Pawns (autonomous, need-driven) on a tile map
```

| Layer | Choice | Source / Notes |
|---|---|---|
| Runtime | Python 3.11+ | `pyproject.toml` `requires-python = ">=3.11"`; CI/gates use 3.12; sandbox verifies core on 3.10 |
| Simulation core | Deterministic, Pygame-free dataclasses and pure functions | `src/agent_town` civilization modules |
| Frontend | Pygame desktop window | `civilization_view.py`; renders civilization state and is the smoke-test surface |
| Optional local AI | OpenAI-compatible chat completions adapter | `llm.py` + `LLMGovernor`; falls back to the rule-based governor on any error |
| Testing | Standard library `unittest`, headless | Per-module tests; core is testable without Pygame |
| Packaging | setuptools, editable install; console entry `agent-town` | `pyproject.toml` |

Architecture constraints (hard):

- Local-only. No web server, no browser UI, no hosted AI by default.
- The simulation core runs and is fully testable without Pygame.
- The LLM never blocks the sim loop (non-blocking `CivilizationDecisionScheduler`
  in the viewer).
- The Governor sets policy only; it does not act for individual pawns tick by
  tick.
- Determinism: same seed + same policy = same outcome. Mood and mental-break
  timing use a seeded PRNG keyed to the civilization seed.

Operator interaction principles:

- Reach features through visible UI controls first; keyboard shortcuts are
  secondary accelerators.
- Important state changes get visible status treatment (icons, colour, borders,
  badges) so the operator can tell at a glance whether a feature is on, off,
  pending, blocked, or degraded.
- Persistent UI is for scanability; full detail lives in inspectors/drill-downs.
- Do not rely on colour alone; critical states need at least two channels.

Full readability/UI rules live in `VISUAL_DESIGN.md`.

## Directory Map

```text
Little_Local_World/
├── src/agent_town/          <- deterministic engine + governor + viewer (real tree below)
├── tests/                   <- unittest, headless, per module (~28 test modules)
├── scripts/                 <- run analysis, scaling benchmark, LLM run, PS launchers, validator
├── research_papers/         <- design inputs (Papers 1-8); source leads, not code truth
├── docs/                    <- screenshots + run_reports (proof artifacts)
├── logs/                    <- generated JSONL run logs (git-ignored)
├── AGENTS.md                <- agent behavior and read/edit scope
├── BLUEPRINT.md             <- this file: stable project definition and direction
├── TASKBOARD.md             <- live task queue, blockers, proof log
├── RUNBOOK.md               <- setup, operation, verification, recovery
├── README.md                <- public entry point
├── HARNESS_FEEDBACK.md      <- return channel to the LLM Workbench harness
├── VISUAL_DESIGN.md         <- local visual baseline (kept, project-local)
├── Local_little_world_refactor1.md  <- frozen refactor plan (historical)
└── archive/legacy-harness/  <- retired pre-v2 harness docs (ROADMAP, policy, checklist)
```

Real `src/agent_town/` modules (observed in the tree; supersedes the older module
list):

```text
src/agent_town/
  core.py             <- shared dataclasses + the frozen contract
  world.py            <- map, tiles, resource nodes
  economy.py          <- stockpile, recipes, production, tax, wages/market, averages
  buildings.py        <- building types, job slots
  construction.py     <- build sites, hauling to site
  pawns.py            <- pawn schema, needs, nutrition, breaks
  mood.py             <- mood ledger + effective-work seam
  schedule.py         <- schedule templates, day clock
  work.py             <- lane-based work-priority arbiter + reservations
  governor.py         <- context builder, FallbackGovernor, LLMGovernor
  llm.py              <- OpenAI-compatible adapter (LocalLLMClient)
  engine.py           <- deterministic stepper (step_hour / run / run_days)
  health.py           <- invariant checks / health verdict
  telemetry.py        <- run logging + snapshots
  civilization.py     <- default civilization construction (FactionState)
  civilization_view.py <- Pygame viewer (default `python -m agent_town`)
  __main__.py         <- entry point (viewer + --smoke-test)
  assets/             <- CC0/provenance-tracked sprites (colony/, kenney/) + source zips
```

Note: the legacy social-sim (`Agent`, `Simulation`, `Location`, `app.py`,
`persistence.py`, `spatial.py`, `colony*.py`) was retired after integration
milestone I3 reached civilization-viewer parity.

## Main Contracts

### Frozen contract (`core.py`)

Written first and frozen; both build tracks build against it. Any change is a
small one-file PR that both tracks rebase on, never a unilateral edit.

| Entity | Key fields |
|---|---|
| `Good` (enum) | logs, planks, grain, flour, bread, water, stone |
| `GridMap` | width, height, tiles; `in_bounds`, `tile_at` |
| `ResourceNode` | kind (a Good), amount, x, y |
| `Stockpile` | counts (Good -> int), capacity; `add`, `remove`, `has` |
| `Recipe` | inputs, outputs, work_units, skill |
| `JobRef` | building_id, role |
| `Building` | id, kind, x, y, recipe or None, job_slots, staffed_by, built |
| `ConstructionSite` | id, building_kind, x, y, required, delivered, work_remaining |
| `Pawn` | id, name, skills, traits, wants, needs, mood, mood_target, thoughts, schedule, assignment, coin, x, y, state |
| `ScheduleTemplate` | name, blocks (24 long); `block_at` |
| `FactionState` | stockpile, coin, pawns, buildings, construction_sites, research, research_target, research_points, season, tax_rate, day, time_of_day, grid, resource_nodes, seed |
| `CivilizationException` | kind, pawn_id or None, building_id or None, detail |
| `GovernorAction` | kind plus the fields for that action |

Naming decision: the exception-queue entity is `CivilizationException` so it
never shadows the builtin `Exception` (the LLM governor's hard fallback relies on
a broad `except Exception`).

### The one cross-track seam

Each tick, a built building with a recipe, at least one staffed pawn, and inputs
in the stockpile produces output at:

```text
building_output_rate = base_rate * sum(pawn.effective_work for staffed pawns)

pawn.effective_work = skill_factor(skill in recipe.skill)
                    * mood_factor(pawn.mood)      # neutral hook; hunger/break cut work directly
                    * trait_factor(pawn.traits, recipe)
                    * schedule_factor(pawn.schedule, time_of_day)   # 0 off-shift
```

`effective_work(pawn, recipe, time_of_day) -> float` is defined in `mood.py` and
is the only place Track A (town/goods) and Track B (people/sovereign) meet.

### Governor interface

| Category | Actions |
|---|---|
| Pawns | `assign_pawn(pawn_id, building_id, role)` (forced override), `set_schedule(pawn_id_or_group, template)`, `set_work_priority(pawn_id_or_group, work_type, level)` |
| Town | `place_building(kind, x, y)`, `set_production_target(building_id, good, amount)` |
| Progression | `set_research(tech)` |

Actions are validated against state before they mutate it. Pawns have
RimWorld-style free will; the Governor's main lever is tuning priorities and
schedules. `set_research` selects an active tech; staffed Laboratory work
completes it and completed techs change simulation behavior (`efficient_baking`
raises Bakery output).

Two governors share one `decide(context)` interface returning a list of
`GovernorAction`:

- `FallbackGovernor`: deterministic greedy matcher; also the winnability oracle
  (if a town survives N days under the fallback, the economy is winnable).
- `LLMGovernor`: same signature, OpenAI-compatible endpoint via `llm.py` with
  JSON-schema output and a hard fallback to `FallbackGovernor` on any error.
  Guardrail: LLM-origin `set_work_priority` must target named pawns (not
  `group=all`) and stay within safe essential levels, or it falls back.

What the Governor reads (`governor.build_context`): faction summary, roster
summary (grouped by assignment, standout skills/traits only), and the exception
queue (the only per-pawn detail, and only on a problem). It never receives all
raw pawn records.

### Production chains (build 1 cut)

| Chain | Buildings | Flow |
|---|---|---|
| Wood | Forester, Sawmill | tree node -> logs -> planks |
| Food | Farm, Mill, Bakery | grain -> flour -> bread |
| Stone | Quarry | stone node -> stone |
| Water | Water Well | water table -> water |
| Research | Laboratory | staffed research work -> research points |

Construction consumes planks + stone. Bread (0.25 nutrition/portion, Bakery
outputs 4-5/cycle) feeds the food need; water feeds thirst. The full target
content design (tiers 0-3, full needs set, service/civic buildings, money loop,
healthcare, storage, disasters) is sequenced across builds 2-4; see the build
arc above and `research_papers/`.

## Core Logic And Invariants

Core behavior lives in the civilization modules under `src/agent_town`.

Rules:

- All economy, pawn, mood, schedule, work, and governor logic is testable
  without Pygame.
- Governor actions are validated against state before they mutate it.
- The viewer may read civilization state but must not duplicate engine logic or
  block on model output.
- The deterministic core and the fallback governor must pass tests before the LLM
  layer is trusted.
- The Governor is never fed raw pawn state; summaries plus exceptions only.
- Conservation: no good, coin, or pawn is created from nothing (see North Star).

### Mood and hunger (RimWorld model, build-1 foundation)

- **0-100 mood scale.** `mood_target = base + sum(active thoughts)`; displayed
  `pawn.mood` drifts toward it at +12/hour rising, -8/hour falling, frozen while
  asleep.
- **Thoughts are the ledger.** `Pawn.thoughts` is a list of `Thought
  {kind, label, value, age, stack}`; many small negatives stack into a crisis.
- **Food is a nutrition reserve** (0-1, max 1.0), drained by hunger and refilled
  only by opportunistically eating bread (~30% trigger, up to 4 portions, excess
  wasted). No meal schedule block, no free off-shift restoration (conservation).
- **Breaks are band + roll:** minor <35, major ~20, extreme ~5, on a seeded
  mean-time-between roll; Catharsis thought after a break ends. Breaks are the
  Governor's early-warning exceptions and cut `effective_work`.
- `mood_factor` is a neutral hook; `effective_work` is reduced directly by hunger
  and break state (RimWorld does not use a generic mood-to-work multiplier).

Lethal starvation (72h-since-meal death) is designed but **deferred** behind the
visible autonomy/readability work; build 1 ships hunger mood pressure as its
stakes. See `TASKBOARD.md` Deferred.

### Scale architecture (Paper 7)

At ~12 pawns, keep visible truth exact. Two low-cost foundations come first:
reachability regions (reject impossible jobs before pathfinding) and
deterministic phases (stable ordered job claims/reservations/movement/production/
needs/tax). Hard trust rule: any pawn that is selected, visible, in conflict,
carrying a scarce object, or transferring ownership is forced back into exact
simulation; approximation is only for opportunity search and offscreen movement.

## Trust, Privacy, And Safety Boundaries

Sensitive data / boundaries:

- Keep the project local-only by default. No hosted LLM providers, telemetry, or
  external persistence without explicit user approval.
- Do not commit `.venv`, logs, databases, private exports, tokens, or generated
  dumps (enforced by `.gitignore`).
- Local LLM use stays local-only unless the operator explicitly points
  `AGENT_TOWN_LLM_BASE_URL` at a hosted OpenAI-compatible endpoint and supplies
  `OPENAI_API_KEY`. `AGENT_TOWN_LLM_MODEL` overrides discovery;
  `AGENT_TOWN_LLM_AUTO_DISCOVER=0` disables startup discovery for deterministic
  non-LLM runs.
- Hosted OpenAI runs are opt-in operator tests, not the default runtime; keep the
  key in an ignored local env file.

## Known Risks

Immediate blockers belong in `TASKBOARD.md` -> Blocked. Stable risks:

| Risk | Impact | Mitigation / owner |
|---|---|---|
| LLM governor can starve the town with bad policy | A model run empties stockpiles / drops mood | Deterministic fallback is the oracle; LLM-origin work-priority guardrails; Mac LM acceptance gate before merge |
| Pygame as the viewer may cap scale | Rendering could block the 1000-pawn goal | Keep the engine testable/benchmarkable headless; migrate engines only on benchmark evidence, not taste |
| Determinism regressions | Break the winnability oracle and replayability | Seeded PRNG keyed to `FactionState.seed`; determinism tests; the LLM is the only nondeterministic layer |
| Frozen-contract drift | Two-track collisions / silent breakage | `core.py` changes go through the one-file-PR process, not unilateral edits |
| Research papers treated as code truth | Silent design drift | Papers are inputs; conflicts become `TASKBOARD.md` tasks, not doc edits |

## Design Decisions

Decisions future agents must preserve (most recent last). Older per-slice
decisions are preserved in `archive/legacy-harness/ROADMAP.md`.

| Decision | Rationale | Date / Source |
|---|---|---|
| Refactor the social-sim into an LLM-governed civilization builder | New product direction; supersedes the social-sim blueprint | 2026-06-27 `Local_little_world_refactor1.md` |
| Freeze a shared contract in `core.py`; `effective_work` is the only cross-track seam | Lets two tracks build in parallel without colliding; keeps the integration point small | 2026-06-27 Phase 0 |
| Name the exception entity `CivilizationException` | Avoids shadowing the builtin `Exception` the LLM fallback relies on | 2026-06-27 Phase 0 |
| Deterministic fallback governor before the LLM governor; retire the legacy social-sim after I3 | The fallback is the winnability oracle and safety net; removes obsolete runtime once the civilization viewer covers the product | 2026-06-27 / 2026-06-28 |
| Rename colony -> Civilization (Civ) everywhere | One consistent player-facing and code vocabulary; isolated behaviour-preserving commit | 2026-06-28 user request |
| Adopt RimWorld's mood model (0-100, two-layer target/actual, thought ledger, break bands), foundation-first; food is a nutrition reserve; pawns eat opportunistically | Mood is the story engine; building it RimWorld-shaped now lets later thoughts/expectations/inspirations slot in; closes the "food from nothing" conservation gap | 2026-06-28 / retuned 2026-06-29 |
| Research papers are implementation inputs, not automatic code truth; adopt Paper 8 synthesis build order | Papers become explicit tasks/tests/deferrals; "make autonomous causality visible" with a strict build order (food -> work priorities -> water -> readability -> governor card -> scale -> deeper economy) | 2026-06-29 research intake |
| Build-2 step 1: pawns self-select work via `work.py`; governor stops routine `assign_pawn` | Lane-based arbiter (forced -> hard-state -> self-care -> normal work -> idle) with reservations; `set_work_priority` is the lever, `assign_pawn` the forced override | 2026-06-29 build-2 step 1 |
| Water shipped as the first essential economy extension | `Good.WATER`, Water Well, drinking, thirst thoughts, Civ Water readout, `low_water` exception make the first Townsmen essential conserved and visible | 2026-06-29 water slice |
| Paper 5 readability, Paper 6 governor observer card + exception stack shipped | Diagnosis-first observer UI; hover/selection separated, danger rings, idle badges, construction ghosts; Governor card + severity-sorted exception stack | 2026-06-29 Paper 5/6 slices |
| Truth-loop cleanup: `set_production_target` honored; minimal research spine; finite storage capacity; first wage/market money loop; Storehouse capacity + pressure badges; household spending + sales tax; Market service-pressure signal | Make each governor lever cause real, visible simulation change without faking systems that do not exist yet | 2026-06-30 truth-loop slices |
| LLM-origin `set_work_priority` must target named pawns; `group=all` edits fall back | All-town priority edits flattened the seeded town's specialization and starved it under the Mac LM gate; named-pawn constraint preserves the fallback oracle | 2026-06-30 PR #23 fix |
| Adopt LLM Workbench v2.1 harness (four control docs) via the Adoption protocol | Replace the pre-v2 doc set (AGENTS/ROADMAP/BOOTSTRAP_CHECKLIST/UNATTENDED_WORK_POLICY) with AGENTS/BLUEPRINT/TASKBOARD/RUNBOOK; retire old docs to `archive/`; preserve all content | 2026-07-02 harness adoption |

## Health Criteria

The project is healthy when:

- the headless unittest suite passes (`unittest discover -s tests`);
- the frozen contract in `core.py` imports and instantiates;
- `python -m agent_town --smoke-test` exits successfully;
- `scripts/validate-workbench.ps1` passes (control-doc structure check);
- the primary viewer workflow renders and steps without crashing;
- secrets and local data are not exposed in committed or built output.

Exact verification commands live in `RUNBOOK.md`. Current task status and proof
history live in `TASKBOARD.md`.
