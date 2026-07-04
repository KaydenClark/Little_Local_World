"""Repair debt: buildings degrade, slow down, and consume material/labour to recover."""

import unittest

from agent_town import buildings, civilization_view, economy, engine, governor, health, save
from agent_town.core import FactionState, Good, JobRef, Pawn, Stockpile


def worker(pawn_id: str, skill: str) -> Pawn:
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={skill: 10},
        needs={},
        mood=80.0,
        schedule="default",
    )


def staffed(kind: str, skill: str, *, building_id: str):
    building = buildings.make_building(kind, 0, 0, building_id=building_id)
    pawn = worker("worker1", skill)
    building.staffed_by.append(pawn.id)
    pawn.assignment = JobRef(building.id, skill)
    return building, pawn


class RepairDebtTests(unittest.TestCase):
    def test_decay_lowers_built_building_condition(self):
        building = buildings.make_building("Sawmill", 0, 0, building_id="saw1")
        state = FactionState(buildings={building.id: building})

        degraded = economy.decay_buildings(state, amount=0.1)

        self.assertEqual(degraded, ("saw1",))
        self.assertAlmostEqual(economy.building_condition(building), 0.9)

    def test_damaged_building_slows_production_before_failure(self):
        building, pawn = staffed("Sawmill", "woodworking", building_id="saw1")
        economy.set_building_condition(building, 0.5)
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.LOGS: 4}),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )

        economy.production_tick(state)
        self.assertEqual(state.stockpile.counts, {Good.LOGS: 4})
        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {Good.LOGS: 2, Good.PLANKS: 1})

    def test_repair_spends_material_and_hour_before_production(self):
        building, pawn = staffed("Sawmill", "woodworking", building_id="saw1")
        economy.set_building_condition(building, 0.5)
        economy.set_building_repair_progress(building, 0.51)
        state = FactionState(
            time_of_day=8,
            stockpile=Stockpile({Good.LOGS: 4, Good.PLANKS: 1, Good.STONE: 1}),
            buildings={building.id: building},
            pawns={pawn.id: pawn},
        )

        result = engine.step_hour(state, governor.FallbackGovernor())

        self.assertEqual(result.buildings_repaired, ("saw1",))
        self.assertEqual(state.stockpile.counts, {Good.LOGS: 4})
        self.assertGreater(economy.building_condition(building), 0.5)

    def test_storehouse_condition_reduces_storage_service_capacity(self):
        state = FactionState(stockpile=Stockpile({Good.BREAD: 5}, capacity=20))
        storehouse = buildings.make_building("Storehouse", 0, 0, building_id="storehouse1")
        economy.set_building_condition(storehouse, 0.5)
        state.buildings[storehouse.id] = storehouse

        self.assertEqual(economy.refresh_storage_capacity(state), 80)

    def test_snapshot_records_building_condition_and_repair_progress(self):
        building = buildings.make_building("Sawmill", 0, 0, building_id="saw1")
        economy.set_building_condition(building, 0.6)
        economy.set_building_repair_progress(building, 0.25)
        state = FactionState(buildings={building.id: building})

        snapshot = __import__("agent_town.telemetry", fromlist=["telemetry"]).build_snapshot(state, object())

        self.assertEqual(
            snapshot["building_conditions"]["saw1"],
            {"kind": "Sawmill", "condition": 0.6, "efficiency": 0.6, "repair_progress": 0.25},
        )

    def test_save_round_trips_condition_and_repair_progress(self):
        building = buildings.make_building("Sawmill", 0, 0, building_id="saw1")
        economy.set_building_condition(building, 0.6)
        economy.set_building_repair_progress(building, 0.25)
        state = FactionState(buildings={building.id: building})

        loaded = save.from_dict(save.to_dict(state))

        self.assertAlmostEqual(economy.building_condition(loaded.buildings["saw1"]), 0.6)
        self.assertAlmostEqual(economy.building_repair_progress(loaded.buildings["saw1"]), 0.25)

    def test_building_card_surfaces_condition_and_repair_state(self):
        building, pawn = staffed("Sawmill", "woodworking", building_id="saw1")
        economy.set_building_condition(building, 0.55)
        state = FactionState(
            buildings={building.id: building},
            pawns={pawn.id: pawn},
            stockpile=Stockpile({Good.PLANKS: 1, Good.STONE: 1}),
        )

        lines = [text for text, _tone in civilization_view.building_card_lines(state, building)]

        self.assertTrue(any("Condition 55%" in text for text in lines), lines)
        self.assertTrue(any("Repair ready" in text for text in lines), lines)

    def test_damaged_building_surfaces_as_warning_badge(self):
        building = buildings.make_building("Sawmill", 0, 0, building_id="saw1")
        economy.set_building_condition(building, 0.55)
        state = FactionState(buildings={building.id: building})

        exceptions = governor.build_exception_queue(state)
        badges = civilization_view.building_exception_badges(state)

        self.assertTrue(any(exc.kind == "building_damaged" for exc in exceptions), exceptions)
        self.assertEqual(badges["saw1"], health.WARN)


if __name__ == "__main__":
    unittest.main()
