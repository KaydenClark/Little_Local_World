"""Turn a JSONL run-log into a health report (and a pass/fail exit code).

Reads a log written by ``llm_governor_run.py`` or the viewer, prints run
metadata, the aggregate health summary, and the flagged events, then exits
non-zero if the run hit any red condition (invariant violation, food-staple
depletion, mood collapse, or a high LLM dropped-decision rate). That makes it
usable both for eyeballing a run and as a post-run gate.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\analyze_run.py logs\\run-20260629-192141.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_town import health  # noqa: E402


def load_records(path: Path) -> list[dict]:
    records: list[dict] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"  ! skipped unparseable line {line_no}", file=sys.stderr)
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a Local Agent Town run log.")
    parser.add_argument("path", type=str, help="path to a JSONL run log")
    parser.add_argument("--events", action="store_true", help="list every warn/critical event")
    args = parser.parse_args(argv)

    path = Path(args.path)
    if not path.exists():
        print(f"No such log: {path}", file=sys.stderr)
        return 2

    records = load_records(path)
    start = next((r for r in records if r.get("type") == "run_start"), {})
    summary = health.health_summary(records)
    events = [r for r in records if r.get("type") == "event"]
    flagged = [e for e in events if e.get("severity") in (health.WARN, health.CRITICAL)]

    print(f"Run log: {path}")
    if start:
        print(f"  governor={start.get('governor')} seed={start.get('seed')} "
              f"population={start.get('population')} started={start.get('wall')}")
    print("\nHealth summary:")
    print(f"  hours          : {summary['hours']}")
    print(f"  mood           : start {summary['mood_start']} -> min {summary['mood_min']} -> end {summary['mood_end']}")
    print(f"  idle peak      : {summary['idle_peak']}")
    print(f"  breaks         : {summary['breaks']}")
    print(f"  food depletions: {summary['depletions']}")
    print(f"  LLM decisions  : {summary['llm_decisions']} (uptime {summary['llm_uptime']:.0%}, "
          f"dropped {summary['llm_dropped']} = {summary['llm_dropped_rate']:.0%})")
    print(f"  applied actions: {summary['actions'] or '(none)'}")
    print(f"  events         : {summary['event_counts'] or '(none)'}")

    if args.events and flagged:
        print("\nFlagged events:")
        for event in flagged:
            print(f"  [{event['severity'].upper():8}] day{event['day']} {event['hour']:>2}:00  "
                  f"{event['kind']}: {event.get('text', '')}")

    problems = health.run_problems(summary)
    if problems:
        print("\nRESULT: PROBLEMS")
        for problem in problems:
            print(f"  - {problem}")
        return 1
    print("\nRESULT: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
