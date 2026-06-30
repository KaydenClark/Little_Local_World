"""Manual proof + run-log generator for the LLM governor (integration I2).

Runs the seeded civilization under ``LLMGovernor`` backed by the local model
(LM Studio / Ollama via ``LocalLLMClient.from_env``) and writes our own
structured JSONL run log (per-hour snapshot, governor decision, anomaly events)
so the run can be verified afterwards with ``scripts/analyze_run.py``. Needs a
running local OpenAI-compatible endpoint; it is NOT part of the headless test
suite.

With no endpoint the LLM client stays disabled and the governor hard-falls back
to the deterministic ``FallbackGovernor`` - so this script also runs offline and
simply demonstrates the safety net (and still produces a clean log).

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\llm_governor_run.py --hours 24
    .\\.venv\\Scripts\\python.exe scripts\\analyze_run.py logs\\run-*.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_town import civilization, engine, governor, health, telemetry  # noqa: E402
from agent_town.llm import LocalLLMClient  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the civilization under the LLM governor and log it.")
    parser.add_argument("--hours", type=int, default=24, help="simulated hours to run")
    parser.add_argument("--log", type=str, default=None, help="JSONL run-log path (default logs/run-<stamp>.jsonl)")
    parser.add_argument("--no-log", action="store_true", help="do not write a run-log file")
    args = parser.parse_args(argv)

    client = LocalLLMClient.from_env()
    print(f"LLM enabled={client.enabled} model={client.model!r} base_url={client.base_url}")
    if not client.enabled:
        print("No local model discovered; LLMGovernor hard-falls back to the deterministic governor.\n")

    state = civilization.create_default_civilization()
    gov = telemetry.TelemetryGovernor(governor.LLMGovernor(client=client))

    # Keep all records in memory for the end-of-run summary; also stream to a file.
    memory = telemetry.RingBufferSink(maxlen=100_000)
    sinks: list = [memory]
    log_path: Path | None = None
    if not args.no_log:
        log_path = Path(args.log) if args.log else telemetry.default_run_log_path()
        sinks.append(telemetry.JsonlFileSink(log_path))
        print(f"Run log -> {log_path}\n")
    logger = telemetry.RunLogger(telemetry.MultiSink(sinks))

    logger.log_run_start(state, gov, hours=args.hours, max_tokens=client.max_tokens)
    for _ in range(max(0, args.hours)):
        result = engine.step_hour(state, gov)
        _snap, decision, events = logger.log_hour(state, result, gov)
        flag = (health.max_severity(events) or "").upper()[:4]
        applied = ", ".join(decision["applied"]) or "(none)"
        drop = " DROPPED" if decision.get("dropped") else ""
        print(f"  day{state.day} {state.time_of_day:>2}:00  applied -> {applied}{drop}  {flag}")

    summary = health.health_summary(list(memory.records))
    logger.log_run_end(state, summary)
    logger.close()

    print(
        f"\nAfter {args.hours}h (day {state.day}): coin={state.coin} "
        f"mood={summary['mood_end']:.0f} (min {summary['mood_min']:.0f}) "
        f"idle_peak={summary['idle_peak']} breaks={summary['breaks']} "
        f"llm_dropped={summary['llm_dropped']}/{summary['llm_decisions']}"
    )
    problems = health.run_problems(summary)
    print("HEALTH: OK" if not problems else "HEALTH: PROBLEMS -> " + "; ".join(problems))


if __name__ == "__main__":
    main()
