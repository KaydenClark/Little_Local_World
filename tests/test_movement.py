"""Pawn activity state and sim-level movement (commute to work, walk home)."""

import unittest

from agent_town import buildings, civilization, engine, pawns
from agent_town.core import FactionState, JobRef, Pawn


def _commuter(**kw):
    base = dict(
        id="p",
        name="P",
        skills={"farming": 18},
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=80.0,
        schedule="default",
        home_x=0,
        home_y=10,
        x=0,
        y=10,
    )
    base.update(kw)
    return Pawn(**base)


def _farm_state(time_of_day):
    state = FactionState(day=0, time_of_day=time_of_day)
    farm = buildings.make_building("Farm", 8, 2, building_id="farm1")
    state.buildings[farm.id] = farm
    pawn = _commuter(assignment=JobRef("farm1", "farming"))
    farm.staffed_by.append(pawn.id)
    state.pawns[pawn.id] = pawn
    return state, pawn


class ActivityStateTests(unittest.TestCase):
    def test_assigned_pawn_on_work_block_is_working(self):
        pawn = _commuter(assignment=JobRef("farm1", "farming"))
        self.assertEqual(pawns.activity_state(pawn, "work"), pawns.STATE_WORKING)

    def test_unassigned_pawn_on_work_block_is_idle(self):
        pawn = _commuter(assignment=None)
        self.assertEqual(pawns.activity_state(pawn, "work"), pawns.STATE_IDLE)

    def test_sleep_and_rec_blocks_map_to_their_states(self):
        pawn = _commuter()
        self.assertEqual(pawns.activity_state(pawn, "sleep"), pawns.STATE_SLEEPING)
        self.assertEqual(pawns.activity_state(pawn, "rec"), pawns.STATE_RECREATING)


def _chebyshev(a, b):
    return max(abs(a[0] - b[0]), abs(a[1] - b[1]))


class MovementTests(unittest.TestCase):
    WORK_TILE = (8, 2 + engine.BUILDING_FRONT_OFFSET)  # farm at (8,2), stand in front

    def test_awake_assigned_pawn_walks_to_and_holds_its_workplace(self):
        state, pawn = _farm_state(time_of_day=8)  # pawn home/start (0,10)
        for _ in range(10):  # any waking block heads to the workplace
            engine._move_pawn(state, pawn, "work", broken=False)
        self.assertEqual((pawn.x, pawn.y), self.WORK_TILE)
        # A midday rec hour does not yank it home - it holds the workplace.
        engine._move_pawn(state, pawn, "rec", broken=False)
        self.assertEqual((pawn.x, pawn.y), self.WORK_TILE)

    def test_sleeping_pawn_walks_home(self):
        state, pawn = _farm_state(time_of_day=8)
        pawn.x, pawn.y = self.WORK_TILE
        for _ in range(10):
            engine._move_pawn(state, pawn, "sleep", broken=False)
        self.assertEqual((pawn.x, pawn.y), (pawn.home_x, pawn.home_y))

    def test_broken_pawn_leaves_work_for_home(self):
        state, pawn = _farm_state(time_of_day=8)
        pawn.x, pawn.y = self.WORK_TILE
        for _ in range(10):
            engine._move_pawn(state, pawn, "work", broken=True)
        self.assertEqual((pawn.x, pawn.y), (pawn.home_x, pawn.home_y))

    def test_step_hour_sets_working_state_and_takes_a_step(self):
        state, pawn = _farm_state(time_of_day=8)
        start = (pawn.x, pawn.y)
        engine.step_hour(state)
        self.assertEqual(pawn.state, pawns.STATE_WORKING)
        self.assertEqual(_chebyshev((pawn.x, pawn.y), start), engine.PAWN_MOVE_TILES_PER_HOUR)

    def test_movement_is_deterministic(self):
        first, _ = _farm_state(time_of_day=7)
        second, _ = _farm_state(time_of_day=7)
        for _ in range(15):
            engine.step_hour(first)
            engine.step_hour(second)
        self.assertEqual(
            {pid: (p.x, p.y) for pid, p in first.pawns.items()},
            {pid: (p.x, p.y) for pid, p in second.pawns.items()},
        )

    def test_default_civilization_pawns_leave_their_spawn_cluster(self):
        state = civilization.create_default_civilization()
        spawn = {pid: (p.x, p.y) for pid, p in state.pawns.items()}
        max_disp = {pid: 0 for pid in state.pawns}
        for _ in range(24):  # over one day pawns commute away from spawn
            engine.step_hour(state)
            for pid, p in state.pawns.items():
                max_disp[pid] = max(max_disp[pid], _chebyshev((p.x, p.y), spawn[pid]))
        moved = sum(1 for disp in max_disp.values() if disp > 0)
        self.assertGreaterEqual(moved, 8)


if __name__ == "__main__":
    unittest.main()
