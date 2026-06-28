"""Manual proof for the LLM governor (integration milestone I2).

Runs the seeded colony under ``LLMGovernor`` backed by the local model
(LM Studio / Ollama via ``LocalLLMClient.from_env``), logging the governor's
actions each hour and the colony's survival. Needs a running local
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

from agent_town import colony, economy, engine, governor  # noqa: E402
from agent_town.core import Good  # noqa: E402
from agent_town.llm import LocalLLMClient  # noqa: E402
from agent_town.pawns import STATE_WANDERING  # noqa: E402


class _LoggingGovernor:
    """Wraps a governor to print the actions it decides each hour."""

    def __init__(self, inner) -> None:
        self.inner = inner

    def decide(self, context):
        actions = self.inner.decide(context)
        kinds = ", ".join(a.kind for a in actions) or "(none)"
        hour = context.get("faction", {}).get("time_of_day", "?")
        print(f"  {hour:>2}:00  decide -> {kinds}")
        return actions


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the colony under the LLM governor.")
    parser.add_argument("--hours", type=int, default=24, help="simulated hours to run")
    args = parser.parse_args(argv)

    client = LocalLLMClient.from_env()
    print(f"LLM enabled={client.enabled} model={client.model!r} base_url={client.base_url}")
    if not client.enabled:
        print("No local model discovered; LLMGovernor hard-falls back to the deterministic governor.\n")

    state = colony.create_default_colony()
    gov = _LoggingGovernor(governor.LLMGovernor(client=client))

    for _ in range(max(0, args.hours)):
        engine.step_hour(state, gov)

    counts = state.stockpile.counts
    wandering = sum(1 for pawn in state.pawns.values() if pawn.state == STATE_WANDERING)
    print(
        f"\nAfter {args.hours}h (day {state.day}): coin={state.coin} "
        f"mood={economy.average_mood(state):.0%} wandering={wandering} "
        f"bread={counts.get(Good.BREAD, 0)} planks={counts.get(Good.PLANKS, 0)} "
        f"stone={counts.get(Good.STONE, 0)}"
    )


if __name__ == "__main__":
    main()
