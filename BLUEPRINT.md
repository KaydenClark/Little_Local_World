# Local Agent Town - Blueprint

**Last reviewed:** 2026-06-29
**Status:** active
**Source root:** `E:\GPTCode\local-agent-town`

## What This Project Is

Local Agent Town is being refactored from an AI-Town social wander-sim into a
single-faction, LLM-governed civilization builder: a Townsmen-style town economy
staffed by about a dozen RimWorld-style pawns, run by one Governor agent that
sets policy and never micro-controls pawns.

One sentence:

> One Agent governs one town of about 12 Pawns by setting policy (assign,
> schedule, build, research) while a deterministic engine runs the pawns and
> economy.

Primary users:

- Kayden, as the local operator and designer of the civilization.
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
- The Pygame viewer renders the civilization state and remains a smoke-test surface.

### Non-Goals

This project is not trying to:

- become a web app or multiplayer game, or require hosted infrastructure;
- require paid AI services for the base experience;
- add a second faction, contested map, crowns/objectives layer, or military in
  build 1;
- add spatial indexing, benchmarks, or performance optimization at 12 pawns;
- let the Governor micromanage pawns - it issues policy commands only.

"Multiplayer game" above means human multiplayer. Multiple AI agents each
running their own civilization on one map (below) is a planned later build, not a
non-goal.

## Long-term vision (beyond build 1)

Build 1 is the foundation: one civilization, one Governor, about 12 pawns, headless
then rendered. The product it grows into:

- **Pure autopilot, watched not played.** The operator does not play the civilization.
  One Governor agent per civilization runs it end to end; the operator spectates -
  opening any civilization and seeing its live state (pawn assignments, work
  priorities, stockpiles, mood, construction) as if they were the one playing,
  but only to confirm the agent is managing well. The civilization is hands-off by
  design.
- **One voice per civilization.** The Governor agent is the civilization's single voice and
  mind. Pawns have no voice; they have RimWorld-style free will - each pawn
  autonomously picks its highest-priority available job from a priority list the
  Governor tunes. The point of the spectator view is watching how the agent
  juggles those priorities across a dozen, then hundreds, of autonomous pawns.
- **Scale arc:** 1 agent / about 12 pawns, then 1 agent / up to about 1000
  pawns, then two agents each running their own civilization on one shared map,
  competing for the same finite resources. Rivals do not know the other exists
  at first; contact is emergent.
- **Victory is the Space Age.** The primary win is technological: research and
  build a civilization able to leave the planet (a launch / space-age milestone). The
  secondary, implied win is to outlast the rival civilization. Research is therefore a
  core progression spine, not a stretch goal.
- **A player avatar / "the keep."** Each civilization has a seat of power in the world
  the agent is identified with, so the agent has visible stake. Revolution
  targets the keep; losing it is a fail state.
- **Immortal agents, mortal pawns.** Real time maps to game time at roughly
  1 real hour = 1 game year. The Governor agent is immortal; pawns age (live to
  about 80, productive about 16-60; the Space Age extends this to about 120,
  productive to about 80). The very old and very young are cared for, not worked.

These are marked direction. Build 1 stays single-civilization, single-map, no rival,
no military; the roadmap sequences the rest, governed by the law below.

## Design north star: conservation ("nothing from nothing")

Stated as a law because it governs every system: nothing is created from
nothing; everything traces to a source.

- Goods come from chains: bread is baked from flour milled from grain grown on a
  farm.
- Soldiers come from people: a soldier is a pawn who was born from two parent
  pawns, grew up, walked to a barracks, and trained. The barracks never spawns a
  unit from nothing.
- Coin comes from circulation: taxes are collected from wages the civilization already
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
| Simulation core | Deterministic, Pygame-free dataclasses and pure functions | `src\agent_town` civilization modules |
| Frontend | Pygame desktop window | Smoke test today; renders civilization state at integration milestone I3 |
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
  fallback. Mood and mental-break timing use a seeded PRNG keyed to the civilization
  seed, which is still deterministic per seed.

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
- Persistent UI is for scanability, not completeness. Keep the Civ strip, pawn
  roster, alert stack, and governor status short; put causes, full thought
  ledgers, decision traces, and stockpile detail in the inspector or drill-downs.
- Do not rely on color alone. Critical states need at least two channels such as
  color plus icon, shape, position, or brief motion. Text belongs on dark
  back-plates, not directly on terrain.

## Research-backed design inputs

The `research_papers` folder is now the source-input shelf for external game
reference work. These papers guide future implementation, but active code and
tests remain the source of truth until a research finding is implemented and
verified.

