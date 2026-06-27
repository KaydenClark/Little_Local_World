"""Schedule templates and the day clock. [Track B]

Defines named 24-hour schedules (which hours are work / sleep / rec / any) and
advances the colony clock, rolling ``time_of_day`` over into a new ``day``.

Phase 0 status: signatures frozen, bodies stubbed. Implemented in milestone B1.
"""

from __future__ import annotations

from .core import (
    FactionState,
    SCHEDULE_ANY,
    SCHEDULE_REC,
    SCHEDULE_SLEEP,
    SCHEDULE_WORK,
    ScheduleTemplate,
)

HOURS_PER_DAY = 24

# Build-1 schedules. Hours are local colony hours, 0-23.
SCHEDULE_TEMPLATES: dict[str, ScheduleTemplate] = {
    "default": ScheduleTemplate(
        "default",
        (
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_ANY,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_REC,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_ANY,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
        ),
    ),
    "night": ScheduleTemplate(
        "night",
        (
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_REC,
            SCHEDULE_ANY,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_ANY,
            SCHEDULE_REC,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
            SCHEDULE_WORK,
        ),
    ),
    "rest": ScheduleTemplate(
        "rest",
        (
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_ANY,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_REC,
            SCHEDULE_ANY,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
            SCHEDULE_SLEEP,
        ),
    ),
}


def template(name: str) -> ScheduleTemplate:
    """Look up a schedule template by name (falls back to the default)."""
    return SCHEDULE_TEMPLATES.get(name, SCHEDULE_TEMPLATES["default"])


def block_for(schedule_name: str, hour: int) -> str:
    """The schedule block kind for ``schedule_name`` at ``hour`` (0-23)."""
    return template(schedule_name).block_at(hour)


def advance_clock(state: FactionState, hours: int = 1) -> int:
    """Advance ``time_of_day`` by ``hours``; return the number of new days rolled."""
    if hours < 0:
        raise ValueError("hours must be non-negative")

    total_hours = state.time_of_day + hours
    rolled_days = total_hours // HOURS_PER_DAY
    state.time_of_day = total_hours % HOURS_PER_DAY
    state.day += rolled_days
    return rolled_days
