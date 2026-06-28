# Little Local World - Build 1 Refactor Plan

**Status:** active
**Owner:** Kayden (director); Codex and Claude Code (build agents)
**Supersedes:** the social-sim blueprint. This project is now an LLM-governed colony builder.

---

## 1. Goal

Refactor `Little_Local_World` from an AI-Town social wander-sim into a single-faction, LLM-governed colony builder: a Townsmen-style town economy staffed by a dozen RimWorld-style pawns, run by one Governor agent that sets policy and never micro-controls pawns.

One sentence: **one Agent governs one town of ~12 Pawns by setting policy (assign, schedule, build, research) while a deterministic engine runs the pawns and economy.**

### In scope (build 1)

- Single faction, one town, one map. No enemy, no PvP.
- ~12 Pawns with skills, traits, wants, needs, mood, schedule, and mental breaks.
- Real economy: 2 to 3 production chains, construction, distribution, happiness-to-tax loop.
- One Governor agent: deterministic rule-based fallback first, local LLM (Gemma 4 E4B) as a drop-in second.
- Governor reads summaries plus an exception queue, never raw pawn state.
- Existing Pygame viewer kept working as a smoke test; renders the new state, nothing fancy.

### Out of scope (defer to build 2+)

- Second faction, shared or contested map, the AoE crowns/objectives layer.
- Military, bandits, combat.
- Seasons and research are stretch goals at the end of build 1, not core.
- Spatial indexing, scaling benchmarks, hundreds of pawns, visual polish.
- Economy persistence (keep the existing SQLite scaffold dormant; repoint it in build 2).

---

## 2. Hard constraints

- Local-only. No web server, no browser UI, no hosted AI.
- The simulation core runs and is fully testable **without Pygame**.
- The LLM never blocks the sim loop (reuse the existing non-blocking scheduler pattern).
- The Governor sets policy only. It does not move or act for individual pawns tick-by-tick.
- Determinism: same seed plus same policy equals same outcome. The LLM is the only nondeterministic layer, and it must be swappable for the deterministic fallback.

---

## 3. Architecture (three layers)

```
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

Build every layer bottom-up. The engine and pawns work and pass tests headless **before** the Governor is wired on top. The fallback Governor is built before the LLM Governor.

---

## 4. Target module layout

```
src/agent_town/                 (keep the package name for now)
  core.py            <- shared dataclasses + the frozen contract (Phase 0)
  world.py           <- map, tiles, resource nodes              [Track A]
  economy.py         <- stockpile, recipes, production, tax     [Track A]
  buildings.py       <- building types, job slots               [Track A]
  construction.py    <- build sites, hauling to site            [Track A]
  pawns.py           <- pawn schema, needs, breaks              [Track B]
  mood.py            <- mood + effective-work formula           [Track B]
  schedule.py        <- schedule templates, day clock           [Track B]
  governor.py        <- context builder + fallback governor     [Track B]
  llm.py             <- existing adapter, extended for governor  [Track B]
  app.py             <- Pygame viewer, renders new state        [integration]
tests/               <- unittest, headless, per module
```

---

## 5. Frozen contract (Phase 0 deliverable)

These shapes live in `core.py`, are written and committed **first**, and are frozen. Both tracks build against them. Any change after the freeze is a small PR to `main` that both tracks rebase on, never a unilateral edit.

### Core dataclasses

| Entity | Key fields |
|---|---|
| `Good` (enum) | logs, planks, grain, flour, bread, stone |
| `GridMap` | width, height, tiles |
| `ResourceNode` | kind (Good), amount, x, y |
| `Stockpile` | counts: dict[Good,int]; `add/remove/has` |
| `Recipe` | inputs: dict[Good,int], outputs: dict[Good,int], work_units: float, skill: str |
| `Building` | kind, x, y, recipe \| None, job_slots: int, staffed_by: list[str], built: bool |
| `ConstructionSite` | building_kind, required: dict[Good,int], delivered: dict[Good,int], work_remaining: float |
| `Pawn` | id, name, skills: dict[str,int], traits: tuple[str,...], wants: tuple[str,...], needs: dict[str,float], mood: float, schedule: str, assignment: JobRef \| None, x, y, state |
| `JobRef` | building_id, role |
| `ScheduleTemplate` | name, blocks: list[str] length 24 (work\|sleep\|rec\|any) |
| `FactionState` | stockpile, coin, pawns, buildings, construction_sites, research, season, tax_rate, day, time_of_day |
| `Exception` | kind, pawn_id \| None, building_id \| None, detail |
| `GovernorAction` | one of the action types in section 7 |

### The one seam that couples the two tracks

Each tick, a built building with a recipe, at least one staffed pawn, and inputs in the stockpile produces output at:

```
building_output_rate = base_rate * sum(pawn.effective_work for staffed pawns)

