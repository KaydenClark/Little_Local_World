"""Schedule templates and the day clock. [Track B]

Defines named 24-hour schedules (which hours are work / sleep / rec / any) and
advances the colony clock, rolling ``time_of_day`` over into a new ``day``.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone B1.
"""

from __future__ import annotations

from .core import FactionState, ScheduleTemplate

HOURS_PER_DAY = 24

# Populated in B1: at least "default", "night" (for night-owl pawns), "rest".
SCHEDULE_TEMPLATES: dict[str, ScheduleTemplate] = {}


def template(name: str) -> ScheduleTemplate:
    """Look up a schedule template by name (falls back to the default)."""
    raise NotImplementedError("template - Track B, milestone B1")


def block_for(schedule_name: str, hour: int) -> str:
    """The schedule block kind for ``schedule_name`` at ``hour`` (0-23)."""
    raise NotImplementedError("block_for - Track B, milestone B1")


def advance_clock(state: FactionState, hours: int = 1) -> int:
    """Advance ``time_of_day`` by ``hours``; return the number of new days rolled."""
    raise NotImplementedError("advance_clock - Track B, milestone B1")
