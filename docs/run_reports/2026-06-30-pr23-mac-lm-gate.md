# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `032afc730862d799354c718431d0e0334f0e7308`
- Gate time: 2026-06-30 02:17-02:27 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-021727-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-022028.jsonl`

## Commands

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -File scripts/validate-workbench.ps1`
- `curl -fsS http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot and draw under `SDL_VIDEODRIVER=dummy`
- `CivilizationViewer` 96 simulated hours with blocking `LLMGovernor`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-022028.jsonl --events`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed with `local-agent-town==0.1.0`. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 223 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted, drew, stepped to day 0 hour 15 with `LLMGovernor`. |
| 4-day LM run | red | 96 simulated hours reached day 4 hour 7, but food and water collapsed. |
| Analyzer health | red | `RESULT: RED`; analyzer exit 1 with one critical food-depleted event. |
| Optional expanded checks | skipped | No scale/pathfinding/performance or visible UI change in this PR. |

## Model And Health Evidence

- Model decisions: 96 attempted LLM decisions, 83 model outcomes, 13 invalid-JSON fallback-covered hours.
- Applied model actions: 388 `set_work_priority` actions and 102 `set_schedule` actions.
- Fallback/degraded evidence: 13 `llm_decision_dropped`, 9 `llm_offline`, 9 `llm_recovered`; dropped reason was `LLM response must contain valid JSON object`.
- Health summary: mood 85.8 -> min 38.0 -> end 39.9; idle peak 3; breaks 0; bread depletions 1; supply stalls 2.
- Final state: day 4 hour 7, stockpile only had grain 10; final needs were food 0.0, water 0.0, recreation 0.7, rest 1.0.
- Flagged events: bread low, bread depleted, flour and water stalled, one mood dip, and 13 dropped LLM decisions.

## Decision

Not ready to merge under the full Mac LM acceptance gate. Required install, smoke, unit, docs, LM ping, and viewer boot gates passed, and the model was actually used, but the 4-day analyzer result is RED. There is no evidence that the failure is Apple-Silicon-specific; this is a likely current game-state/LM-gate health issue driven by model-policy/runtime behavior.
