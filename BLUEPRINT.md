# Local Agent Town - Blueprint

**Last reviewed:** 2026-06-28
**Status:** active
**Source root:** `E:\GPTCode\local-agent-town`

## What This Project Is

Local Agent Town is being refactored from an AI-Town social wander-sim into a
single-faction, LLM-governed colony builder: a Townsmen-style town economy
staffed by about a dozen RimWorld-style pawns, run by one Governor agent that
sets policy and never micro-controls pawns.

One sentence:

> One Agent governs one town of about 12 Pawns by setting policy (assign,
> schedule, build, research) while a deterministic engine runs the pawns and
> economy.

Primary users:

- Kayden, as the local operator and designer of the colony.
- Future coding agents extending the engine, governor, and viewer.

Authoritative build plan: `Local_little_world_refactor1.md`. This blueprint is
the stable summary; the refactor plan is the milestone-by-milestone spec.

### In scope (build 1)

- Single faction, one town, one map. No enemy, no PvP.
- About 12 Pawns with skills, traits, wants, needs, mood, schedule, and mental
  breaks.
- A real economy: 2 to 3 production chains, construction, distribution, and a
  happiness-to-tax loop.
- One Governor: a deterministic rule-based fallback first, a local LLM
  (Gemma 4 E4B) as a drop-in second.
- The Governor reads summaries plus an exception queue, never raw pawn state.
- The Pygame viewer renders the colony state and remains a smoke-test surface.

### Non-Goals

This project is not trying to:

- become a web app or multiplayer game, or require hosted infrastructure;
- require paid AI services for the base experience;
- add a second faction, contested map, crowns/objectives layer, or military in
  build 1;
- add spatial indexing, benchmarks, or performance optimization at 12 pawns;
- let the Governor micromanage pawns - it issues policy commands only.

"Multiplayer game" above means human multiplayer. Multiple AI agents each
running their own colony on one map (below) is a planned later build, not a
non-goal.

## Long-term vision (beyond build 1)

Build 1 is the foundation: one colony, one Governor, about 12 pawns, headless
then rendered. The product it grows into:

- **Pure autopilot, watched not played.** The operator does not play the colony.
  One Governor agent per colony runs it end to end; the operator spectates -
  opening any colony and seeing its live state (pawn assignments, work
  priorities, stockpiles, mood, construction) as if they were the one playing,
  but only to confirm the agent is managing well. The colony is hands-off by
  design.
- **One voice per colony.** The Governor agent is the colony's single voice and
  mind. Pawns have no voice; they have RimWorld-style free will - each pawn
  autonomously picks its highest-priority available job from a priority list the
  Governor tunes. The point of the spectator view is watching how the agent
  juggles those priorities across a dozen, then hundreds, of autonomous pawns.
- **Scale arc:** 1 agent / about 12 pawns, then 1 agent / up to about 1000
  pawns, then two agents each running their own colony on one shared map,
  competing for the same finite resources. Rivals do not know the other exists
  at first; contact is emergent.
- **Victory is the Space Age.** The primary win is technological: research and
  build a colony able to leave the planet (a launch / space-age milestone). The
  secondary, implied win is to outlast the rival colony. Research is therefore a
  core progression spine, not a stretch goal.
- **A player avatar / "the keep."** Each colony has a seat of power in the world
  the agent is identified with, so the agent has visible stake. Revolution
  targets the keep; losing it is a fail state.
- **Immortal agents, mortal pawns.** Real time maps to game time at roughly
  1 real hour = 1 game year. The Governor agent is immortal; pawns age (live to
  about 80, productive about 16-60; the Space Age extends this to about 120,
  productive to about 80). The very old and very young are cared for, not worked.

These are marked direction. Build 1 stays single-colony, single-map, no rival,
no military; the roadmap sequences the rest, governed by the law below.

## Design north star: conservation ("nothing from nothing")

Stated as a law because it governs every system: nothing is created from
nothing; everything traces to a source.

- Goods come from chains: bread is baked from flour milled from grain grown on a
  farm.
- Soldiers come from people: a soldier is a pawn who was born from two parent
  pawns, grew up, walked to a barracks, and trained. The barracks never spawns a
  unit from nothing.
- Coin comes from circulation: taxes are collected from wages the colony already
  paid out (see the money loop). The only external coin source is trade.

