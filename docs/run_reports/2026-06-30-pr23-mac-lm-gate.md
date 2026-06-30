# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `f6834eefbefcb3e0ffa148d89a60d0cf0cc25bb4`
- Gate time: 2026-06-30 03:48-03:55 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-094853-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-034953.jsonl`

## Commands

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`
- `GET http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot, draw, and 96 simulated hours under `SDL_VIDEODRIVER=dummy`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-034953.jsonl --events`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed in the existing `.venv` with `pygame==2.6.1`. |
| Smoke/build | pass | `.venv/bin/python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 233 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed under `pwsh`. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted, drew frames, and wrote `logs/run-20260630-034953.jsonl`. |
| 4-day LM run | amber | 96 simulated viewer hours reached day 4 hour 7; model decisions were used on 91/96 hours and fallback covered 5 invalid-JSON hours. |
| Analyzer health | amber | `RESULT: AMBER`; zero critical events, but 9 warning events from dropped/recovered LLM decisions. |
| Optional expanded checks | skipped | Scaling benchmark was not required because this PR does not touch scale/pathfinding/performance; screenshot proof was not required because no visible UI changed. |
| Diff hygiene | pass | `git diff --check` passed after this documentation proof. |

## Model And Health Evidence

- Model decisions: 96 LLM decisions, 91 model outcomes, 5 invalid-JSON dropped/fallback-covered hours, 95% LLM uptime.
- Applied model actions: 365 `set_work_priority` actions.
- Rejected/invalid decisions: no rejected actions after parsing; 5 model responses failed JSON parsing and fell back.
- Health summary: mood 85.8 -> min 72.4 -> end 82.4; idle peak 0; breaks 0; food depletions 0; supply stalls 0; warn events 9; critical events 0.
- Flagged events: dropped/offline warnings at day 0 hour 8, day 2 hours 6-7, day 3 hour 6, and day 4 hour 6; recovery events followed the offline periods.
- Action histogram: 365 applied `set_work_priority` actions.

## Decision

Not ready to merge under the full Mac LM acceptance gate. Install, smoke, unit, docs, LM ping, viewer boot, and the 96-hour run completed, and the current game state stayed materially healthy. The required analyzer result is still AMBER, not GREEN, because the local model emitted invalid JSON on 5/96 decision hours and fallback had to cover. There is no evidence that the failure is Apple-Silicon-specific; this is a likely current LM-gate/model-output reliability failure.
