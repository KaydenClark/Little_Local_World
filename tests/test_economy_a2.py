import unittest

from agent_town.buildings import create_building
from agent_town.core import FactionState, Good, Stockpile
from agent_town.economy import advance_economy


def _state(*buildings, stockpile=None):
    return FactionState(
        stockpile=stockpile or Stockpile(),
        coin=0,
        pawns=[],
        buildings=list(buildings),
        construction_sites=[],
        research="",
        season="spring",
        tax_rate=0.1,
        day=1,
        time_of_day=9,
    )


class BuildingDefinitionTests(unittest.TestCase):
    def test_create_wood_chain_buildings_with_recipes_and_slots(self):
        forester = create_building("Forester", 1, 2)
        sawmill = create_building("Sawmill", 3, 4)

        self.assertEqual(forester.recipe.inputs, {})
        self.assertEqual(forester.recipe.outputs, {Good.LOGS: 1})
        self.assertEqual(forester.job_slots, 1)
        self.assertTrue(forester.built)

        self.assertEqual(sawmill.recipe.inputs, {Good.LOGS: 2})
        self.assertEqual(sawmill.recipe.outputs, {Good.PLANKS: 1})
        self.assertEqual(sawmill.job_slots, 1)
        self.assertTrue(sawmill.built)

    def test_create_building_rejects_unknown_kind(self):
        with self.assertRaisesRegex(ValueError, "Unknown building kind"):
            create_building("Moon Mill", 0, 0)


class EconomyProductionTests(unittest.TestCase):
    def test_forester_produces_logs_when_built_and_staffed(self):
        forester = create_building("Forester", 1, 1)
        forester.staffed_by.append("temp-worker")
        state = _state(forester)

        advance_economy(state, 1.0)

        self.assertEqual(state.stockpile.counts[Good.LOGS], 1)

    def test_unstaffed_or_unbuilt_buildings_do_not_produce(self):
        unstaffed = create_building("Forester", 1, 1)
        unbuilt = create_building("Forester", 2, 2)
        unbuilt.staffed_by.append("temp-worker")
        unbuilt.built = False
        state = _state(unstaffed, unbuilt)

        advance_economy(state, 5.0)

        self.assertNotIn(Good.LOGS, state.stockpile.counts)

    def test_sawmill_consumes_logs_and_produces_planks(self):
        sawmill = create_building("Sawmill", 2, 2)
        sawmill.staffed_by.append("temp-worker")
        state = _state(sawmill, stockpile=Stockpile({Good.LOGS: 4}))

        advance_economy(state, 1.0)

        self.assertEqual(state.stockpile.counts[Good.LOGS], 2)
        self.assertEqual(state.stockpile.counts[Good.PLANKS], 1)

    def test_sawmill_waits_when_inputs_are_missing(self):
        sawmill = create_building("Sawmill", 2, 2)
        sawmill.staffed_by.append("temp-worker")
        state = _state(sawmill, stockpile=Stockpile({Good.LOGS: 1}))

        advance_economy(state, 1.0)

        self.assertEqual(state.stockpile.counts[Good.LOGS], 1)
        self.assertNotIn(Good.PLANKS, state.stockpile.counts)

    def test_seeded_headless_wood_chain_produces_planks(self):
        forester = create_building("Forester", 1, 1)
        sawmill = create_building("Sawmill", 2, 1)
        forester.staffed_by.append("temp-forester")
        sawmill.staffed_by.append("temp-sawyer")
        state = _state(forester, sawmill)

        for _ in range(4):
            advance_economy(state, 1.0)

        self.assertEqual(state.stockpile.counts[Good.PLANKS], 2)
        self.assertNotIn(Good.LOGS, state.stockpile.counts)


if __name__ == "__main__":
    unittest.main()
