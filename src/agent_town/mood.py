"""Mood and the effective-work seam. [Track B]

Home of ``effective_work`` - the single function where Track A (production) and
Track B (people) meet. Production multiplies a building's base rate by the sum
of ``effective_work`` over its staffed pawns:

    effective_work = skill_factor * mood_factor * trait_factor * schedule_factor

``schedule_factor`` is 0 when the pawn's current hour is not a work block, so an
off-shift or broken pawn contributes nothing.

Phase 0 status: the seam returns a neutral placeholder so Track A can integrate
before Track B lands the real formula in B2; the sub-factors and ``compute_mood``
are honest stubs.
"""

from __future__ import annotations

from .core import Pawn, Recipe

# Mood below this and the pawn starts to break (B3).
BREAK_THRESHOLD = 0.25


def effective_work(pawn: Pawn, recipe: Recipe, time_of_day: int) -> float:
    """The frozen cross-track seam (signature is contract; see module docstring).

    Phase 0 placeholder: returns 1.0 so Track A's production is deterministic
    before Track B implements the real formula in milestone B2. Do not change
    the signature without a one-file PR both tracks rebase on.
    """
    return 1.0


def skill_factor(skill_level: int) -> float:
    """Work multiplier from the pawn's skill in the recipe's skill (B2)."""
    raise NotImplementedError("skill_factor - Track B, milestone B2")


def mood_factor(mood: float) -> float:
    """Work multiplier from current mood (B2)."""
    raise NotImplementedError("mood_factor - Track B, milestone B2")


def trait_factor(traits: tuple[str, ...], recipe: Recipe) -> float:
    """Work multiplier from traits relative to the recipe (e.g. industrious) (B2)."""
    raise NotImplementedError("trait_factor - Track B, milestone B2")


def schedule_factor(schedule_name: str, time_of_day: int) -> float:
    """1.0 during a work block, 0.0 otherwise (B2)."""
    raise NotImplementedError("schedule_factor - Track B, milestone B2")


def compute_mood(pawn: Pawn) -> float:
    """base + needs_satisfaction + trait_modifiers + want_progress (B1/B3)."""
    raise NotImplementedError("compute_mood - Track B, milestone B1/B3")
