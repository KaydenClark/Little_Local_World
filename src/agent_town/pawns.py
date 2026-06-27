"""Pawn needs, restoration, and the mental-break state machine. [Track B]

Pawns are autonomous and need-driven. Needs (rest, food, recreation) decay over
time and are restored by the right schedule block plus the right good/building.
When mood falls under the break threshold the pawn slacks, then wanders off the
job - surfaced to the governor as an exception.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in B1 and B3.
"""

from __future__ import annotations

from .core import Pawn

# Pawn.state values for the break machine.
STATE_IDLE = "idle"
STATE_WORKING = "working"
STATE_SLEEPING = "sleeping"
STATE_RECREATING = "recreating"
STATE_HAULING = "hauling"
STATE_SLACKING = "slacking"  # breaking: effective_work drops
STATE_WANDERING = "wandering"  # broken: left the job


def decay_needs(pawn: Pawn, dt: float) -> None:
    """Decay every tracked need toward 0.0 by ``dt`` worth of time (B1)."""
    raise NotImplementedError("decay_needs - Track B, milestone B1")


def restore_need(pawn: Pawn, need: str, amount: float) -> None:
    """Raise ``need`` toward 1.0 (clamped) (B1)."""
    raise NotImplementedError("restore_need - Track B, milestone B1")


def needs_satisfaction(pawn: Pawn) -> float:
    """Mean satisfaction across tracked needs, in [0, 1] (B1)."""
    raise NotImplementedError("needs_satisfaction - Track B, milestone B1")


def update_break_state(pawn: Pawn) -> None:
    """Advance idle -> slacking -> wandering based on mood vs threshold (B3)."""
    raise NotImplementedError("update_break_state - Track B, milestone B3")
