"""`set_production_target` is a real lever: production honors the target.

Before this slice the governor could set a building's `production_target` and the
production tick ignored it, so the Governor card reported a change that never
happened. These tests pin the truthful behavior: a target caps a good at
`amount` in the stockpile (largest whole batch at or below it), an already-met
target idles the building (no inputs consumed), and the full governor lever path
(apply_actions -> production_tick) respects it.
"""

import unittest

from agent_town import buildings, economy, governor
from agent_town.core import FactionState, Good, GovernorAction, Pawn, Stockpile


def worker(pawn_id: str, skill: str, level: int = 10) -> Pawn:
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={skill: level},
        needs={},
        mood=80.0,
        schedule="default",
    )


def staffed(kind: str, skill: str, *, building_id: str) -> tuple:
    building = buildings.make_building(kind, 0, 0, building_id=building_id)
    pawn = worker(f"{building_id}-worker", skill)
    building.staffed_by.append(pawn.id)
    return building, pawn


def civ_with(building, pawn, *, time_of_day: int = 8, stock: dict | None = None) -> FactionState:
    state = FactionState(time_of_day=time_of_day)
    state.buildings = {building.id: building}
    state.pawns = {pawn.id: pawn}
    if stock is not None:
        state.stockpile = Stockpile(dict(stock))
    return state


class ProductionTargetTests(unittest.TestCase):
    def test_target_caps_output_then_building_idles(self):
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        building.production_target[Good.LOGS] = 2
        state = civ_with(building, pawn)

        for _ in range(5):
            economy.production_tick(state)

        # One log/tick would reach 5 in 5 ticks; the target holds it at 2.
        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 2)

    def test_met_target_consumes_no_inputs(self):
        building, pawn = staffed("Sawmill", "woodworking", building_id="saw1")
        building.production_target[Good.PLANKS] = 3
        state = civ_with(building, pawn, stock={Good.LOGS: 10, Good.PLANKS: 3})

        for _ in range(3):
            economy.production_tick(state)

        # Already at target: no planks made, and crucially no logs burned.
        self.assertEqual(state.stockpile.counts.get(Good.PLANKS), 3)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 10)

    def test_batch_output_never_overshoots_target(self):
        # Bakery yields 4 bread/cycle; a target of 10 settles at the nearest
        # whole batch at or below it (8), never above.
        building, pawn = staffed("Bakery", "baking", building_id="bakery1")
        building.production_target[Good.BREAD] = 10
        state = civ_with(building, pawn, stock={Good.FLOUR: 100})

        for _ in range(6):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.BREAD), 8)
        self.assertEqual(state.stockpile.counts.get(Good.FLOUR), 96)  # 2 batches * 2 flour

    def test_raising_and_clearing_target_resumes_production(self):
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        building.production_target[Good.LOGS] = 1
        state = civ_with(building, pawn)

        for _ in range(3):
            economy.production_tick(state)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 1)

        building.production_target[Good.LOGS] = 3
        for _ in range(3):
            economy.production_tick(state)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 3)

        building.production_target.pop(Good.LOGS)
        for _ in range(2):
            economy.production_tick(state)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 5)

    def test_no_target_is_unbounded(self):
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        state = civ_with(building, pawn)

        for _ in range(3):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 3)

    def test_governor_lever_path_is_honored(self):
        # The whole point: the governor's set_production_target action, applied
        # through apply_actions, actually constrains the next ticks.
        building, pawn = staffed("Forester", "forestry", building_id="forester1")
        state = civ_with(building, pawn)

        action = GovernorAction.set_production_target("forester1", Good.LOGS, 2)
        applied = governor.apply_actions(state, [action])
        self.assertEqual([a.kind for a in applied], ["set_production_target"])
        self.assertEqual(building.production_target.get(Good.LOGS), 2)

        for _ in range(5):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.LOGS), 2)


if __name__ == "__main__":
    unittest.main()
