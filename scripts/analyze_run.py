"""Analyze a Local Agent Town JSONL run log.

Exit code is non-zero when the log contains a red health condition, so this can
be used as a post-run gate.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from agent_town import health  # noqa: E402


def read_records(path: Path) -> list[dict]:
    records = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise SystemExit(f"Invalid JSONL at line {line_no}: {exc}") from exc
    return records


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze a Local Agent Town run log.")
    parser.add_argument("log", type=Path, help="Path to a JSONL run log")
    args = parser.parse_args(argv)

    records = read_records(args.log)
    starts = [record for record in records if record.get("type") == "run_start"]
    snapshots = [record for record in records if record.get("type") == "snapshot"]
    decisions = [record for record in records if record.get("type") == "decision"]
    events = [record for record in records if record.get("type") == "event"]
    summary = health.health_summary(snapshots, decisions, events)
    red = health.red_conditions(summary)

    run_id = starts[0].get("run_id", "(unknown)") if starts else "(unknown)"
    print(f"Run: {run_id}")
    if starts:
        print(f"Governor: {starts[0].get('governor_kind', '')} model={starts[0].get('model', '')}")
    print(f"Snapshots: {len(snapshots)}  Decisions: {len(decisions)}  Events: {len(events)}")
    print(
        "Mood: "
        f"start={summary['mood_start']:.1f} min={summary['mood_min']:.1f} "
        f"end={summary['mood_end']:.1f} trend={summary['mood_trend']}"
    )
    print(
        "Operations: "
        f"idle_peak={summary['idle_peak']} breaks={summary['break_count']} "
        f"llm_uptime={summary['llm_uptime_pct']:.1f}% "
        f"dropped={summary['dropped_decision_count']} ({summary['dropped_decision_rate']:.0%})"
    )
    if summary["action_kind_histogram"]:
        actions = ", ".join(f"{kind}={count}" for kind, count in summary["action_kind_histogram"].items())
        print(f"Actions: {actions}")

    flagged = [event for event in events if event.get("severity") in ("warn", "critical")]
    if flagged:
        print("Flagged events:")
        for event in flagged[:20]:
            print(
                f"- D{event.get('day', '?')} {event.get('hour', '?')}:00 "
                f"{str(event.get('severity', '')).upper()} {event.get('kind', '')}: {event.get('text', '')}"
            )

    if red:
        print("RED: " + "; ".join(red))
        return 1
    print("GREEN: no red health conditions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
