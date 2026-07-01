# PR #29 Mac LM Gate - 2026-06-30

## Scope

- PR: #29, `codex/district-service-pressure`
- Title: Add Market service pressure signal
- Tested SHA: `5da495fc73e5eac7e097e3baaa6524bd4382ee3a`
- Gate host: Apple Silicon Mac mini
- Time: 2026-06-30 07:19 -06:00
- LM Studio endpoint: `http://192.168.1.131:1234/v1`
- Preferred model: `google/gemma-4-e4b`
- Detailed local log: `logs/run-20260630-071917-pr29.log`
- Viewer JSONL: `logs/run-20260630-071922.jsonl`

## Commands

```bash
.venv/bin/python -m pip install -e .
.venv/bin/python -m agent_town --smoke-test
.venv/bin/python -m unittest discover -s tests
pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/validate-workbench.ps1
GET http://192.168.1.131:1234/v1/models
AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1 \
AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b \
AGENT_TOWN_LLM_TIMEOUT=30 \
AGENT_TOWN_LLM_MAX_TOKENS=400 \
SDL_VIDEODRIVER=dummy \
.venv/bin/python - <<'PY'
# Instantiated CivilizationViewer, drew frames, and advanced 96 simulated hours
# through viewer _step_and_log telemetry with a blocking LLMGovernor.
PY
.venv/bin/python scripts/analyze_run.py logs/run-20260630-071922.jsonl --events
git diff --check
```

## Results

| Gate | Result | Evidence |
| --- | --- | --- |
| Install | pass | Editable install completed under the existing Python 3.12.13 venv. |
| Smoke/build | pass | `python -m agent_town --smoke-test` exited 0. |
| Unit suite | pass | `unittest discover -s tests` ran 260 tests. |
| Workbench/docs validation | pass | `validate-workbench.ps1` passed under available PowerShell. |
| LM Studio ping | pass | `/v1/models` returned `google/gemma-4-e4b`. |
| Pygame viewer boot | pass | `CivilizationViewer` booted, drew frames, and wrote viewer telemetry. |
| 4-day LM-governed run | pass | 96 simulated hours completed through viewer `_step_and_log`. |
| Analyzer health | pass | `RESULT: GREEN`. |
| Optional expanded checks | skipped | PR #29 changes economy/telemetry/governor observer state, not scale/pathfinding/performance or direct visible UI assets. |
| Diff hygiene | pass | `git diff --check` passed after this documentation proof. |

## Model Decision Evidence

- LLM client: enabled, model `google/gemma-4-e4b`, base URL `http://192.168.1.131:1234/v1`.
- Decision outcomes: 96 model-backed decisions.
- Dropped/fallback-covered hours: 0 of 96.
- Fallback-only run: no.
- Applied action histogram: `{'set_work_priority': 388}`.
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

## Operational Note

The shell wrapper's post-run summary helper failed after the 96th simulated hour
because it read `Stockpile.amounts`; this branch exposes the stockpile through
log snapshots and `Stockpile.counts`. The viewer JSONL already contained all 96
hours and a completed `run_end` record from `CivilizationViewer` shutdown, and
the direct analyzer pass on that JSONL returned GREEN. Those completed artifacts
are the source of the gate decision.

## Decision

Ready to merge into `main`.

No Apple Silicon-specific failure evidence was observed. The gate exercised install, smoke/build, full tests, docs validation, live LM Studio connectivity, Pygame viewer boot, the 4-day LM-governed viewer path, analyzer health, and branch-relevant model-decision evidence.
