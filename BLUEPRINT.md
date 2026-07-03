# Local Agent Town - Blueprint

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

**Last reviewed:** 2026-07-03
**Status:** active
**Source root:** `E:\GPTCode\local-agent-town`

This is the stable reference for what the project is. The live work queue,
blockers, and proof history live in `TASKBOARD.md`; setup and verification
commands live in `RUNBOOK.md`.

Authoritative build plan for the refactor: `Local_little_world_refactor1.md`
(frozen historical artifact). This blueprint is the stable summary. Local visual
baseline: `VISUAL_DESIGN.md` (project-local reference; the harness defers visual
style to it). Branch/merge conventions: `BRANCHING.md`.

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
- open **Architect** (build costs/blockers), **Assign** (forced-override
  browser), **Research** (current spine + honest disabled entries), **History**
  (decision audit + event feed), and **Menu** (run controls, 1x/8x/20x watch
  speed, local model status) - every bottom command opens a real docked panel;
- read a Civ stats panel (Mood, Food, Water, Recreation, Rest), a resource HUD
  with storage fullness, a Governor observer card, and a right-edge exception
  stack;
- press `L` to hand policy to a local LLM (LM Studio/Ollama), with a hard
  fallback to the deterministic governor on any error;
- click any building to open a derived inspector card (staffing, recipe I/O,
  cycle progress, targets, source state, active exceptions);
- watch fields grow (bare -> growing % -> ripe), tree stands deplete/regrow, and
  a Storehouse render real held stock instead of an abstract fullness ring;
- quit and relaunch without losing the run: the civilization autosaves daily and
  on exit and resumes on boot (`save.py`).

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

This is also an executable contract, not only prose. `Stockpile` journals every
inflow/outflow (`flow_in`/`flow_out`, seed stock included), `health.check_invariants`
asserts `stock == inflow - outflow` for every good on every telemetry hour, and
any code path that mints or vanishes goods around `Stockpile.add`/`remove`
surfaces as a CRITICAL `invariant_violation` event in the viewer feed and the
analyzer. `tests/test_conservation.py` pins the law across a 10-day engine run at
every hour and proves the oracle can fail (tamper tests). Primary-producer
faucets (empty-input recipes) journal their output as inflow - they are the named
external sources, and the ledger guarantees everything downstream is conserved.

### Physical sourcing (2026-07-02, SHIPPED)

The conservation ledger proves goods balance in *count*; physical sourcing makes
them exist in *place* and *time* as well. Before this shipped, every Tier 0
faucet (Farm, Forester, Quarry, Water Well) had an empty-input recipe: a staffed
pawn's `effective_work` minted the output the instant
`Building.production_progress` crossed `recipe.work_units`, with no reference to
the `ResourceNode` map data - the field/tree/outcrop sprite the player saw was
decorative. "Labour in, resource out" with no located source violated the
conservation law's spirit even while the ledger's numbers balanced (review
finding E-9).

The refined law, enforced by `economy.production_tick`: **a faucet's output must
be tied to a located, finite- or time-gated source**, not a labor-only spigot.
Three mechanics cover every Tier 0 producer:

- **Cultivated** (Farm -> grain): the source is empty until planted, then needs
  elapsed growth time before it can be harvested. Grain cannot appear faster than
  a growing season, regardless of headcount.
- **Extracted** (Forester -> logs, Quarry -> stone): the source is a
  `ResourceNode` with a finite `amount`; harvesting depletes it. Logs regrow over
  time (a tree is a renewable but slow-growing extracted resource); stone does
  not regrow (a quarry face is mined out - the building eventually relocates or
  goes idle).
- **Replenished** (Water Well): the source is effectively inexhaustible at
  colony scale (an aquifer/water table) - modeled as an always-available
  extracted node with no depletion.

#### The field/node lifecycle

```
work "farming" at Farm, targeting the Farm's owned field (a ResourceNode on TILE_FIELD):

  state == EMPTY:
      if seed_reserve >= PLANT_COST:
          plant(field)                # consumes from a *local* seed store, not bread stock
          state -> PLANTED
      else:
          idle; raise exception "no_seed_grain"

  state in (PLANTED, GROWING):
      field.growth_progress += 1 per elapsed hour   # ticks even if the farmer is reassigned
      if field.growth_progress >= GROWTH_TARGET:
          state -> READY

  state == READY:
      harvested = harvest(field)      # yields grain; node.amount -> 0 for this cycle
      seed_reserve += harvested * SEED_RESERVE_FRACTION   # next planting's seed, not purchased
      stockpile.add(GRAIN, harvested - seed_taken)
      state -> EMPTY
```

