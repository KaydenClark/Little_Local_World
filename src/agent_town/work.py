"""Lane-based work-priority arbiter with reservations. [Track B - Build 2]

This is the point where pawns stop being hourly counters the governor pins into
slots and start *choosing* their own work for understandable reasons. It is a
small, inspectable flattening of RimWorld's layered work logic (research_papers/
3.rimworld_autonomous-pawn-report.md), not a full think-tree clone.

Each engine hour :func:`assign_jobs` re-plans the roster:

1. release assignments that are now illegal or held by a mentally-broken pawn;
2. reserve the slots pawns are keeping so two pawns never claim the same job;
3. seat each pawn that needs work into its best *legal* job, chosen by a
   lexicographic key that mirrors RimWorld - manual priority first, then
   work-type natural order, then target urgency, distance, and finally skill
   fit. Skill never rescues an illegal, reserved, disabled, or lower-priority
   job;
4. record a :class:`~.core.WorkDecision` per pawn (winning lane + top rejected
   candidates) so the spectator can see *why* a pawn chose one job over another.

Decision lanes, in priority order: forced/manual -> hard-state -> medical-rest
-> self-care -> emergency -> normal-work -> idle. Build 1's economy only has
normal-work jobs (staffing a production building), so forced, hard-state,
self-care (hungry), normal-work, and idle are live; medical-rest and emergency
are defined for ordering but have no content until injuries/fires exist.

Work types in build 1 *are* the production skills already declared on recipes
(``Building.recipe.skill``): forestry, woodworking, farming, milling, baking,
mining. The governor or player tunes per-pawn priorities via
``set_work_priority``; with no override a pawn's priorities are derived from its
skill so a fresh civilization staffs itself sensibly with zero micro.
"""

from __future__ import annotations

from . import pawns, schedule
from .core import (
    Building,
    FactionState,
    JobRef,
    NEED_FOOD,
    Pawn,
    RejectedJob,
    SCHEDULE_SLEEP,
    WorkDecision,
    WORK_PRIORITY_DISABLED,
)

# --- Decision lanes (Paper 3), highest priority first -----------------------
LANE_FORCED = "forced"
LANE_HARD_STATE = "hard_state"
LANE_MEDICAL = "medical_rest"  # reserved for build 2 healthcare (no content yet)
LANE_SELF_CARE = "self_care"
LANE_EMERGENCY = "emergency"  # reserved for build 2 disasters (no content yet)
LANE_NORMAL_WORK = "normal_work"
LANE_IDLE = "idle"

LANE_ORDER = (
    LANE_FORCED,
    LANE_HARD_STATE,
    LANE_MEDICAL,
    LANE_SELF_CARE,
    LANE_EMERGENCY,
    LANE_NORMAL_WORK,
    LANE_IDLE,
)

# Work-type natural order: the left-to-right tiebreaker RimWorld applies when two
# work types share a manual priority (higher = earlier/preferred). Build-1 order
# is project-chosen (research-derived from the food-chain dependency, not a
# verified RimWorld constant) so the survival staple resolves ties first.
WORK_TYPE_ORDER: dict[str, int] = {
    "farming": 70,
    "milling": 65,
    "baking": 60,
    "forestry": 50,
    "woodworking": 45,
    "mining": 40,
}
DEFAULT_WORK_TYPE_ORDER = 30  # unknown work types sort after the known chain

# Skill thresholds for a pawn's *default* priority when the governor/player has
# set none. Mirrors RimWorld's "skilled pawns gravitate to their specialty"
# without forcing the governor to micro-manage every priority.
_DEFAULT_PRIORITY_BANDS = ((10, 1), (4, 2), (1, 3))
DERIVED_UNSKILLED_PRIORITY = 4

MAX_SKILL = 20  # RimWorld skill cap, used to normalise skill_fit
MAX_REJECTED = 4  # how many rejected candidates to keep in the decision trace


# --- Priorities --------------------------------------------------------------


def default_priority(pawn: Pawn, work_type: str) -> int:
    """The pawn's effective manual priority for ``work_type`` (0 = disabled).

    An explicit ``pawn.work_priorities`` entry always wins (including a deliberate
    ``0`` to disable). Otherwise the priority is derived from the pawn's skill so
    a civilization with no governor priorities still staffs itself by specialty.
    """
    explicit = pawn.work_priorities.get(work_type)
    if explicit is not None:
        return explicit
    level = pawn.skills.get(work_type, 0)
    for floor, priority in _DEFAULT_PRIORITY_BANDS:
        if level >= floor:
            return priority
    return DERIVED_UNSKILLED_PRIORITY


