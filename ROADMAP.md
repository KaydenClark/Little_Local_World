# Local Agent Town - Roadmap

**Current phase:** prototype  
**Owner:** Kayden and local coding agents

This is the active work plan. Keep it forward-looking and proof-oriented.

## Current State

The project has a local Python desktop slice: a Pygame town viewer, ten autonomous NPCs, selectable inspection state, suggestion input, Kenney sprites/emotes, event feed, SQLite snapshot helpers, replay events, a rule-agent benchmark harness, and unit-tested simulation core.

Important drift or uncertainty:

- Pygame was not installed globally when the project was created; local `.venv` setup is required.
- LLM-backed planning is implemented as an optional local OpenAI-compatible adapter. It uses `AGENT_TOWN_LLM_MODEL` when set, otherwise it quickly discovers a local non-embedding model from the configured `/models` endpoint when LM Studio/Ollama is already running.
- Persistence exists as a library-level SQLite snapshot/replay helper; viewer save/load controls are not implemented yet.

## Current Goal

Stabilize the first local LLM-backed desktop prototype while keeping the non-LLM town loop reliable and benchmarkable.

Done when:

- core and LLM adapter tests pass;
- the Pygame smoke test opens, draws assets briefly, and exits;
- the rule-agent benchmark harness runs for the target scale slice;
- workbench validation passes.

## Next Tasks

1. **Scale benchmark pass** - run rule-agent counts at 100, 500, 1,000, and 5,000, then add render benchmark coverage for visible entities. Proof: benchmark output with p95 timings and pass/fail notes.
2. **Manual LM Studio/Ollama tuning pass** - run Gemma 4 E4B-it, Qwen3-8B, Phi-4-mini-instruct, and Gemma 4 12B only if memory allows; record speed, RAM/VRAM, context, and responsiveness. Proof: manual notes with model status and responsiveness.
3. **Viewer save/load controls** - expose SQLite snapshot save/load from the desktop viewer or a small CLI once the snapshot contract has one more use. Proof: create, load, and replay a short simulation through the user-facing path.
4. **Deeper objects and places** - add usable objects, resources, and location-specific tasks. Proof: deterministic simulation tests and viewer smoke test.

## Blocked Or Deferred

Do not start these until their prerequisite is met.

| Item | Blocked on | Why it matters |
|---|---|---|
| Hosted AI providers | explicit user approval | Avoids accidental paid or network-dependent behavior |
| Multiplayer or remote viewing | explicit product direction change | Current requirement is local and not web based |
| Large map editor | stable core loop | Editing tools are less useful before agent behavior is interesting |

## Backlog

- Add places with objects and tasks.
- Add agent-to-agent message summaries.
- Add screenshots or GIF capture for quick review.
- Add render benchmark for 500, 1,000, 5,000, and 10,000 visible entities.
- Add grid or navmesh pathfinding behind the existing direct pathfinder interface.

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
| 2026-06-27 | Partially scale architecture while keeping Pygame | `.\.venv\Scripts\python.exe -m unittest discover -s tests`; `.\.venv\Scripts\python.exe -m agent_town --smoke-test`; `.\.venv\Scripts\python.exe .\scripts\benchmark_scale.py --agents 100 500 1000 --iterations 10`; `.\scripts\validate-workbench.ps1` | pass | Full render benchmarks, LM Studio model-memory pass, and viewer save/load controls remain next |