pawn.effective_work = skill_factor(pawn.skills[recipe.skill])
                      * mood_factor(pawn.mood)
                      * trait_factor(pawn.traits, recipe)
                      * schedule_factor(pawn.schedule, time_of_day)   # 0 if not a work block
```

Track A owns the building/production side of this. Track B owns `effective_work`. Both depend only on the signature `effective_work(pawn, recipe, time_of_day) -> float`, defined in `mood.py` and stubbed in Phase 0. This is the only place the tracks meet. Get this signature right in Phase 0 and the parallel work will not collide.

---

## 6. Build 1 content scope

Keep content small. Real chains, not 150 buildings.

### Production chains

| Chain | Buildings | Flow |
|---|---|---|
| Wood | Forester, Sawmill | tree node -> logs -> planks |
| Food | Farm, Mill, Bakery | grain -> flour -> bread |
| Stone | Quarry | stone node -> stone |

Construction consumes planks plus stone. Bread is the consumable that feeds the food need.

### Pawn needs (build 1)

`rest`, `food`, `recreation`. Comfort and social are stretch. Needs decay over time, restored by schedule blocks plus the right building (bed for rest, bread for food, a recreation building for joy).

### Trait subset (build 1)

`industrious`/`lazy` (work speed), `tough`/`frail` (later combat, mood floor now), `optimist`/`pessimist` (mood floor), `loner` (solo jobs lift mood), `night owl` (better on night schedule). Extend later.

### Wants subset (build 1)

`wants_outdoor_work`, `wants_own_house`, `wants_soldier` (flagged, unused until build 2). Met want = mood boost; ignored = slow mood drag.

### Mood and breaks

`mood = base + needs_satisfaction + trait_modifiers + want_progress`. Below a threshold the pawn **breaks**: slacks (effective_work drops) then wanders off the job. The break, surfaced as an `Exception`, is the Governor's early-warning signal.

---

## 7. Governor action schema and interface

### Actions the Governor may emit (validated against state before mutating)

| Category | Actions |
|---|---|
| Pawns | `assign_pawn(pawn_id, building_id, role)`, `set_schedule(pawn_id_or_group, template)` |
| Town | `place_building(kind, x, y)`, `set_production_target(building_id, good, amount)` |
| Progression | `set_research(tech)` *(stretch)* |

### What the Governor reads (built by `governor.build_context`)

- **Faction summary**: population, avg mood, stockpile levels, coin, day/season, tax_rate.
- **Roster summary**: pawns grouped by current assignment, with standout skills and traits only.
- **Exception queue**: the only per-pawn detail, only on a problem (unhappy pawn + reason, idle pawn, skill-mismatched assignment, unstaffed building, missing inputs, pawn about to break).

The Governor pulls a full pawn sheet only when an exception names that pawn. Never dump all 12 raw records when the count grows past a dozen this is what keeps the context small.

### Two governors, same interface

- `FallbackGovernor` (rule-based greedy matcher): assigns each pawn to its best-skill open slot, sets a sensible schedule, builds the next missing chain link. This is also the **test oracle**: if a town survives N days under the fallback, the economy is winnable.
- `LLMGovernor`: same `decide(context) -> list[GovernorAction]` signature, backed by Gemma 4 E4B via the existing `llm.py` adapter with JSON-schema output and a hard fallback to `FallbackGovernor` on any error.

---

## 8. Milestones (2 to 3 hour chunks, each with proof)

Red/green TDD: write the failing test, implement, go green, record proof.

### Phase 0 - Re-blueprint and freeze the contract (shared, do first)

- Rewrite `BLUEPRINT.md` to the colony-builder definition above.
- Create the module skeleton and every dataclass in section 5, with method stubs raising `NotImplementedError`.
- Stub `effective_work(pawn, recipe, time_of_day)`.
- **Proof:** package imports; stub test suite green; committed to `main`. Both tracks branch from this commit.

### Track A - Economy and world (one agent)

- **A1 Map + nodes + stockpile.** Grid map, resource nodes, stockpile add/remove/has. *Proof: unit tests.*
- **A2 One chain end to end.** Forester -> logs, Sawmill -> planks, driven by a temporary `staffed=True` flag (no pawns yet). *Proof: a seeded headless run produces planks; test asserts counts.*
- **A3 Construction.** Place a `ConstructionSite`, haul required goods to it, consume work_units, building flips to `built`. *Proof: tests for partial delivery, completion, and insufficient goods.*
- **A4 Multi-chain + tax loop.** Add food and stone chains; `coin += f(avg_mood, population, tax_rate)` per day; coin gates `place_building`. Reads a mood value through the frozen seam (still stubbed). *Proof: tests for income scaling and a build blocked by low coin.*

### Track B - Pawns and Governor (other agent)

- **B1 Pawn + needs + schedule + mood.** Pawn schema, need decay, schedule templates, day clock, base mood. *Proof: tests for need decay over a day and schedule-driven restoration.*
- **B2 effective_work formula.** Implement the section-5 seam: skill, mood, trait, schedule factors. *Proof: table-driven tests (high skill + good mood + work block = high; mismatched or off-shift = low/zero).*
- **B3 Traits, wants, breaks, exceptions.** Trait and want modifiers on mood; break state machine; `build_exception_queue`. *Proof: tests that a starved/overworked pawn breaks and emits the right exception.*
- **B4 Context + fallback governor.** `build_context` (summary + roster + exceptions) and `FallbackGovernor.decide`. *Proof: tests that the fallback assigns by best skill and reschedules an unhappy pawn.*

### Integration (after both tracks pass)

- **I1 Wire the seam.** Pawns fill building slots; production reads real `effective_work`. Run a headless sim: fallback governor keeps 12 pawns alive across N simulated days. *Proof: test asserts avg mood and bread stock stay above a floor for N days, no death spiral.*
- **I2 LLM governor.** Drop `LLMGovernor` in for the fallback against a live Gemma 4 E4B endpoint. *Proof: manual run log; decisions logged; town remains functional unprompted.*
- **I3 Viewer.** Render buildings, pawns, stockpile, and per-pawn mood in `app.py`. *Proof: smoke test opens, draws, exits.*

### Stretch (build 1.5)

- **S1 Seasons:** winter shortens work daylight and raises recreation/comfort demand; a summer schedule that worked tanks mood in winter.
- **S2 Research:** 2 to 3 techs (e.g. +tax, +work speed, unlock a building) spendable with coin or prestige.

---

## 9. Two-track division of labor

| | Track A | Track B |
|---|---|---|
| Owns | `world.py`, `economy.py`, `buildings.py`, `construction.py` | `pawns.py`, `mood.py`, `schedule.py`, `governor.py`, `llm.py` |
| Theme | the town and its goods | the people and the sovereign |
| Depends on | `effective_work` signature only | `Building.job_slots`, `Stockpile`, recipes only |

Assign one track to Codex and one to Claude Code. The split is by subsystem behind the frozen contract, so the two can work fully in parallel without editing the same files. Integration (I1 to I3) is done jointly or by whoever finishes first, against `main`.

**Interface-freeze protocol:** after Phase 0, `core.py` and the `effective_work` signature are frozen. If a track needs to change them, it opens a one-file PR to `main`; the other track rebases. No silent contract edits.

---

## 10. Test and verification strategy

- Core, economy, pawn, mood, schedule, and governor tests run headless, no Pygame.
- The fallback governor surviving N days is the integration oracle for "the economy is winnable."
- Pygame limited to a smoke test (open, draw, exit).
- Each milestone appends a row to a verification log (date, milestone, proof command, result, remaining gap), matching the existing repo convention.

---

## 11. Definition of done (build 1)

- Headless sim: 12 pawns, 3 chains, construction, happiness-to-tax loop.
- Pawns have skills, traits, wants, needs, mood, schedule, and breaks.
- Governor (fallback and LLM) keeps the town alive across simulated days reading only summaries plus exceptions.
- All tests green; viewer renders the new state.

---

## 12. Do not (anti-drift guardrails)

- Do not add a second faction, contested map, AoE objectives, or military in build 1.
- Do not add spatial indexing, benchmarks, or any performance optimization at 12 pawns.
- Do not polish visuals before the economy sim is real and tested.
- Do not let the Governor micromanage pawns; policy commands only.
- Do not build the LLM layer before the deterministic core and the fallback governor pass tests.
- Do not feed the Governor raw pawn state; summaries plus exceptions only.
- Update `BLUEPRINT.md` first. Both agents build against the new blueprint, not the old social-sim one.
