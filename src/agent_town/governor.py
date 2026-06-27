from __future__ import annotations

from dataclasses import dataclass

from .core import Exception, FactionState, GovernorAction


@dataclass(frozen=True)
class GovernorContext:
    faction_summary: dict[str, object]
    roster_summary: dict[str, object]
    exception_queue: tuple[Exception, ...]


def build_context(state: FactionState) -> GovernorContext:
    raise NotImplementedError("Governor context is implemented in Track B4")


class FallbackGovernor:
    def decide(self, context: GovernorContext) -> list[GovernorAction]:
        raise NotImplementedError("Fallback governor decisions are implemented in Track B4")
