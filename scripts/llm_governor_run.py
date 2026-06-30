"""Manual proof for the LLM governor (integration milestone I2).

Runs the seeded civilization under ``LLMGovernor`` backed by the local model
(LM Studio / Ollama via ``LocalLLMClient.from_env``), writing a structured JSONL
run log plus the civilization's survival summary. Needs a running local
OpenAI-compatible endpoint; it is NOT part of the headless test suite.

With no endpoint the LLM client stays disabled and the governor hard-falls back
to the deterministic ``FallbackGovernor`` - so this script also runs offline and
simply demonstrates the safety net.

Usage:
    .\\.venv\\Scripts\\python.exe scripts\\llm_governor_run.py --hours 24
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agent_town import civilization, economy, engine, governor, telemetry  # noqa: E402
from agent_town.core import Good  # noqa: E402
from agent_town.llm import LocalLLMClient  # noqa: E402
from agent_town.pawns import STATE_WANDERING  # noqa: E402


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the civilization under the LLM governor.")
    parser.add_argument("--hours", type=int, default=24, help="simulated hours to run")
    parser.add_argument("--log", type=Path, default=None, help="JSONL run-log path")
    args = parser.parse_args(argv)

    client = LocalLLMClient.from_env()
    print(f"LLM enabled={client.enabled} model={client.model!r} base_url={client.base_url}")
    if not client.enabled:
        print("No local model discovered; LLMGovernor hard-falls back to the deterministic governor.\n")

    state = civilization.create_default_civilization()
    gov = telemetry.TelemetryGovernor(governor.LLMGovernor(client=client))
    log_path = args.log or telemetry.default_log_path()
    logger = telemetry.RunLogger(telemetry.JsonlFileSink(log_path))
    logger.log_run_start(
        state,
        governor_kind="LLMGovernor",
        model=client.model,
        config={"hours": max(0, args.hours), "base_url": client.base_url},
    )

    for _ in range(max(0, args.hours)):
        result = engine.step_hour(state, gov)
        logger.log_hour(state, result, gov)
        kinds = ", ".join(action.kind for action in gov.last_actions) or "(none)"
        print(f"  {state.time_of_day:>2}:00  decide -> {kinds}")

    logger.log_run_end(state)
    logger.close()
    counts = state.stockpile.counts
    wandering = sum(1 for pawn in state.pawns.values() if pawn.state == STATE_WANDERING)
    print(
        f"\nAfter {args.hours}h (day {state.day}): coin={state.coin} "
        f"mood={economy.average_mood(state):.0f} wandering={wandering} "
        f"bread={counts.get(Good.BREAD, 0)} planks={counts.get(Good.PLANKS, 0)} "
        f"stone={counts.get(Good.STONE, 0)}"
    )
    print(f"Run log: {log_path}")


if __name__ == "__main__":
    main()