Current research inputs, in implementation order:

1. `research_papers/1.rimworld_mood-system-report.md` - keep the mood ledger,
   target/current mood split, asymmetric drift, break thresholds, Catharsis, and
   expectations as the future baseline correction. Treat generic mood-to-work
   speed as a deliberate non-vanilla choice if retained.
2. `research_papers/2.rimworld_hunger-system-report.md` - pawns eat from a
   threshold-driven self-care job, not meal schedules. Bread is a custom Local
   Agent Town staple; the paper recommends 0.25 nutrition per bread and up to
   four bread per eat job before starvation is made lethal.
3. `research_papers/3.rimworld_autonomous-pawn-report.md` - Build 2 work
   priorities should use a visible lane-based arbiter: forced/manual, hard
   state, medical rest, self-care, emergencies, normal work, idle.
4. `research_papers/4.townsmen_economy-loop-report.md` - Build 2 economy depth
   should use district-aware logistics, essentials before comfort, storage caps,
   repair debt, wages -> spending -> taxes, and reserve-aware external trade.
5. `research_papers/5.aoe_civ-readability-report.md` - viewer readability should
   prioritize silhouettes, stable anchors, explicit draw layers, hover/selection
   separation, threshold badges, and accessibility contrast.
6. `research_papers/6.ui-report.md` - the observer UI should combine an
   Age-style Civ strip with a RimWorld-style pawn roster/inspector and an
   always-visible local Governor status card.
7. `research_papers/7.scalable-sim-report.md` - scale comes from indexed and
   tiered work, not smarter global agents: exact truth near the player,
   reachability prefilters, deterministic command phases, job packets, path
   abstraction, cadence tiers, and visual/update LOD outside the active bubble.
8. `research_papers/8.little-local-world-research-synthesis.md` - the project
   synthesis and the sequencing authority over Papers 1-7. It collapses them into
   one product rule, *make autonomous causality visible*, and one strict build
   order: food (done) -> work priorities + reservations (done) -> water (done)
   -> map readability (done) -> governor card (done) -> *close the 12-pawn truth
   loop* -> scale foundations -> deeper economy. A 2026-06-30 audit found the
   12-pawn loop is not yet truthful (governor levers that apply but change
   nothing, an autopilot that halts, a one-way economy), so the next code task is
   closing that loop, not Paper 7 scale work - this honors Paper 8's own rule that
   population must not scale before the 12-pawn loop is satisfying. See
   `ROADMAP.md` "Truth-loop gaps (close before scale)". Lethal starvation and the
   deeper economy remain deferred behind the visible autonomy loop.

When these papers conflict with current implementation, the conflict becomes a
roadmap task instead of being silently folded into docs. Paper 8 sets the order
in which the others are implemented; see `ROADMAP.md`'s Research Paper
Implementation Queue.

## Scale architecture

Paper 7 turns the 1000-pawn goal into a staged architecture instead of a late
optimization project. At 12 pawns, keep visible truth exact: reservations,
inventory transfers, short-range movement, health/death, scarce-resource
ownership, construction completion, and deterministic event order. Even at that
scale, build two low-cost foundations early:

- **Reachability regions.** Every walkable tile eventually gets a `region_id`,
  with dirty-region recomputation when topology changes, so impossible jobs can
  be rejected before pathfinding.
- **Deterministic phases.** Job claims, reservations, path requests, movement,
  interactions, production, needs, and tax advance in stable ordered phases so
  later batching does not break replayability.

Scale thresholds are design guidance, not source claims:

| Scale | Keep exact | Start abstracting |
|---|---|---|
| Up to about 16 active pawns | Almost everything | Optional render cadence only |
| About 16 to 64 | Inventory, reservations, local interaction truth | Candidate indexes and deterministic update buckets |
| About 64 to 150 | Near-goal movement and active-bubble behavior | Chunk/HPA-style long paths, shared routes to common sinks, animation LOD |
| About 150 to 400 | Selected/near/conflict pawns | District work packets, path budgets, offscreen corridor ETAs |
| About 400 to 1000 | Player-near truth and state transfers | Far-needs cadence, simplified local avoidance, strong visual and overlay LOD |

The hard trust rule: if a pawn is selected, visible, in conflict, carrying or
touching a scarce object, or about to transfer ownership of a good/building/job,
force it back into exact simulation. Approximation is allowed for opportunity
search and offscreen movement, not for player-readable truth.

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
  civilization_view.py    <- Pygame viewer for civilization state            (integration)
