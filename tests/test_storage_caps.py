"""Storage caps make downstream saturation a real economy blocker.

Paper 4 calls out storage pressure as the first economy bottleneck before
markets/wages. These tests pin the narrow slice: a finite stockpile refuses
overflow, production that would increase total stored goods idles when full
without burning inputs, and net-shrinking transforms can still run while full.
"""

import unittest

from agent_town import buildings, economy, health, telemetry
from agent_town.core import FactionState, Good, Pawn, Stockpile


def worker(pawn_id: str, skill: str, level: int = 10) -> Pawn:
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={skill: level},
        needs={},
        mood=80.0,
        schedule="default",
    )


def staffed(kind: str, skill: str, *, building_id: str):
    building = buildings.make_building(kind, 0, 0, building_id=building_id)
    pawn = worker(f"{building_id}-worker", skill)
    building.staffed_by.append(pawn.id)
    return building, pawn


class StorageCapTests(unittest.TestCase):
    def test_stockpile_capacity_rejects_overflow_and_reports_fullness(self):
        stockpile = Stockpile(capacity=5)
        stockpile.add(Good.LOGS, 3)
        stockpile.add(Good.STONE, 2)

        self.assertEqual(stockpile.used_capacity(), 5)
        self.assertEqual(stockpile.available_capacity(), 0)
        self.assertEqual(stockpile.fullness(), 1.0)
        self.assertFalse(stockpile.has_capacity_for(1))
        with self.assertRaisesRegex(ValueError, "Stockpile capacity exceeded"):
            stockpile.add(Good.BREAD, 1)

    def test_output_only_production_stops_at_capacity(self):
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.STONE: 2}, capacity=3),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )

        for _ in range(4):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {Good.STONE: 2, Good.LOGS: 1})

    def test_full_storage_blocks_net_growing_recipe_without_burning_inputs(self):
        building, pawn = staffed("Bakery", "baking", building_id="bakery1")
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.FLOUR: 4, Good.STONE: 6}, capacity=10),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )

        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {Good.FLOUR: 4, Good.STONE: 6})

    def test_full_storage_allows_net_shrinking_transform(self):
        building, pawn = staffed("Sawmill", "woodworking", building_id="saw1")
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.LOGS: 8, Good.STONE: 2}, capacity=10),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )

        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {Good.LOGS: 6, Good.STONE: 2, Good.PLANKS: 1})
        self.assertEqual(state.stockpile.used_capacity(), 9)

    def test_snapshot_includes_storage_capacity(self):
        state = FactionState(stockpile=Stockpile({Good.BREAD: 5}, capacity=20))
        snap = telemetry.build_snapshot(state, object())

        self.assertEqual(snap["storage"], {"used": 5, "capacity": 20, "fullness": 0.25})

    def test_built_storehouses_raise_capacity_without_double_counting(self):
        state = FactionState(stockpile=Stockpile({Good.BREAD: 5}, capacity=20))
        state.buildings["storehouse1"] = buildings.make_building(
            "Storehouse", 0, 0, building_id="storehouse1"
        )
        state.buildings["storehouse2"] = buildings.make_building(
            "Storehouse", 2, 0, building_id="storehouse2"
        )
        state.buildings["ghost"] = buildings.make_building(
            "Storehouse", 4, 0, building_id="ghost", built=False
        )

        self.assertEqual(economy.refresh_storage_capacity(state), 260)
        self.assertEqual(economy.refresh_storage_capacity(state), 260)
        self.assertEqual(state.stockpile.base_capacity, 20)
        self.assertEqual(state.stockpile.capacity, 260)

    def test_storehouse_capacity_is_applied_before_storage_limited_production(self):
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.STONE: 2}, capacity=2),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )
        state.buildings["storehouse1"] = buildings.make_building(
            "Storehouse", 2, 0, building_id="storehouse1"
        )

        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {Good.STONE: 2, Good.LOGS: 1})
        self.assertEqual(state.stockpile.capacity, 122)

    def test_invariants_flag_over_capacity_state(self):
        state = FactionState(stockpile=Stockpile({Good.BREAD: 5}, capacity=5))
        state.stockpile.counts[Good.WATER] = 1

        self.assertIn("stockpile over capacity (6/5)", health.check_invariants(state))


if __name__ == "__main__":
    unittest.main()
