# Little Local World - Blueprint

**Last reviewed:** 2026-06-27
**Status:** active
**Source root:** `/Users/kayden/GPT_OS/Projects/Little_Local_World`

## What This Project Is

Little Local World is a local Python desktop colony-builder simulation. One Governor agent runs one town of about twelve pawns by setting policy, while a deterministic engine runs pawns, buildings, resources, construction, mood, and tax.

Core promise:

> One Agent governs one town by assigning work, schedules, construction, and research while pawns remain autonomous and the economy stays deterministic.

Primary users:

- Kayden, as the local operator and designer of the simulation.
- Future coding agents extending the deterministic economy, pawn model, Governor, and viewer.

## Non-Goals

Build 1 does not include:

- a web server, browser UI, hosted AI, telemetry, or paid services;
- a second faction, PvP, enemies, bandits, combat, or AoE-style objectives;
- hundreds of pawns, spatial indexing, scale benchmarks, or engine migration work;
- visual polish before the economy and Governor loop are real and tested;
- Governor micromanagement of pawn movement or tick-by-tick pawn actions.

## Current Product Shape

The project is pivoting from the earlier social wander-sim prototype to an LLM-governed colony builder.

For Build 1, the working system should provide:

- one town, one faction, one map;
- about twelve pawns with skills, traits, wants, needs, mood, schedule, assignments, and breaks;
- two to three production chains: wood, food, and stone;
- construction that consumes planks and stone;
- bread as the food consumable;
- a happiness-to-tax loop;
- a deterministic fallback Governor before any LLM Governor;
- a local LLM Governor using the existing non-blocking adapter pattern after the fallback passes;
- a Pygame viewer that remains a smoke test and renders the new state without owning simulation logic.

## Architecture

Three layers own the system:

| Layer | Responsibility | Rule |
|---|---|---|
| Governor agent | Reads town summaries and exceptions, emits policy actions | No raw full-pawn dump and no direct pawn micromanagement |
| Policy and engine | Validates Governor actions, advances economy, construction, needs, mood, and tax | Fully testable without Pygame |
| Pawns and map | Autonomous pawn state, schedules, resources, buildings, and stockpile | Same seed plus same policy produces same outcome |

Module layout:

```text
src/agent_town/
  core.py            <- shared dataclasses and frozen contract
  world.py           <- map, tiles, resource nodes
  economy.py         <- stockpile, recipes, production, tax
  buildings.py       <- building types and job slots
  construction.py    <- build sites and delivery
  pawns.py           <- pawn schema, needs, breaks
  mood.py            <- mood and effective_work seam
  schedule.py        <- schedule templates and day clock
  governor.py        <- context builder and fallback governor
  llm.py             <- existing non-blocking local LLM adapter, later extended for Governor
  app.py             <- Pygame smoke viewer
tests/
  <- headless unittest coverage by module
```

Architecture constraints:

- Keep the simulation core testable without importing or initializing Pygame.
- Keep LLM calls non-blocking; the sim loop must never wait on a model response.
- Keep the fallback Governor deterministic and usable as the test oracle.
- Keep the LLM Governor swappable with the fallback Governor.
- Keep the existing SQLite persistence scaffold dormant until Build 2 unless correctness requires a smaller repoint.
- Do not introduce hosted services or external integrations without explicit approval.

## Main Contracts

### Frozen Phase 0 Types

These live in `src/agent_town/core.py` and are the shared contract for Track A and Track B:

| Entity | Required fields |
|---|---|
| `Good` | `logs`, `planks`, `grain`, `flour`, `bread`, `stone` |
| `GridMap` | `width`, `height`, `tiles` |
| `ResourceNode` | `kind`, `amount`, `x`, `y` |
| `Stockpile` | `counts`, `add`, `remove`, `has` |
| `Recipe` | `inputs`, `outputs`, `work_units`, `skill` |
| `Building` | `kind`, `x`, `y`, `recipe`, `job_slots`, `staffed_by`, `built` |
| `ConstructionSite` | `building_kind`, `required`, `delivered`, `work_remaining` |
| `Pawn` | `id`, `name`, `skills`, `traits`, `wants`, `needs`, `mood`, `schedule`, `assignment`, `x`, `y`, `state` |
| `JobRef` | `building_id`, `role` |
| `ScheduleTemplate` | `name`, `blocks` with 24 hourly entries |
| `FactionState` | `stockpile`, `coin`, `pawns`, `buildings`, `construction_sites`, `research`, `season`, `tax_rate`, `day`, `time_of_day` |
| `Exception` | `kind`, `pawn_id`, `building_id`, `detail` |
| `GovernorAction` | one validated policy action plus payload |