When a new system is proposed, the test is: where does each thing come from, and
where does it go? If the answer is "nowhere," the design is wrong.

## Architecture

Three layers, built bottom-up. The engine and pawns work and pass tests
headless before the Governor is wired on top. The fallback Governor is built
before the LLM Governor.

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

| Layer | Choice | Source or notes |
|---|---|---|
| Runtime | Python 3.11 or newer | Verified locally with Python 3.11.6 |
| Simulation core | Deterministic, Pygame-free dataclasses and pure functions | `src\agent_town` colony modules |
| Frontend | Pygame desktop window | Smoke test today; renders colony state at integration milestone I3 |
| Optional local AI | OpenAI-compatible chat completions adapter | Governor backend; falls back to the rule-based governor on any error |
| Testing | Standard library `unittest`, headless | Per-module tests, no Pygame for the core |

Architecture constraints (hard):

- Local-only. No web server, no browser UI, no hosted AI.
- The simulation core runs and is fully testable without Pygame.
- The LLM never blocks the sim loop. Reuse the existing non-blocking scheduler
  in `llm.py`.
- The Governor sets policy only; it does not act for individual pawns tick by
  tick.
- Determinism: same seed plus same policy equals same outcome. The LLM is the
  only nondeterministic layer and must be swappable for the deterministic
  fallback.

Operator interaction principles:

- User-facing features should be reachable through visible UI controls first:
  buttons, toggles, segmented controls, sliders, or panel actions as fits the
  feature. Keyboard shortcuts may exist, but they are secondary accelerators,
  not the only way to discover or use the feature.
- Important state changes need visible status treatment: use compact icons,
  color indicators, borders, or badges so the operator can tell at a glance
  whether a feature is on, off, pending, blocked, or degraded.
- Be creative but practical. Prefer small, game-readable controls that match
  the desktop settlement UI over plain text instructions buried in a footer.

## Module Layout

```text
src\agent_town\
  core.py            <- shared dataclasses + the frozen contract (Phase 0)
  world.py           <- map, tiles, resource nodes              (Track A)
  economy.py         <- stockpile, recipes, production, tax     (Track A)
  buildings.py       <- building types, job slots               (Track A)
  construction.py    <- build sites, hauling to site            (Track A)
  pawns.py           <- pawn schema, needs, breaks              (Track B)
  mood.py            <- mood + effective-work formula           (Track B)
  schedule.py        <- schedule templates, day clock           (Track B)
  governor.py        <- context builder + fallback governor     (Track B)
  llm.py             <- adapter, extended for the governor       (Track B)
  colony_view.py    <- Pygame viewer for colony state            (integration)
tests\               <- unittest, headless, per module
```

Transition note: the legacy social-sim (`Agent`, `Simulation`, `Location`,
`app.py`, `persistence.py`, and `spatial.py`) was retired after I3 reached
colony-viewer parity. Current runtime code is the colony contract, engine,
governor, local LLM client, and `colony_view.py`.

## Frozen contract

These shapes live in `core.py`, were written first, and are frozen. Both build
tracks build against them. Any change after the freeze is a small one-file PR
that both tracks rebase on, never a unilateral edit.

| Entity | Key fields |
|---|---|
| `Good` (enum) | logs, planks, grain, flour, bread, stone |
| `GridMap` | width, height, tiles; `in_bounds`, `tile_at` |
| `ResourceNode` | kind (a Good), amount, x, y |
| `Stockpile` | counts (Good to int); `add`, `remove`, `has` |
| `Recipe` | inputs, outputs, work_units, skill |
| `JobRef` | building_id, role |
| `Building` | id, kind, x, y, recipe or None, job_slots, staffed_by, built |
| `ConstructionSite` | id, building_kind, x, y, required, delivered, work_remaining |
| `Pawn` | id, name, skills, traits, wants, needs, mood, schedule, assignment, x, y, state |
| `ScheduleTemplate` | name, blocks (24 long); `block_at` |
| `FactionState` | stockpile, coin, pawns, buildings, construction_sites, research, season, tax_rate, day, time_of_day, grid, resource_nodes |
| `ColonyException` | kind, pawn_id or None, building_id or None, detail |
| `GovernorAction` | kind plus the fields for that action (see Governor interface) |