Growth does not require the pawn's continuous attention - only planting and
harvesting are labor. The work arbiter (`work.py`) frees a farmer while the field
is growing (nothing to do there) and upgrades them back on strict priority once
the field is ready to plant/harvest.

Forester/logs follow the same shape without an explicit plant step (a felled
stand regrows on its own at `world.TREE_REGROW_PER_HOUR`). Quarry/stone uses
extracted-node depletion only; extractors harvest shared nodes nearest-first via
`world.harvest_from_nodes`. As shipped: fields ripen to `world.FIELD_YIELD` (24
grain) after `world.FIELD_GROWTH_HOURS` (24h); planting costs
`economy.PLANT_SEED_COST` (2) from `FactionState.seed_grain`; each harvest tops
the reserve back up to `economy.SEED_RESERVE_TARGET` (8) before grain reaches the
stockpile. A fresh colony starts with a small bootstrap seed grain reserve
(brought from the old country, not purchased) so the first Farm is never
seed-locked.

Exception codes: `no_seed_grain` (field empty, nothing to plant), `field_growing`
(informational, not a warning - genuinely waiting on time; suppresses the
unstaffed alarm on that farm since the arbiter frees the farmer by design), and
`node_depleted` (Quarry/Forester's nodes are exhausted; the building needs
relocation or is dead weight). These feed the `!`-badge system
(`building_exception_badges`) so a field waiting to grow does not misread as
broken.

#### Visible storage (SHIPPED 2026-07-02)

`Stockpile` stays faction-wide for now - per-building storage (pawns walking to
a specific granary to eat) is a materially bigger change touching engine,
economy, governor, health, and telemetry, and is deferred as its own later
slice. The near-term honesty fix shipped: the Storehouse renders what is
actually held - crates scale with fullness and the largest stacks are named
(`storehouse_stock_lines`), so "how much bread exists" is answerable by looking
at the map. The map also draws the field lifecycle (bare / growing % / ripe),
faded depleted tree stands, crossed-out mined-out stone, a `Seed` chip for the
planting reserve, and source-state building sublabels; clicking any building
opens a derived inspector card (staffing, recipe I/O, cycle progress, targets,
source state, active exceptions).

## Direction And Build Order

Stable product direction and sequencing. The current executable task queue lives
in `TASKBOARD.md`, not here.

**Current phase:** prototype, finishing build 1 and deep into build 2. Build 1's
engine, both governors, the viewer, mood/hunger, work-priority arbiter, water,
storage caps, the first wage/market money loop, physical resource sourcing (real
fields/nodes with growth time and depletion), visible storage, save/load, and
the UI navigation/spectator baseline are shipped. A 2026-07-01 peer review
(Fable 5) found P0/P1 harness gaps; all five confirmed findings (one-pawn-one-job,
default-deny model safety, executable conservation, analyzer honesty, watchability
refresh) are fixed. The next code task is **the trader** (crisis-line Slice 3),
now genuinely unblocked since grain has a real growing season to price against;
repair debt is now implemented in the next slice, and the Paper 7 scale
foundations follow after these branches land.

Build arc (each gated on the prior; conservation governs every system):

1. **Build 1 - one civilization works (current).** ~12 pawns, 3 chains (wood,
   food, stone), construction, needs/mood/breaks, happiness-to-tax, deterministic
   fallback Governor then the LLM Governor, viewer renders civilization state.
2. **Build 2 - depth and the spectator (in progress).** Water (done), physical
   sourcing (done), save/load (done), spectator navigation/day-night/KPI strip
   (done); clothes/beauty chain remains; full needs set; building quality to
   happiness; decay + repair as a material sink (done); the wage money loop
   (started) and Storehouse/storage caps (done); RimWorld work priorities (done)
   and the per-civilization spectator view (done); skill-based healthcare; the
   Church; operator-triggered disasters; the revolution meter + keep + fail
   state; pets; the trader (next); an era ladder (stone -> farming (current) ->
   castle -> city-state -> full civilization, gated by upgrading old buildings,
   not just unlocking new ones - owner is researching the specifics before this
   is scoped).
3. **Build 3 - the people are real.** Pawn lifecycle (aging, productivity bands,
   death, including the deferred lethal-starvation slice); birth with lineage;
   the home -> barracks -> soldier pipeline; Watch Tower, Police, Firehouse; the
   ore -> metal -> tools/parts chain; cooking/meat.
