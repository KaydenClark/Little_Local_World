"""Pawn needs, restoration, and the mental-break state machine. [Track B]

Pawns are autonomous and need-driven. Needs (rest, food, recreation) decay over
time and are restored by the right schedule block plus the right good/building.
When mood falls under the break threshold the pawn slacks, then wanders off the
job - surfaced to the governor as an exception.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in B1 and B3.
"""

from __future__ import annotations

from .core import (
    BUILD1_NEEDS,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    SCHEDULE_ANY,
    SCHEDULE_BLOCK_KINDS,
    SCHEDULE_REC,
    SCHEDULE_SLEEP,
)

# Pawn.state values for the break machine.
STATE_IDLE = "idle"
STATE_WORKING = "working"
STATE_SLEEPING = "sleeping"
STATE_RECREATING = "recreating"
STATE_HAULING = "hauling"
STATE_SLACKING = "slacking"  # breaking: effective_work drops
STATE_WANDERING = "wandering"  # broken: left the job

NEED_DECAY_PER_HOUR: dict[str, float] = {
    NEED_REST: 0.035,
    NEED_FOOD: 0.045,
    NEED_RECREATION: 0.025,
}

SCHEDULE_RESTORATION_PER_HOUR: dict[str, dict[str, float]] = {
    SCHEDULE_SLEEP: {NEED_REST: 0.14},
    SCHEDULE_REC: {NEED_RECREATION: 0.16},
    SCHEDULE_ANY: {NEED_FOOD: 0.12, NEED_RECREATION: 0.03},
}

# Mood thresholds for the break state machine (B3). Canonical home; mood.py and
# governor.py read these so there is one source of truth.
BREAK_THRESHOLD = 0.25  # below this a pawn slacks (effective_work drops)
HARD_BREAK_THRESHOLD = 0.12  # below this a pawn wanders off the job


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _validate_non_negative(value: float, name: str) -> None:
    if value < 0:
        raise ValueError(f"{name} must be non-negative")


def _ensure_build1_needs(pawn: Pawn) -> None:
    for need in BUILD1_NEEDS:
        pawn.needs[need] = _clamp01(pawn.needs.get(need, 1.0))


def decay_needs(pawn: Pawn, dt: float) -> None:
    """Decay every tracked need toward 0.0 by ``dt`` worth of time (B1)."""
    _validate_non_negative(dt, "dt")
    _ensure_build1_needs(pawn)
    for need in BUILD1_NEEDS:
        decay = NEED_DECAY_PER_HOUR[need] * dt
        pawn.needs[need] = _clamp01(pawn.needs[need] - decay)


def restore_need(pawn: Pawn, need: str, amount: float) -> None:
    """Raise ``need`` toward 1.0 (clamped) (B1)."""
    if need not in BUILD1_NEEDS:
        raise ValueError(f"unknown build-1 need: {need!r}")
    _validate_non_negative(amount, "amount")
    _ensure_build1_needs(pawn)
    pawn.needs[need] = _clamp01(pawn.needs[need] + amount)


def needs_satisfaction(pawn: Pawn) -> float:
    """Mean satisfaction across tracked needs, in [0, 1] (B1)."""
    _ensure_build1_needs(pawn)
    return sum(pawn.needs[need] for need in BUILD1_NEEDS) / len(BUILD1_NEEDS)


def apply_schedule_block(pawn: Pawn, block: str, dt: float) -> None:
    """Restore needs that match a schedule block for ``dt`` hours (B1)."""
    if block not in SCHEDULE_BLOCK_KINDS:
        raise ValueError(f"unknown schedule block: {block!r}")
    _validate_non_negative(dt, "dt")
    _ensure_build1_needs(pawn)
    for need, rate in SCHEDULE_RESTORATION_PER_HOUR.get(block, {}).items():
        restore_need(pawn, need, rate * dt)


def update_break_state(pawn: Pawn) -> None:
    """Advance idle -> slacking -> wandering based on mood vs threshold (B3).

    Reads ``pawn.mood`` (set the mood with ``mood.compute_mood`` first). A pawn
    that recovers above the break threshold returns to idle from a broken state;
    deliberate working/sleeping/recreating states are left untouched.
    """
    if pawn.mood < HARD_BREAK_THRESHOLD:
        pawn.state = STATE_WANDERING
    elif pawn.mood < BREAK_THRESHOLD:
        pawn.state = STATE_SLACKING
    elif pawn.state in (STATE_SLACKING, STATE_WANDERING):
        pawn.state = STATE_IDLE
