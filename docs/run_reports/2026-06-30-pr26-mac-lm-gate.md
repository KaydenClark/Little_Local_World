# PR #26 Mac LM Gate - 2026-06-30

## Scope

- PR: #26, `codex/wage-market-money-loop`
- Title: Add first wage and market money loop
- Tested SHA: `bb2f17ad3f1a5594d8ceea11d2b00c23d86c2fa1`
- Gate host: Apple Silicon Mac mini
- Time: 2026-06-30 05:47 -06:00
- LM Studio endpoint: `http://192.168.1.131:1234/v1`
- Preferred model: `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-114753-pr26.log`
- Viewer JSONL: `logs/run-20260630-054944-viewer96.jsonl`

## Commands

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/python -m agent_town --smoke-test
.venv/bin/python -m unittest discover -s tests
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1
GET http://192.168.1.131:1234/v1/models
AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1 \
AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b \
AGENT_TOWN_LLM_TIMEOUT=45 \
AGENT_TOWN_LLM_MAX_TOKENS=400 \
SDL_VIDEODRIVER=dummy \
.venv/bin/python - <<'PY'
# Instantiated CivilizationViewer, drew frames, and advanced 96 simulated hours
# through viewer _step_and_log telemetry with a blocking LLMGovernor.
PY
.venv/bin/python scripts/analyze_run.py logs/run-20260630-054944-viewer96.jsonl --events
SDL_VIDEODRIVER=dummy .venv/bin/python - <<'PY'
# Rendered a fresh CivilizationViewer frame to docs/screenshots/current-state.png.
PY
git diff --check
```

Note: the first fresh-worktree bootstrap used macOS `/usr/bin/python3` 3.9.6 and failed because `pyproject.toml` requires Python `>=3.11`. The gate was rerun in the same disposable worktree with installed Python 3.12.13, matching the repo prerequisite.

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed under Python 3.12.13 after the unsupported Python 3.9 bootstrap failed. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | `unittest discover -s tests` ran 251 tests. |
| Workbench/docs validation | pass | `validate-workbench.ps1` passed under available PowerShell. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Pygame viewer boot | pass | `CivilizationViewer` booted, drew frames, and wrote viewer telemetry. |
| 4-day LM-governed run | pass | 96 simulated hours completed through viewer `_step_and_log`. |
| Analyzer health | pass | `RESULT: GREEN`. |
| Screenshot proof | pass | Fresh dummy-SDL frame rendered to `docs/screenshots/current-state.png`. |
| Diff hygiene | pass | `git diff --check` passed after this documentation proof. |

## Model Decision Evidence

- LLM client: enabled, model `google/gemma-4-e4b`, base URL `http://192.168.1.131:1234/v1`.
- Decision outcomes: 96 model-backed decisions.
- Dropped/fallback-covered hours: 0 of 96.
- Fallback-only run: no.
- Applied action histogram: `{'set_work_priority': 386}`.
- Viewer run-start telemetry still prints analyzer `model=(none)`, but per-hour decisions record `governor_kind=LLMGovernor`, `llm_source=llm`, and `outcome=model`.

## Health Summary

- Final sim time: day 4, hour 7.
- Mood: 85.8 start -> 72.4 min -> 82.4 end.
- Idle peak: 0.
- Breaks: 0.
- Food depletions: 0.
- Supply stalls: 0.
- Warnings/critical events: 0/0.
- Final stockpile: bread 16, water 96, planks 20, stone 40.
- Final storage: 172 / 240 used (71.7% full).
- Final money-loop fields: coin 44, market revenue 0, wages paid 0 in the final hour.

## Optional Checks

- Scaling benchmark: not run; this PR does not touch scale, pathfinding, or performance architecture.
- Screenshot proof: pass; the current-state screenshot was refreshed from the PR branch after the gate.
- Dedicated branch check: covered by the full unit suite, including `tests/test_money_loop.py`.

## Decision

Ready to merge into `main`.

No Apple Silicon-specific failure evidence was observed. The gate exercised install, smoke/build, full tests, docs validation, live LM Studio connectivity, Pygame viewer boot, the 4-day LM-governed viewer path, analyzer health, and fresh visible-state screenshot proof.
