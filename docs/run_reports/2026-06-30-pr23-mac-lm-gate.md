# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `c4ce58a23e1d9f061e474f5f3214497fa848964c`
- Gate time: 2026-06-30 02:47-02:54 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-024730-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-024744.jsonl`

## Commands

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -File scripts/validate-workbench.ps1`
- `curl -fsS http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot and draw under `SDL_VIDEODRIVER=dummy`
- `CivilizationViewer` 96 simulated hours with blocking `LLMGovernor`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-024744.jsonl --events`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed with `local-agent-town==0.1.0`. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 226 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted, drew, stepped to day 0 hour 10 with `LLMGovernor`. |
| 4-day LM run | red | 96 simulated hours reached day 4 hour 7, but bread depleted and water stalled. |
| Analyzer health | red | `RESULT: RED`; analyzer exit 1 with one critical food-depleted event. |
| Optional expanded checks | skipped | No scale/pathfinding/performance or visible UI change in this PR. |

## Model And Health Evidence

- Model decisions: 96 attempted LLM decisions, 92 model outcomes, 4 invalid-JSON fallback-covered hours.
- Applied model actions: 478 `set_work_priority` actions and 48 `set_schedule` actions.
- Fallback/degraded evidence: 4 `llm_decision_dropped`, 3 `llm_offline`, 3 `llm_recovered`; dropped reason was `LLM response must contain valid JSON object`.
- Health summary: mood 85.8 -> min 39.2 -> end 39.9; idle peak 1; breaks 0; bread depletions 1; supply stalls 1.
- Final state: day 4 hour 7, stockpile only had grain 20; final needs were food 0.0, water 0.0, recreation 0.7, rest 1.0.
- Flagged events: bread depleted at day 1 hour 7, water stalled at day 2 hour 18, one mood dip, and 4 dropped LLM decisions.
- Operational note: the wrapper command printed `viewer_run=complete` and wrote a valid `run_end`, then exited non-zero because the summary-print snippet referenced a stale `Stockpile.quantities` attribute. The authoritative analyzer consumed the completed JSONL and returned RED.

## Decision

Not ready to merge under the full Mac LM acceptance gate. Required install, smoke, unit, docs, LM ping, and viewer boot gates passed, and the model was actually used, but the 4-day analyzer result is RED. There is no evidence that the failure is Apple-Silicon-specific; this is a likely current game-state/LM-gate health issue driven by model-policy/runtime behavior.