def set_priority(pawn: Pawn, work_type: str, level: int) -> None:
    """Set a pawn's manual priority for ``work_type`` (0..4; 0 disables it)."""
    if not isinstance(level, int) or isinstance(level, bool):
        raise TypeError("work priority level must be an int")
    if level < WORK_PRIORITY_DISABLED or level > 4:
        raise ValueError("work priority level must be in 0..4")
    if not work_type:
        raise ValueError("work_type is required")
    pawn.work_priorities[work_type] = level


def work_type_order(work_type: str) -> int:
    return WORK_TYPE_ORDER.get(work_type, DEFAULT_WORK_TYPE_ORDER)


def building_work_type(building: Building | None) -> str | None:
    """The work type a building offers (its recipe skill), or None if it has no work."""
    if building is None or building.recipe is None:
        return None
    return building.recipe.skill


def skill_fit(pawn: Pawn, work_type: str) -> int:
    return pawn.skills.get(work_type, 0)


def target_urgency(state: FactionState, building: Building) -> float:
    """How urgently this job wants doing (higher = sooner). Build-1 hook: flat.

    Reserved in the ranking tuple so build-2 can make a starved output chain or a
    spreading fire outrank a calm one without reshaping the arbiter.
    """
    return 0.0


def _distance(pawn: Pawn, building: Building) -> int:
    """Chebyshev tiles from the pawn to the building (matches diagonal movement)."""
    return max(abs(pawn.x - building.x), abs(pawn.y - building.y))


# --- Job selection (the normal-work lane) -----------------------------------


def _is_broken(pawn: Pawn) -> bool:
    return pawn.state in (pawns.STATE_SLACKING, pawns.STATE_WANDERING)


def _wants_self_care(state: FactionState, pawn: Pawn) -> bool:
    """Whether self-care (eating) outranks work for this waking hour.

    Build-1 self-care is a lane label: a hungry pawn's winning lane flips to
    self-care so the spectator sees it prioritising food. Eating is instantaneous
    (see ``pawns.eat``), so this does not yet cost a work hour - that arrives with
    build-2 building-based services.
    """
    if schedule.block_for(pawn.schedule, state.time_of_day) == SCHEDULE_SLEEP:
        return False
    return pawn.needs.get(NEED_FOOD, 1.0) < pawns.EAT_FOOD_THRESHOLD


def _live_lane(state: FactionState, pawn: Pawn, base_lane: str) -> str:
    """Promote a working pawn's lane to self-care when it is hungry this hour."""
    if base_lane in (LANE_FORCED, LANE_NORMAL_WORK) and _wants_self_care(state, pawn):
        return LANE_SELF_CARE
    return base_lane


def _rank_key(state: FactionState, pawn: Pawn, building: Building, work_type: str, priority: int):
    """Lexicographic ranking key (lower sorts first) mirroring RimWorld's order."""
    return (
        priority,  # manual priority: 1 beats 4
        -work_type_order(work_type),  # work-type natural order: higher first
        -target_urgency(state, building),  # urgency: higher first
        _distance(pawn, building),  # nearer first
        -skill_fit(pawn, work_type),  # more skilled first
        building.id,  # final deterministic tiebreak
    )


def _why_lost(state: FactionState, pawn: Pawn, winner, candidate) -> str:
    """A short reason a legal runner-up lost to the winning job."""
    _wb, w_wt, w_prio = winner
    cb, c_wt, c_prio = candidate
    if c_prio > w_prio:
        return f"lower priority ({c_prio} vs {w_prio})"
    if work_type_order(c_wt) < work_type_order(w_wt):
        return f"{c_wt} ranks below {w_wt}"
    if _distance(pawn, cb) > _distance(pawn, winner[0]):
        return "farther away"
    if skill_fit(pawn, c_wt) < skill_fit(pawn, w_wt):
        return "lower skill"
    return "tie-break by id"


def _scan_candidates(
    state: FactionState, pawn: Pawn, reserved: dict[str, int], *, exclude_id: str | None = None
) -> tuple[list[tuple[Building, str, int]], list[RejectedJob]]:
    """Split the pawn's possible jobs into ranked legal ones and rejected ones.

    ``reserved`` maps building_id -> intended occupancy this cycle (kept staff
    plus claims made so far), so a slot at capacity is rejected rather than
    double-claimed. ``exclude_id`` skips one building (the pawn's own job when
    explaining a kept assignment).
    """
    legal: list[tuple[Building, str, int]] = []
    illegal: list[RejectedJob] = []
    for building in sorted(state.buildings.values(), key=lambda b: b.id):
        if building.id == exclude_id or not building.built:
            continue
        work_type = building_work_type(building)
        if work_type is None:
            continue
        priority = default_priority(pawn, work_type)
        if priority <= WORK_PRIORITY_DISABLED:
            illegal.append(RejectedJob(building.id, work_type, "work disabled"))
            continue
        if reserved.get(building.id, 0) >= building.job_slots:
            illegal.append(RejectedJob(building.id, work_type, "reserved/full"))
            continue
        legal.append((building, work_type, priority))
    legal.sort(key=lambda c: _rank_key(state, pawn, c[0], c[1], c[2]))
    return legal, illegal


