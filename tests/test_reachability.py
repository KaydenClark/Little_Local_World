"""Reachability regions reject impossible work before pathfinding."""

import unittest

from agent_town import buildings, pawns, work, world
from agent_town.core import FactionState, GridMap, JobRef, Pawn


def _worker(pid: str = "p") -> Pawn:
    return Pawn(
        id=pid,
        name=pid.upper(),
        skills={"baking": 20, "woodworking": 1},
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=80.0,
        x=0,
        y=1,
    )


def _split_grid() -> GridMap:
    return GridMap(
        width=5,
        height=3,
        tiles=(
            (world.TILE_GRASS, world.TILE_GRASS, world.TILE_WATER, world.TILE_GRASS, world.TILE_GRASS),
            (world.TILE_GRASS, world.TILE_GRASS, world.TILE_WATER, world.TILE_GRASS, world.TILE_GRASS),
            (world.TILE_GRASS, world.TILE_GRASS, world.TILE_WATER, world.TILE_GRASS, world.TILE_GRASS),
        ),
    )


class ReachabilityRegionTests(unittest.TestCase):
    def test_region_ids_split_walkable_tiles_around_water_barrier(self):
        regions = world.reachability_regions(_split_grid())

        self.assertEqual(regions[1][0], regions[0][1])
        self.assertNotEqual(regions[1][0], regions[1][4])
        self.assertIsNone(regions[1][2])
        self.assertFalse(world.same_reachability_region(_split_grid(), (0, 1), (4, 1)))
        self.assertTrue(world.same_reachability_region(_split_grid(), (0, 1), (1, 2)))


class WorkReachabilityTests(unittest.TestCase):
    def test_unreachable_high_priority_job_is_rejected_for_reachable_work(self):
        pawn = _worker()
        work.set_priority(pawn, "baking", 1)
        work.set_priority(pawn, "woodworking", 4)
        state = FactionState(grid=_split_grid(), time_of_day=8)
        reachable = buildings.make_building("Sawmill", 1, 1, building_id="sawmill1")
        unreachable = buildings.make_building("Bakery", 4, 1, building_id="bakery1")
        state.buildings = {reachable.id: reachable, unreachable.id: unreachable}
        state.pawns[pawn.id] = pawn

        work.assign_jobs(state)

        self.assertEqual(pawn.assignment, JobRef("sawmill1", "woodworking"))
        self.assertEqual(state.buildings["sawmill1"].staffed_by, ["p"])
        self.assertEqual(state.buildings["bakery1"].staffed_by, [])
        rejected = state.work_decisions["p"].rejected
        self.assertTrue(
            any(r.building_id == "bakery1" and r.reason == "unreachable region" for r in rejected)
        )


if __name__ == "__main__":
    unittest.main()
