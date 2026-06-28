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
- The existing Pygame viewer kept working as a smoke test, eventually rendering
  the new colony state.

### Non-Goals

This project is not trying to:

- become a web app or multiplayer game, or require hosted infrastructure;
- require paid AI services for the base experience;
- add a second faction, contested map, crowns/objectives layer, or military in
  build 1;
- add spatial indexing, benchmarks, or performance optimization at 12 pawns;
- let the Governor micromanage pawns - it issues policy commands only.

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
  app.py             <- Pygame viewer, renders new state         (integration)
tests\               <- unittest, headless, per module
```

Transition note: the legacy social-sim (`Agent`, `Simulation`, `Location` in
`core.py`, plus the current `app.py`, `persistence.py`, `spatial.py`) is kept
importable and green so the existing viewer keeps working. It is retired when
the viewer is rewritten to render colony state at integration milestone I3.

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

## Governor interface

Actions the Governor may emit (validated against state before they mutate it):

| Category | Actions |
|---|---|
| Pawns | `assign_pawn(pawn_id, building_id, role)`, `set_schedule(pawn_id_or_group, template)` |
| Town | `place_building(kind, x, y)`, `set_production_target(building_id, good, amount)` |
| Progression | `set_research(tech)` (stretch) |

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

## Health Criteria

The project is healthy when:

- `.\.venv\Scripts\python.exe -m unittest discover -s tests` passes headless;
- the frozen contract in `core.py` imports and instantiates;
- `.\.venv\Scripts\python.exe -m agent_town --smoke-test` exits successfully;
- `.\scripts\validate-workbench.ps1` passes;
- secrets and local data are not exposed in committed or built output.