### Production And Mood Seam

Track A owns building production. Track B owns pawn work effectiveness. The only shared seam is:

```python
effective_work(pawn, recipe, time_of_day) -> float
```

A built building with a recipe, inputs, and staffed pawns produces at:

```text
building_output_rate = base_rate * sum(pawn.effective_work for staffed pawns)
```

The effective work formula depends on skill, mood, traits, and whether the pawn is currently scheduled to work.

### Governor Interface

The Governor reads:

- faction summary: population, average mood, stockpile, coin, day, season, tax rate;
- roster summary: assignments, standout skills, and standout traits;
- exception queue: unhappy pawns, idle pawns, skill mismatch, unstaffed buildings, missing inputs, or break risk.

The Governor may emit only these policy actions:

- `assign_pawn`
- `set_schedule`
- `place_building`
- `set_production_target`
- `set_research`

`FallbackGovernor.decide(context)` returns a list of `GovernorAction` values. It is built before `LLMGovernor` and remains the oracle for whether the town is economically winnable.

## Trust, Privacy, And Safety Boundaries

Sensitive data:

- future local LLM logs;
- future save files;
- future user-authored pawn memories, suggestions, or town policies.

Rules:

- Keep the base project local-only.
- Do not commit `.venv`, logs, databases, private exports, tokens, or generated dumps.
- Do not enable hosted LLM providers, telemetry, external persistence, or billing without explicit approval.
- Local LLM use must remain local-only and must fall back to deterministic behavior on errors.

## Known Risks

| Risk | Impact | Mitigation or owner |
|---|---|---|
| Old viewer still reflects the social-sim runtime | Viewer will lag behind the new colony contract until integration | Keep existing tests green while replacing the engine bottom-up |
| Contract drift between Track A and Track B | Parallel work collides or invalidates tests | Freeze `core.py` and `effective_work` after Phase 0 |
| LLM output is slow, malformed, or unavailable | Governor decisions could stall or corrupt policy | Non-blocking scheduler, schema validation, hard fallback to `FallbackGovernor` |
| Economy balance may be unwinnable | Pawns spiral into hunger, low mood, and low tax | Use fallback survival over N days as the integration oracle |
| Runbook still supports mixed Windows and macOS paths | Verification command confusion | Prefer the live venv commands in `RUNBOOK.md` and update proof rows with exact commands |

## Design Decisions

| Decision | Rationale | Date or source |
|---|---|---|
| Pivot from social-sim to colony-builder | Current refactor plan supersedes the earlier social-sim blueprint | 2026-06-27 refactor plan |
| Keep package name `agent_town` for now | Avoids broad import churn during Phase 0 | 2026-06-27 Phase 0 |
| Keep Pygame as smoke viewer | Existing viewer is useful proof, but engine logic must stay headless | 2026-06-27 refactor plan |
| Build deterministic fallback before LLM Governor | Provides a test oracle and prevents model dependency from blocking the sim | 2026-06-27 refactor plan |
| Freeze `core.py` dataclasses and `effective_work` seam first | Allows Track A and Track B to work in parallel | 2026-06-27 refactor plan |

## Health Criteria

The project is healthy when:

- `./.venv/bin/python -m unittest discover -s tests` passes;
- `./.venv/bin/python -m agent_town --smoke-test` exits successfully;
- `pwsh -File scripts/validate-workbench.ps1` passes;
- `ROADMAP.md` has a current verification row for durable state changes;
- no hosted service, secret, local database, log, or generated dump is included.