4. **Build 4 - competition and the Space Age.** Two Governor agents, one shared
   map, finite contested resources. The research spine to industrial components
   and the space-program launch victory. Scale target ~1000 pawns per
   civilization via the Paper 7 path.

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
- **Log-as-source-of-truth narration.** Keep the JSONL run log rich and answer
  "what happened while I was away" by writing the story *from* the log on
  request, rather than building an always-on digest UI. No auto-summary feature
  should be added without revisiting this framing first.
- **No ambient/compact desktop-pet mode until packaging.** Simulation depth beats
  presentation modes until the project is ready to package.

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
| Runtime | Python 3.11+ | `pyproject.toml` `requires-python = ">=3.11"` |
| Simulation core | Deterministic, Pygame-free dataclasses and pure functions | `src/agent_town` civilization modules |
| Frontend | Pygame desktop window | `civilization_view.py`; renders civilization state and is the smoke-test surface |
| Optional local AI | OpenAI-compatible chat completions adapter | `llm.py` + `LLMGovernor`; falls back to the rule-based governor on any error |
| Persistence | JSON save/load, autosave on day-rollover and exit | `save.py` |
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
  Screen regions are exclusive by default: top macro strip, pawn roster, central
  map, right inspector/exception column, docked command panel, and bottom
  command strip.
- Do not rely on colour alone; critical states need at least two channels.

Full readability/UI rules live in `VISUAL_DESIGN.md`.

## Directory Map

```text
local-agent-town/
├── src/agent_town/          <- deterministic engine + governor + viewer (real tree below)
├── tests/                   <- unittest, headless, per module
├── scripts/                 <- run analysis, scaling benchmark, LLM run, PS launchers, validator
├── research_papers/         <- design inputs (Papers 1-8); source leads, not code truth
├── docs/                    <- screenshots, proof/<slice>, run_reports, reviews (proof artifacts)
├── logs/                    <- generated JSONL run logs (git-ignored)
├── AGENTS.md                <- agent behavior and read/edit scope
├── BLUEPRINT.md             <- this file: stable project definition and direction
├── TASKBOARD.md             <- live task queue, blockers, proof log
├── RUNBOOK.md                <- setup, operation, verification, recovery
├── README.md                <- public entry point
├── HARNESS_FEEDBACK.md      <- return channel to the LLM Workbench harness
├── VISUAL_DESIGN.md         <- local visual baseline (kept, project-local)
├── BRANCHING.md             <- three-tier branch model (kept, project-local)
├── Local_little_world_refactor1.md  <- frozen refactor plan (historical)
└── archive/legacy-harness/  <- retired pre-v2 harness docs (ROADMAP, policy, checklist)
```

Real `src/agent_town/` modules:

