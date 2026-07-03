# Local Agent Town

> Generated from LLM Workbench v2.1. See `RUNBOOK.md` -> Upgrading The Harness.

A local desktop prototype for watching one LLM-governed civilization run on
autopilot.

This is intentionally not web based. The simulation core is deterministic
Python; Pygame is the local viewer for the civilization state. One Governor
agent sets policy; a deterministic engine runs about a dozen RimWorld-style
pawns and the economy. You watch; you do not play.

## Current State Screenshot

![Current Local Agent Town UI](docs/screenshots/current-state.png)

This is a screenshot of the current local viewer state: a trimmed KPI strip
(Day, Pop, Idle, Mood, Coin, Food-days, Storage, News), a day/night light
overlay, a RimWorld-style pawn roster, a readable civilization map with fields
mid-growth and real held storage, right-side alerts plus selected-pawn/building
inspection, and a bottom command strip. Pawns self-select their work through
the lane-based arbiter, and the selected-pawn inspector keeps the "Why this
job" trace visible.

Every bottom command opens one real panel. **Architect** shows build costs,
counts, slots, missing inputs, and construction blockers. **Work** opens the
RimWorld-style priority grid; click a cell to cycle a pawn's priority (1
highest .. 4 lowest, blank disables it). **Assign** opens a direct override
browser: select a pawn, pin them to an open job slot, or click an occupied slot
to inspect the worker holding it. **Research** shows the current research
spine and honest disabled future entries. **History** opens a live decisions +
events timeline; click a Governor decision to inspect proposed, applied, and
rejected policy payloads plus the after-state goods/needs and causality map.
**Menu** shows run controls, 1x/8x/20x watch speed, local model status, and
overlay toggles/status.

![Work-priority grid](docs/screenshots/work-grid.png)

## How This Project Is Run

This repository is governed by a small set of control documents. Read them
before changing anything:

- [`AGENTS.md`](AGENTS.md) - how agents behave here: authority order, read/edit
  scope, the task-selection loop, documentation ownership, and proof rules.
- [`BLUEPRINT.md`](BLUEPRINT.md) - what this project is: identity, direction,
  architecture, the frozen contract, invariants, and preserved decisions.
- [`TASKBOARD.md`](TASKBOARD.md) - the live work queue and append-only proof
  log. Its **Executive Brief** (top of the file) is the one-glance status for
  anyone who does not want to read code.
- [`RUNBOOK.md`](RUNBOOK.md) - how to set up, run, test, build, and recover
  this project, plus the verification commands that gate "done".
- [`HARNESS_FEEDBACK.md`](HARNESS_FEEDBACK.md) - the return channel to the
  reusable harness these docs came from.

Project-local references the harness does not own:
[`VISUAL_DESIGN.md`](VISUAL_DESIGN.md) (visual baseline) and
[`BRANCHING.md`](BRANCHING.md) (the three-tier branch model). The pre-v2.1
harness docs (`ROADMAP.md`, `UNATTENDED_WORK_POLICY.md`,
`BOOTSTRAP_CHECKLIST.md`) are archived under
[`archive/legacy-harness/`](archive/legacy-harness/README.md); their full
content is preserved in git history.

## Architecture Stance

The current scale decision is: keep Pygame as the prototype viewer, but keep
the engine testable and measurable without the viewer.

That means new scale work should start with evidence instead of an engine
rewrite:

- benchmark the headless civilization engine, governor context building, and
  dummy draw loop;
- keep the Governor as policy only, never a pawn micromanager;
- migrate engines only if benchmark evidence shows rendering, editor tooling,
  or Pygame-specific limits are the blocker.

## Research Papers

The `research_papers/` folder contains GPT Pro reference papers for the games
and UI patterns this project borrows from. They are source leads and design
inputs, then reduced into `BLUEPRINT.md` decisions and `TASKBOARD.md` tasks.

Current intake order:

