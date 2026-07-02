# Mac LM Gate - PR #34

- Date: 2026-07-01 03:37 -0600
- PR: #34 - 
- Branch: `feat/llm-governor-dig-out-verify`
- Tested source SHA: `5f56638d69e292b8687d2f3da77c42cde224dc1a`
- Apple Silicon gate: Mac mini Codex
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1` / `google/gemma-4-e4b`
- Ready decision: `no`
- Platform assessment: likely-real-repo-game-state-or-lm-gate-failure-unless-noted; python3-default-3.9-so-venv-used-python3.12

## Commands

- `/opt/homebrew/bin/python3.12 -m venv .venv`
- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`
- `curl http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(LocalLLMClient.from_env()))` with 96 `_step_and_log()` hours and draw frames
- `.venv/bin/python scripts/analyze_run.py logs/run-20260701-033736.jsonl --events`
- `git diff --check`

## Results

| Gate | Result |
|---|---|
| Install | pass-python312 |
| Smoke/build | pass |
| Unit suite | pass |
| Docs validation | pass |
| LM ping | pass |
| Viewer boot | pass |
| 4-day LM run | pass |
| Analyzer | red |
| Optional expanded checks | skipped-not-scale-pathfinding-performance |

## Model Decision Evidence

- Model decision hours: 96 / 96
- Dropped/fallback-covered hours: 0
- Decision outcomes: `{'model': 96}`
- Action histogram: `{'assign_pawn': 2, 'place_building': 19, 'set_production_target': 3, 'set_work_priority': 22}`
- Failing unit tests: none

## Health Summary

- hours=96 mood=85.8->72.4->82.4 idle_peak=0 breaks=0 depletions=0 stalls=0 llm=96 dropped=0
- Warnings: 0
- Critical events: 64
- Final stockpile: `{'bread': 120, 'planks': 1, 'stone': 50, 'water': 174}`
- Viewer log copied to operational log: `/Users/kayden/GPT_OS/Projects/Little_Local_World/logs/run-20260701-033720-pr34-viewer.jsonl`
- Detailed gate log: `/Users/kayden/GPT_OS/Projects/Little_Local_World/logs/run-20260701-033720-pr34.log`

## Analyzer Output

```text
Run log: logs/run-20260701-033736.jsonl
  run_id=437ceb62e7fb schema=1
  governor=LLMGovernor model=(none) seed=0 population=12 started=2026-07-01T03:37:36

Health summary:
  hours          : 96
  mood           : start 85.8 -> min 72.4 -> end 82.4 (down)
  idle peak      : 0
  breaks         : 0 (peak concurrent 0)
  food depletions: 0   supply stalls: 0
  LLM decisions  : 96 (uptime 100%, dropped 0 = 0%)
  applied actions: {'assign_pawn': 2, 'place_building': 19, 'set_production_target': 3, 'set_work_priority': 22}
  events         : {'building_completed': 16, 'invariant_violation': 64}

Flagged events:
  [CRITICAL] day1 16:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 17:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 18:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 19:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 20:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 21:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 22:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day1 23:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  0:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  1:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  2:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  3:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  4:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  5:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  6:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  7:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  8:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2  9:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 10:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 11:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 12:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 13:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 14:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 15:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 16:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 17:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 18:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 19:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 20:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 21:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 22:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day2 23:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day3  0:00  invariant_violation: 1 invariant violation(s)
  [CRITICAL] day3  1:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  2:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  3:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  4:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  5:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  6:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  7:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  8:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  9:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 10:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 11:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 12:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 13:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 14:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 15:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 16:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 17:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 18:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 19:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 20:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 21:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 22:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 23:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  0:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  1:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  2:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  3:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  4:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  5:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  6:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  7:00  invariant_violation: 2 invariant violation(s)

RESULT: RED
  - 64 critical event(s)
```

## Last 30 Detailed Log Lines

```text
  [CRITICAL] day3  7:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  8:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3  9:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 10:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 11:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 12:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 13:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 14:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 15:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 16:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 17:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 18:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 19:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 20:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 21:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 22:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day3 23:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  0:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  1:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  2:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  3:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  4:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  5:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  6:00  invariant_violation: 2 invariant violation(s)
  [CRITICAL] day4  7:00  invariant_violation: 2 invariant violation(s)

RESULT: RED
  - 64 critical event(s)
Optional scaling benchmark skipped; changed files do not indicate scale/pathfinding/performance work.
[03:44:59] PR #34: write docs proof
```
