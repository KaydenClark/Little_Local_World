# PR #42 Mac LM Gate

**PR:** #42, `claude/trader-crisis-slice-3` -> `integration`
**Title:** The trader: coin -> bread crisis relief (T-101, crisis-line Slice 3)
**Tested source SHA:** `476663f9603d2b2377f4eca171cc4cccd66ab01a`
**Run time:** 2026-07-03 08:18-08:28 UTC on Apple Silicon Mac mini
**Endpoint/model:** `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
**Detailed local log:** `/Users/kayden/GPT_OS/Projects/Little_Local_World/logs/run-20260703-081813-pr42.log`

## Commands

```bash
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src .venv/bin/python -m agent_town --smoke-test
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
pwsh -NoProfile -File scripts/validate-workbench.ps1
GET http://192.168.1.131:1234/v1/models
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYTHONPATH=src AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1 AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b AGENT_TOWN_LLM_TIMEOUT=45 AGENT_TOWN_LLM_MAX_TOKENS=320 .venv/bin/python <viewer-path blocking LLMGovernor script>
PYTHONPATH=src .venv/bin/python scripts/analyze_run.py logs/run-20260703-021958.jsonl --events
```

`python3` on this Mac is the system Python 3.9.6, so the gate used available Homebrew Python 3.12.13 as required by `RUNBOOK.md`.

## Results

| Gate | Result | Evidence |
|---|---|---|
| Install | pass | Editable install completed in `.venv` with Python 3.12.13 and Pygame 2.6.1. |
| Smoke/build | pass | `.venv/bin/python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | `Ran 416 tests in 1.976s`, `OK`. |
| Workbench/docs validation | pass | `Adopted workbench validation passed.` |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | Instantiated `CivilizationViewer`, drew a frame, and wrote viewer JSONL telemetry. |
| 4-day LM run | pass with blocking issue noted | Completed 96 simulated viewer hours to day 4 07:00 with `LLMGovernor`; ad hoc evidence wrapper exited 1 after `run_end` due to using stale `Stockpile.amounts` instead of `Stockpile.counts`, not due to a game crash. |
| Analyzer health | AMBER, not green | `RESULT: AMBER` with two `good_stalled` warnings for planks. |
| Optional scale benchmark | skipped | PR touches trader/runtime viewer/docs/tests, not scale/pathfinding/performance. |
| Screenshot proof | skipped | No new screenshot was requested by the gate and the branch already carries trader proof frames under `docs/proof/trader/`. |

## Model Decision Evidence

- Run log: `logs/run-20260703-021958.jsonl` inside the test worktree.
- `llm_decisions`: 96/96.
- `model_decisions`: 96.
- `llm_dropped`: 0.
- `model_actions_applied`: 102.
- Model-origin action histogram: `buy_good: 1`, `place_building: 70`, `set_work_priority: 31`.
- Final state: day 4 07:00; mood 82.4, mood minimum 72.4, idle peak 3, breaks 0, depletions 0.
- Final stockpile: bread 105, flour 1, grain 4, logs 1, planks 2, stone 34, water 33.

The model path was actually used. This was not a fallback-only run.

## Analyzer Output

```text
RESULT: AMBER
  - 2 warn event(s)

Flagged events:
  [WARN] day2 06:00 good_stalled: Planks empty 12h - supply chain stalled
  [WARN] day2 23:00 good_stalled: Planks empty 12h - supply chain stalled
```

## Decision

**Not ready to merge.** Required install, smoke, unit, docs, LM ping, viewer boot, and 96-hour LM evidence were present, but the analyzer verdict was AMBER. This gate treats AMBER as not green.

## Platform Assessment

Likely real repo/game-state/LM-gate result, not Apple-Silicon-specific. The blocking readiness issue is analyzer health (`good_stalled` warnings), not a Mac display/path/architecture failure. The post-run wrapper `AttributeError` came from this gate's evidence extraction snippet after telemetry `run_end`; it does not invalidate the completed JSONL or analyzer result, but it is recorded as a harness wrapper gap.
