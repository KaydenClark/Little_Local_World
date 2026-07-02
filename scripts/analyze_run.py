"""Turn a JSONL run-log into a health report (and a pass/fail exit code).

Reads a log written by ``llm_governor_run.py`` or the viewer, prints run
metadata, the aggregate health summary, and the flagged events, then exits
non-zero if the run hit any red condition (invariant violation, food-staple
depletion, mood collapse, or a high LLM dropped-decision rate). That makes it
usable both for eyeballing a run and as a post-run gate.

A log with no ``run_end`` record (an interrupted run) is summarized anyway over
the completed hourly records and flagged as incomplete, rather than failing.

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
    end = next((r for r in records if r.get("type") == "run_end"), None)
    snapshots = [r for r in records if r.get("type") == "snapshot"]
    decisions = [r for r in records if r.get("type") == "decision"]
    events = [r for r in records if r.get("type") == "event"]
    # Prefer the log's self-contained summary; recompute for interrupted runs.
    summary = end.get("summary") if end else None
    if summary is None:
        summary = health.health_summary(snapshots, decisions, events)
    # Always recompute model-efficacy from the raw decisions (review E-4 / Slice
    # D): embedded summaries from older schemas predate the pipeline-vs-efficacy
    # split, and a stale summary must not hand out a GREEN the records don't earn.
    summary = {**summary, **health.model_efficacy(decisions)}
    flagged = [e for e in events if e.get("severity") in (health.WARN, health.CRITICAL)]

    print(f"Run log: {path}")
    print(f"  run_id={start.get('run_id', '(unknown)')} schema={start.get('schema', '?')}")
    if start:
        print(f"  governor={start.get('governor')} model={start.get('model') or '(none)'} "
              f"seed={start.get('seed')} population={start.get('population')} started={start.get('wall')}")
    if end is None:
        print("  ! incomplete run (no run_end record) - summarizing completed hours")

    print("\nHealth summary:")
    print(f"  hours          : {summary['hours']}")
    print(f"  mood           : start {summary['mood_start']} -> min {summary['mood_min']} -> "
          f"end {summary['mood_end']} ({summary['mood_trend']})")
    print(f"  idle peak      : {summary['idle_peak']}")
    print(f"  breaks         : {summary['breaks']} (peak concurrent {summary['break_peak']})")
    print(f"  food depletions: {summary['depletions']}   supply stalls: {summary['stalls']}")
    print(f"  LLM hours      : {summary['llm_decisions']} with a model in play "
          f"(pipeline uptime {summary['llm_uptime']:.0%}, "
          f"dropped {summary['llm_dropped']} = {summary['llm_dropped_rate']:.0%})")
    print(f"  model emissions: {summary['model_decisions']} hour(s) actually driven by the model")
    print(f"  model applied  : {summary['model_actions'] or '(none)'}")
    print(f"  applied actions: {summary['actions'] or '(none)'} (all sources incl. fallback)")
    print(f"  events         : {summary['event_counts'] or '(none)'}")

    if args.events and flagged:
        print("\nFlagged events:")
        for event in flagged:
            print(f"  [{event['severity'].upper():8}] day{event['day']} {event['hour']:>2}:00  "
                  f"{event['kind']}: {event.get('text', '')}")

    problems = health.run_problems(summary)
    cautions = health.run_cautions(summary)
    color = health.run_color(summary).upper()
    print(f"\nRESULT: {color}")
    for problem in problems:
        print(f"  - {problem}")
    if not problems:
        for caution in cautions:
            print(f"  - {caution}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
