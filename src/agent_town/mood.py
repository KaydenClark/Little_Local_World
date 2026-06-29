"""Mood and the effective-work seam. [Track B]

Home of ``effective_work`` - the single function where Track A (production) and
Track B (people) meet. Production multiplies a building's base rate by the sum
of ``effective_work`` over its staffed pawns:

    effective_work = skill_factor * trait_factor * schedule_factor * hunger_factor * break_factor

``schedule_factor`` is 0 when the pawn's current hour is not a work block, and
``break_factor`` pauses productive work during a break.

Mood is the RimWorld model on a **0-100 scale**: ``mood_target`` is the base mood
plus the sum of active :class:`Thought` values, and the displayed ``pawn.mood``
drifts toward the target each hour (see :func:`drift_mood`). Build-1 thoughts are
hunger (from the food saturation reserve), a blended rest+rec thought, and the
trait/want contributions. Event thoughts (e.g. Catharsis) live in
``pawn.thoughts`` and are summed in too.
"""

from __future__ import annotations

from . import pawns, schedule
from .core import (
    NEED_FOOD,
    NEED_RECREATION,
    NEED_REST,
    Pawn,
    Recipe,
    SCHEDULE_WORK,
    Thought,
)

# Mood runs on a 0-100 scale (RimWorld 1:1).
MOOD_MIN = 0.0
MOOD_MAX = 100.0
BASE_MOOD = 55.0  # storyteller/difficulty baseline before thoughts (RimWorld ~42-55)

# Two-layer mood: the displayed mood chases mood_target, rising faster than it
# falls, so one bad event does not instabreak a pawn but sustained misery does.
MOOD_DRIFT_UP = 12.0
MOOD_DRIFT_DOWN = 8.0

# effective_work sub-factor tuning. Skills are assumed in RimWorld's 0-20 range.
SKILL_BASE = 0.5
SKILL_PER_LEVEL = 0.05
SKILL_FACTOR_FLOOR = 0.4
TRAIT_WORK = {"industrious": 1.15, "lazy": 0.85}

# Thought point values on the 0-100 mood scale (RimWorld 1:1).
TRAIT_MOOD = {"optimist": 8.0, "pessimist": -8.0, "tough": 4.0, "frail": -4.0}
WANT_MET_BONUS = 5.0
WANT_UNMET_DRAG = -2.0
REST_REC_SWING = 40.0  # blended rest+rec thought spans [-20, +20] around 0.5

# Hunger thought, read off the food saturation reserve (1.0 == full nutrition).
HUNGER_FED_BAND = 0.24  # >= this: Fed, no thought
HUNGER_RAVENOUS_BAND = 0.12  # below this (and > 0): Ravenously hungry
HUNGER_HUNGRY_VALUE = -6.0
HUNGER_RAVENOUS_VALUE = -12.0
HUNGER_MALNOURISHED_VALUE = -20.0


def _clamp_mood(value: float) -> float:
    return max(MOOD_MIN, min(MOOD_MAX, value))


def skill_factor(skill_level: int) -> float:
    """Work multiplier from the pawn's skill in the recipe's skill (B2)."""
    return max(SKILL_FACTOR_FLOOR, SKILL_BASE + SKILL_PER_LEVEL * skill_level)


def mood_factor(mood: float) -> float:
    """Neutral compatibility hook: vanilla mood has no generic work-speed boost."""
    return 1.0


def trait_factor(traits: tuple[str, ...], recipe: Recipe) -> float:
    """Work multiplier from traits relative to the recipe (e.g. industrious) (B2)."""
    factor = 1.0
    for trait in traits:
        factor *= TRAIT_WORK.get(trait, 1.0)
    return factor


def schedule_factor(schedule_name: str, time_of_day: int) -> float:
    """1.0 during a work block, 0.0 otherwise (B2)."""
    return 1.0 if schedule.block_for(schedule_name, time_of_day) == SCHEDULE_WORK else 0.0


def hunger_productivity_factor(pawn: Pawn) -> float:
    """Direct work multiplier from hunger state."""
    food = pawn.needs.get(NEED_FOOD, 1.0)
    if food <= 0.0:
        return 0.0
    if food < HUNGER_RAVENOUS_BAND:
        return 0.25
    if food < HUNGER_FED_BAND:
        return 0.5
    return 1.0


