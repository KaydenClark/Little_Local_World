# 2026-07-03 Mac UI LM Gate

## Decision

**PASS WITH WARNINGS for LM governance; not clean GREEN.**

The visible Mac Pygame UI opened and ran against LM Studio with
`google/gemma-4-e4b`. The run was not fallback-only: the JSONL log contains
61 model-origin decision hours and 63 model-applied actions. The analyzer
returned `RESULT: AMBER` because of two early `good_stalled` warnings.

## Tested Target

- PR: #46, `codex/taskboard-pr-gates`
- Title: Mark taskboard PR gates
- Tested SHA: `2c299075344e69a43e76379c11d570e213e2aee0`
- Test checkout: `/tmp/little-local-world-pr46-2c29907`
- Main checkout status before test: dirty, so the PR head was tested in an
  isolated detached worktree to preserve unrelated local edits.

## LM Studio Preflight

- Endpoint: `http://192.168.1.131:1234/v1`
- Requested model: `google/gemma-4-e4b`
- `/v1/models`: reachable
- Requested model listed: yes

## Viewer Run

Command:

```bash
AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1 \
AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b \
AGENT_TOWN_LLM_TIMEOUT=20 \
AGENT_TOWN_LLM_MAX_TOKENS=320 \
.venv/bin/python -m agent_town --new-world
```

Notes:

- Used `--new-world` to avoid reading any prior local autosave.
- Visible run duration: about 11 minutes, from 06:18 to 06:29 local time.
- macOS blocked synthetic Esc via `osascript`, so the viewer was stopped by
  terminal interrupt after the end screenshot. The viewer shutdown path still
  wrote a `run_end` record, verified in the JSONL log.

## Visible Proof

- Start: `docs/proof/mac-ui-lm/2026-07-03-pr46-2c29907-start.png`
- Mid: `docs/proof/mac-ui-lm/2026-07-03-pr46-2c29907-mid.png`
- End: `docs/proof/mac-ui-lm/2026-07-03-pr46-2c29907-end.png`

UI observations:

- Start screenshot shows `Governor: Local model thinking`.
- Mid screenshot shows `Governor: Local model idle` and active exception stack.
- End screenshot shows `Governor: Local model idle`, stable population, and
  warning exceptions for low water/source depletion.

## Run Log And Analyzer

- Run log: `logs/run-20260703-061810.jsonl`
- Analyzer output: `docs/run_reports/2026-07-03-pr46-2c29907-analyzer-output.txt`

Analyzer summary:

```text
RESULT: AMBER
hours          : 1126
mood           : start 85.8 -> min 72.4 -> end 75.8 (down)
idle peak      : 3
breaks         : 0 (peak concurrent 0)
food depletions: 0   supply stalls: 2
LLM hours      : 1126 with a model in play (pipeline uptime 57%, dropped 0 = 0%)
model emissions: 61 hour(s) actually driven by the model
model applied  : {'place_building': 44, 'set_production_target': 1, 'set_research': 7, 'set_work_priority': 11}
applied actions: {'place_building': 55, 'set_production_target': 1, 'set_research': 8, 'set_work_priority': 11}
events         : {'building_completed': 70, 'good_stalled': 2}
```

Raw-count check:

- Total records: 2326
- Snapshots: 1126
- Decisions: 1126
- Events: 72
- Model-origin decisions: 61
- Fallback-origin decisions: 1065
- Dropped decisions: 0
- Invalid/dropped decisions: 0
- `run_end` present: yes

Warnings:

- Day 1 06:00: `Logs empty 12h - supply chain stalled`
- Day 1 06:00: `Planks empty 12h - supply chain stalled`

## Gate Result

Pass criteria status:

- UI visibly opened on the Mac: pass
- LM Studio endpoint reachable: pass
- Requested model available: pass
- Viewer ran against that model: pass
- At least one model-origin decision: pass, 61 model-origin decision hours
- Analyzer not RED: pass, `RESULT: AMBER`
- Screenshots and report saved: pass

Remaining gap:

- This is not warning-free GREEN. The analyzer reports AMBER from supply-stall
  warnings, so this should be treated as LM-governance proof with gameplay
  warnings rather than clean merge-readiness evidence.

Docs checked; no BLUEPRINT/RUNBOOK update needed because this run produced proof
artifacts only and did not change product behavior, architecture, setup, or
operations.
