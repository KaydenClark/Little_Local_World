"""Pawn needs, eating, and the mental-break state machine. [Track B]

Pawns are autonomous and need-driven. Rest and recreation decay over time and
are restored by the matching schedule block. Food is different: it is a
**nutrition/saturation reserve** (RimWorld-style) that only drains - the pawn
refills it by :func:`eat`-ing bread, never for free from a schedule block.

Mood (0-100) is computed in ``mood.py``; this module turns a low mood into a
mental break. The break uses three RimWorld-style bands (minor 35 / major 20 /
extreme 5) and fires on a seeded mean-time-between roll - sooner in worse bands -
so a dip does not instabreak a pawn. A pawn that rides a break out and recovers
banks a Catharsis thought.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in B1, B3, step 2.
"""

from __future__ import annotations

import math

from .core import (
    BUILD1_NEEDS,
    Good,
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    SCHEDULE_ANY,
    SCHEDULE_BLOCK_KINDS,
    SCHEDULE_REC,
    SCHEDULE_SLEEP,
    Stockpile,
    Thought,
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

# Food is no longer restored here - it is a nutrition reserve refilled only by
# eating bread (see ``eat``). This removal is the conservation fix: no civilization
# gets free food from merely being off-shift.
SCHEDULE_RESTORATION_PER_HOUR: dict[str, dict[str, float]] = {
    SCHEDULE_SLEEP: {NEED_REST: 0.14},
    SCHEDULE_REC: {NEED_RECREATION: 0.16},
    SCHEDULE_ANY: {NEED_RECREATION: 0.03},
}

# One loaf of bread is a simple meal worth this much nutrition (RimWorld 1:1).
BREAD_NUTRITION = 0.9

# Mental-break bands on the 0-100 mood scale (RimWorld 1:1). Each is the mood at
# or below which the pawn becomes *eligible* for that break; the break then fires
# on a mean-time-between roll. Canonical home; mood.py and governor.py read these.
BREAK_MINOR = 35.0  # eligible to slack (effective_work drops)
BREAK_MAJOR = 20.0  # eligible to wander off the job
BREAK_EXTREME = 5.0  # eligible to wander, and breaks fastest

# Mean time between breaks (hours) per band - lower mood breaks sooner.
MTB_MINOR = 10.0
MTB_MAJOR = 5.0
MTB_EXTREME = 2.0

# Per-trait offsets to the break thresholds. A negative offset lowers the bands
# (the pawn endures more before breaking); a positive offset raises them.
BREAK_TRAIT_OFFSET: dict[str, float] = {
    "tough": -6.0,
    "optimist": -4.0,
    "frail": 4.0,
    "pessimist": 4.0,
}

# Catharsis: the relief thought a pawn banks after riding out and recovering from
# a mental break (RimWorld-style).
CATHARSIS_VALUE = 12.0
CATHARSIS_DURATION = 8  # hours
MAX_THOUGHT_STACK = 3

# How bad a state is, so a break never downgrades to a milder one in the same tick.
_BREAK_SEVERITY: dict[str, int] = {STATE_SLACKING: 1, STATE_WANDERING: 2}


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


def eat(pawn: Pawn, stockpile: Stockpile) -> bool:
    """Consume one bread to refill the nutrition reserve, returning whether a meal happened.

    The pawn's food need *is* its saturation reserve (1.0 == full). A loaf adds
    :data:`BREAD_NUTRITION` and anything over the 1.0 cap is wasted (RimWorld
    overeating waste). Eats nothing and returns ``False`` when no bread is on hand.
    """
    if not stockpile.has(Good.BREAD, 1):
        return False
    stockpile.remove(Good.BREAD, 1)
    _ensure_build1_needs(pawn)
    pawn.needs[NEED_FOOD] = _clamp01(pawn.needs[NEED_FOOD] + BREAD_NUTRITION)
    return True


# --- Thought ledger (event thoughts; situational ones live in mood.py) -------


def add_thought(
    pawn: Pawn, kind: str, label: str, value: float, duration: int, *, max_stack: int = MAX_THOUGHT_STACK
) -> None:
    """Add an event thought, stacking onto an identical one and refreshing its age."""
    for thought in pawn.thoughts:
        if thought.kind == kind and thought.label == label:
            thought.stack = min(max_stack, thought.stack + 1)
            thought.age = 0
            return
    pawn.thoughts.append(Thought(kind, label, value, age=0, stack=1, duration=duration))


def add_catharsis(pawn: Pawn) -> None:
    """Bank the Catharsis relief thought after recovering from a mental break."""
    add_thought(pawn, "catharsis", "Catharsis", CATHARSIS_VALUE, CATHARSIS_DURATION)


def age_thoughts(pawn: Pawn) -> None:
    """Age every event thought one hour and drop the ones that have expired."""
    survivors = []
    for thought in pawn.thoughts:
        if thought.duration <= 0:
            survivors.append(thought)
            continue
        thought.age += 1
        if thought.age < thought.duration:
            survivors.append(thought)
    pawn.thoughts[:] = survivors


# --- Mental-break state machine (RimWorld bands + seeded MTB roll) -----------


def _severity(state: str) -> int:
    return _BREAK_SEVERITY.get(state, 0)


def break_thresholds(pawn: Pawn) -> tuple[float, float, float]:
    """The pawn's (minor, major, extreme) break thresholds after trait offsets."""
    offset = sum(BREAK_TRAIT_OFFSET.get(trait, 0.0) for trait in pawn.traits)
    return (BREAK_MINOR + offset, BREAK_MAJOR + offset, BREAK_EXTREME + offset)


def break_chance(mtb_hours: float) -> float:
    """Per-hour probability of a break from a mean-time-between value in hours."""
    if mtb_hours <= 0:
        return 1.0
    return 1.0 - math.exp(-1.0 / mtb_hours)


def advance_break_state(pawn: Pawn, roll: float) -> None:
    """Advance idle -> slacking -> wandering for one hour (step 2, RimWorld bands).

    ``roll`` is a uniform value in [0, 1); the engine derives it from the faction
    seed so runs are reproducible. While the pawn's mood sits in a break band it
    breaks on a mean-time-between roll (sooner in worse bands) rather than
    instantly. A pawn that climbs back above the minor band recovers to idle and
    banks a :func:`add_catharsis` thought; deliberate non-broken states only break
    *down*, never recover here.
    """
    minor, major, extreme = break_thresholds(pawn)
    mood = pawn.mood
    if mood < major:
        target, mtb = STATE_WANDERING, (MTB_EXTREME if mood < extreme else MTB_MAJOR)
    elif mood < minor:
        target, mtb = STATE_SLACKING, MTB_MINOR
    else:
        if pawn.state in (STATE_SLACKING, STATE_WANDERING):
            pawn.state = STATE_IDLE
            add_catharsis(pawn)
        return
    if _severity(pawn.state) >= _severity(target):
        return
    if roll < break_chance(mtb):
        pawn.state = target
