# Local Agent Town

A local desktop prototype for watching autonomous NPCs move through a small social world.

This is intentionally not web based. The first version uses Python and Pygame for a watchable 2D world, with the simulation logic kept separate from the renderer.

Project structure follows the `LLM_Workbench` pattern:

- `AGENTS.md` - agent instructions, scope, and verification rules.
- `BLUEPRINT.md` - stable project definition and architecture.
- `ROADMAP.md` - active plan, backlog, and verification log.
- `RUNBOOK.md` - setup, run, test, and troubleshooting commands.
- `BOOTSTRAP_CHECKLIST.md` - workbench adoption checks.
- `UNATTENDED_WORK_POLICY.md` - guardrails for longer agent work.
- `VISUAL_DESIGN.md` - local visual baseline.

## Run

From this folder:

```powershell
.\setup.ps1
.\run.ps1
```

Or double-click:

```text
Launch Local Agent Town.cmd
```

## Controls

- Pan: `WASD` or arrow keys
- Zoom: mouse wheel
- Select NPC: click an NPC or press `Tab`
- Pause: `P`
- Speed: `-` and `=`
- Suggest an idea to the selected NPC: press `/`, type, then `Enter`
- Cancel suggestion text: `Esc`

## Optional Local AI

The simulation runs without an LLM. To let a local model occasionally enrich agent plans, start an OpenAI-compatible local server such as LM Studio, then set:

```powershell
$env:AGENT_TOWN_LLM_MODEL = "gemma-4-e4b-it"
$env:AGENT_TOWN_LLM_BASE_URL = "http://localhost:1234/v1"
.\run.ps1
```

Ollama can use the same adapter with `AGENT_TOWN_LLM_BASE_URL=http://localhost:11434/v1`.

## What exists now

- A small town map with named places.
- Ten NPCs with needs, activities, destinations, short memories, relationships, routines, and visible emotes.
- Lightweight autonomous behavior: eat, rest, socialize, reflect, work, and wander.
- Optional local LLM planning through an OpenAI-compatible adapter.
- Kenney CC0 sprites for agents, locations, and emotes.
- Suggestions that influence the selected NPC's next decision.
- Inspect panel for activity, needs, local model status, memory, event feed, and pending suggestions.

## Next useful upgrades

- Persist world history to SQLite.
- Add locations that contain objects and routines.
- Add event summaries so you can scrub through what happened.
