# PR #27 Mac LM Gate - 2026-06-30

## Scope

- PR: #27, `codex/storehouse-capacity-badges`
- Title: Add Storehouse capacity and storage pressure badges
- Tested SHA: `889d1a5ba3447df96da12bd37e58dea6da0b8947`
- Gate host: Apple Silicon Mac mini
- Time: 2026-06-30 06:18 -06:00
- LM Studio endpoint: `http://192.168.1.131:1234/v1`
- Preferred model: `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-121852-pr27.log`
- Viewer JSONL: `logs/run-20260630-061901.jsonl`

## Commands

```bash
.venv/bin/python -m pip install -e .
.venv/bin/python -m agent_town --smoke-test
.venv/bin/python -m unittest discover -s tests
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1
GET http://192.168.1.131:1234/v1/models
AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1 \
AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b \
AGENT_TOWN_LLM_TIMEOUT=45 \
AGENT_TOWN_LLM_MAX_TOKENS=260 \
SDL_VIDEODRIVER=dummy \
.venv/bin/python - <<'PY'
# Instantiated CivilizationViewer, drew frames, and advanced 96 simulated hours
# through viewer _step_and_log telemetry with a blocking LLMGovernor.
PY
.venv/bin/python scripts/analyze_run.py logs/run-20260630-061901.jsonl --events
.venv/bin/python scripts/benchmark_scaling.py --pawns 100 500 1000 --steps 24 --context-repeats 8 --draw-frames 3
SDL_VIDEODRIVER=dummy .venv/bin/python - <<'PY'
# Rendered a fresh CivilizationViewer frame to docs/screenshots/current-state.png.
PY
git diff --check
```

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed under the existing Python 3.12.13 venv. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | `unittest discover -s tests` ran 255 tests. |
| Workbench/docs validation | pass | `validate-workbench.ps1` passed under available PowerShell. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Pygame viewer boot | pass | `CivilizationViewer` booted, drew frames, stepped once, and wrote viewer telemetry. |
| 4-day LM-governed run | pass | 96 simulated hours completed through viewer `_step_and_log`. |
| Analyzer health | pass | `RESULT: GREEN`. |
| Scaling benchmark | pass | 100/500/1000 pawn benchmark completed. |
| Screenshot proof | pass | Fresh dummy-SDL frame rendered to `docs/screenshots/current-state.png`; tracked bytes were unchanged. |
| Diff hygiene | pass | `git diff --check` passed after this documentation proof. |

## Model Decision Evidence

- LLM client: enabled, model `google/gemma-4-e4b`, base URL `http://192.168.1.131:1234/v1`.
- Decision outcomes: 96 model-backed decisions.
- Dropped/fallback-covered hours: 0 of 96.
- Fallback-only run: no.
- Applied action histogram: `{'set_work_priority': 385}`.
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

## Operational Note

The first wrapper pass completed the 96-hour viewer run and printed a GREEN
summary, then exited non-zero while writing `VIEWER_PATH_FILE` because that
environment variable was not exported into the inline Python process. The
completed JSONL was present at `logs/run-20260630-061901.jsonl`; direct analyzer
verification on that file returned GREEN and is the source of the gate decision.

## Decision

Ready to merge into `main`.

No Apple Silicon-specific failure evidence was observed. The gate exercised install, smoke/build, full tests, docs validation, live LM Studio connectivity, Pygame viewer boot, the 4-day LM-governed viewer path, analyzer health, the branch-relevant scaling benchmark, and fresh visible-state screenshot proof.
