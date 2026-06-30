# Local Agent Town - Roadmap

**Current phase:** prototype  
**Owner:** Kayden and local coding agents

This is the active work plan. Keep it forward-looking and proof-oriented.

## Current State

The project is mid-refactor from the AI-Town social wander-sim into a
single-faction, LLM-governed civilization builder. The authoritative build plan is
`Local_little_world_refactor1.md`; `BLUEPRINT.md` carries the stable summary.

Phase 0 is complete: the frozen civilization contract lives in `core.py` (Good,
GridMap, ResourceNode, Stockpile, Recipe, Building, ConstructionSite, Pawn,
JobRef, ScheduleTemplate, FactionState, CivilizationException, GovernorAction), eight
civilization modules exist (world, economy, buildings, construction, pawns, mood,
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

- The legacy social-sim (`Agent`, `Simulation`, `Location`, `app.py`,
  `persistence.py`, `spatial.py`, and their compatibility tests) has been
  retired after I3 reached civilization-viewer parity. The package now exports the
  civilization runtime (`FactionState`, `create_default_civilization`) and the console
  entrypoint goes directly to `civilization_view.py`.
- The default `python -m agent_town` view is now the civilization viewer
  (`civilization_view.py`), which renders the civilization `FactionState`, steps the
  engine, supports camera pan/zoom, and has a RimWorld-style UI shell: top pawn
  roster, right pawn sheet with needs/skills/traits, and bottom command/status
  strip. The legacy social-sim entrypoints and tests are removed; final viewer
  cleanup now means polishing the civilization viewer itself, not keeping the old
  viewer alive.
- The LLM governor (I2) is integrated: `governor.LLMGovernor` implements the
  same `decide(context)` interface backed by `LocalLLMClient.complete_json` with
  a JSON-schema action list and a hard fallback to `FallbackGovernor` on any
  error. It is proven faithful (an always-failing LLM governor drives the civilization
  identically to the fallback over three days), has a live Gemma 4 E4B run log
  through `scripts/llm_governor_run.py --hours 6`, and is wired into the
  real-time viewer through the non-blocking `CivilizationDecisionScheduler`.
- The I1/I2/I3 bridge goal is complete. Final viewer cleanup has landed as the
  RimWorld-style overlay shell, in-map panels, Civ stats readout, pawn selection
  and inspection, local-model status/toggle, and deterministic pawn commute
  movement. The bottom command strip's **Work** button is now live (it opens the
  work-priority grid, build-2 step 1); the remaining buttons (Architect, Assign,
  Research, History, Menu) stay visual placeholders until their actions exist.
  The first Build-2 essential economy slice is also live: Water Well production,
  stockpiled water, pawn drinking, thirst mood pressure, Civ Water readout, HUD
  Water chip, and a `low_water` governor exception.

## Current Goal

The Build-1 mood/hunger reconciliation is complete (Papers 1 and 2 are
implemented: 0-100 mood ledger, seeded break bands, conserved nutrition reserve,
0.25-nutrition bread, neutral `mood_factor`). Build-2 step 1 is complete: the
**lane-based work-priority arbiter with reservations and `set_work_priority`
(Paper 3)** ships in `work.py` with a clickable Work grid and an inspector
decision trace. Build-2 water is now also complete as the first essential
economy slice (Paper 4): Water Well -> stockpiled water -> water need/thirst
pressure -> Civ Water readout/HUD chip -> `low_water` governor exception.
Paper 5 current-systems readability is now also live: hover and selection are
separate, danger rings outrank selection, `work.LANE_IDLE` pawns get an overhead
idle badge, and active construction sites draw as ghosts with footprint outlines
and progress bars. Storage-pressure badges stay deferred until stockpile capacity
exists. The synthesis paper (`research_papers/8.little-local-world-research-synthesis.md`)
Paper 6 governor observer UI is now also live: a compact Governor card shows
current plan, phase, bottleneck, confidence, last policy change, and top
exception; the right-edge exception stack sorts active governor exceptions by
severity/actionability with likely causes. Paper 7 scale foundations are also
live: walkable-region ids reject unreachable jobs before ranking, and the engine
reports its deterministic command/update phase order. The synthesis paper now
points next to deeper Paper 4 economy before comfort chains. Per user direction
(2026-06-29) lethal starvation (build-1 step 5.4) stays deferred behind the
visible autonomy/readability work; Build-1 ships with hunger mood pressure as
its stakes.

Done when:

- each research paper is reduced to a small implementation slice with affected
  files, tests, risks, and explicit deferrals;
- the chosen slice is implemented through the deterministic core first, with
  viewer/status updates only where they make the new state visible;
- tests cover the new conservation path and any changed governor/viewer surface;
- `BLUEPRINT.md`, `RUNBOOK.md`, and this roadmap are updated if the slice changes
  the product contract or operator workflow;
- the full verification path still passes.

## Build arc (the long road)

The immediate goal above finishes build 1. The product then grows in builds,
each gated on the prior. Conservation ("nothing from nothing", `BLUEPRINT.md`)
governs every system. The full content design lives in `BLUEPRINT.md`'s "Target
content design"; this is the sequencing.

- **Build 1 - one civilization works (current).** About 12 pawns, 3 chains (wood,
  food, stone), construction, needs/mood/breaks, happiness-to-tax, deterministic
  fallback Governor then the LLM Governor, viewer renders civilization state.
