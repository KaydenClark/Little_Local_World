# Gemma 4 E4B Partial-Week Governor Run

Date: 2026-06-29  
Branch: `codex/run-log-monitoring-week-proof`  
Endpoint: `http://192.168.1.131:1234/v1`  
Model: `google/gemma-4-e4b`  
Raw log: `logs/week-proof-2026-06-29-gemma-4-e4b.jsonl` (ignored local artifact)

## Result

This was started as a 168-hour in-game week proof and stopped by operator request
after enough evidence had accumulated. The run completed 133 simulated hours
(day 5, hour 20), so it is a partial-week proof, not a full-week pass.

Analyzer result: **RED**.

Reason: bread depleted at day 2, hour 7. The analyzer correctly treated that as
a critical good-depletion condition.

## Summary

| Metric | Value |
|---|---:|
| Completed simulated hours | 133 |
| Last sim time | Day 5, 20:00 |
| Snapshots | 133 |
| Decisions | 133 |
| Events | 16 |
| Applied LLM actions | 89 `set_work_priority` |
| Dropped decisions | 0 |
| LLM uptime | 100% |
| Latency range | 2.6984s to 4.0120s |
| Average latency | 3.8447s |
| Mood start / min / end | 85.8 / 52.4 / 56.4 |
| Food need start / min / end | 0.955 / 0.0 / 0.0 |
| Final coin | 97 |
| Final idle pawns | 1 |
| Final broken pawns | 0 |
| Final stockpile | grain 10 |

## Analyzer Output

```text
Run: b96e6555-03ac-4ca5-84e2-f83a31519c37
Governor: LLMGovernor model=google/gemma-4-e4b
Snapshots: 133  Decisions: 133  Events: 16
Mood: start=85.8 min=52.4 end=56.4 trend=down
Operations: idle_peak=1 breaks=0 llm_uptime=100.0% dropped=0 (0%)
Actions: set_work_priority=89
Flagged events:
- D0 9:00 WARN good_depleted: grain depleted
- D0 11:00 WARN good_depleted: flour depleted
- D0 11:00 WARN good_depleted: grain depleted
- D0 14:00 WARN good_depleted: grain depleted
- D0 16:00 WARN good_depleted: flour depleted
- D0 16:00 WARN good_depleted: grain depleted
- D0 18:00 WARN good_depleted: grain depleted
- D1 9:00 WARN good_depleted: flour depleted
- D1 9:00 WARN good_depleted: grain depleted
- D1 11:00 WARN good_depleted: grain depleted
- D1 14:00 WARN good_depleted: flour depleted
- D1 14:00 WARN good_depleted: grain depleted
- D1 16:00 WARN good_depleted: grain depleted
- D1 18:00 WARN good_depleted: flour depleted
- D1 18:00 WARN good_depleted: grain depleted
- D2 7:00 CRITICAL good_depleted: bread depleted
RED: critical good depleted
```

## Interpretation

- The PC-hosted model endpoint is reachable from the Mac and usable by the
  headless runner.
- The logging/analyzer stack handled a long live-model run and correctly surfaced
  the food failure instead of hiding it behind a passing command.
- The governor actively changed work priorities, but those policy changes did
  not prevent the build-1 food chain from running out of bread.
- No dropped decisions or invariant violations appeared in this partial run.
- The run log was interrupted by request, so there is no `run_end` record; the
  analyzer still works over completed hourly records.

## Follow-Up

- Treat food-chain recovery as a gameplay/governor issue, not a telemetry issue.
- The next food-focused proof should run after adding either stronger food-chain
  urgency, better production targets, or the planned water/economy slice if that
  changes priorities.
- Keep the analyzer red on critical bread depletion; this is the correct gate for
  proving a week-long autonomous run is healthy.
