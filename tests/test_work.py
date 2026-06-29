"""Lane-based work-priority arbiter: priorities, reservations, lanes, trace."""

import unittest

from agent_town import buildings, pawns, work
from agent_town.core import FactionState, JobRef, Pawn


def _pawn(pid, skills=None, **kw):
    base = dict(
        id=pid,
        name=pid.upper(),
        skills=skills or {},
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=80.0,
        schedule="default",
    )
    base.update(kw)
    return Pawn(**base)


def _state(time_of_day=8, *, buildings_spec=(), pawn_list=()):
    state = FactionState(time_of_day=time_of_day)
    for bid, kind, x, y in buildings_spec:
        state.buildings[bid] = buildings.make_building(kind, x, y, building_id=bid)
    for pawn in pawn_list:
        state.pawns[pawn.id] = pawn
    return state


class PriorityTests(unittest.TestCase):
    def test_default_priority_derives_from_skill(self):
        p = _pawn("p", {"farming": 19, "baking": 5, "mining": 2, "milling": 0})
        self.assertEqual(work.default_priority(p, "farming"), 1)  # >=10
        self.assertEqual(work.default_priority(p, "baking"), 2)  # >=4
        self.assertEqual(work.default_priority(p, "mining"), 3)  # >=1
        self.assertEqual(work.default_priority(p, "milling"), 4)  # unskilled

    def test_explicit_priority_overrides_skill_including_disable(self):
        p = _pawn("p", {"farming": 19})
        work.set_priority(p, "farming", 0)
        self.assertEqual(work.default_priority(p, "farming"), 0)  # disabled wins over skill

    def test_set_priority_validates_range(self):
        p = _pawn("p")
        with self.assertRaises(ValueError):
            work.set_priority(p, "farming", 5)
        with self.assertRaises(ValueError):
            work.set_priority(p, "", 1)


class SelectionTests(unittest.TestCase):
    def test_manual_priority_beats_work_type_natural_order(self):
        # Farming has the higher natural order, but baking@1 must beat farming@4.
        p = _pawn("p", {"farming": 20, "baking": 20})
        work.set_priority(p, "baking", 1)
        work.set_priority(p, "farming", 4)
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0), ("bake1", "Bakery", 1, 0)), pawn_list=[p])

        work.assign_jobs(state)

        self.assertEqual(p.assignment, JobRef("bake1", "baking"))

    def test_skill_default_routes_specialist_to_its_building(self):
        farmer = _pawn("p", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0), ("bake1", "Bakery", 1, 0)), pawn_list=[farmer])

        work.assign_jobs(state)

        self.assertEqual(farmer.assignment.building_id, "farm1")

    def test_disabled_work_type_is_rejected_not_rescued_by_skill(self):
        p = _pawn("p", {"farming": 20})
        work.set_priority(p, "farming", 0)
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[p])

        work.assign_jobs(state)

        self.assertIsNone(p.assignment)
        self.assertEqual(state.work_decisions["p"].lane, work.LANE_IDLE)

    def test_building_without_recipe_is_never_work(self):
        from agent_town.core import Building

        p = _pawn("p", {"farming": 20})
        state = _state(pawn_list=[p])
        state.buildings["house1"] = Building(id="house1", kind="House", x=0, y=0, recipe=None, job_slots=2)

        work.assign_jobs(state)

        self.assertIsNone(p.assignment)


class ReservationTests(unittest.TestCase):
    def test_two_pawns_never_claim_the_same_single_slot(self):
        a = _pawn("p0", {"farming": 20})
        b = _pawn("p1", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[a, b])

        work.assign_jobs(state)

        seated = [pid for pid in ("p0", "p1") if state.pawns[pid].assignment is not None]
        self.assertEqual(seated, ["p0"])  # lower id wins the single slot
        self.assertEqual(state.buildings["farm1"].staffed_by, ["p0"])
        self.assertEqual(state.work_decisions["p1"].lane, work.LANE_IDLE)
        self.assertTrue(any(r.reason == "reserved/full" for r in state.work_decisions["p1"].rejected))

    def test_kept_assignment_is_reserved_against_new_claimers(self):
        a = _pawn("p0", {"farming": 20}, assignment=JobRef("farm1", "farming"))
        b = _pawn("p1", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[a, b])
        state.buildings["farm1"].staffed_by.append("p0")

        work.assign_jobs(state)

        self.assertEqual(state.pawns["p0"].assignment, JobRef("farm1", "farming"))
        self.assertIsNone(state.pawns["p1"].assignment)