Naming decision: the refactor plan calls the exception-queue entity
"Exception". It is implemented as `ColonyException` so it never shadows the
builtin `Exception`; the LLM governor's hard fallback relies on a broad
`except Exception`.

### The one cross-track seam

Each tick, a built building with a recipe, at least one staffed pawn, and inputs
in the stockpile produces output at:

```text
building_output_rate = base_rate * sum(pawn.effective_work for staffed pawns)

pawn.effective_work = skill_factor(skill in recipe.skill)
                    * mood_factor(pawn.mood)
                    * trait_factor(pawn.traits, recipe)
                    * schedule_factor(pawn.schedule, time_of_day)   # 0 off-shift
```

Track A owns the production side. Track B owns `effective_work`. Both depend
only on the signature `effective_work(pawn, recipe, time_of_day) -> float`,
defined in `mood.py`. In Phase 0 it returns a neutral placeholder of 1.0 so
Track A can integrate before Track B lands the real formula in milestone B2.
This is the only place the two tracks meet.

## Build 1 content scope

Production chains:

| Chain | Buildings | Flow |
|---|---|---|
| Wood | Forester, Sawmill | tree node to logs to planks |
| Food | Farm, Mill, Bakery | grain to flour to bread |
| Stone | Quarry | stone node to stone |

Construction consumes planks plus stone. Bread is the consumable that feeds the
food need.

Pawn needs (build 1): rest, food, recreation. Each value is in the range 0.0 to
1.0 where 1.0 means fully satisfied; needs decay toward 0.0 over time and are
restored by the matching schedule block plus the right good or building.

Trait subset: industrious or lazy (work speed), tough or frail (mood floor now,
combat later), optimist or pessimist (mood floor), loner (solo jobs lift mood),
night owl (better on the night schedule).

Wants subset: wants_outdoor_work, wants_own_house, wants_soldier (flagged,
unused until build 2). A met want is a mood boost; an ignored one is a slow mood
drag.

Mood and breaks: `mood = base + needs_satisfaction + trait_modifiers +
want_progress`. Below a threshold the pawn breaks: it slacks (effective_work
drops), then wanders off the job. The break, surfaced as a `ColonyException`, is
the Governor's early-warning signal.

## Target content design (full game)

Build 1 ships only the first rows; `ROADMAP.md` sequences the rest. This table
is the design target the chains converge on, not the build-1 cut. Every "from /
to" obeys the conservation law above. The `Build` column is the earliest build
that ships the row.

### Production chains

Tier 0 is extraction from map resource nodes. Each later tier needs the prior
tier's output and, past tier 1, a research unlock - so an advanced building can
only exist once its supplier and its tech do.

| Tier | Building | Consumes | Produces | Skill | Build |
|---|---|---|---|---|---|
| 0 | Forester | tree node | logs | forestry | 1 |
| 0 | Quarry | stone node | stone | mining | 1 |
| 0 | Farm (crops) | field node | grain, vegetables | farming | 1 |
| 0 | Water Well | water table | water | hauling | 2 |
| 0 | Mine | ore node | ore | mining | 3 |
| 0 | Pasture / Animal Farm | feed (grain) | raw meat, hide, wool | herding | 3 |
| 0 | Hunter's Hut | wild game node | raw meat, hide | hunting | 3 |
| 1 | Sawmill | logs | planks | woodworking | 1 |
| 1 | Mill | grain | flour | milling | 1 |
| 1 | Bakery | flour, water | bread | baking | 1 |
| 1 | Brewery | grain, water | beer | brewing | 2 |
| 1 | Tailor | wool / hide | cloth, clothes | tailoring | 2 |
| 1 | Kitchen / Butcher | raw meat | meat (cooked) | cooking | 3 |
| 1 | Smelter | ore | metal | smithing | 3 |
| 2 | Carpenter / Workshop | planks, parts | furniture | crafting | 2 |
| 2 | Apothecary | herbs, cloth | medicine | medicine | 2 |
| 2 | Blacksmith / Forge | metal | tools, parts | smithing | 3 |
| 3 | Laboratory | books/components + researcher | research points | research | 3 |
| 3 | Foundry / Machine shop | metal, parts | components | engineering | 4 |
| 3 | Space program | components, research | launch readiness | engineering | 4 |

