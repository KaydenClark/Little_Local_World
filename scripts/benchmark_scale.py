from __future__ import annotations

import argparse
from dataclasses import asdict
import json

from agent_town.benchmarks import run_rule_agent_benchmark


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Local Agent Town scale benchmarks.")
    parser.add_argument(
        "--agents",
        nargs="+",
        type=int,
        default=[100, 500, 1000],
        help="Agent counts to benchmark.",
    )
    parser.add_argument("--iterations", type=int, default=60, help="Simulation steps per benchmark.")
    parser.add_argument("--json", action="store_true", help="Emit JSON lines.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for count in args.agents:
        result = run_rule_agent_benchmark(count, iterations=args.iterations)
        if args.json:
            print(json.dumps(asdict(result), separators=(",", ":")))
        else:
            status = "PASS" if result.passed else "FAIL"
            print(
                f"{status} {result.name} agents={result.entity_count} "
                f"avg={result.average_ms:.3f}ms p95={result.p95_ms:.3f}ms "
                f"threshold={result.threshold_ms:.1f}ms bottleneck={result.bottleneck}"
            )


if __name__ == "__main__":
    main()
