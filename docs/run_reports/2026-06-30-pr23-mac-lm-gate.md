# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `88715b93a24580e04f183e88788e3b60018fb892`
- Gate time: 2026-06-30 01:49-01:58 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-014905-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-015421.jsonl`

## Commands

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -File scripts/validate-workbench.ps1`
- `curl -fsS http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot and draw under `SDL_VIDEODRIVER=dummy`
- `CivilizationViewer` 96 simulated hours with blocking `LLMGovernor`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-015421.jsonl --events`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed with `local-agent-town==0.1.0`. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 222 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted, drew, stepped to day 0 hour 8 with `LLMGovernor`. |
| 4-day LM run | amber | 96 simulated hours reached day 4 hour 7. |
| Analyzer health | amber | `RESULT: AMBER`; analyzer exit 0, but AMBER is not merge-green for this gate. |
| Optional expanded checks | skipped | No scale/pathfinding/performance or visible UI change in this PR. |

## Model And Health Evidence

- Model decisions: 96 attempted LLM decisions, 95 model outcomes, 1 invalid-JSON fallback-covered hour.
- Applied model actions: 256 `set_work_priority` actions.
- Fallback/degraded evidence: 1 `llm_decision_dropped`, 1 `llm_offline`, 1 `llm_recovered`.
- Health summary: mood 85.8 -> min 72.4 -> end 82.4; idle peak 0; breaks 0; bread depletions 0; supply stalls 4.
- Final state: day 4 hour 7, coin 92, bread 16, water 96, planks 20, stone 40, all 12 pawns staffed.
- Flagged events: four `good_stalled` warnings for logs being empty 12h, plus the single dropped LLM decision.

## Decision

Not ready to merge under the full Mac LM acceptance gate. Required install, smoke, unit, docs, LM ping, and viewer boot gates passed, and the model was actually used, but the 4-day analyzer result is AMBER rather than GREEN. There is no evidence that the failure is Apple-Silicon-specific; this is a likely current game-state/LM-gate health issue.