def select_job(
    state: FactionState, pawn: Pawn, reserved: dict[str, int]
) -> tuple[Building | None, str | None, list[RejectedJob]]:
    """Choose the pawn's best legal normal-work job, with the rejected trace.

    Returns the winning building and work type (or ``None`` when nothing is legal)
    and an ordered list of rejected candidates: legal runner-ups first (with the
    reason they lost), then illegal ones (disabled / reserved).
    """
    legal, illegal = _scan_candidates(state, pawn, reserved)
    if not legal:
        return None, None, illegal[:MAX_REJECTED]
    winner = legal[0]
    runner_ups = [RejectedJob(b.id, wt, _why_lost(state, pawn, winner, (b, wt, prio))) for b, wt, prio in legal[1:]]
    return winner[0], winner[1], (runner_ups + illegal)[:MAX_REJECTED]


def _kept_rejected(state: FactionState, pawn: Pawn, reserved: dict[str, int]) -> list[RejectedJob]:
    """The jobs a pawn holding an assignment is passing over, for the trace."""
    assignment = pawn.assignment
    if assignment is None:
        return []
    building = state.buildings.get(assignment.building_id)
    work_type = building_work_type(building) if building is not None else assignment.role
    winner = (building, work_type, default_priority(pawn, work_type) if work_type else 0)
    legal, illegal = _scan_candidates(state, pawn, reserved, exclude_id=assignment.building_id)
    runner_ups = [RejectedJob(b.id, wt, _why_lost(state, pawn, winner, (b, wt, prio))) for b, wt, prio in legal]
    return (runner_ups + illegal)[:MAX_REJECTED]


# --- The per-hour assignment pass -------------------------------------------


def _matches(assignment: JobRef | None, forced: JobRef) -> bool:
    return assignment is not None and assignment.building_id == forced.building_id


def _forced_building_ok(state: FactionState, pawn: Pawn) -> bool:
    forced = pawn.forced_assignment
    if forced is None:
        return False
    building = state.buildings.get(forced.building_id)
    return building is not None and building.built and building.recipe is not None


def _assignment_legal(state: FactionState, pawn: Pawn) -> bool:
    """Whether a pawn's current (non-forced) assignment is still valid to hold."""
    assignment = pawn.assignment
    if assignment is None:
        return False
    building = state.buildings.get(assignment.building_id)
    if building is None or not building.built or building.recipe is None:
        return False
    if pawn.id not in building.staffed_by:
        return False
    work_type = building_work_type(building)
    if work_type is None:
        return False
    # A work type the governor/player just disabled releases the pawn to replan.
    return default_priority(pawn, work_type) > WORK_PRIORITY_DISABLED


def _release(state: FactionState, pawn: Pawn) -> None:
    """Drop a pawn's assignment and free its building slot."""
    assignment = pawn.assignment
    if assignment is not None:
        building = state.buildings.get(assignment.building_id)
        if building is not None and pawn.id in building.staffed_by:
            building.staffed_by.remove(pawn.id)
    pawn.assignment = None


def _seat(state: FactionState, pawn: Pawn, building: Building, work_type: str, reserved: dict[str, int]) -> None:
    """Staff a pawn into a building and book the reservation for this cycle."""
    if pawn.id not in building.staffed_by:
        building.staffed_by.append(pawn.id)
    pawn.assignment = JobRef(building.id, work_type)
    reserved[building.id] = reserved.get(building.id, 0) + 1


def _winner_reason(pawn: Pawn, building: Building, work_type: str) -> str:
    return f"{work_type} priority {default_priority(pawn, work_type)}, skill {skill_fit(pawn, work_type)}"