Tools and furniture are quality boosters: tools raise pawn work speed; furniture
raises building quality, which raises mood (see needs).

### Pawn needs (full set)

Each need is 0.0 to 1.0, decays over time, and is restored by the matching
good/building on a schedule block. Build 1 ships rest, food, recreation; the
rest follow.

| Need | Restored by | Build |
|---|---|---|
| Rest | House / bed; quality raises the cap | 1 |
| Food | Bread, later meat/vegetables for variety | 1 |
| Recreation | Tavern, Church | 1 |
| Water | Well water | 2 |
| Shelter | An assigned House; quality raises mood | 2 |
| Clothes | Clothing from the Tailor; warmth matters in cold | 2 |
| Beauty ("pretty things") | Furniture, building quality, decorations | 2 |
| Protection | Watch Tower / soldier coverage, Firehouse, Police | 3 |

### Service and civic buildings (satisfy needs / logistics, no output good)

| Building | Role | Build |
|---|---|---|
| House | Shelter + rest; quality raises mood | 1 |
| Tavern | Recreation + mood; sells beer/bread to pawns (money loop); soldiers want beer + meat | 2 |
| Church | Recreation and mood-boost center; one worker slot | 2 |
| Storehouse | Raises stockpile capacity (see storage) | 2 |
| Market | Trade with off-map caravans (coin in/out); pawns spend wages here | 2 |
| Infirmary | Treat injured/sick; skill-based healthcare | 2 |
| Watch Tower | Protection; one slot, must be staffed by a soldier pawn | 3 |
| Firehouse | Cuts fire-disaster spread and damage | 3 |
| Police House | Suppresses crime/unrest, lowers revolution risk | 3 |
| Barracks | Trains a grown pawn into a soldier (needs a real pawn) | 3 |

### The money loop

Coin is conserved internally and only enters or leaves through trade.

- Wages: treasury to pawn purse each day. Unpaid pawns lose mood.
- Spending + tax: pawn purse back to treasury, via purchases at the
  Market/Tavern and via tax on wages.
- Trade: the Market sells surplus goods to off-map caravans for net new coin, or
  buys scarce goods for coin. This is the only external source and sink.

So "where do taxes come from if you don't pay your people" resolves cleanly: you
tax the wages you paid, and net colony wealth comes from selling what the pawns
produced. No wages means nothing to tax, plus a mood penalty.

### Healthcare (skill, not a punishing chain)

Treatment is a labour + skill task, not a deep supply chain. A pawn with a
doctoring priority tends a patient (at the Infirmary or in a bed); care quality
scales with the doctor's skill, and every treatment raises that skill. Medicine
(one cheap Apothecary good) is an optional booster that improves outcomes but is
never required - you can run healthcare with a willing, improving pawn and
nothing else, RimWorld-style.

### Research and the Space Age

Research points (Laboratory output) buy techs along a spine that ends in space
flight. Techs unlock the later building tiers and raise pawn lifespan and
productivity. Reaching and completing the space-age milestone is the primary
victory.

### Storage

Stockpile capacity is finite and raised by the Storehouse; a "storage full %"
readout surfaces it (see `ROADMAP.md`). Build 1 keeps the uncapped stockpile;
caps and hauling pressure land in build 2.

### Disasters (operator as storyteller)

Disasters (fire, lightning, cold snaps that freeze crops or kill unsheltered
pawns) are operator-triggered, not random: the operator is the storyteller, via
a deliberate UI action or a separate prompting model - never the Governor agent
that is playing the colony.

### Pets

Decoration in build 1 (dogs/cats appear once population passes a threshold).
Later, dogs gain a guard role: protecting the colony area alongside pawns.

## Governor interface

Actions the Governor may emit (validated against state before they mutate it):

| Category | Actions |
|---|---|
| Pawns | `assign_pawn(pawn_id, building_id, role)`, `set_schedule(pawn_id_or_group, template)`, `set_work_priority(pawn_id_or_group, work_type, level)` |
| Town | `place_building(kind, x, y)`, `set_production_target(building_id, good, amount)` |
| Progression | `set_research(tech)` |

Pawns have RimWorld-style free will: each picks its highest-priority available
job from its priority list. The Governor's main lever is tuning priorities and
schedules, not hand-placing pawns in slots - `assign_pawn` is an override for
the rare case. Watching how the agent balances priorities across the roster is
the substance of the spectator view. (`set_work_priority` is a build-2 addition;
build 1 still assigns slots directly. `set_research` is core to the Space-Age
victory, not a stretch.)

