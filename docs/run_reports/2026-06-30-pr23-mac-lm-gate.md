# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `edf828ec778d14e3e9f4b5fa1d44220910a2eadc`
- Gate time: 2026-06-30 04:18-04:25 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-101824-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-041958.jsonl`

## Commands

- `.venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1`
- `GET http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot, draw, and 96 simulated hours under `SDL_VIDEODRIVER=dummy`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-041958.jsonl --events`
- Completed-viewer-log proof assertion over `logs/run-20260630-041958.jsonl`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed in the existing `.venv` with `pygame==2.6.1`. |
| Smoke/build | pass | `.venv/bin/python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 234 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed under `pwsh`. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted, drew frames, and wrote `logs/run-20260630-041958.jsonl`. |
| 4-day LM run | pass | 96 simulated viewer hours reached day 4 hour 7; model decisions were used on 96/96 hours with 0 dropped/fallback-covered hours. |
| Analyzer health | pass | `RESULT: GREEN`; zero warning or critical events. |
| Optional expanded checks | skipped | Scaling benchmark was not required because this PR does not touch scale/pathfinding/performance; screenshot proof was not required because no visible UI changed. |
| Diff hygiene | pass | `git diff --check` passed after this documentation proof. |

## Model And Health Evidence

- Model decisions: 96 LLM decisions, 96 model outcomes, 0 dropped decisions, 0 fallback/invalid hours, 100% LLM uptime.
- Applied model actions: 396 `set_work_priority` actions and 2 `place_building` actions.
- Rejected/invalid decisions: none that affected the health gate; hour day 4 / 0 rejected three no-op `set_work_priority` actions after parsing, with no drop or fallback.
- Health summary: mood 85.8 -> min 72.4 -> end 82.4; idle peak 0; breaks 0; food depletions 0; supply stalls 0; warn events 0; critical events 0.
- Final state: day 4 hour 7, coin 74, stockpile bread 16 / planks 12 / stone 36 / water 96, needs food 1.0 / recreation 0.805 / rest 0.965 / water 1.0.
- Event summary: 4 building-completed events, no health warnings.
- Operational note: the custom harness printed a stale `Stockpile.quantities` attribute after the completed `run_end` and exited non-zero, but the viewer JSONL had a valid `run_end`, `analyze_run.py` returned `RESULT: GREEN`, and the completed-log proof assertion exited 0.

## Decision

Ready to merge into `main` under the full Mac LM acceptance gate. Install, smoke/build, unit suite, docs validation, LM ping, viewer boot, 96-hour LM-governed viewer run, analyzer health, and proof assertion are green, and PR #23 is not draft. There is no Apple Silicon-specific failure evidence.
