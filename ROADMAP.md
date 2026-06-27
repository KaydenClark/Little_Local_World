# Little Local World - Roadmap

**Current phase:** Track B1 pawns, needs, schedule, mood
**Owner:** Kayden and local coding agents

This is the active work plan. Keep it forward-looking and proof-oriented.

## Current State

The project is pivoting from the earlier local social wander-sim into a single-faction, LLM-governed colony builder.

Verified live state:

- The existing Python package is still named `agent_town`.
- The old Pygame viewer, social simulation core, optional local LLM adapter, SQLite snapshot helpers, replay events, assets, and tests still exist.
- Phase 0 now adds the colony-builder frozen contract in `src/agent_town/core.py`.
- Skeleton modules now exist for `world`, `economy`, `buildings`, `construction`, `pawns`, `mood`, `schedule`, and `governor`.
- Track A1 now implements stockpile `add/remove/has`, grid map creation, map validation, and deterministic starter resource nodes.
- Track A2 now implements Forester and Sawmill building definitions plus deterministic headless logs-to-planks production with temporary staffing through `Building.staffed_by`.
- Track A3 now implements construction sites with partial delivery, insufficient-goods blocking, work completion, built-building creation, and site removal.
- Track A4 now implements food and stone production chains, daily mood-based tax collection, and coin-gated building placement.
- Track A planned work is complete through A4 on the current Track A branch; Track B behavior remains intentionally explicit stubs until each milestone implements it.

Important drift or uncertainty:

- `BLUEPRINT.md` now defines the colony-builder target; older README text may still describe the prior social-sim prototype until touched.
- The live checkout is macOS, while some launcher and setup docs still include Windows PowerShell paths.
- The existing viewer is not yet wired to the new colony state.
- The SQLite persistence scaffold remains oriented to the old snapshot model and is dormant for Build 1 unless later work repoints it.

## Current Goal

Implement the first pawn needs, schedule, and mood behavior against the frozen contract.

Done when:

- pawn needs decay over a day;
- schedule blocks restore the matching needs;
- base mood derives from current needs;
- targeted pawn, schedule, and mood tests pass;
- the full test suite, smoke test, and workbench validation pass.

## Next Tasks

1. **Track B1: pawns, needs, schedule, mood** - implement needs decay/restoration, schedule templates, and base mood. Proof: day-cycle tests.
2. **Track B2: effective work** - implement the skill, mood, trait, and schedule formula behind `effective_work`. Proof: table-driven tests.
3. **Track B3: traits, wants, breaks, exceptions** - implement break state and exception queue. Proof: starved or overworked pawn breaks and emits the right exception.
4. **Track B4: context and fallback Governor** - implement summary context and greedy fallback decisions. Proof: fallback assigns by best skill and reschedules unhappy pawns.
5. **Integration I1-I3** - wire pawns to production, add LLM Governor after fallback works, then render new state in Pygame. Proof: fallback keeps twelve pawns alive over N days, LLM run logs decisions, viewer smoke test opens and exits.

## Blocked Or Deferred

Do not start these until their prerequisite is met.

| Item | Blocked on | Why it matters |
|---|---|---|
| Hosted AI providers | explicit user approval | Avoids accidental paid or network-dependent behavior |
| Second faction, contested map, enemies, or combat | Build 2 direction | Build 1 is one town and one faction |
| Large scale benchmarking or engine migration | working 12-pawn economy | Performance work is premature before core systems exist |
| Viewer polish | tested economy and Governor loop | Visual polish should not outrun simulation correctness |
| Persistence repoint | Build 2 or correctness blocker | Existing SQLite scaffold is intentionally dormant for Build 1 |

## Backlog

- Seasons: winter changes daylight and raises recreation or comfort pressure.
- Research: two or three techs that spend coin or prestige for tax, work speed, or building unlocks.
- Viewer save/load only after the new colony snapshot contract exists.
- Better visual assets after the economy and Governor are proven.
- Scale benchmarks after Build 1 works with about twelve pawns.

## Release Checks

Verification commands live in `RUNBOOK.md` Test And Build.

Project-specific release and checkpoint checks:

- Confirm no `.venv`, logs, databases, private exports, or generated dumps are included.
- Confirm no web server or browser runtime was introduced.
- Confirm the Governor still emits policy actions only.
- Confirm core colony tests run headless without Pygame.
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
| 2026-06-27 | Phase 0 colony-builder contract freeze | `./.venv/bin/python -m unittest tests.test_colony_contract`; `./.venv/bin/python -m unittest discover -s tests`; `./.venv/bin/python -m agent_town --smoke-test`; `pwsh -File scripts/validate-workbench.ps1` | pass | Track A and Track B behavior remains intentionally stubbed; commit-to-main handoff not performed from this branch |
| 2026-06-27 | Track A1 map, nodes, and stockpile | `./.venv/bin/python -m unittest tests.test_world_a1 tests.test_colony_contract`; `./.venv/bin/python -m unittest discover -s tests`; `./.venv/bin/python -m agent_town --smoke-test`; `pwsh -File scripts/validate-workbench.ps1`; `git diff --check` | pass | Track A2 production chain remains next |
| 2026-06-27 | Track A2 one wood production chain | `./.venv/bin/python -m unittest tests.test_economy_a2 tests.test_world_a1 tests.test_colony_contract`; `./.venv/bin/python -m unittest discover -s tests`; `./.venv/bin/python -m agent_town --smoke-test`; `pwsh -File scripts/validate-workbench.ps1`; `git diff --check` | pass | Track A3 construction remains next |
| 2026-06-27 | Track A3 construction flow | `./.venv/bin/python -m unittest tests.test_construction_a3 tests.test_economy_a2 tests.test_world_a1 tests.test_colony_contract`; `./.venv/bin/python -m unittest discover -s tests`; `./.venv/bin/python -m agent_town --smoke-test`; `pwsh -File scripts/validate-workbench.ps1`; `git diff --check` | pass | Track A4 multi-chain plus tax remains next |
| 2026-06-27 | Track A4 multi-chain plus tax | `./.venv/bin/python -m unittest tests.test_economy_a4 tests.test_construction_a3 tests.test_economy_a2 tests.test_world_a1 tests.test_colony_contract`; `./.venv/bin/python -m unittest discover -s tests`; `./.venv/bin/python -m agent_town --smoke-test`; `pwsh -File scripts/validate-workbench.ps1`; `git diff --check` | pass | Track B1 pawn needs and mood remains next |
