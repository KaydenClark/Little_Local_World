from __future__ import annotations

from .core import ScheduleTemplate


def default_schedule_templates() -> tuple[ScheduleTemplate, ...]:
    raise NotImplementedError("Schedule templates are implemented in Track B1")