def _kept_decision(state: FactionState, pawn: Pawn, reserved: dict[str, int]) -> WorkDecision:
    """The decision trace for a pawn that was not re-seated this cycle."""
    if _is_broken(pawn):
        return WorkDecision(LANE_HARD_STATE, None, None, f"Mental break ({pawn.state})")
    assignment = pawn.assignment
    if assignment is not None:
        building = state.buildings.get(assignment.building_id)
        work_type = building_work_type(building) if building is not None else assignment.role
        forced = pawn.forced_assignment is not None and _matches(assignment, pawn.forced_assignment)
        base_lane = LANE_FORCED if forced else LANE_NORMAL_WORK
        lane = _live_lane(state, pawn, base_lane)
        if lane == LANE_SELF_CARE:
            reason = "Hungry - eating before work"
        elif forced:
            reason = "Forced by governor"
        else:
            reason = _winner_reason(pawn, building, work_type) if work_type else "Holding work assignment"
        # The rejected trace (an O(buildings) scan) is computed lazily by
        # ``explain`` for the one inspected pawn, not for the whole roster here -
        # so the per-hour cost stays flat as the population grows.
        return WorkDecision(lane, assignment.building_id, work_type, reason)
    return WorkDecision(LANE_IDLE, None, None, "Idle")


def assign_jobs(state: FactionState) -> dict[str, WorkDecision]:
    """Re-plan the whole roster for one hour; return (and store) the decisions.

    Deterministic: pawns are processed in sorted-id order with no randomness, so
    the same state always produces the same assignments - the integration
    survival oracle and the LLM-vs-fallback equality proof both depend on it.
    """
    # Phase A: release assignments that are illegal now or held by broken pawns.
    for pawn in state.pawns.values():
        if pawn.assignment is None:
            continue
        if _is_broken(pawn):
            _release(state, pawn)
        elif pawn.forced_assignment is not None and _matches(pawn.assignment, pawn.forced_assignment):
            if not _forced_building_ok(state, pawn):
                _release(state, pawn)
                pawn.forced_assignment = None
        elif not _assignment_legal(state, pawn):
            _release(state, pawn)

    # Phase B: reserve the slots pawns are still holding.
    reserved: dict[str, int] = {}
    for pawn in state.pawns.values():
        if pawn.assignment is not None:
            reserved[pawn.assignment.building_id] = reserved.get(pawn.assignment.building_id, 0) + 1

    # Phase C: seat the pawns that need work, in deterministic order.
    decisions: dict[str, WorkDecision] = {}
    needers = sorted(
        (p for p in state.pawns.values() if not _is_broken(p) and p.assignment is None),
        key=lambda p: p.id,
    )
    for pawn in needers:
        building, work_type, rejected = select_job(state, pawn, reserved)
        if building is not None:
            _seat(state, pawn, building, work_type, reserved)
            decisions[pawn.id] = WorkDecision(
                _live_lane(state, pawn, LANE_NORMAL_WORK),
                building.id,
                work_type,
                _winner_reason(pawn, building, work_type),
                rejected,
            )
        else:
            decisions[pawn.id] = WorkDecision(LANE_IDLE, None, None, "No legal job available", rejected)

    # Phase D: record the decision trace for pawns kept or broken.
    for pawn in state.pawns.values():
        if pawn.id not in decisions:
            decisions[pawn.id] = _kept_decision(state, pawn, reserved)

    state.work_decisions = decisions
    return decisions


def _current_reservations(state: FactionState) -> dict[str, int]:
    reserved: dict[str, int] = {}
    for pawn in state.pawns.values():
        if pawn.assignment is not None:
            reserved[pawn.assignment.building_id] = reserved.get(pawn.assignment.building_id, 0) + 1
    return reserved


def explain(state: FactionState, pawn_id: str) -> WorkDecision | None:
    """A full decision trace (lane, reason, and rejected jobs) for one pawn.

    Recomputed on demand from current state - the viewer calls this only for the
    inspected pawn, so the expensive rejected scan never runs across the whole
    roster every hour. Returns ``None`` when the pawn is unknown.
    """
    pawn = state.pawns.get(pawn_id)
    if pawn is None:
        return None
    reserved = _current_reservations(state)
    if _is_broken(pawn):
        return WorkDecision(LANE_HARD_STATE, None, None, f"Mental break ({pawn.state})")
    if pawn.assignment is not None:
        decision = _kept_decision(state, pawn, reserved)
        decision.rejected = _kept_rejected(state, pawn, reserved)
        return decision
    # Idle pawn: explain what it would take, or why nothing is legal.
    building, work_type, rejected = select_job(state, pawn, reserved)
    if building is None:
        return WorkDecision(LANE_IDLE, None, None, "No legal job available", rejected)
    return WorkDecision(
        _live_lane(state, pawn, LANE_NORMAL_WORK),
        building.id,
        work_type,
        _winner_reason(pawn, building, work_type),
        rejected,
    )