What the Governor reads, built by `governor.build_context`:

- Faction summary: population, average mood, stockpile levels, coin, day and
  season, tax_rate.
- Roster summary: pawns grouped by current assignment, with standout skills and
  traits only.
- Exception queue: the only per-pawn detail, and only on a problem (unhappy
  pawn plus reason, idle pawn, skill-mismatched assignment, unstaffed building,
  missing inputs, pawn about to break).

The Governor pulls a full pawn sheet only when an exception names that pawn. It
never receives all raw pawn records; summaries plus exceptions keep the context
small.

Two governors share one `decide(context) -> list of GovernorAction` interface:

- `FallbackGovernor`: rule-based greedy matcher that assigns each pawn to its
  best-skill open slot, sets a sensible schedule, and builds the next missing
  chain link. This is also the test oracle: if a town survives N days under the
  fallback, the economy is winnable.
- `LLMGovernor`: same signature, backed by Gemma 4 E4B via `llm.py` with
  JSON-schema output and a hard fallback to `FallbackGovernor` on any error.

## Two-track division of labor

| | Track A | Track B |
|---|---|---|
| Owns | `world.py`, `economy.py`, `buildings.py`, `construction.py` | `pawns.py`, `mood.py`, `schedule.py`, `governor.py`, `llm.py` |
| Theme | the town and its goods | the people and the sovereign |
| Depends on | the `effective_work` signature only | `Building.job_slots`, `Stockpile`, recipes only |

The split is by subsystem behind the frozen contract, so the two tracks can work
in parallel without editing the same files. Integration is done jointly or by
whoever finishes first.

## Core Logic And Invariants

Core behavior lives in the colony modules under `src\agent_town`.

Rules:

- All economy, pawn, mood, schedule, and governor logic is testable without
  Pygame.
- Governor actions are validated against state before they mutate it.
- The viewer may read colony state but must not duplicate engine logic or block
  on model output.
- The deterministic core and the fallback governor must pass tests before the
  LLM layer is built.
- The Governor is never fed raw pawn state; summaries plus exceptions only.

## Trust, Privacy, And Safety Boundaries

- Keep the project local-only. No hosted LLM providers, telemetry, or external
  persistence without explicit user approval.
- Do not commit `.venv`, logs, databases, private exports, tokens, or generated
  dumps.
- Local LLM use stays local-only. `AGENT_TOWN_LLM_MODEL` overrides discovery,
  and `AGENT_TOWN_LLM_AUTO_DISCOVER=0` disables startup discovery for
  deterministic non-LLM runs.

## Design Decisions

| Decision | Rationale | Date or source |
|---|---|---|
| Refactor the social-sim into an LLM-governed colony builder | New product direction; supersedes the social-sim blueprint | 2026-06-27 `Local_little_world_refactor1.md` |
| Freeze a shared contract in `core.py` first | Lets two tracks build in parallel without colliding | 2026-06-27 Phase 0 |
| `effective_work` is the only cross-track seam | Keeps the parallel split clean and the integration point small | 2026-06-27 Phase 0 |
| Name the exception entity `ColonyException` | Avoids shadowing the builtin `Exception` the LLM fallback relies on | 2026-06-27 Phase 0 |
| Keep the legacy social-sim importable during the refactor | Keeps the existing viewer and tests green until milestone I3 | 2026-06-27 Phase 0 |
| Deterministic fallback governor before the LLM governor | The fallback is the winnability oracle and the safety net | 2026-06-27 refactor plan |
| Retire the legacy social-sim after I3 parity | Removes obsolete viewer/runtime code once the colony viewer, LLM governor, smoke test, and benchmarks cover the current product | 2026-06-28 I3 cleanup |

## Health Criteria

The project is healthy when:

- `.\.venv\Scripts\python.exe -m unittest discover -s tests` passes headless;
- the frozen contract in `core.py` imports and instantiates;
- `.\.venv\Scripts\python.exe -m agent_town --smoke-test` exits successfully;
- `.\scripts\validate-workbench.ps1` passes;
- secrets and local data are not exposed in committed or built output.
