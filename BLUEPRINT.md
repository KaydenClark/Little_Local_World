# Local Agent Town - Blueprint

**Last reviewed:** 2026-06-27
**Status:** active  
**Source root:** `E:\GPTCode\local-agent-town`

## What This Project Is

Local Agent Town is a Python desktop simulation for watching autonomous NPCs move through a small social world. It is for local experimentation with AI-agent town behavior without a browser app or hosted service.

Core promise:

> Run a local watchable town where NPCs move, make lightweight decisions, remember interactions, receive occasional suggestions, and optionally use a local model for richer plans.

Primary users:

- Kayden, as the local operator and designer of the simulation.
- Future coding agents extending the simulation, viewer, and LLM planning layer.

## Non-Goals

This project is not trying to:

- become a web app;
- create a multiplayer game;
- require hosted infrastructure;
- require paid AI services for the base experience;
- support direct control of every NPC action as the primary interaction model.

## Current Product Shape

When the project is working, a user can:

- launch a local desktop window;
- pan and zoom around a small town map;
- select NPCs and inspect activity, goals, needs, memories, and suggestions;
- suggest a lightweight idea to the selected NPC;
- optionally connect LM Studio or Ollama through an OpenAI-compatible local endpoint;
- run simulation tests without opening the viewer.

The most important quality bar is:

- local reliability first, then richer NPC behavior.

## Architecture

| Layer | Choice | Source or notes |
|---|---|---|
| Runtime | Python 3.11 or newer | Verified locally with Python 3.11.6 |
| Frontend | Pygame desktop window | No browser runtime |
| Backend | None | Simulation runs in-process |
| Optional local AI | OpenAI-compatible chat completions adapter | Uses `AGENT_TOWN_LLM_MODEL` when set; otherwise quickly discovers a local non-embedding model from `/models` if LM Studio/Ollama is already running |
| Database or storage | SQLite snapshot helper | Library-level save/load for simulation state and replay events |
| Auth | None | Local-only prototype |
| Testing | Standard library `unittest` | Tests cover simulation core |
| Deployment or runtime | Local PowerShell scripts | `setup.ps1` and `run.ps1` |

Architecture constraints:

- Keep simulation logic in `src\agent_town\core.py` testable without Pygame.
- Keep rendering and input in `src\agent_town\app.py`.
- Keep local model calls in `src\agent_town\llm.py`; never block the Pygame loop on model output.
- Keep serializable world state, replay events, planner contracts, pathfinding seams, and model profiles outside the Pygame renderer.
- Do not add web server or browser UI unless the user reverses the non-web requirement.
- Treat LLM integration as an adapter layer, not as a replacement for deterministic core state transitions.

## Directory Map

```text
E:\GPTCode\local-agent-town\
├── src\agent_town\      <- simulation core and desktop viewer
├── tests\               <- unittest coverage for core behavior
├── scripts\             <- validation helpers
├── AGENTS.md            <- agent behavior and edit or read scope
├── BLUEPRINT.md         <- stable project definition
├── ROADMAP.md           <- active work plan and proof log
├── RUNBOOK.md           <- setup, operation, verification, recovery
├── setup.ps1            <- create local environment and install package
└── run.ps1              <- launch desktop viewer
```

## Main Contracts

### Screens

| Screen | Purpose | Status | Source |
|---|---|---|---|
| Pygame town viewer | Watch NPCs move, pan, zoom, select agents, and suggest ideas | working prototype | `src\agent_town\app.py` |
| Local LLM scheduler | Stagger occasional local-model planning turns without blocking the viewer | working prototype | `src\agent_town\llm.py` |
| Snapshot persistence | Save and restore serializable simulation snapshots and replay events | working library helper | `src\agent_town\persistence.py` |
| Scale benchmark harness | Measure rule-agent tick cost before engine changes | working script | `scripts\benchmark_scale.py` |

### Commands

| Command | Purpose | Required for done |
|---|---|---|
| `.\setup.ps1` | Create `.venv` and install the project | yes for local run |
| `.\run.ps1` | Launch the desktop viewer | yes for manual use |
| `.\.venv\Scripts\python.exe -m unittest discover -s tests` | Run core tests | yes for behavior changes |
| `.\.venv\Scripts\python.exe -m agent_town --smoke-test` | Verify viewer imports, opens, draws briefly, and exits | yes for viewer changes |
| `.\scripts\validate-workbench.ps1` | Validate workbench docs | yes for doc structure changes |
| `.\.venv\Scripts\python.exe .\scripts\benchmark_scale.py --agents 100 500 1000` | Run rule-agent scale benchmark | yes before engine-scale decisions |

### Data Model