tests\               <- unittest, headless, per module
```

Transition note: the legacy social-sim (`Agent`, `Simulation`, `Location`,
`app.py`, `persistence.py`, and `spatial.py`) was retired after I3 reached
civilization-viewer parity. Current runtime code is the civilization contract, engine,
governor, local LLM client, and `civilization_view.py`.

## Frozen contract

These shapes live in `core.py`, were written first, and are frozen. Both build
tracks build against them. Any change after the freeze is a small one-file PR
that both tracks rebase on, never a unilateral edit.

| Entity | Key fields |
|---|---|
| `Good` (enum) | logs, planks, grain, flour, bread, water, stone |
| `GridMap` | width, height, tiles; `in_bounds`, `tile_at` |
| `ResourceNode` | kind (a Good), amount, x, y |
| `Stockpile` | counts (Good to int); `add`, `remove`, `has` |
| `Recipe` | inputs, outputs, work_units, skill |
| `JobRef` | building_id, role |
| `Building` | id, kind, x, y, recipe or None, job_slots, staffed_by, built |
| `ConstructionSite` | id, building_kind, x, y, required, delivered, work_remaining |
| `Pawn` | id, name, skills, traits, wants, needs, mood, schedule, assignment, x, y, state |
| `ScheduleTemplate` | name, blocks (24 long); `block_at` |
| `FactionState` | stockpile, coin, pawns, buildings, construction_sites, research, research_target, research_points, season, tax_rate, day, time_of_day, grid, resource_nodes |
| `CivilizationException` | kind, pawn_id or None, building_id or None, detail |
| `GovernorAction` | kind plus the fields for that action (see Governor interface) |

Naming decision: the refactor plan calls the exception-queue entity
"Exception". It is implemented as `CivilizationException` so it never shadows the
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
| Research | Laboratory | staffed research work to research points |

Construction consumes planks plus stone. Bread is the consumable that feeds the
food need.

The current research spine is deliberately minimal: the Governor can select the
first tech (`efficient_baking`), staffed Laboratory work completes it, and the
completed tech increases Bakery bread output. The full Space-Age victory spine
remains a later build target.

Pawn needs currently tracked: rest, food, water, recreation. Rest and recreation
are 0.0-1.0 satisfaction values that decay over time and are restored by the
matching schedule block. Food is a RimWorld-style **nutrition/saturation
reserve** (0.0-1.0 nutrition, max 1.0) refilled only by eating bread portions
(0.25 nutrition each, up to four per eat job). Water is the first Build-2
essential reserve: it decays over time, is refilled only by consuming stockpiled
water, and creates thirst mood pressure plus a governor `low_water` exception
when supply or need is low. No schedule block or idle hour grants food or water
for free (conservation law); full design in "Mood: the RimWorld model" below.

Trait subset: industrious or lazy (work speed), tough or frail (mood floor now,
combat later), optimist or pessimist (mood floor), loner (solo jobs lift mood),
night owl (better on the night schedule).

Wants subset: wants_outdoor_work, wants_own_house, wants_soldier (flagged,
unused until build 2). A met want is a mood boost; an ignored one is a slow mood
drag.

Mood and breaks use the RimWorld model on a **0-100 scale**: `mood_target = base +
sum(thoughts)` and the displayed mood drifts toward it. Below the break bands a
pawn slacks (effective_work drops), then wanders off the job. The break, surfaced
as a `CivilizationException`, is the Governor's early-warning signal. Full design in
"Mood: the RimWorld model (build 1 foundation)" below.

### Mood: the RimWorld model (build 1 foundation)

We adopt RimWorld's mood model as closely as the engine allows, including its
**0-100 mood scale** (replacing the earlier 0-1 mood, so thoughts and break bands
use RimWorld's own point values directly). Mood is a story-generating system, not
a cosmetic meter: logistics (food, rest, recreation, later clothes/death/etc.)
become emotion, and emotion feeds back into work, breaks, and tax. Shape:

> mood_target = base mood + expectations + sum of active thoughts
> actual mood drifts toward the target over time
> low actual mood risks a mental break; high mood (later) enables inspirations

Build 1 builds the foundation; the deferred pieces below slot into the same
architecture rather than replacing it.

- **Two layers (target vs actual).** Each tick we compute `mood_target` from the
  ledger; the displayed `pawn.mood` (actual) drifts toward it at +12 per hour
  rising and -8 per hour falling (on the 0-100 scale), and is frozen while the
  pawn sleeps. The
  buffer means one bad event does not instabreak a pawn, but sustained misery
  does - and fixing a problem lifts the target at once while the pawn recovers
  gradually. `Pawn.mood_target` is added to the frozen contract for the readout.
- **Thoughts are the ledger.** Mood is the sum of named moodlets - `Thought
  {kind, label, value, age, stack}`, in a `Pawn.thoughts` list (contract change)
  - sourced from needs, traits, wants, and later events. Many small negatives
  stack into a crisis. The pawn inspector shows the list, RimWorld-style. Values
  are RimWorld points on the 0-100 mood scale (e.g. Hungry = -6).
- **Base mood from difficulty.** The base is a storyteller/difficulty setting
  (RimWorld uses ~42 down to ~22); build 1 ships one default and exposes the
  knob later.
- **Food is a nutrition reserve, and hunger is the first real thought.** The food
  need becomes a RimWorld-style saturation reserve (0-1 nutrition, max 1.0)
  drained by hunger and refilled only by eating: a pawn opportunistically eats
  one or more bread when it drops to ~30% saturation, capping at 1.0 with excess
  wasted. There is no meal schedule block (RimWorld has none) and no free
  off-shift restoration. Bread is a 0.25 nutrition portion and pawns eat a
  rounded portion count, up to four bread per eat job. The Bakery outputs four
  bread portions per cycle so the production chain stays balanced after the
  smaller food unit.
  Saturation drives one hunger thought: Fed (>=24%) none; Hungry (24-12%) -6;
  Ravenously hungry (12-0%) -12; Malnourished/Starving (0%) -20 until the
  starvation system lands. Food is pulled out of the blended needs term so hunger
  hits mood exactly once. The deeper malnutrition bands and lethal starvation
  arrive with starvation death (below, step 4). This is the primary near-term
  incentive to keep pawns fed.
- **Breaks are band + roll.** Three bands replace the old single threshold:
  minor < 35%, major around 20%, extreme around 5%. A break fires on a mean-time-between
  roll that is faster in lower bands, off a seeded PRNG keyed to a civilization seed -
  so the engine stays reproducible (same seed + same policy = same outcome) while
  still feeling unpredictable, the way RimWorld's "story generator" does. Traits
  shift a pawn's break thresholds (iron-willed vs volatile). After a break ends
  the pawn gets a large Catharsis thought, so colonies are not trapped in endless
  consecutive breaks. Breaks remain the Governor's early-warning exceptions and
  still cut `effective_work`.
- **Civ stats bar.** "Civ" (Civilization, the renamed civilization) mood is the average
  of all pawns; a Civ stats bar shows five Civ-wide averages - Mood, Food,
  Water, Recreation, Rest - as coloured percentages. Food and water now have
  direct mood consequences; recreation and rest remain readouts until their
  richer thought slices.

Deferred to build 2, in the same architecture: **expectations** (a wealth-driven
mood treadmill, +30 early to 0 when rich - needs wealth valuation; stubbed
"extremely low" until then); **richer thoughts** (meal quality, recreation
variety, slept-outside, darkness, social fights, death/corpse); and
**inspirations** (the positive mirror of breaks, mood > ~49%, once there are
systems - craft / recruit / trade - for them to boost). Rooms/beauty and
prisoners are out of build-1 scope.

Note: adopting base + expectations + thoughts changes absolute mood numbers, and
mood feeds `daily_tax_income`, so the tax constant is rebalanced in the same pass,
not silently.

Productivity note from the mood research: vanilla RimWorld does not use a simple
generic mood-to-work-speed multiplier. Local Agent Town follows that: the legacy
`mood_factor` hook is neutral, while `effective_work` is reduced directly by
hunger and break state. High-mood upside remains deferred to explicit inspiration
events once there are systems worth boosting.

### Starvation and pawn loss (build 1)

Food is the first need with a lethal failure mode and the build-1 reason to keep
the supply chain fed - but it is sequenced *after* the mood foundation above (the
hunger thought is the primary near-term incentive). Rules:

- Food is restored only by eating bread (a `Good`). No schedule block, building,
  or idle hour grants food for free - this is the conservation law applied to
  hunger ("nothing from nothing"). The free off-shift food restoration is removed
  with the nutrition reserve in the mood foundation (step 2); this section then
  adds the lethal failure mode on top. At step 4 the flat "72h since last meal"
  rule may be replaced by a RimWorld-style malnutrition ailment (severity accrues
  while at zero nutrition, death ~6 days after) - finalised when step 4 lands.
- Each pawn tracks `hours_since_meal`, reset to 0 when it eats and incremented
  every hour otherwise. A pawn that goes 72 hours (three game-days) without a
  meal dies and is removed from the civilization; the engine scrubs it from every
  building's `staffed_by`. (Optional follow-on: a witnessed-death civilization-wide
  mood debuff, RimWorld-style.)
- The Governor gets an early-warning `starving_pawn` exception well before the
  72-hour mark plus a civilization food readout (bread on hand / days of food /
  starving count), so policy - build and staff Farm -> Mill -> Bakery - can
  respond before anyone dies. The deterministic fallback prioritises the food
  chain under starvation, keeping it a valid winnability oracle.
- The viewer surfaces hunger as visible status: a starvation badge on the pawn,
  a "starving / Nd since food" line and death countdown in the inspector, a
  civilization food/starving readout in the HUD, and a death line in the event log.

This pulls a narrow slice of the build-3 pawn lifecycle (death) forward into
build 1: starvation death only. Aging, productivity bands, and birth stay in
build 3. Adding `Pawn.hours_since_meal` is a deliberate post-freeze change to the
frozen contract in `core.py`, made via the documented one-file-PR process, not a
silent edit.

## Target content design (full game)

Build 1 ships only the first rows; `ROADMAP.md` sequences the rest. This table
is the design target the chains converge on, not the build-1 cut. Every "from /
to" obeys the conservation law above. The `Build` column is the earliest build
that ships the row.

Build-2 economy direction from the Townsmen research:

- Model essentials before comfort: water, food, shelter/warmth, and repair stay
  ahead of clothing, beauty, taverns, and luxury services.
- Make logistics district-aware before making them large. District storage,
  market stalls, and travel-share readouts are more useful than global stock
  totals alone.
- Add storage caps as real blockers with visible pressure: warning at about 80%
  full and critical at about 95% full.
- Add repair debt as a material and labour sink. Building condition should
  degrade into output/service penalties before catastrophic failure.
- Keep the money loop legible: treasury pays wages, households buy essentials
  and comfort goods, taxes and building revenue return coin, and reserve-aware
  trade is the main net-new coin source.

### Production chains

Tier 0 is extraction from map resource nodes. Each later tier needs the prior
tier's output and, past tier 1, a research unlock - so an advanced building can
only exist once its supplier and its tech do.

| Tier | Building | Consumes | Produces | Skill | Build |
|---|---|---|---|---|---|
| 0 | Forester | tree node | logs | forestry | 1 |
| 0 | Quarry | stone node | stone | mining | 1 |
| 0 | Farm (crops) | field node | grain, vegetables | farming | 1 |
| 0 | Water Well | water table | water | water | 2 |
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
| 2 | Laboratory | researcher labour | research points | research | 2 |
| 3 | Foundry / Machine shop | metal, parts | components | engineering | 4 |
| 3 | Space program | components, research | launch readiness | engineering | 4 |

Tools and furniture are quality boosters: tools raise pawn work speed; furniture
raises building quality, which raises mood (see needs).

### Pawn needs (full set)

Each need is 0.0 to 1.0, decays over time, and is restored by the matching
good/building or schedule block. The current runtime ships rest, food, water,
and recreation; the rest follow.

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

**Status (2026-06-30): designed, not implemented.** Today coin only enters via
tax (`economy.daily_tax_income`) and only leaves via the finite build order;
pawns are never paid, so "tax" recirculates nothing. The wage loop below is the
first economy coupling in the truth-loop work (see `ROADMAP.md` "Truth-loop
gaps"), because without it only the upstream-shortage bottleneck can occur.

Coin is conserved internally and only enters or leaves through trade.

- Wages: treasury to pawn purse each day. Unpaid pawns lose mood.
- Spending + tax: pawn purse back to treasury, via purchases at the
  Market/Tavern and via tax on wages.
- Trade: the Market sells surplus goods to off-map caravans for net new coin, or
  buys scarce goods for coin. This is the only external source and sink.
- Current runtime slice: daily wages move treasury coin into assigned pawn
  wallets; a staffed Market sells bread to pawn wallets above reserve, collects
  whole-coin sales tax, reports unmet bread buyers as the first Market service
  pressure signal, then exports remaining bread surplus above reserve. Taverns,
  comfort spending, reserve-aware imports/exports, and full district market
  queues remain later Build-2 work.

So "where do taxes come from if you don't pay your people" resolves cleanly: you
tax the wages you paid, and net civilization wealth comes from selling what the pawns
produced. No wages means nothing to tax, plus a mood penalty.

### Healthcare (skill, not a punishing chain)

Treatment is a labour + skill task, not a deep supply chain. A pawn with a
doctoring priority tends a patient (at the Infirmary or in a bed); care quality
scales with the doctor's skill, and every treatment raises that skill. Medicine
(one cheap Apothecary good) is an optional booster that improves outcomes but is
never required - you can run healthcare with a willing, improving pawn and
nothing else, RimWorld-style.

### Research and the Space Age

Research points from staffed Laboratory work buy techs along a spine that ends
in space flight. The current runtime ships only the first truthful slice:
`efficient_baking` raises Bakery bread output, proving that `set_research`
causes measurable simulation change. Later techs unlock building tiers, raise
pawn lifespan/productivity, and eventually complete the space-age milestone.
Reaching that milestone is the primary victory.

### Storage

Stockpile capacity is finite and raised by the Storehouse; a "storage full %"
readout surfaces it (see `ROADMAP.md`). The current Build-2 slice gives the
default civilization a conservative global stockpile cap, blocks production
that would grow storage past the cap, and logs storage fullness. Built
Storehouses raise the cap, and 80/95% storage pressure is shown in the HUD and
on Storehouse buildings. Per-district storage and hauling pressure remain later
Build-2 work.

### Disasters (operator as storyteller)

Disasters (fire, lightning, cold snaps that freeze crops or kill unsheltered
pawns) are operator-triggered, not random: the operator is the storyteller, via
a deliberate UI action or a separate prompting model - never the Governor agent
that is playing the civilization.

### Pets

Decoration in build 1 (dogs/cats appear once population passes a threshold).
Later, dogs gain a guard role: protecting the civilization area alongside pawns.

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
the substance of the spectator view. `set_research` now selects an active tech
target; Laboratory work completes it, and completed techs must change simulation
behavior. The full Space-Age victory remains a later spine, not a stretch goal.

Build-2 autonomy direction from the RimWorld work-priority research:

- Do not implement a full RimWorld think tree. Use a compact, inspectable
  lane-based arbiter.
- Decision lanes, in order: forced/manual, hard state, medical rest, self-care,
  emergency, normal work, idle.
- Normal work sorts by manual priority first, then work-type order, workgiver
  order, target urgency, path/distance cost, and skill fit. Skill never rescues
  an illegal, unreachable, reserved, disabled, or lower-lane job.
- Add reservations before broad autonomy so two pawns do not claim the same
  target.
- The spectator UI must show why a job won and why the top rejected candidates
  lost; otherwise autonomous behavior will look arbitrary.

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

Core behavior lives in the civilization modules under `src\agent_town`.

Rules:

- All economy, pawn, mood, schedule, and governor logic is testable without
  Pygame.
- Governor actions are validated against state before they mutate it.
- The viewer may read civilization state but must not duplicate engine logic or block
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
| Refactor the social-sim into an LLM-governed civilization builder | New product direction; supersedes the social-sim blueprint | 2026-06-27 `Local_little_world_refactor1.md` |
| Freeze a shared contract in `core.py` first | Lets two tracks build in parallel without colliding | 2026-06-27 Phase 0 |
| `effective_work` is the only cross-track seam | Keeps the parallel split clean and the integration point small | 2026-06-27 Phase 0 |
| Name the exception entity `CivilizationException` | Avoids shadowing the builtin `Exception` the LLM fallback relies on | 2026-06-27 Phase 0 |
| Keep the legacy social-sim importable during the refactor | Keeps the existing viewer and tests green until milestone I3 | 2026-06-27 Phase 0 |
| Deterministic fallback governor before the LLM governor | The fallback is the winnability oracle and the safety net | 2026-06-27 refactor plan |
| Retire the legacy social-sim after I3 parity | Removes obsolete viewer/runtime code once the civilization viewer, LLM governor, smoke test, and benchmarks cover the current product | 2026-06-28 I3 cleanup |
| Pull starvation death into build 1 (72h since last meal -> pawn dies) | Food had no lethal consequence, so the food economy carried no stakes; death by starvation is the build-1 incentive to keep pawns fed. Aging/birth stay in build 3 | 2026-06-28 user request |
| Hunger as an explicit -5/-10/-15 mood modifier; death deferred behind it | Makes the mood hit the near-term feed-your-pawns incentive; food is pulled out of the blended needs term so hunger is one clean RimWorld-style modifier, not a double drag | 2026-06-28 user request |
| Rename "civilization" -> "Civilization (Civ)" everywhere | One consistent player-facing and code vocabulary; done as an isolated behaviour-preserving commit (~327 refs / 32 files) before the mood work | 2026-06-28 user request |
| Adopt RimWorld's mood model (two-layer target/actual, thoughts ledger, break bands), foundation-first | Mood is the game's story engine; building it RimWorld-shaped now means later thoughts/expectations/inspirations slot in without rework. Break timing uses a seeded PRNG so runs stay reproducible per seed | 2026-06-28 user request |
| Food is a nutrition/saturation reserve (max 1.0, bread unit = 0.25), eaten opportunistically below 30% with rounded portions up to four bread and overeating waste | Authentic RimWorld hunger; makes the bread chain conservation-real instead of an abstract satisfaction bar; Bakery output is four bread portions per cycle so the smaller unit does not break Build-1 food balance | 2026-06-28 user decision, updated 2026-06-29 research retune |
| Pawns eat opportunistically when hungry, not on a meal schedule block; the free off-shift food restoration is removed | RimWorld has no meal block - pawns eat when they drop to ~30%; closes the "food from nothing" conservation gap | 2026-06-28 user decision |
| Mood moves to a 0-100 scale (RimWorld 1:1); thoughts use RimWorld point values (Hungry -6 etc.); `daily_tax_income` recalibrated in the same pass | Hunger, break, and thought numbers match RimWorld exactly with no 0-1 translation; supersedes the earlier "-5/-10/-15 on 0-1" hunger sketch | 2026-06-28 user decision |
| Research papers are implementation inputs, not automatic code truth | Papers in `research_papers` are converted into explicit tasks, tests, and deferrals; source-level constants are verified or marked research-derived before exact implementation | 2026-06-29 research intake |
| Reconcile Build-1 hunger with the hunger paper before lethal starvation | Bread is now 0.25 nutrition with up to four units per eat job; starvation death remains deferred until malnutrition/death timing is implemented deliberately | 2026-06-29 research retune |
| Build-2 pawn autonomy uses a lane-based arbiter, not full RimWorld think-tree parity | Forced/manual, hard-state, self-care, emergency, and normal-work lanes preserve the feel while keeping decisions inspectable and testable | 2026-06-29 research intake |
| Build-2 economy starts with district logistics and essentials before comfort | Water, food, storage, repair, wages, spending, taxes, and trade should surface bottlenecks through days-of-cover, blocked time, travel share, queue wait, and reserve-aware export rules | 2026-06-29 research intake |
| Viewer readability follows AoE-style silhouette/layer/status rules and observer UI density budgets | Identity should read through silhouette and anchor consistency first; state/cause/actionability stay visually separated; persistent UI stays compact while detail lives in inspectors | 2026-06-29 research intake |
| Scale work starts with reachability regions and deterministic phases, not a new engine | Paper 7 says exactness should stay near player-visible truth while job search, long movement, update cadence, and overlays become indexed, batched, or approximate as population grows | 2026-06-29 research intake |
| Adopt the Paper 8 synthesis build order as sequencing authority | The seven source papers collapse into one rule - make autonomous causality visible - and one build order. Food, work priorities, and water are now implemented in that order; lethal starvation and deeper economy stay deferred behind the visible autonomy loop | 2026-06-29 research synthesis + user direction |
| Build-2 step 1 shipped: pawns self-select work via `work.py`; the governor stops routine `assign_pawn` | A deterministic lane arbiter (forced -> hard-state -> self-care -> normal work -> idle; medical/emergency are ordered stubs) does staffing by manual priority -> work-type order -> distance -> skill, with `job_slots`-aware reservations (no double-claim), no-thrash job retention, and a `work.explain` decision trace. `set_work_priority` is the governor/LLM lever and the player's clickable Work grid; `assign_pawn` becomes the forced override. Self-care is a lane label only (eating/drinking stays instant); job-candidate indexes (Paper 7) and emergency/medical content are deferred. Both survival oracles (I1 3-day, LLM==fallback) stay green | 2026-06-29 build-2 step 1 |
| Build-2 water slice shipped as the first essential economy extension | `Good.WATER`, `NEED_WATER`, Water Well production, one-unit drinking, thirst thoughts, Civ Water readout, HUD stockpile chip, water work priority, days-of-cover summary, and `low_water` governor exception make the first Townsmen essential conserved and visible. District buffers, service queues, seasonal demand, markets, wages, and storage caps remain deferred | 2026-06-29 build-2 water slice |
| Paper 5 current-systems readability shipped before the governor card | The viewer now separates hover from selection, draws danger rings above selection, shows `work.LANE_IDLE` pawns with an overhead `!`, and renders construction sites as ghosts with footprint outlines and two-stage material/work progress. Storage 80/95% badges remain deferred until stockpile capacity exists, because uncapped totals cannot produce truthful pressure | 2026-06-29 Paper 5 current-systems slice |
| Paper 6 governor observer shell shipped | The viewer derives a read-only Governor card from current exceptions, scheduler status, and recent policy actions: plan, phase, bottleneck, confidence, last reallocation, and top exception. A right-edge exception stack sorts active governor exceptions by severity and actionability. It is diagnosis-first UI, not a micromanagement surface; decision-log drill-down and policy editors remain deferred | 2026-06-29 Paper 6 observer UI slice |
| Close the 12-pawn truth loop before Paper 7 scale work | A 2026-06-30 audit found dead governor levers (`set_production_target`, `set_research` applied but changed nothing), an autopilot that halted after a 7-item build order, and a one-way economy where only the upstream-shortage bottleneck can occur. Paper 8 itself says not to scale before the 12-pawn loop is satisfying, so scale (PR #21) was re-sequenced behind these fixes. PRs #23-#29 closed them | 2026-06-30 audit + user direction |
| No Potemkin governor actions: an applied action must change sim state or be rejected | A validated-and-"applied" action that mutates nothing makes the Governor card report changes that did not happen, which breaks the Paper 5/6 truth contract that the UI must let the player verify the sim is honest. `set_production_target` must cap production or be rejected; `set_research` must accrue/spend toward a real tech effect | 2026-06-30 audit |
| The autopilot needs a goal function; a minimal research/Space-Age spine is the first one | "Watch a town grow over time" fails when the fallback halts at a fixed build order. The stated primary victory (Space Age via research) did not exist in code, so a minimal Laboratory -> research-points -> linear tech spine with at least one real effect is the autopilot's first end-game and the minimum thing worth spectating | 2026-06-30 audit |
| Household spending starts as a treasury-run Market loop | Build-2 money circulation remains inspectable and conservative: daily wages fund one bread purchase per pawn from a staffed Market above reserve, whole-coin sales tax is collected from buyer wallets, and off-map export only gets the remaining surplus. Full private firms, comfort services, and district market queues stay deferred | 2026-06-30 Paper 4 truth-loop slice |
| Market service pressure starts as unmet bread demand | The first service-pressure signal stays narrow and truthful: a staffed Market counts pawn wallets that wanted bread but could not buy above the reserve, reports that count in telemetry, and raises `market_service_pressure` for the Governor card/exception stack. Full district hubs, queues, Tavern comfort spending, and reserve-aware trade remain deferred | 2026-06-30 Paper 4 service-pressure slice |
| Minimal research spine shipped before scale work | `set_research` is no longer a dead lever: it selects an active tech target, staffed Laboratory work produces research points through the existing `effective_work` seam, and `efficient_baking` raises Bakery output. This proves the progression lever before the larger Space-Age spine, deeper economy, and victory condition land | 2026-06-30 truth-loop cleanup |
| Finite storage capacity shipped before wages/markets | Storage saturation is now a real bottleneck: `Stockpile.capacity` blocks net-growing production before inputs are consumed, telemetry records storage used/capacity/fullness, and the HUD shows storage percent. Storehouse upgrades and pressure badges are now live; district storage, hauling pressure, repair, and trade stay deferred | 2026-06-30 Paper 4 storage slice |
| First wage/market money loop shipped | Pawns now have personal coin, assigned pawns receive deterministic daily wages from the treasury, and a staffed Market can export a small bread surplus above reserve into treasury coin. This starts the money loop without replacing the legacy abstract tax floor; richer household spending, service spending, reserve-aware trade, and Storehouse capacity upgrades followed or remain future Build-2 slices | 2026-06-30 wage/market slice |
| Storehouse capacity and pressure badges shipped | Built Storehouses add deterministic global storage capacity, while the HUD and Storehouse world badge shift from normal to amber at 80% and critical red at 95%. This keeps storage pressure truthful without faking district storage or hauling pressure before those systems exist | 2026-06-30 Storehouse slice |

## Health Criteria

The project is healthy when:

- `.\.venv\Scripts\python.exe -m unittest discover -s tests` passes headless;
- the frozen contract in `core.py` imports and instantiates;
- `.\.venv\Scripts\python.exe -m agent_town --smoke-test` exits successfully;
- `.\scripts\validate-workbench.ps1` passes;
- secrets and local data are not exposed in committed or built output.
