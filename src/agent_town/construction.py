from __future__ import annotations

from .core import ConstructionSite, FactionState


def advance_construction(state: FactionState, site: ConstructionSite, dt: float) -> None:
    raise NotImplementedError("Construction flow is implemented in Track A3")