1. RimWorld mood/thoughts.
2. RimWorld hunger/nutrition.
3. RimWorld autonomous pawn work priorities.
4. Townsmen-style economy loops.
5. Age of Empires settlement readability.
6. Observer-first RimWorld + Age UI.
7. Scale from 12 pawns to 1000 pawns.
8. A project synthesis collapsing 1-7 into one build order.

When a paper conflicts with current code, the conflict is tracked as a
`TASKBOARD.md` task instead of being treated as already implemented.

## Run

From this folder, on Windows:

```powershell
.\setup.ps1
.\run.ps1
```

Or double-click:

```text
Launch Local Agent Town.cmd
```

On macOS/Linux:

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m agent_town
```

Full setup, environment, and troubleshooting steps live in
[`RUNBOOK.md`](RUNBOOK.md).

## Controls

- Pan: `WASD` or arrow keys (held for continuous glide).
- Zoom: mouse wheel, `+`, or `-`.
- Select pawn: click a pawn or press `Tab`. Select a building: click it.
- Follow camera: `F` toggles following the selected pawn.
- Open a command panel: click `Architect`, `Work`, `Assign`, `Research`,
  `History`, or `Menu` in the bottom strip.
- Watch speed: open `Menu` and click `1x`, `8x`, or `20x`.
- Local model governor: press `L` to connect or disconnect LM Studio/Ollama.
- Close panel / quit: `Esc` closes an open panel first; with no panel open,
  `Esc` quits.

## Optional Local AI

The civilization runs without an LLM. To let a local model govern policy,
start an OpenAI-compatible local server such as LM Studio, then set:

```powershell
$env:AGENT_TOWN_LLM_MODEL = "google/gemma-4-e4b"
$env:AGENT_TOWN_LLM_BASE_URL = "http://localhost:1234/v1"
.\run.ps1
```

Ollama can use the same adapter with
`AGENT_TOWN_LLM_BASE_URL=http://localhost:11434/v1`.

## What Exists Now

- A deterministic build-1 civilization engine.
- Twelve pawns with skills, traits, needs, mood, schedule, assignments, and
  break states.
- Production chains for logs, planks, stone, grain, flour, bread, and water -
  every Tier 0 faucet (Farm, Forester, Quarry, Water Well) draws from a
  located, gated map node (real growth time, finite depletion, or a named
  replenished source), not a labor-only spigot.
- Construction, daily tax, and a fallback Governor that keeps the civilization
  moving, plus a local LLM Governor behind the same interface with a hard
  fallback on any error and a default-deny model-action safety filter.
- A Pygame civilization viewer with camera pan/zoom, a follow camera, pawn and
  building selection/inspection, a trimmed KPI strip, day/night lighting, and
  docked command panels (Architect, Work, Assign, Research, History, Menu).
- A lane-based work-priority arbiter with reservations and a decision trace.
- A conservation-safe water slice, finite storage caps with pressure badges,
  and a first wage/market money loop with sales tax and a service-pressure
  signal.
- An executable conservation ledger (`health.check_invariants` asserts the
  goods ledger holds every hour, not just at a snapshot) and an analyzer that
  distinguishes model pipeline availability from applied model-origin policy.
- Save/load: the civilization autosaves daily and on exit and resumes on boot,
  so the pocket universe persists between sessions.
- A live History decision audit, CC0/provenance-tracked sprites, and a
  repeatable civilization scaling benchmark.

## Project Status

See the **Executive Brief** at the top of [`TASKBOARD.md`](TASKBOARD.md) for
the current shipping state, health, any decision the owner needs to make,
blockers, and the next milestone. In short: build 1 is done and build-2 depth
(physical sourcing, save/load, spectator UI) is well underway; a 2026-07-01
peer review's confirmed P0/P1 findings are all fixed; the next code task is
the trader, then repair debt, then the Paper 7 scale foundations.

## License

No license file yet; see `TASKBOARD.md` -> Pending Decisions (D-001).