```text
src/agent_town/
  core.py              <- shared dataclasses + the frozen contract
  world.py             <- map, tiles, resource nodes, field/node lifecycle
  economy.py           <- stockpile, recipes, production, tax, wages/market, averages
  buildings.py         <- building types, job slots
  construction.py      <- build sites, hauling to site
  pawns.py             <- pawn schema, needs, nutrition, breaks
  mood.py              <- mood ledger + effective-work seam
  schedule.py          <- schedule templates, day clock
  work.py              <- lane-based work-priority arbiter + reservations
  governor.py          <- context builder, FallbackGovernor, LLMGovernor
  llm.py               <- OpenAI-compatible adapter (LocalLLMClient)
  engine.py            <- deterministic stepper (step_hour / run / run_days)
  health.py            <- invariant checks / health verdict
  telemetry.py         <- run logging + snapshots
  save.py              <- JSON save/load round-trip, autosave/resume
  civilization.py      <- default civilization construction (FactionState)
  civilization_view.py <- Pygame viewer (default `python -m agent_town`)
  __main__.py          <- entry point (viewer + --smoke-test)
  assets/              <- CC0/provenance-tracked sprites (colony/, kenney/) + source zips
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
| `ResourceNode` | kind (a Good), amount, x, y, plus field-lifecycle state (planted/growing/ready) |
| `Stockpile` | counts (Good -> int), capacity; `add`, `remove`, `has`; journals `flow_in`/`flow_out` |
| `Recipe` | inputs, outputs, work_units, skill |
| `JobRef` | building_id, role |
| `Building` | id, kind, x, y, recipe or None, job_slots, staffed_by, built, production_progress, production_target |
| `ConstructionSite` | id, building_kind, x, y, required, delivered, work_remaining |
| `Pawn` | id, name, skills, traits, wants, needs, mood, mood_target, thoughts, schedule, assignment, coin, x, y, state |
| `ScheduleTemplate` | name, blocks (24 long); `block_at` |
| `FactionState` | stockpile, coin, pawns, buildings, construction_sites, research, research_target, research_points, season, tax_rate, day, time_of_day, grid, resource_nodes, seed, seed_grain |
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
is the only place Track A (town/goods) and Track B (people/sovereign) meet. For
Tier 0 faucets this rate now also gates on the field/node's physical state (see
Physical sourcing above): a farm with no ripe field or a depleted quarry produces
nothing regardless of `effective_work`.

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
  (if a town survives N days under the fallback, the economy is winnable). On a
  `low_food` exception it grows food capacity front-of-chain first
  (`governor.food_expansion_action`: Farm -> Mill -> Bakery toward a 4:2:1
  ratio), one building at a time.
- `LLMGovernor`: same signature, OpenAI-compatible endpoint via `llm.py` with
  JSON-schema output and a hard fallback to `FallbackGovernor` on any error.
  Model-originated actions pass an explicit **default-deny allowlist**: unlisted
  action kinds are rejected. The model may rest a flagged pawn, raise essential
  priorities, place known buildings, pick research, and retarget non-essential
  goods; it may **not** force `assign_pawn` or cap a survival good
  (grain/flour/bread/water). LLM-origin `set_work_priority` must target named
  pawns, not `group="all"`, and stay at safe essential levels.

What the Governor reads (`governor.build_context`): faction summary, roster
summary (grouped by assignment, standout skills/traits only), and the exception
queue (the only per-pawn detail, and only on a problem). It never receives all
raw pawn records.

### Production chains (build 1 cut)

| Chain | Buildings | Flow | Mechanic |
|---|---|---|---|
| Wood | Forester, Sawmill | tree node -> logs -> planks | extracted + regrows |
| Food | Farm, Mill, Bakery | field -> grain -> flour -> bread | cultivated (plant/grow/harvest) |
| Stone | Quarry | stone node -> stone | extracted, no regrow |
| Water | Water Well | water table -> water | replenished (no depletion) |
| Research | Laboratory | staffed research work -> research points | n/a |

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
- Governor actions are validated against state before they mutate it;
  model-origin actions also pass the stricter default-deny safety filter.
- One pawn may count for one staffed job at a time. Forced/manual assignment
  must release the previous slot, and the arbiter must heal or reject stale
  staffed entries before production can count them.
- The viewer may read civilization state but must not duplicate engine logic or
  block on model output.
- The deterministic core and the fallback governor must pass tests before the LLM
  layer is trusted.
- The Governor is never fed raw pawn state; summaries plus exceptions only.
- Conservation: no good, coin, or pawn is created from nothing, and every Tier 0
  faucet's output is tied to a located, finite- or time-gated source (see North
  Star and Physical sourcing above). Conservation is executable:
  `health.check_invariants` asserts the ledger holds every telemetry hour, not
  only on a fresh state or a final snapshot.

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
stakes. A starving-work floor (`mood.HUNGER_STARVING_FLOOR`) plus continuous
production (`Building.production_progress` banks fractional work) keep the death
spiral escapable with good governance and fatal without it. See `TASKBOARD.md`
Deferred.

### Crisis, response, consequence

When a civ hits a food crisis the Governor tries to fix it (re-tasking pawns to
grow more wheat -> flour -> bread, and eventually buying from a trader); if it
cannot, the design intends the civ to die, the run to end, and the failure to be
documented (starvation death itself is deferred - see above). Escape design: a
starving-productivity floor *plus* an early governor response - death loops must
be escapable with good governance, fatal without. The trader (not yet built) is
a second, external escape valve (coin -> food) reusing the **local**
`LocalLLMClient`, not a cloud API, behind a deterministic trade core.

A 2026-06-30 audit found the 12-pawn loop was not yet truthful (dead governor
levers, an autopilot that halted, a one-way economy); the truth-loop chain
closed those gaps (`set_production_target` caps output, `set_research` drives a
real tech effect, finite storage capacity is a real bottleneck, the first
wage/market money loop runs). A 2026-07-01 peer review (Fable 5,
`docs/reviews/2026-07-01-fable5-critical-review.md`) found further P0/P1 gaps,
all now fixed:

- **One pawn, one job.** Forced `assign_pawn` releases the pawn's previous
  `staffed_by` slot; the arbiter prunes stale duplicate staffed entries.
- **Default-deny model guard.** Model-origin action safety
  (`_model_action_reason`) is an explicit per-kind allowlist; unlisted kinds
  default-deny (see Governor interface above).
- **Executable conservation.** `health.check_invariants` asserts the ledger
  every telemetry hour, not just at a snapshot (see Core Logic above).
- **Analyzer honesty.** Decision records carry a per-hour `origin`
  ("model"/"fallback"); `health.model_efficacy` separates pipeline availability
  from applied model-origin actions, so a healthy-pipeline run with zero
  model-origin actions is AMBER ("pipeline-only"), never an unearned GREEN.
- **Watchability refresh.** Exception age tags (chronic vs. fresh), a rolling
  goods-flow readout, a Mood chip, attribution-first Governor text, and
  truthful `!` building badges replaced five named visibility gaps.

Unifying the crisis line with the truth-loop's finite storage exposed a latent
starvation: uncapped surplus producers (water, logs, planks, stone) flood the
storage cap and crowd out food. The default civ now seeds each surplus producer
a starting `production_target` (water 48, logs 24, planks 40, stone 40), leaving
food headroom, and research is unavailable while bread cover is under a day so a
farmer never idles on the Laboratory during a shortage.

### Repair debt (T-102)

Built production/service buildings now carry a 0-100% maintenance condition
without changing the frozen `core.py` contract. Minor wear is cosmetic; below
75% condition it becomes a visible efficiency penalty before catastrophic
failure. Staffed damaged production buildings spend their hour on repair before
normal production, consume one plank and one stone per completed repair packet,
and recover condition. Storehouse capacity is also condition-scaled, so service
debt is real rather than only decorative. Telemetry snapshots record per-building
condition/efficiency/repair progress, and the viewer surfaces damaged buildings
through the exception stack, map badge, and building inspector.

### Scale architecture (Paper 7)

At ~12 pawns, keep visible truth exact. Two low-cost foundations come first:
reachability regions (reject impossible jobs before pathfinding) and
deterministic phases (stable ordered job claims/reservations/movement/production/
needs/tax). Hard trust rule: any pawn that is selected, visible, in conflict,
carrying a scarce object, or transferring ownership is forced back into exact
simulation; approximation is only for opportunity search and offscreen movement.
Population growth (build 3) is what makes the real scale need appear; there is
no in-play way to reach large populations yet.

## Trust, Privacy, And Safety Boundaries

Sensitive data / boundaries:

- Keep the project local-only by default. No hosted LLM providers, telemetry, or
  external persistence without explicit user approval.
- Do not commit `.venv`, logs, databases, private exports, tokens, or generated
  dumps (enforced by `.gitignore`).
- Local LLM use stays local-only. `AGENT_TOWN_LLM_MODEL` overrides discovery;
  `AGENT_TOWN_LLM_AUTO_DISCOVER=0` disables startup discovery for deterministic
  non-LLM runs.

## Known Risks

Immediate blockers belong in `TASKBOARD.md` -> Blocked. Stable risks:

| Risk | Impact | Mitigation / owner |
|---|---|---|
| LLM governor can starve the town with bad policy | A model run empties stockpiles / drops mood | Deterministic fallback is the oracle; LLM-origin work-priority guardrails (named pawns, no `group="all"`); default-deny model-action allowlist |
| Pygame as the viewer may cap scale | Rendering could block the 1000-pawn goal | Keep the engine testable/benchmarkable headless; migrate engines only on benchmark evidence, not taste |
| Determinism regressions | Break the winnability oracle and replayability | Seeded PRNG keyed to `FactionState.seed`; determinism tests; the LLM is the only nondeterministic layer |
| Frozen-contract drift | Two-track collisions / silent breakage | `core.py` changes go through the one-file-PR process, not unilateral edits |
| Research papers treated as code truth | Silent design drift | Papers are inputs; conflicts become `TASKBOARD.md` tasks, not doc edits |
| Trader economics not yet balanced against real grain lead time | Physical sourcing gave grain a 24h growing season; trader pricing (coin -> bread) must account for that lead time or the crisis line's "escapable" claim could silently stop being true | Land the trader (crisis-line Slice 3) with the real growth-time delay already in play, not against the old instant-mint assumption |
| Repair tuning is first-pass | Decay rate, repair threshold, and material packet are deliberately conservative and not playtested against long watched runs | Revisit if run reports show repair never matters or drains planks/stone too aggressively |
| The sim can still starve even with the money loop live | Balance is not fully proven under all governor/crisis combinations | Tracked in `docs/run_reports/` observation notes; governor/balance tuning is prioritized over new surface area |

## Design Decisions

Decisions future agents must preserve (most recent last). Older per-slice
decisions and the full pre-v2 verification history are preserved in
`archive/legacy-harness/ROADMAP.md` and git history.

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
| Escape design for the crisis line: a starving-productivity floor plus an early governor response, not one or the other | Death loops must be escapable with good governance, fatal without; the fallback grows food capacity front-of-chain on `low_food` | 2026-07-01 owner direction |
| Critical review findings become harness inputs before feature work; all five confirmed P0/P1s fixed (one-pawn-one-job, default-deny model safety, executable conservation, analyzer honesty, watchability refresh) | Confirmed findings from `docs/reviews/` block new roadmap features until reproduced and fixed or explicitly downgraded with evidence | 2026-07-01 Fable 5 peer review |
| Physical sourcing shipped: every Tier 0 faucet draws from a located, gated node | Farms plant/grow/harvest owned field nodes (24h season, seed reserve), Foresters deplete regrowing tree stands, Quarries mine finite outcrops, the Well stays a named aquifer. The crisis line was re-verified after (marginal civ recovers by day 4; fail state proven under an inert governor). Closes review E-9 | 2026-07-02 physical sourcing |
| Repair debt shipped as dynamic building condition outside the frozen core contract | Keeps `core.py` unchanged while making building wear visible, persisted, logged, and consequential: damaged buildings lose efficiency, staffed repair consumes planks/stone plus the production hour, and Storehouse service capacity scales with condition | 2026-07-03 T-102 repair debt |
| Surplus producers get a starting production ceiling so food survives the storage cap | Unifying the crisis line (sustain floor) with the truth loop (finite storage) exposed a latent starvation: uncapped water/logs/planks/stone flood the 240-cap stockpile and crowd out grain/flour/bread | 2026-07-01 crisis+truth-loop merge |
| Viewer P2 batch: derived attention label, shared idle definition, decodable mood dots, per-decision pressures, visible storage, building inspection | The Governor card/macro/menu drop the invented confidence %; pawn sheets say "off shift" vs "idle (no job)"; hovering decodes the mood dot; decision records carry live exception kinds; the Storehouse names real held stock; clicking a building opens a derived "why is this (not) producing" card | 2026-07-02 review P-5/P-8/P-9/P-10 + Slice 5 |
| Save/load shipped: the civilization persists across sessions | `save.py` round-trips the full `FactionState` as JSON; the viewer autosaves daily and on exit and resumes on boot. Supersedes the earlier "wake the dormant SQLite scaffold" plan | 2026-07-02 owner direction |
| Spectator navigation + day/night + KPI strip shipped | Held-key WASD pan, clickable roster + alerts, a follow camera, a day/night light overlay, and a top KPI strip make the civilization watchable as a spectator experience, not only a debug view | 2026-07-02 spectator UI batch |
| Adopt LLM Workbench v2.1 harness (four control docs) via the Adoption protocol | Replace the pre-v2 doc set (AGENTS/ROADMAP/BOOTSTRAP_CHECKLIST/UNATTENDED_WORK_POLICY) with AGENTS/BLUEPRINT/TASKBOARD/RUNBOOK; retire old docs to `archive/`; preserve all content; `BRANCHING.md` and `VISUAL_DESIGN.md` stay as project-local "keep" docs | 2026-07-03 harness adoption (redone against current `integration`, superseding the stale PR #40 draft forked before physical sourcing shipped) |

## Health Criteria

The project is healthy when:

- the headless unittest suite passes (`unittest discover -s tests`);
- the frozen contract in `core.py` imports and instantiates;
- `python -m agent_town --smoke-test` exits successfully;
- `scripts/validate-workbench.ps1` passes (control-doc structure check);
- `health.check_invariants` or its run-level companion catches double-staffing,
  phantom staff, negative stock, and any executable conservation ledger breach;
- model-originated actions are explicit-allowlist only, with unsafe proposals
  rejected or falling back visibly;
- local-model proof distinguishes pipeline availability from useful, applied
  non-fallback model policy;
- the primary viewer workflow renders and steps without crashing;
- secrets and local data are not exposed in committed or built output.

Exact verification commands live in `RUNBOOK.md`. Current task status and proof
history live in `TASKBOARD.md`.