def break_factor(pawn: Pawn) -> float:
    """Break states pause productive work until the pawn recovers."""
    if pawn.state in (pawns.STATE_SLACKING, pawns.STATE_WANDERING):
        return 0.0
    return 1.0


def effective_work(pawn: Pawn, recipe: Recipe, time_of_day: int) -> float:
    """The frozen cross-track seam: how much work a staffed pawn contributes.

    Signature is contract - do not change it without a one-file PR that both
    tracks rebase on.
    """
    level = pawn.skills.get(recipe.skill, 0)
    return (
        skill_factor(level)
        * trait_factor(pawn.traits, recipe)
        * schedule_factor(pawn.schedule, time_of_day)
        * hunger_productivity_factor(pawn)
        * break_factor(pawn)
    )


# --- The mood ledger -------------------------------------------------------


def hunger_thought(pawn: Pawn) -> Thought | None:
    """The single hunger thought from the food saturation reserve, or None when Fed."""
    food = pawn.needs.get(NEED_FOOD, 1.0)
    if food >= HUNGER_FED_BAND:
        return None
    if food <= 0.0:
        return Thought("hunger", "Malnourished", HUNGER_MALNOURISHED_VALUE)
    if food < HUNGER_RAVENOUS_BAND:
        return Thought("hunger", "Ravenously hungry", HUNGER_RAVENOUS_VALUE)
    return Thought("hunger", "Hungry", HUNGER_HUNGRY_VALUE)


def rest_rec_thought(pawn: Pawn) -> Thought:
    """A blended rest+recreation thought (food is its own thought now)."""
    rest = pawn.needs.get(NEED_REST, 1.0)
    rec = pawn.needs.get(NEED_RECREATION, 1.0)
    value = (((rest + rec) / 2.0) - 0.5) * REST_REC_SWING
    return Thought("needs", "Rested & recreated", round(value, 2))


def trait_thoughts(pawn: Pawn) -> list[Thought]:
    """Mood thoughts from mood-affecting traits (optimist, pessimist, ...)."""
    return [
        Thought("trait", trait, TRAIT_MOOD[trait])
        for trait in pawn.traits
        if trait in TRAIT_MOOD
    ]


def want_thoughts(pawn: Pawn, met_wants: frozenset[str]) -> list[Thought]:
    """A thought per want: a boost when met, a slow drag when ignored."""
    thoughts: list[Thought] = []
    for want in pawn.wants:
        if want in met_wants:
            thoughts.append(Thought("want", f"{want} (met)", WANT_MET_BONUS))
        else:
            thoughts.append(Thought("want", f"{want} (unmet)", WANT_UNMET_DRAG))
    return thoughts


def situational_thoughts(pawn: Pawn, met_wants: frozenset[str] = frozenset()) -> list[Thought]:
    """Thoughts derived from the pawn's current state (recomputed each tick)."""
    thoughts: list[Thought] = []
    hunger = hunger_thought(pawn)
    if hunger is not None:
        thoughts.append(hunger)
    thoughts.append(rest_rec_thought(pawn))
    thoughts.extend(trait_thoughts(pawn))
    thoughts.extend(want_thoughts(pawn, met_wants))
    return thoughts


def current_thoughts(pawn: Pawn, met_wants: frozenset[str] = frozenset()) -> list[Thought]:
    """Every active thought: situational ones plus persistent event thoughts."""
    return situational_thoughts(pawn, met_wants) + list(pawn.thoughts)


def mood_target(pawn: Pawn, met_wants: frozenset[str] = frozenset()) -> float:
    """The mood the pawn is heading toward: base + sum of active thoughts (0-100).

    Stacked event thoughts (e.g. Catharsis felt twice) contribute ``value * stack``;
    situational thoughts always have ``stack == 1``.
    """
    total = BASE_MOOD + sum(t.value * t.stack for t in current_thoughts(pawn, met_wants))
    return _clamp_mood(total)


def drift_mood(actual: float, target: float, asleep: bool = False) -> float:
    """Move ``actual`` mood one hour toward ``target`` (+12 up / -8 down), frozen asleep."""
    if asleep:
        return _clamp_mood(actual)
    if target > actual:
        return _clamp_mood(actual + min(MOOD_DRIFT_UP, target - actual))
    return _clamp_mood(actual - min(MOOD_DRIFT_DOWN, actual - target))
