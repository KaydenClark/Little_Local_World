from __future__ import annotations

from .core import FactionState


def advance_economy(state: FactionState, dt: float) -> None:
    raise NotImplementedError("Economy ticks are implemented in Track A2")