| Entity | Key fields | Stored where | Notes |
|---|---|---|---|
| `Location` | name, x, y, kind, radius | memory only | Town places and behavior effects |
| `Agent` | id, name, position, needs, goal, activity, destination, memories, suggestions, relationships, routine hints, emote state | memory only | NPC state |
| `MemoryEntry` | tick, text | memory only | Short rolling event history |
| `EventEntry` | tick, text | memory only | Short town feed |
| `DecisionResult` | destination, intent, optional speech, optional memory, optional relationship effect | memory only | Validated output from local LLM planning |
| `Simulation` | locations, agents, tick, random seed | memory only | Owns simulation step and social interactions |
| `WorldState` | serializable locations, agents, events, replay events | memory, optional SQLite snapshot | Save/replay boundary |
| `ReplayEvent` | tick, elapsed, kind, payload | memory, optional SQLite snapshot | Debug/replay event stream |
| `PlannerRequest` / `PlannerResult` | agent id, world snapshot, context, validated plan fields | memory only | LLM planning boundary |
| `RenderSnapshot` | serializable world state plus visible/selected ids | memory only | Renderer handoff seam |
| `ModelProfile` | model name, tier, context, RAM/VRAM estimate, concurrency, notes | memory only | Local/API model benchmark planning |

## Core Logic And Invariants

Core behavior lives in `src\agent_town\core.py`.

Rules:

- Agents always target a named `Location`.
- Suggestions must validate the target agent id before mutating state.
- LLM decisions must validate agent id, destination, relationship target, and text lengths before mutating state.
- The viewer may show local model state but must not block waiting for model output.
- Movement, needs, location effects, and conversations must be testable without Pygame.
- Renderer code may read simulation state but should not duplicate decision logic.
- LLM contexts must be capped to relevant nearby or high-relationship agents, with omitted counts visible to the planner.
- The Pygame renderer must use viewport culling, label level-of-detail, and scaled sprite caching before an engine migration is considered.
- Save/load must serialize simulation state and replay events, not Pygame surfaces or renderer objects.

Do not duplicate this logic in:

- Pygame draw code;
- future LLM prompts;
- persistence adapters.

## Trust, Privacy, And Safety Boundaries

Sensitive data:

- future local LLM logs;
- future save files;
- future user-authored agent memories or suggestions.

Rules:

- Keep the base project local-only.
- Do not commit `.venv`, logs, databases, private exports, tokens, or generated dumps.
- Do not enable hosted LLM providers, telemetry, or external persistence without explicit user approval.
- Local LLM use must remain local-only. `AGENT_TOWN_LLM_MODEL` overrides discovery, and `AGENT_TOWN_LLM_AUTO_DISCOVER=0` disables startup discovery when the user wants deterministic non-LLM runs.

## Known Risks

| Risk | Impact | Mitigation or owner |
|---|---|---|
| Pygame dependency missing | Viewer cannot launch | Use `setup.ps1`; smoke-test import after install |
| Local model offline, slow, or rejecting request payloads | Agents could appear not to think | Keep deterministic fallback, use JSON Schema structured output, and show visible model status |
| NPC behavior is still lightweight | Agents can feel repetitive | Add persistence and deeper memory after prototype is stable |
| Pygame render scale | Large visible crowds can exceed frame budget | Culling, label LOD, scaled sprite cache, and benchmark proof before engine migration |
| Prompt/context bloat | More agents could create giant local-model prompts | Cap planner context to relevant agents and record omitted counts |
| Persistence has no user-facing controls yet | Save/load is available to tests and helpers, not the viewer UI | Add UI or CLI only after the snapshot contract is stable |

## Design Decisions

| Decision | Rationale | Date or source |
|---|---|---|
| Desktop Pygame instead of web | User explicitly does not want a web-based thing | 2026-06-26 user request |
| Testable core separate from renderer | Enables red and green testing without opening a window | 2026-06-26 implementation |
| Workbench docs adopted | User requested `KaydenClark/LLM_Workbench` project structure | 2026-06-26 user request |
| OpenAI-compatible local model adapter | Supports LM Studio and Ollama without hosted services or provider lock-in | 2026-06-26 implementation |
| Kenney CC0 sprites bundled from local zips | Improves watchability while keeping original zip files untouched | 2026-06-26 implementation |
| Partial scale-up without engine migration | Benchmarks, snapshots, replay events, bounded planner context, and render guardrails reduce migration risk while keeping Pygame | 2026-06-27 implementation |

## Health Criteria

The project is healthy when:

- `.\.venv\Scripts\python.exe -m unittest discover -s tests` passes;
- `.\.venv\Scripts\python.exe -m agent_town --smoke-test` exits successfully;
- `.\scripts\validate-workbench.ps1` passes;
- the desktop viewer launches through `.\run.ps1`;
- secrets and local data are not exposed in committed or built output.
