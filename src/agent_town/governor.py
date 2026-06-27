"""Governor context, exception queue, and the rule-based fallback. [Track B]

The governor sets policy only - it never moves pawns tick by tick. It reads a
compact context (faction summary + roster summary + exception queue), and emits
``GovernorAction``s that are validated against state before they mutate it.

Two governors share one ``decide(context) -> list[GovernorAction]`` interface:
``FallbackGovernor`` (deterministic greedy matcher, also the test oracle) and
the later ``LLMGovernor`` (llm.py), which falls back to it on any error.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone B4.
"""

from __future__ import annotations

from typing import Any, Protocol

from .core import ColonyException, FactionState, GovernorAction


class Governor(Protocol):
    """Anything that turns a context dict into a list of policy actions."""

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]: ...


def build_faction_summary(state: FactionState) -> dict[str, Any]:
    """Population, avg mood, stockpile levels, coin, day/season, tax_rate (B4)."""
    raise NotImplementedError("build_faction_summary - Track B, milestone B4")


def build_roster_summary(state: FactionState) -> list[dict[str, Any]]:
    """Pawns grouped by assignment, standout skills/traits only (B4)."""
    raise NotImplementedError("build_roster_summary - Track B, milestone B4")


def build_exception_queue(state: FactionState) -> list[ColonyException]:
    """The only per-pawn detail: unhappy/idle/mismatched/unstaffed/etc (B3/B4)."""
    raise NotImplementedError("build_exception_queue - Track B, milestone B3/B4")


def build_context(state: FactionState) -> dict[str, Any]:
    """Assemble summary + roster + exception queue for a governor (B4)."""
    raise NotImplementedError("build_context - Track B, milestone B4")


def validate_action(state: FactionState, action: GovernorAction) -> bool:
    """Whether ``action`` is legal against the current state (B4)."""
    raise NotImplementedError("validate_action - Track B, milestone B4")


def apply_actions(state: FactionState, actions: list[GovernorAction]) -> list[GovernorAction]:
    """Validate then apply each action; return the ones that took effect (B4)."""
    raise NotImplementedError("apply_actions - Track B, milestone B4")


class FallbackGovernor:
    """Deterministic greedy governor: best-skill slot, sane schedule, next link.

    Also the integration oracle - if a town survives N days under it, the
    economy is winnable.
    """

    def decide(self, context: dict[str, Any]) -> list[GovernorAction]:
        raise NotImplementedError("FallbackGovernor.decide - Track B, milestone B4")
