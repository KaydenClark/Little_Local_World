from __future__ import annotations

from .core import Pawn, Recipe


def effective_work(pawn: Pawn, recipe: Recipe, time_of_day: int) -> float:
    raise NotImplementedError("effective_work is implemented in Track B2")
