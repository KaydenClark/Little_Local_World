"""Mood and the effective-work seam. [Track B]

Home of ``effective_work`` - the single function where Track A (production) and
Track B (people) meet. Production multiplies a building's base rate by the sum
of ``effective_work`` over its staffed pawns:

    effective_work = skill_factor * mood_factor * trait_factor * schedule_factor

``schedule_factor`` is 0 when the pawn's current hour is not a work block, so an
off-shift or broken pawn contributes nothing.

B2 lands the real formula; B1/B3 own ``compute_mood`` (base mood from needs plus
trait and want modifiers).
"""

from __future__ import annotations

from . import schedule
from .core import Pawn, Recipe, SCHEDULE_WORK
from .pawns import needs_satisfaction

BASE_MOOD = 0.2
NEEDS_MOOD_WEIGHT = 0.7

# effective_work sub-factor tuning. Skills are assumed in RimWorld's 0-20 range.
SKILL_BASE = 0.5
SKILL_PER_LEVEL = 0.05
SKILL_FACTOR_FLOOR = 0.4
MOOD_BONUS_SLOPE = 0.4  # mood above 0.5 grants up to +20% work at mood 1.0
TRAIT_WORK = {"industrious": 1.15, "lazy": 0.85}

# compute_mood modifiers (B3). A met want lifts mood; an ignored want drags it.
TRAIT_MOOD = {"optimist": 0.08, "pessimist": -0.08, "tough": 0.04, "frail": -0.04}
WANT_MET_BONUS = 0.05
WANT_UNMET_DRAG = -0.02


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def skill_factor(skill_level: int) -> float:
    """Work multiplier from the pawn's skill in the recipe's skill (B2)."""
    return max(SKILL_FACTOR_FLOOR, SKILL_BASE + SKILL_PER_LEVEL * skill_level)


def mood_factor(mood: float) -> float:
    """Work multiplier from current mood (B2). Neutral mood 0.5 maps to 1.0."""
    if mood >= 0.5:
        return 1.0 + (mood - 0.5) * MOOD_BONUS_SLOPE
    return max(0.1, mood / 0.5)


def trait_factor(traits: tuple[str, ...], recipe: Recipe) -> float:
    """Work multiplier from traits relative to the recipe (e.g. industrious) (B2)."""
    factor = 1.0
    for trait in traits:
        factor *= TRAIT_WORK.get(trait, 1.0)
    return factor


def schedule_factor(schedule_name: str, time_of_day: int) -> float:
    """1.0 during a work block, 0.0 otherwise (B2)."""
    return 1.0 if schedule.block_for(schedule_name, time_of_day) == SCHEDULE_WORK else 0.0


def effective_work(pawn: Pawn, recipe: Recipe, time_of_day: int) -> float:
    """The frozen cross-track seam: how much work a staffed pawn contributes.

    Signature is contract - do not change it without a one-file PR that both
    tracks rebase on.
    """
    level = pawn.skills.get(recipe.skill, 0)
    return (
        skill_factor(level)
        * mood_factor(pawn.mood)
        * trait_factor(pawn.traits, recipe)
        * schedule_factor(pawn.schedule, time_of_day)
    )


def trait_mood_modifier(traits: tuple[str, ...]) -> float:
    """Mood floor/ceiling contribution from traits (optimist, pessimist, ...)."""
    return sum(TRAIT_MOOD.get(trait, 0.0) for trait in traits)


def want_mood_modifier(wants: tuple[str, ...], met_wants: frozenset[str]) -> float:
    """Mood contribution from wants: a boost when met, a slow drag when ignored."""
    total = 0.0
    for want in wants:
        total += WANT_MET_BONUS if want in met_wants else WANT_UNMET_DRAG
    return total


def compute_mood(pawn: Pawn, met_wants: frozenset[str] = frozenset()) -> float:
    """base + needs_satisfaction + trait_modifiers + want_progress (B1/B3).

    ``met_wants`` is the set of the pawn's wants currently satisfied, supplied by
    the caller that has the world context (a pawn alone cannot tell whether, say,
    ``wants_outdoor_work`` is met). Defaults to none met.
    """
    mood = BASE_MOOD + NEEDS_MOOD_WEIGHT * needs_satisfaction(pawn)
    mood += trait_mood_modifier(pawn.traits)
    mood += want_mood_modifier(pawn.wants, met_wants)
    return _clamp01(mood)
