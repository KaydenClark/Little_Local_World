# PR #23 Mac LM Gate Report

- PR: #23, `feat/production-target-honored`
- Tested SHA: `017834e9fcf4c7ebf9cf0f3df7df69f0e80af4e7`
- Gate time: 2026-06-30 03:18-03:24 America/Denver
- Machine: Apple Silicon Mac gate
- LM Studio endpoint/model: `http://192.168.1.131:1234/v1`, `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-091804-pr23.log`
- Authoritative viewer JSONL: `logs/run-20260630-031923.jsonl`
- Copied Mac local viewer JSONL: `logs/pr23-run-20260630-031923.jsonl`

## Commands

- `python3 -m venv .venv && .venv/bin/python -m pip install -e .`
- `/opt/homebrew/bin/python3.12 -m venv .venv && .venv/bin/python -m pip install -e .`
- `.venv/bin/python -m agent_town --smoke-test`
- `.venv/bin/python -m unittest discover -s tests`
- `pwsh -NoLogo -NoProfile -File scripts/validate-workbench.ps1`
- `GET http://192.168.1.131:1234/v1/models`
- `CivilizationViewer(smoke_test=False, governor=LLMGovernor(client=LocalLLMClient.from_env()))` boot, draw, and 96 simulated hours under `SDL_VIDEODRIVER=dummy`
- `.venv/bin/python scripts/analyze_run.py logs/run-20260630-031923.jsonl --events`
- `.venv/bin/python scripts/benchmark_scaling.py --pawns 100 500 1000 --steps 24 --context-repeats 8 --draw-frames 3`
- `git diff --check`

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass with platform note | The exact fresh-worktree `python3` bootstrap selected Apple Python 3.9 and failed editable install support. Rerun with the repo-supported `/opt/homebrew/bin/python3.12` completed editable install with `pygame==2.6.1`. |
| Smoke/build | pass | `.venv/bin/python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | 231 tests passed. |
| Workbench/docs validation | pass | `scripts/validate-workbench.ps1` passed under `pwsh`. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Viewer boot | pass | `CivilizationViewer` booted and wrote `logs/run-20260630-031923.jsonl`. |
| 4-day LM run | red | 96 simulated viewer hours reached day 4 hour 7, with 96/96 model outcomes and zero dropped decisions, but the civilization repeatedly depleted bread. |
| Analyzer health | red | `RESULT: RED`; analyzer exit 1 with 4 critical events and 4 food-staple depletions. |
| Optional expanded checks | pass | Scaling benchmark passed: 100 pawns 1.617 ms/hour, 500 pawns 8.588 ms/hour, 1000 pawns 17.023 ms/hour; dummy draw at 1000 pawns 8.130 ms/frame. |
| Diff hygiene | pass | `git diff --check` passed after documentation proof. |

## Model And Health Evidence

- Model decisions: 96 LLM decisions, 96 model outcomes, 0 dropped/fallback-covered hours, 100% LLM uptime.
- Applied model actions: 380 `set_work_priority` actions.
- Fallback/degraded evidence: none during the 96-hour run.
- Health summary: mood 85.8 -> min 39.4 -> end 45.75; idle peak 0; breaks 0; food depletions 4; supply stalls 2; warn events 4; critical events 4.
- Final state: day 4 hour 7, stockpile empty, food need 0.0, water need 0.0, recreation 0.805, rest 0.965, coin 84.
- Flagged events: bread depleted at day 2 hours 7, 10, and 12, and day 3 hour 7; bread low at day 2 hour 9; water stalled at day 2 hour 18; mood dipped to 44 at day 3 hour 14; flour stalled at day 3 hour 18.

## Decision

Not ready to merge under the full Mac LM acceptance gate. Install, smoke, unit, docs, LM ping, viewer boot, model usage, and scaling checks passed under the supported Mac Python 3.12 toolchain, but the required 4-day analyzer result is RED. There is no evidence that the failure is Apple-Silicon-specific; this is a likely current game-state/LM-gate failure where model policy still cannot keep the exposed 12-pawn civilization fed and watered for four in-game days.