class LaneTests(unittest.TestCase):
    def test_broken_pawn_releases_slot_to_a_healthy_pawn(self):
        broken = _pawn("p0", {"farming": 20}, assignment=JobRef("farm1", "farming"), state=pawns.STATE_WANDERING)
        healthy = _pawn("p1", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[broken, healthy])
        state.buildings["farm1"].staffed_by.append("p0")

        work.assign_jobs(state)

        self.assertIsNone(broken.assignment)
        self.assertEqual(state.work_decisions["p0"].lane, work.LANE_HARD_STATE)
        self.assertEqual(healthy.assignment, JobRef("farm1", "farming"))
        self.assertEqual(state.buildings["farm1"].staffed_by, ["p1"])

    def test_hungry_pawn_keeps_job_but_lane_flips_to_self_care(self):
        p = _pawn("p", {"farming": 20}, assignment=JobRef("farm1", "farming"))
        p.needs["food"] = 0.2  # below the eat threshold
        state = _state(time_of_day=8, buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[p])
        state.buildings["farm1"].staffed_by.append("p")

        work.assign_jobs(state)

        decision = state.work_decisions["p"]
        self.assertEqual(decision.lane, work.LANE_SELF_CARE)
        self.assertEqual(decision.building_id, "farm1")  # standing job retained
        self.assertEqual(p.assignment, JobRef("farm1", "farming"))

    def test_forced_assignment_pins_pawn_across_replans(self):
        forced = JobRef("farm1", "farming")
        p = _pawn("p", {"baking": 20}, assignment=forced, forced_assignment=forced)
        state = _state(
            buildings_spec=(("farm1", "Farm", 0, 0), ("bake1", "Bakery", 1, 0)), pawn_list=[p]
        )
        state.buildings["farm1"].staffed_by.append("p")

        work.assign_jobs(state)
        work.assign_jobs(state)  # second replan must not move the forced pawn

        self.assertEqual(p.assignment, forced)
        self.assertEqual(state.work_decisions["p"].lane, work.LANE_FORCED)

    def test_disabling_a_work_type_releases_a_working_pawn(self):
        p = _pawn("p", {"farming": 20}, assignment=JobRef("farm1", "farming"))
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[p])
        state.buildings["farm1"].staffed_by.append("p")

        work.set_priority(p, "farming", 0)
        work.assign_jobs(state)

        self.assertIsNone(p.assignment)
        self.assertEqual(state.buildings["farm1"].staffed_by, [])
        self.assertEqual(state.work_decisions["p"].lane, work.LANE_IDLE)


class TraceTests(unittest.TestCase):
    def test_decision_explains_winner_and_top_rejection(self):
        p = _pawn("p", {"farming": 20})
        state = _state(
            buildings_spec=(("farm1", "Farm", 0, 0), ("bake1", "Bakery", 5, 0)), pawn_list=[p]
        )

        work.assign_jobs(state)

        decision = state.work_decisions["p"]
        self.assertEqual(decision.lane, work.LANE_NORMAL_WORK)
        self.assertEqual(decision.building_id, "farm1")
        self.assertIn("farming", decision.reason)
        self.assertTrue(decision.rejected)  # the Bakery it passed over, with a reason
        self.assertEqual(decision.rejected[0].building_id, "bake1")
        self.assertTrue(decision.rejected[0].reason)

    def test_explain_shows_what_a_settled_pawn_passes_over(self):
        # The per-hour stored decision stays cheap (no roster-wide reject scan);
        # work.explain computes the rejected alternatives on demand for the one
        # inspected pawn so the inspector can say "why here, not there".
        p = _pawn("p", {"farming": 20}, assignment=JobRef("farm1", "farming"))
        state = _state(
            buildings_spec=(("farm1", "Farm", 0, 0), ("bake1", "Bakery", 5, 0)), pawn_list=[p]
        )
        state.buildings["farm1"].staffed_by.append("p")
        work.assign_jobs(state)

        # Cheap stored decision: lane + reason, no roster-wide reject scan.
        self.assertEqual(state.work_decisions["p"].lane, work.LANE_NORMAL_WORK)
        self.assertEqual(state.work_decisions["p"].rejected, [])

        # On-demand explanation carries the rejected alternatives.
        detail = work.explain(state, "p")
        self.assertEqual(detail.building_id, "farm1")
        self.assertTrue(any(r.building_id == "bake1" for r in detail.rejected))

    def test_explain_tells_an_idle_pawn_why(self):
        a = _pawn("p0", {"farming": 20})
        b = _pawn("p1", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[a, b])
        work.assign_jobs(state)  # p0 seated, p1 idle

        detail = work.explain(state, "p1")
        self.assertEqual(detail.lane, work.LANE_IDLE)
        self.assertTrue(any(r.reason == "reserved/full" for r in detail.rejected))


class StabilityTests(unittest.TestCase):
    def test_legal_assignment_is_kept_no_thrash(self):
        p = _pawn("p", {"farming": 20})
        state = _state(buildings_spec=(("farm1", "Farm", 0, 0),), pawn_list=[p])

        work.assign_jobs(state)
        first = p.assignment
        work.assign_jobs(state)

        self.assertEqual(p.assignment, first)
        self.assertEqual(state.buildings["farm1"].staffed_by, ["p"])

    def test_assign_jobs_is_deterministic(self):
        def fresh():
            ps = [_pawn(f"p{i}", {"farming": 20}) for i in range(3)]
            return _state(
                buildings_spec=(("farm1", "Farm", 0, 0), ("farm2", "Farm", 2, 0)), pawn_list=ps
            )

        first, second = fresh(), fresh()
        work.assign_jobs(first)
        work.assign_jobs(second)

        self.assertEqual(
            {pid: (p.assignment.building_id if p.assignment else None) for pid, p in first.pawns.items()},
            {pid: (p.assignment.building_id if p.assignment else None) for pid, p in second.pawns.items()},
        )
        self.assertEqual(
            {pid: d.lane for pid, d in first.work_decisions.items()},
            {pid: d.lane for pid, d in second.work_decisions.items()},
        )


if __name__ == "__main__":
    unittest.main()