- **Build 2 - depth and the spectator.** Water and clothes/beauty chains; the
  full needs set (water, shelter, clothes, beauty); building quality to
  happiness; decay + repair as a material/coin sink; the wage money loop
  (wages -> spend -> tax) with the Market and Tavern; storage caps and a
  "storage full %" readout; RimWorld work priorities (`set_work_priority`) and
  the per-civilization spectator view; skill-based healthcare (Infirmary + optional
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
  civilization to launch wins, and outlasting the rival is the implied secondary win.
  Scale target up to about 1000 pawns per civilization.

## Next Tasks

The bridge order I1 -> I3 -> I2 is complete. Start the next implementation work
from the research-backed queue below, keeping every slice small and verified.

1. **(done) Extract the I1 headless stepper** - `engine.py` is the reusable
   civilization engine; the three-day survival test runs through it. See the current
   state above.
2. **(done) Viewer I3** - `civilization_view.py` renders the civilization
   `FactionState` (tiles, buildings with staffing, pawns by mood, HUD) with the
   authored `assets/colony` sprites and steps `engine.step_hour`; it is now the
   default `python -m agent_town` view and its smoke test is green. Camera
   pan/zoom, pawn selection, the inspection panel, and the LLM toggle are now in
   place. The final cleanup pass also added in-map overlays, Civ stats, and
   deterministic pawn commute movement; command buttons remain visual placeholders
   until build-2 command actions exist.
3. **(done) LLM governor I2** - `governor.LLMGovernor` is behind the fallback
   `decide` interface with JSON-schema output and a hard fallback;
   `test_llm_governor.py` is green, `scripts/llm_governor_run.py --hours 6`
   completed against live `google/gemma-4-e4b`, and the real-time viewer uses
   `CivilizationDecisionScheduler` so local model calls never block the sim loop.
4. **Manual LM Studio/Ollama tuning pass** - run Gemma 4 E4B-it, Qwen3.5-4B,
   and Phi-4-mini-instruct locally and record which model gives the best
   speed/personality balance.
5. **Civilization rename, the RimWorld mood foundation, and the Civ stats bar
   (build 1 stakes, in order).** The mood system is the priority; starvation
   death is kept but deferred behind it. Adopt RimWorld's model foundation-first
   (design in `BLUEPRINT.md` "Mood: the RimWorld model" and "Starvation and pawn
   loss"). Do these in order:

   1. **(done) Rename colony -> Civilization (Civ), everywhere** as one isolated,
      behaviour-preserving change (tests stay green before any behaviour
      changes). ~327 refs across 32 files: rename `colony.py` ->
      `civilization.py`, `colony_view.py` -> `civilization_view.py`, and the
      `test_colony_*.py` files; rename `ColonyException` ->
      `CivilizationException` (frozen-contract change via the one-file-PR
      process - it keeps the "does not shadow builtin `Exception`" property),
      `ColonyDecisionScheduler` -> `CivilizationDecisionScheduler`,
      `create_default_colony` -> `create_default_civilization`; update the LLM
      prompt wording ("Governor of a small civilization") and the active docs
      (BLUEPRINT, ROADMAP, README, RUNBOOK, VISUAL_DESIGN, AGENTS). Leave the
      historical `Local_little_world_refactor1.md` as a frozen artifact; the
      `assets/colony/` directory rename is optional (asset-path risk) and may
      trail.
   2. **(done) Nutrition + RimWorld mood foundation on a 0-100 scale.** Food is a
      nutrition reserve (eat bread, overeating waste, no free restoration); mood
      is 0-100 with a Thought ledger, +12/-8 drift (frozen asleep), hunger
      thoughts, and seeded mean-time-between break bands (35/20/5) + Catharsis.
      Per the build-1 stakes decision the food sink is left as a deliberate hunger
      pressure: the default viewer civ can run dry while the I1 survival civ
      sustains; starvation death stays deferred to step 4. Locked design in
      `BLUEPRINT.md` "Mood: the RimWorld model"
      and the "Pawn needs" / Design Decisions rows (nutrition reserve,
      opportunistic eating, 0-100 mood). File-by-file:
      - **`core.py` (frozen-contract change, one-file-PR).** Add a `Thought`
        dataclass (kind, label, value, age, stack, duration); `Pawn.thoughts` (a
        list of `Thought`); `Pawn.mood_target` (float); a `FactionState.seed`
        (int) for the break PRNG. `Pawn.mood` default moves from 0.5 to the 0-100
        base.
      - **`mood.py`.** Replace `compute_mood` with `mood_target` (= base + sum of
        thought values) plus the thought builders: a hunger thought from food
        saturation (Fed >=25% 0; Hungry 25-12.5% -6; Ravenous 12.5-0% -12;
        Malnourished 0% -20), trait/want contributions as thoughts, and a blended
        rest+rec thought. Add `drift_mood(actual, target, asleep)` (+12 / -8 per
        hour, frozen asleep). Update `mood_factor` for the 0-100 scale (neutral 50
        -> 1.0) so `effective_work` is behaviour-unchanged.
      - **`pawns.py`.** Food becomes a nutrition reserve: drain it as saturation;
        add `eat(pawn, stockpile)` (consume 1 bread = 0.9 nutrition, cap at 1.0,
        excess wasted) and **remove the free `SCHEDULE_ANY` food restoration** (the
        conservation fix). Replace slack@0.25 / wander@0.12 with break bands
        minor<35 / major<20 / extreme<5 fired on a seeded-PRNG mean-time-between
        roll (faster in lower bands) keyed to `FactionState.seed`; add per-trait
        break-threshold offsets and a Catharsis thought after a break ends.
      - **`engine.py`.** In `_advance_pawns`, replace the off-shift
        eat-at-<0.65->1.0 block with opportunistic eating (saturation <= ~30% and
        bread on hand, any waking hour); compute `mood_target`, drift `pawn.mood`
        toward it, then advance the break state under the seed.
      - **`economy.py`.** Un-clamp `average_mood` (now 0-100) and recalibrate
        `daily_tax_income` so day-1 coin output stays in the current range (it
        currently multiplies avg_mood expressed in [0,1]).
      - **`governor.py`.** Point the unhappy / about-to-break exceptions at the new
        break bands; mood in the faction/roster summaries is now 0-100.
      - **`civilization_view.py`.** Render mood on 0-100 (bars/colours) and show
        the pawn's thought list in the inspector (RimWorld-style). The Civ stats
        bar is step 3.
      - **Tests.** Update every mood-in-[0,1] assertion to 0-100 (the I1 survival
        regression, `average_mood`); add thought add/stack/expire; drift
        (+12/-8, frozen asleep); hunger bands off saturation; nutrition eat +
        overeating waste + no-free-restoration; break bands fire at the right mood
        under a fixed seed (determinism preserved); catharsis; tax stable after
        recalibration.
      - Deferred to build 2 (same architecture): expectations (wealth treadmill;
        stub "extremely low"), richer thoughts (meal quality, ate-without-table,
        recreation variety, social, death), and inspirations (nothing to boost
        yet).
   3. **(done) Civ stats bar.** `economy.average_need(state, need)` gives the
      Civ-wide mean of a need (alongside `average_mood`), and the viewer renders a
      top-left translucent Civ stats panel (originally Mood + Food/Recreation/Rest;
      item 7 extends it with Water) reusing the need-bar colours. Build 1 only
      adds a mood consequence for food; item 7 adds water/thirst pressure. Tests:
      `average_need` on a known roster + a panel render smoke check.
   4. **(deferred) Starvation death.** After steps 1-3, land the
      72h-since-last-meal death from the prior plan: `Pawn.hours_since_meal`
      (contract change), the conservation fix (food only from bread; remove the
      free off-shift `NEED_FOOD` restoration), engine removal + `staffed_by`
      scrub + loss reporting on `StepResult`, a `starving_pawn` exception, a
      food-first fallback, the LLM prompt update, a viewer starvation badge +
      death event-log line, tests, and a `RUNBOOK.md` manual check (run a
      bakery-less Civ and watch a pawn die).

6. **(done) Build-2 step 1: work-priority arbiter + reservations.** Shipped as
   `work.py`: a lane-based arbiter (forced -> hard-state -> self-care -> normal
   work -> idle; medical/emergency are ordered stubs with no build-1 content) now
   does routine staffing instead of the governor. Pawns self-select their best
   legal job by manual priority -> work-type natural order -> target urgency
   (hook) -> distance -> skill fit; skill never rescues an illegal/reserved/
   disabled/lower-priority job. Target reservations are `job_slots`-aware so two
   pawns never claim the same slot, legal jobs are kept (no thrash), and a break
   or a disabled work type releases the slot. `set_work_priority(group, work_type,
   level)` is a governor action (and the LLM's main labour lever); `assign_pawn`
   is now the forced-override lane. The viewer adds a clickable RimWorld-style
   Work grid (Work button), an inspector "Why this job" trace (winning lane,
   reason, top rejected job) via `work.explain`, and an `Idle N` HUD chip.
   **Lethal starvation (step 5 substep 4 above) stays deferred behind this.**
   Water followed this as item 7 below.

7. **(done) Build-2 first essential economy: water.** Shipped a
   conservation-safe water path: `Good.WATER`, `NEED_WATER`, Water Well
   production, one-unit drinking, thirst thoughts, Civ Water readout, HUD Water
   chip, `water` work priority, `economy.water_days_of_cover`, and a `low_water`
   governor exception. The default 12-pawn civilization starts with one Water
   Well, a water-skilled pawn, and enough water stock to keep the viewer proof
   viable. Paper 5 current-systems map readability followed this as item 8 below.

8. **(done) Paper 5 current-systems map readability.** Shipped viewer-level
   readability for systems that actually exist: hover and selection use separate
   outlines, selected/stressed pawns keep danger rings above selection, idle pawns
   from the work arbiter get an overhead `!` badge, and construction sites render
   as translucent ghosts with footprint outlines and material/work progress bars.
   Storage 80/95% badges are deliberately deferred until stockpile capacity exists.
   Paper 6 governor observer UI followed this as item 9.

9. **(done) Paper 6 governor card + exception stack.** The viewer now derives a
   read-only Governor card from current exceptions, scheduler status, and recent
   policy actions: current plan, phase, bottleneck, confidence, last reallocation,
   and top exception. A right-edge exception stack shows active governor
   exceptions by severity/actionability with likely causes. It stays observer
   UI, not a policy editor. Paper 7 scale foundations followed this as item 10.

10. **(done) Paper 7 scale foundations.** `world.reachability_regions` labels
    current walkable tiles with deterministic region ids, water is the first
    impassable terrain, and `work.py` rejects cross-region jobs as
    `unreachable` before priority ranking. `engine.ENGINE_PHASES` and
    `StepResult.phases_executed` expose the stable command/update order. Dirty
    topology recomputation, job indexes, cadence buckets, and path abstraction
    stay deferred until maps or populations grow. **Next code task is deeper
    Paper 4 economy: district storage/market pressure before comfort chains.**

## Research Paper Implementation Queue

Eight GPT Pro research papers live in `research_papers/`: seven source-game
studies (Papers 1-7) plus a project synthesis (Paper 8,
`8.little-local-world-research-synthesis.md`). Treat them as source leads and
project design inputs; exact constants that affect code should either be verified
from the cited source or marked research-derived in tests and docs.

**Paper 8 is the sequencing authority.** It collapses the seven source papers
into one product rule - *make autonomous causality visible* - and one strict
build order. Work the queue in this order, not in paper-number order:

1. **Food correction (done).** Papers 1-2. Conserved nutrition reserve,
   0.25-nutrition bread, neutral `mood_factor`. Reconciled and merged.
2. **Work priorities + reservations (done).** Paper 3. Lane-based arbiter in
   `work.py`, `job_slots`-aware reservations, `set_work_priority`, clickable Work
   grid, and an inspector decision trace. This is where the town starts feeling
   autonomous; see Next Tasks item 6 and the Paper 3 slice below.
3. **First essential economy: water (done).** Paper 4. Water Well -> water need -> Civ
   readout -> governor exception shipped before storage / markets / wages.
4. **Map readability for current systems (done for existing systems).** Paper 5.
   Idle badge, construction progress, danger-over-selection, and hover vs
   selection are live. Storage 80/95% badges are deferred until storage capacity
   exists.
5. **Governor card + exception stack (done).** Paper 6. Current plan, bottleneck,
   confidence, last reallocation, top exception and its likely cause are visible.
6. **Scale foundations (done).** Paper 7. Reachability region ids and
   deterministic command/update phases are live as cheap scaffolding before
   population grows.
7. **Deeper economy.** Paper 4 (remainder). District storage, market/service
   delivery, repair debt, wages -> spending -> taxes, reserve-aware trade.

Explicit deferrals from Paper 8 (do not start until the autonomy loop is visible
and stable): full RimWorld think-tree parity, full joy/recreation variety,
lethal starvation and detailed malnutrition timing, spoilage-heavy food variety,
the full wages/taxes/trade economy before storage and service bottlenecks exist,
large-population approximations before 12-pawn exactness is proven, and
text-heavy dashboards before world badges and inspector causality are readable.

The per-paper slices below carry the file-by-file detail. They are reference
material; the numbered order above is what to build.

1. **RimWorld mood reconciliation** -
   `research_papers/1.rimworld_mood-system-report.md`
   - Current status: the 0-100 mood ledger, target/current mood split, seeded
     break bands, Catharsis, and the productivity reconciliation are implemented.
     The legacy `mood_factor` hook is neutral; `effective_work` now changes
     through hunger and break state rather than high mood alone.
   - Next code task: none for Build 1; carry expectations and inspirations into
     the later richer-thought/inspiration slice.
   - Tests: high mood alone does not create a hidden productivity boost, hunger
     directly reduces work, and break state stops work.
   - Deferred: wealth-based expectations, richer event thoughts, inspiration
     events.
2. **RimWorld hunger and nutrition retune** -
   `research_papers/2.rimworld_hunger-system-report.md`
   - Current status: food is conserved, pawns seek food below 30%, bread is a
     0.25 nutrition portion, eating consumes a rounded portion count up to four
     bread, and Bakery output/default setup were rebalanced so the 12-pawn civ
     remains winnable.
   - Next code task: keep lethal starvation deferred until the malnutrition/death
     timing slice; then add starvation status, exceptions, viewer surfacing, and
     fallback food-chain urgency.
   - Tests: 0.301 vs 0.299 eat threshold, portion waste near threshold,
     short-stock eating, bread-only deterministic choice, default-civ survival,
     and no free schedule restoration.
   - Deferred: feed-by-other patient/prisoner logic, food policy variety,
     disease/traits/genes that change hunger.
3. **RimWorld autonomous pawn priorities** -
   `research_papers/3.rimworld_autonomous-pawn-report.md`
   - Current status: **done.** `work.py` is the lane-based arbiter (forced ->
     hard-state -> self-care -> normal work -> idle; medical/emergency ordered but
     empty in build 1). It does routine staffing instead of the governor, sorts
     normal work by manual priority -> work-type order -> target urgency (hook) ->
     distance -> skill, makes `job_slots`-aware reservations, keeps legal jobs,
     and releases on break/disable. `set_work_priority` is wired through the
     governor + LLM; `assign_pawn` is the forced override. The viewer has the
     clickable Work grid and an inspector decision trace (`work.explain`).
   - Next code task: none for this paper. Skill is still a *legality-passing*
     tiebreak only, matching the paper; later builds add emergency/medical content
     and richer work types as those systems land.
   - Tests (in `test_work.py`): manual priority beats work-type order; self-care
     lane flips at the hunger threshold; disabled/reserved/no-recipe jobs are
     rejected and not rescued by skill; broken pawn releases its slot; the
     decision trace explains the winning job and top rejection; determinism.
   - Deferred: full think-tree parity, full joy system, combat/drafted AI,
     apparel/inventory housekeeping, deep medical simulation, the self-care
     *time cost* (eating costing a work hour) until building-based services exist,
     and job-candidate indexes (Paper 7) before large populations.
4. **Townsmen economy depth** -
   `research_papers/4.townsmen_economy-loop-report.md`
   - Current status: the first essential economy slice is implemented: Water
     Well production, water reserve/need, thirst mood pressure, Civ readout/HUD
     chip, water days-of-cover, and a `low_water` governor exception.
   - Next code task: add district storage/market pressure before comfort chains.
   - Tests: water days-of-cover is covered; summer/seasonal demand hook,
     storage-full blocked production, repair input reservation, and wage ->
     spending -> tax accounting remain future tests once those loops start.
   - Deferred: full household economy, private firms, premium/mobile timers,
     large multi-district optimization.
5. **Age of Empires readability pass** -
   `research_papers/5.aoe_civ-readability-report.md`
   - Current status: **done for existing systems.** The viewer has a readable
      Pygame map, roster, inspector, overlays, Civ stats, separate hover and
      selection outlines, danger-over-selection rings, idle overhead badges from
      `work.LANE_IDLE`, and construction ghosts with footprint/progress.
   - Next code task: none for Paper 5 until storage capacity or larger-map/LOD
      work lands; Paper 6 observer UI is now complete.
   - Tests/manual proof: `tests.test_civilization_view` covers construction
      progress math, marker priority, and hovered-pawn render smoke; refreshed
      `docs/screenshots/current-state.png`; inspected a temporary proof frame
      with an idle pawn plus construction site.
   - Deferred: storage pressure badges until stockpile capacity exists, full
      64x32 isometric rebase, atlas pipeline, multi-LOD sprite sets,
      reduce-motion settings.
6. **Observer-first UI pass** -
   `research_papers/6.ui-report.md`
   - Current status: **done for the current observer shell.** The viewer has a
     compact Governor card (plan, phase, bottleneck, confidence, last policy
     change, top exception) plus a right-edge exception stack sorted by severity
     and actionability. State, cause, and actionability stay separated.
   - Next code task: none for Paper 6 until a full decision-log drill-down or
     policy editor is explicitly pulled forward.
   - Tests/manual proof: `tests.test_civilization_view.GovernorObserverModelTests`
     covers exception severity ordering, low-water bottleneck surfacing, recent
     policy action text, and render smoke with an exception.
   - Deferred: full decision-log scrubber, policy editor, multi-civilization
     observer dashboards.
7. **Scale architecture intake** -
   `research_papers/7.scalable-sim-report.md`
   - Current status: the first cheap scale foundations are implemented while
     gameplay remains exact and small-population. `world.reachability_regions`
     labels current walkable regions, `work.py` rejects cross-region jobs before
     priority ranking, and `engine.ENGINE_PHASES` reports the deterministic
     command/update order.
   - Next code task: none for Paper 7 until dynamic topology or larger
     populations are pulled forward. Deeper economy resumes next.
   - Tests: unreachable jobs are rejected before pathfinding; region IDs are
     deterministic for the current map; identical setups still produce identical
     state; benchmark still reports core/context/draw timings.
   - Scale gates: at 16-64 pawns add job candidate indexes and cadence buckets;
     at 64-150 add chunk/HPA-style long routes or shared routes to common sinks;
     at 150-400 add district work packets and path budgets; at 400-1000 add
     offscreen ETA movement, far-needs cadence, simplified local avoidance, and
     strong visual/overlay LOD.
   - Exactness rule: selected, visible, conflict-involved, scarce-resource, and
     ownership-transfer pawns stay exact. Approximate opportunity search and
     offscreen travel, not player-readable truth.

## Blocked Or Deferred

Do not start these until their prerequisite is met.

| Item | Blocked on | Why it matters |
|---|---|---|
| Hosted AI providers | explicit user approval | Avoids accidental paid or network-dependent behavior |
| Human multiplayer or remote viewing | explicit product direction change | Local-only, not web based; AI-vs-AI multi-civilization is build 4, not this |
| Large map editor | stable core loop | Editing tools are less useful before agent behavior is interesting |
| Engine migration | benchmark evidence that Pygame rendering or editor tooling is the blocker | Current measured risk is simulation scale, persistence, and future pathfinding before rendering |

## Backlog

Tagged by the earliest build that needs them; see `BLUEPRINT.md` for the design.

Build 2 (depth and the spectator):

- Water chain foundation (Water Well -> water need) is done; clothes/beauty
  chain remains future work (animals -> wool/hide -> Tailor -> cloth/clothes;
  furniture -> beauty).
- Full needs: water, shelter, clothes, beauty, wired to schedule restoration.
- Building quality -> happiness, plus decay + repair consuming planks/stone +
  labour (the missing material/coin sink).
- Wage money loop: pay pawns (treasury -> purse), pawns spend at Market/Tavern,
  tax the wages back; Market trades surplus with off-map caravans.
- Storage caps + "storage full %" readout; Storehouse raises capacity.
- `set_work_priority` action + RimWorld per-pawn work-priority model.
- Per-civilization spectator view: open a civilization and see assignments, priorities,
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
- Scale to ~1000 pawns per civilization through the Paper 7 path: reachability
  regions, deterministic phases, job indexes, chunk/long-route abstraction,
  shared routes/flow fields for common sinks, district work packets, cadence
  tiers, offscreen ETA movement, and visual/overlay LOD.

Carried from the social-sim era (revisit when relevant):

- Event feed and time controls; screenshots/GIF capture for quick review.
- Pathfinding benchmark before obstacles or large maps; Paper 7 says the first
  scalable pathfinding feature should be reachability-region rejection before
  exact A*/JPS pathing.

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
| 2026-06-28 | I3 viewer parity: camera pan/zoom and pawn inspection panel | `.\.venv\Scripts\python.exe -m unittest tests.test_colony_governor tests.test_colony_view` (21 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (152 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; rendered frame inspected at `%TEMP%\local-agent-town-i3-panel.png` | pass | Added a camera transform with clamped pan/zoom, keyboard/mouse viewer controls, click/Tab pawn selection, selected-pawn highlight, and a right inspection panel showing pawn state, assignment, mood, needs, and top skill. Remaining: live local-model run log plus final cleanup before retiring the legacy social-sim |
| 2026-06-28 | Live Gemma proof for the LLM governor bridge | `.\.venv\Scripts\python.exe scripts\llm_governor_run.py --hours 6`; `.\scripts\validate-workbench.ps1` | pass | LM Studio at `http://localhost:1234/v1` auto-selected `google/gemma-4-e4b`; the model emitted assignment actions for 6 simulated hours and the colony ended day 0 with coin 20, mood 91%, wandering 0, bread 15, planks 2, stone 5. Remaining: final viewer cleanup before retiring the legacy social-sim |
| 2026-06-28 | Retire legacy social-sim after I3 viewer parity | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (104 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\.venv\Scripts\agent-town.exe --smoke-test`; `.\scripts\validate-workbench.ps1`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --pawns 100 500 1000 --steps 20 --context-repeats 5 --draw-frames 2`; `git diff --check` | pass | Removed the old `Agent`/`Simulation`/`Location` runtime, `app.py`, social persistence, spatial-index compatibility code, old tests, and old app entrypoint. Package exports now point at the colony runtime; benchmark and docs now describe the colony engine/viewer. Remaining: untracked local asset zips stay excluded from Git until license/sourcing is decided |
| 2026-06-28 | RimWorld-style pawn UI pass | `.\.venv\Scripts\python.exe -m unittest tests.test_colony_view` (17 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (108 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; rendered frame inspected at `%TEMP%\local-agent-town-rimworld-ui.png` | pass | Added a top pawn roster, wider pawn sheet with status/needs/skills/traits, and bottom command/status strip. Remaining: the bottom command buttons are visual shell controls until build/assign/work-priority actions are implemented |
| 2026-06-28 | Document current UI screenshot and placeholder controls | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (108 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1` | pass | Added `docs/screenshots/current-state.png` to the README as the current-state screenshot, documented that bottom command buttons do not act yet, and updated `AGENTS.md` so future visual changes refresh the screenshot |
| 2026-06-28 | Add build-1 starvation/pawn-death design to BLUEPRINT and ROADMAP next task | `.\scripts\validate-workbench.ps1` | pass | Docs only. Recorded the decision (pawn dies after 72h since last meal), the conservation fix (food only from bread, removing the free off-shift restoration), a `BLUEPRINT.md` "Starvation and pawn loss" subsection, a Design Decisions row, and a ROADMAP Next Task #5 listing the full file-by-file touch list. No code changed yet; `Pawn.hours_since_meal` contract change and the cross-module implementation are the next code task |
| 2026-06-28 | Re-scope build-1 stakes: Civilization rename + hunger mood debuff + Civ stats bar ahead of starvation death | `.\scripts\validate-workbench.ps1` | pass | Docs only. Per user: mood debuff is the priority (hunger as an explicit -5/-10/-15 modifier on the mood ledger, with food pulled out of the blended needs term so it is one clean modifier); full colony->Civilization rename chosen (~327 refs / 32 files) as an isolated first commit; a Civ stats bar shows Civ-wide avg Mood/Food/Rec/Rest. Starvation death kept but deferred behind these. Added `BLUEPRINT.md` "Hunger, mood, and the Civ stats readout" subsection + 2 Design Decisions rows and restructured ROADMAP Next Task #5 into four ordered steps. No code yet |
| 2026-06-28 | Adopt the RimWorld mood model (foundation-first, seeded-RNG breaks) into the design | `.\scripts\validate-workbench.ps1` | pass | Docs only. Per user: adopt RimWorld's mood system as close as the engine allows. Replaced the `BLUEPRINT.md` mood subsection with "Mood: the RimWorld model (build 1 foundation)" - two-layer target/actual mood (drift +0.12/-0.08 per hour, frozen asleep), a `Thought` ledger, base-from-difficulty, hunger as the first thought, three break bands (35/20/5%) fired on a seeded PRNG keyed to a colony seed, per-trait break thresholds, and Catharsis; expectations/richer-thoughts/inspirations deferred to build 2; rooms/prisoners out of scope. Updated the determinism constraint to allow a seeded PRNG, added a Design Decisions row, and rewrote ROADMAP Next Task #5 step 2 into the mood foundation (contract adds: `Pawn.thoughts`, `Pawn.mood_target`, a `FactionState` seed). No code yet |
| 2026-06-28 | Move colony UI into resizable in-map overlays | `.\.venv\Scripts\python.exe -m unittest tests.test_colony_view` (20 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (111 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; refreshed and inspected `docs\screenshots\current-state.png` | pass | The map now fills a larger resizable window with stats, roster/pawn sheet, and command strip rendered inside the map viewport; local model status remains in a slim footer outside the map. Command buttons are still visual placeholders |
| 2026-06-28 | Build-1 stakes step 1: rename colony -> Civilization across code and active docs (behaviour-preserving) | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (108 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; renamed-symbol import check | pass | Renamed every `colony`/`Colony`/`COLONY` code symbol and active-doc term to civilization; `git mv` of `colony.py`/`colony_view.py`/`test_colony_*.py` to `civilization*`; `ColonyException` -> `CivilizationException` (frozen-contract change, still avoids shadowing builtin `Exception`); updated `pyproject.toml` entry point. Intentionally kept as `colony`: the on-disk `assets/colony/` directory and its path string (asset-path rename trails per the roadmap), the frozen `Local_little_world_refactor1.md`, local-only `HANDOFF.md`, and the append-only Verification Log history. Not committed pending review. Next: Next Task #5 step 2 (RimWorld mood foundation + hunger thought) |
| 2026-06-28 | Build-1 stakes step 2: nutrition reserve + RimWorld 0-100 mood/break foundation (continues the RED WIP checkpoint to green) | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (124 tests, was 108); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; 3-day bread/mood trajectory inspected | pass | Drove the RED foundation (core.py Thought/mood_target/seed + mood.py 0-100, from the prior WIP) to green. `pawns.py`: food is a nutrition reserve with `eat()` (bread 0.9, overeating waste) and the free `SCHEDULE_ANY` food restoration removed (conservation fix); break bands 35/20/5 fire on a seeded mean-time-between roll + per-trait offsets; `Catharsis` + thought stack/age/expire. `engine.py`: opportunistic eat at <=30% any waking hour, then mood_target -> drift -> age thoughts -> seeded break roll (`random.Random(f"{seed}:{id}:{day}:{hour}")`, process-stable). `economy.py`: `average_mood` un-clamped to 0-100, tax recalibrated (/100) so day-1 coin is unchanged. `governor.py`/`civilization_view.py`: bands + 0-100 mood, plus a thought ledger in the inspector. Added `test_step2_hunger_mood.py` and migrated every [0,1] mood assertion to 0-100. Per user the food sink is left as a deliberate hunger pressure (default viewer civ can run dry; I1 survival civ sustains). Next: step 3 Civ stats bar |
| 2026-06-28 | Build-1 stakes step 3: Civ stats bar (Civ-wide need averages + viewer panel) | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (129 tests, was 124); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; rendered frame inspected (`%TEMP%\...\civ_stats_frame.png`) | pass | Added `economy.average_need(state, need)` (mean need satisfaction, [0,1], missing-need reads as 1.0, unknown need raises) alongside `average_mood`. `civilization_view.py` draws a top-left translucent Civ stats panel: Mood (own colour) + Food/Recreation/Rest readouts reusing the need-bar colours; the red Food bar surfaces the deliberate hunger pressure (rendered 5-day default civ showed Mood 70% / Food 9% / Rec 80% / Rest 96%). Added `test_civ_stats.py` (average_need on a known roster, empty/missing/unknown cases, panel render smoke). Build 1 only adds a mood consequence for food; the other three are readouts. Next: step 4 (deferred) starvation death |
| 2026-06-28 | Pawn activity state + sim-level movement (pawns commute to their jobs) | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (138 tests, was 129); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; rendered frame + refreshed `docs\screenshots\current-state.png` | pass | Closes the two I3/viewer-liveness gaps behind the "pawns clustered at spawn, always idle" look. Added `Pawn.home_x/home_y` (additive frozen-contract change), `pawns.activity_state` (working/sleeping/recreating/idle for non-broken pawns), and deterministic sim-level movement in `engine._advance_pawns`: each hour a non-broken pawn takes its activity state and steps `PAWN_MOVE_TILES_PER_HOUR` (2) tiles toward its destination - its assigned building front while awake, home at night; broken/unassigned pawns head home. No collision/pathfinding yet (a build-2/4 item); production stays position-agnostic. Pawns now distribute to their workplaces and the inspector shows the real state. Added `test_movement.py` (9 tests). Next: step 4 (deferred) starvation death |
| 2026-06-28 | Close completed build-1 bridge goal in ROADMAP/README | `.\.venv\Scripts\python.exe -m unittest tests.test_package_runtime tests.test_engine tests.test_llm_governor tests.test_civilization_view` (33 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (138 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Docs only. Removed stale "final viewer cleanup pending" language from the active roadmap goal and README next-up list. The I1/I2/I3 bridge is now recorded as closed; next code work starts from build-2 depth unless the deferred starvation-death stake is explicitly pulled forward. |
| 2026-06-29 | Integrate research papers into workbench docs and implementation queue | `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Docs only. Wired `research_papers/1..6` into AGENTS, BLUEPRINT, ROADMAP, RUNBOOK, and README as source-input guidance; recorded the mood/hunger conflicts to reconcile (generic mood-to-work multiplier and bread 0.25 vs current larger bread unit); added paper-by-paper implementation slices for mood, hunger, work priorities, Townsmen economy depth, AoE readability, observer UI, and pending scale-paper intake. |
| 2026-06-29 | Integrate Paper 7 scale research into the workbench queue | `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Docs only. Replaced the pending scale-paper slot with concrete scale architecture guidance: exact player-visible truth at 12 pawns, reachability regions and deterministic phases before larger populations, job indexes/cadence buckets by 16-64 pawns, path abstraction/shared routes by 64-150, district work packets/path budgets by 150-400, and offscreen ETA/far-needs/visual LOD by 400-1000. Added scale guidance to AGENTS, BLUEPRINT, ROADMAP, RUNBOOK, and README. |
| 2026-06-29 | Research retune: bread portions and hunger/break productivity | `.\.venv\Scripts\python.exe -m unittest tests.test_step2_hunger_mood tests.test_track_b_b2 tests.test_track_a_current_contract tests.test_integration_i1 tests.test_civilization tests.test_engine` (41 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (143 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Bread is now a 0.25 nutrition portion; pawns eat a rounded portion count up to four bread below the strict 30% threshold; Bakery output is four bread portions per cycle; the default civ starts a fourth Farm and equivalent bread reserve so the 12-pawn viewer civ remains winnable for the 3-day fallback proof. `mood_factor` is neutral; `effective_work` now changes through hunger and break state rather than high mood alone. Starvation death remains deferred until the malnutrition/death timing slice. |
| 2026-06-29 | Synthesize seven research papers into one Little Local World project paper | `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Docs only. Added `research_papers/8.little-local-world-research-synthesis.md`, combining mood, hunger, autonomy, Townsmen economy loops, AoE readability, observer UI, and scale architecture into one project-specific design paper. Strategic result: food was the right first conservation slice, but after the bread correction the next highest-leverage step is `set_work_priority` plus reservations, not deeper starvation or economy complexity. |
| 2026-06-29 | Fold Paper 8 synthesis order into ROADMAP/BLUEPRINT and set the next code task | `.\scripts\validate-workbench.ps1`; `git diff --check` | pass | Docs only. Per user direction, made the research-backed build order explicit (food done -> work priorities + reservations -> water -> readability -> governor card -> scale foundations -> deeper economy) and named the lane-based work-priority arbiter + reservations + `set_work_priority` (Paper 3) as the headline next code task, with lethal starvation deferred behind it. Updated ROADMAP Current Goal, added Next Tasks item 6, rewrote the Research Paper Implementation Queue intro around Paper 8 as sequencing authority, and added Paper 8 + a Design Decisions row to BLUEPRINT. Verified against code: `set_work_priority`/reservations/`region_id` do not exist yet; bread retune (0.25, rounded portions) is present. |
| 2026-06-29 | Build-2 step 1: lane-based work-priority arbiter + reservations + `set_work_priority` + clickable Work grid (Paper 3) | `.\.venv\Scripts\python.exe -m unittest discover -s tests` (174 tests, was 143); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --pawns 100 500 1000 --steps 20`; rendered `work_grid_open.png`/`inspector_trace.png` and refreshed `docs\screenshots\current-state.png` + `work-grid.png` | pass | New `work.py` lane-based arbiter (forced/hard-state/self-care/normal-work/idle; medical+emergency are ordered stubs) replaces the governor's routine `assign_pawn`: pawns self-select their best legal job by manual priority -> work-type order -> target urgency (hook) -> distance -> skill, reserve the slot (`job_slots`-aware, no double-claim), keep legal jobs (no thrash), release on break/disable, and get a decision trace (`WorkDecision`/`RejectedJob`). `set_work_priority` action wired through governor validate/apply + LLM schema/prompt; `assign_pawn` is now a forced-lane override. Contract additions (additive, one-file-PR): `Pawn.work_priorities`/`forced_assignment`, `FactionState.work_decisions`, `WorkDecision`/`RejectedJob`, `ACTION_SET_WORK_PRIORITY`, `GovernorAction.work_type/level`+`set_work_priority`. Engine splits needs/arbiter/activity phases. Viewer: clickable RimWorld Work grid (Work button), inspector "Why this job" trace via `work.explain` (lazy O(buildings) per inspected pawn), `Idle N` HUD chip. Oracles held: I1 3-day survival and the LLM-vs-fallback 3-day determinism proof both stay green; default-civ staffing matches the old best-skill matcher. Scale note: arbiter is O(needers x buildings)/hour - microseconds at 12 pawns; the 1000-pawn benchmark rises to ~21 ms/hour (989 unemployed pawns re-scan 11 slots each hour), which is the Paper 7 job-index/cadence work deferred to the scale gates and stays ~28x under the real-time step budget. Lethal starvation still deferred. |
| 2026-06-29 | Build-2 first essential economy: water need + Water Well + governor exception | `.\.venv\Scripts\python.exe -m unittest tests.test_water`; `.\.venv\Scripts\python.exe -m unittest discover -s tests` (209 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; refreshed and inspected `docs\screenshots\current-state.png` + `work-grid.png` | pass | Added conserved water as the first Townsmen essential: `Good.WATER`, `NEED_WATER`, Water Well production, one-unit drinking, thirst thoughts, Civ Water readout, HUD Water chip, `water` work type/priority, `economy.water_days_of_cover`, and `low_water` governor exception. Default 12-pawn civ starts with one staffed Water Well and water stock. Next: map readability for current systems; district buffers, service queues, seasonal water demand, storage caps, markets, wages/taxes, and deeper logistics remain deferred. |
| 2026-06-30 | Full Mac LM acceptance gate for PR #21 `codex/scale-foundations` at `33ebd642acf80faeab0c1b3efaea5a8ec1544e55` | `.venv/bin/python -m pip install -e .`; `.venv/bin/python -m agent_town --smoke-test`; `.venv/bin/python -m unittest discover -s tests` (219 tests); `pwsh -NoProfile -File scripts/validate-workbench.ps1`; `.venv/bin/python scripts/benchmark_scaling.py --pawns 100 500 1000 --steps 20`; LM Studio ping `http://192.168.1.131:1234/v1/models` found `google/gemma-4-e4b`; Pygame `CivilizationViewer` booted with `LLMGovernor` for 96 simulated hours; `.venv/bin/python scripts/analyze_run.py logs/run-20260630-012152.jsonl` | red | Scale benchmark passed (100/500/1000 pawns: 2.012/10.158/19.691 ms per engine hour; draw 1.943/4.319/6.960 ms), but the full game-state LM gate reached day 4 hour 7 with RED health: bread depleted once, water stalled once, mood dipped to min 44.6 and ended 45.7, final water need 0.14, 4 invalid-JSON dropped decisions/fallback-covered hours, 525 `set_work_priority` and 6 `set_schedule` actions. Not ready to merge; no Apple Silicon-specific failure evidence. |
| 2026-06-29 22:39 -06:00 | Paper 5 current-systems map readability on `codex/build-2-water-need` (branch equal to origin at start; model gpt-5.5 xhigh) | RED `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` failed on missing `_construction_progress`; GREEN `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` (29 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (212 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; refreshed and inspected `docs\screenshots\current-state.png` plus temp `local-agent-town-readability-proof.png` | pass | Decision source: Paper 5 "Showing work, idle, construction, danger, and storage pressure" plus Paper 8 "Roadmap implication." Shipped hover-vs-selection outlines, danger-over-selection rings, idle overhead badges from `work.LANE_IDLE`, and construction ghosts/footprint/progress bars. Storage 80/95% badges deferred until stockpile capacity exists; next code task is Governor card + exception stack. |
| 2026-06-29 23:09 -06:00 | Paper 6 governor card + exception stack on new `codex/governor-card-exception-stack` branch (PR #19 was merged; model gpt-5.5 xhigh; budget metric not readable; `.agent.lock` acquired) | RED `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` failed on missing `exception_stack_items`; GREEN `.\.venv\Scripts\python.exe -m unittest tests.test_civilization_view` (33 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (216 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; refreshed and inspected `docs\screenshots\current-state.png` | pass | PR status read: no open PRs; PR #19 was merged cleanly with Mac gate pass. Decision source: Paper 6 "Local AI governor status" / "Suggested Local Agent Town screen layout" plus Paper 8 "Roadmap implication." Added a read-only Governor card (plan, phase, bottleneck, confidence, last reallocation, top exception) and right-edge exception stack sorted by severity/actionability; next code task is Paper 7 scale foundations. |
| 2026-06-29 23:33 -06:00 | skipped, PR #20 status gate on `codex/governor-card-exception-stack` (branch equal to origin at start; model gpt-5.5 xhigh; `.agent.lock` acquired) | `gh pr view codex/governor-card-exception-stack --json ...` -> PR #20 OPEN/CLEAN, no comments, no reviews, no status checks; `gh pr checks 20 --watch=false` -> no checks reported; `.\.venv\Scripts\python.exe -m unittest discover -s tests` (216 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | skipped | PR status read: PR #20 was not red, green, or merged because GitHub reports no check signal. Decision: do not reuse the Paper 6 branch for Paper 7 and do not open a new branch until the active PR is green or merged; next code task remains Paper 7 scale foundations. |
| 2026-06-30 00:04 -06:00 | skipped, PR #20 status gate on `codex/governor-card-exception-stack` (branch equal to origin at start; model gpt-5.5 xhigh; `.agent.lock` acquired) | `git fetch origin --prune`; `gh pr view 20 --json ...` -> PR #20 OPEN/CLEAN, one prior automation comment, no reviews, no status checks; `gh pr checks 20 --watch=false` -> no checks reported; `.\.venv\Scripts\python.exe -m unittest discover -s tests` (216 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check` | skipped | PR status read: PR #20 is still not red, green, or merged because GitHub reports no check signal and no Mac PR status/comment was present. Decision: do not reuse the Paper 6 branch for Paper 7 and do not open a new branch until the active PR is green or merged; next code task remains Paper 7 scale foundations. |
| 2026-06-30 00:39 -06:00 | Paper 7 scale foundations on new `codex/scale-foundations` branch from updated `origin/main` 47bb44f (model gpt-5.5 xhigh; budget metric not readable; `.agent.lock` acquired) | RED `.\.venv\Scripts\python.exe -m unittest tests.test_world_regions tests.test_work` failed on missing `world.reachability_regions` and unreachable job still choosing `bake1`; RED `.\.venv\Scripts\python.exe -m unittest tests.test_engine.EngineDeterminismTests.test_step_hour_reports_stable_phase_order` failed on missing `StepResult.phases_executed`; GREEN `.\.venv\Scripts\python.exe -m unittest tests.test_engine tests.test_world_regions tests.test_work` (27 tests); `.\.venv\Scripts\python.exe -m unittest discover -s tests` (219 tests); `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\scripts\validate-workbench.ps1`; `git diff --check`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scaling.py --pawns 100 500 1000 --steps 20` -> 1000 pawns 37.701 engine ms/hour, 3.050 context ms, 16.076 draw ms | pass | PR status read: PR #20 was MERGED at 2026-06-30T06:27:00Z and open PR list was empty, so a new branch was required; published PR #21 as OPEN/CLEAN with no checks reported. Decision source: Paper 7 "Region/reachability IDs before pathing" and "Deterministic update flow" plus Paper 8 sequence. Shipped deterministic walkable-region ids, `unreachable` work rejection before priority ranking, cached region reuse per assignment pass, and `engine.ENGINE_PHASES` / `StepResult.phases_executed`; dirty topology, job indexes, cadence buckets, and path abstraction remain deferred. |
