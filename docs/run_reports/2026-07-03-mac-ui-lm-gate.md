# 2026-07-03 Mac UI LM Gate

## Result

PASS WITH WARNINGS, not clean GREEN.

The visible Mac UI opened, LM Studio was reachable, `google/gemma-4-e4b` was
available, and the run log shows model-origin decisions. The analyzer returned
`RESULT: AMBER` because of 4 warning events, so this is valid LM-governance proof
but not warning-free health evidence.

## Tested Target

- PR: #46 `codex/taskboard-pr-gates`
- PR URL: https://github.com/KaydenClark/Little_Local_World/pull/46
- Tested SHA: `f83a52bc41d129eb388a07d98143344e34d4d70c`
- Commit: `Record AFK queue gate recheck`
- Test checkout: `/private/tmp/llw-mac-ui-lm-pr46-20260703-f83a52b`
- Main checkout note: `/Users/kayden/GPT_OS/Projects/Little_Local_World` had
  unrelated dirty files, including source and harness-adoption docs, so the PR
  head was tested in an isolated detached checkout to avoid overwriting or
  stashing user work.

## LM Studio

- Endpoint: `http://192.168.1.131:1234/v1`
- Model requested: `google/gemma-4-e4b`
- `/v1/models`: reachable; requested model listed.
- Viewer environment:
  - `AGENT_TOWN_LLM_BASE_URL=http://192.168.1.131:1234/v1`
  - `AGENT_TOWN_LLM_MODEL=google/gemma-4-e4b`
  - `AGENT_TOWN_LLM_TIMEOUT=20`
  - `AGENT_TOWN_LLM_MAX_TOKENS=320`

## Visible UI Proof

- Start: `docs/proof/mac-ui-lm/2026-07-03-pr46-f83a52b-start.png`
- Mid: `docs/proof/mac-ui-lm/2026-07-03-pr46-f83a52b-mid.png`
- End: `docs/proof/mac-ui-lm/2026-07-03-pr46-f83a52b-end.png`

Observed HUD states:

- Start, 8:17 AM: `Governor: Local model thinking`.
- Mid, 8:22 AM: `Governor: Local model idle`.
- End, 8:28 AM: `Governor: Local model idle`.

Screenshot note: the screenshots are full-desktop captures. A System Settings
window is visible behind the Pygame window, but the Pygame window, Governor HUD,
exception stack, map, and inspector are readable in all three artifacts.

## Run Log And Analyzer

- Run log: `logs/run-20260703-081716-pr46-f83a52b.jsonl`
- Analyzer output:
  `docs/run_reports/2026-07-03-pr46-f83a52b-analyzer-output.txt`
- Started: `2026-07-03T08:17:16-0600`
- Visible screenshot window: about 11 minutes, 8:17 AM to 8:28 AM.
- Stop method: terminal interrupt after final screenshot; viewer cleanup still
  wrote a `run_end` record.
- Simulated hours: 1120.
- Analyzer result: `AMBER`.

Analyzer summary:

- Mood: `85.8 -> min 72.4 -> end 75.8` (`down`)
- Idle peak: 3
- Breaks: 0
- Food depletions: 0
- Supply stalls: 4
- LLM/model hours: 1120 with model configured; pipeline uptime 57%
- Model emissions: 61 hours actually driven by model output
- Fallback-origin decisions: 1059
- Dropped/invalid decisions: 0
- Model-applied actions: `place_building=41`, `set_research=4`,
  `set_work_priority=36`
- All applied actions: `place_building=52`, `set_research=5`,
  `set_work_priority=36`
- Events: `building_completed=64`, `good_stalled=4`

Warnings:

- Day 1 06:00: logs empty 12h.
- Day 1 06:00: planks empty 12h.
- Day 26 07:00: planks empty 12h.
- Day 33 06:00: planks empty 12h.

## Decision

The LM gate passes with warnings under this run's criteria:

- UI visibly opened on the Mac: yes.
- LM Studio endpoint was reachable: yes.
- Requested model was available: yes.
- Viewer ran with the requested model environment: yes.
- At least one hour was model-origin, not fallback-only: yes, 61 model-emission
  hours.
- Analyzer was not RED: yes, AMBER.
- Screenshots and report were saved: yes.

Remaining gap: this is not clean GREEN because the analyzer found 4
`good_stalled` warnings: initial logs/planks stalls and later planks stalls on
days 26 and 33. It should not be described as warning-free or fully clean
merge-readiness evidence.
