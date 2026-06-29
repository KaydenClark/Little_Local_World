import unittest

from agent_town import buildings, construction, economy, world
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


class TrackA1Tests(unittest.TestCase):
    def test_stockpile_add_remove_has_and_validation(self):
        stockpile = Stockpile()

        stockpile.add(Good.LOGS, 5)
        stockpile.add(Good.STONE, 2)
        stockpile.remove(Good.LOGS, 3)

        self.assertEqual(stockpile.counts, {Good.LOGS: 2, Good.STONE: 2})
        self.assertTrue(stockpile.has(Good.LOGS, 2))
        self.assertFalse(stockpile.has(Good.PLANKS, 1))
        with self.assertRaisesRegex(ValueError, "Insufficient logs"):
            stockpile.remove(Good.LOGS, 3)
        with self.assertRaisesRegex(ValueError, "positive"):
            stockpile.add(Good.LOGS, 0)
        with self.assertRaisesRegex(ValueError, "non-negative"):
            stockpile.has(Good.LOGS, -1)

    def test_world_generation_and_nodes_are_deterministic(self):
        first_grid, first_nodes = world.create_world(8, 6, seed=17)
        second_grid, second_nodes = world.create_world(8, 6, seed=17)

        self.assertEqual(first_grid, second_grid)
        self.assertEqual(first_nodes, second_nodes)
        self.assertEqual(len(first_grid.tiles), 6)
        self.assertEqual(len(first_grid.tiles[0]), 8)
        self.assertEqual({node.kind for node in first_nodes}, {Good.LOGS, Good.GRAIN, Good.STONE})
        for node in first_nodes:
            self.assertTrue(first_grid.in_bounds(node.x, node.y))
            self.assertGreater(node.amount, 0)

    def test_harvest_and_filter_resource_nodes(self):
        nodes = [
            world.ResourceNode(Good.LOGS, 5, 1, 1),
            world.ResourceNode(Good.LOGS, 0, 2, 2),
            world.ResourceNode(Good.STONE, 3, 3, 3),
        ]

        self.assertEqual(world.nodes_of_kind(nodes, Good.LOGS), [nodes[0]])
        self.assertEqual(world.harvest_node(nodes[0], 3), 3)
        self.assertEqual(nodes[0].amount, 2)
        self.assertEqual(world.harvest_node(nodes[0], 10), 2)
        self.assertEqual(nodes[0].amount, 0)


class TrackA2Tests(unittest.TestCase):
    def test_building_definitions_cover_all_build1_chains(self):
        expected = {"Forester", "Sawmill", "Farm", "Mill", "Bakery", "Quarry"}

        self.assertEqual({definition.kind for definition in buildings.BUILDING_DEFS.values()}, expected)
        sawmill = buildings.building_def("sawmill")
        self.assertEqual(sawmill.recipe.inputs, {Good.LOGS: 2})
        self.assertEqual(sawmill.recipe.outputs, {Good.PLANKS: 1})
        self.assertEqual(sawmill.job_slots, 1)
        with self.assertRaisesRegex(ValueError, "Unknown building kind"):
            buildings.building_def("Moon Mill")

    def test_make_building_and_open_slots_use_current_contract_ids(self):
        building = buildings.make_building("Sawmill", 4, 5, building_id="saw1")

        self.assertEqual(building.id, "saw1")
        self.assertEqual(building.kind, "Sawmill")
        self.assertTrue(building.built)
        self.assertEqual(buildings.open_slots(building), 1)
        building.staffed_by.append("sawyer")
        self.assertEqual(buildings.open_slots(building), 0)

    def test_production_tick_uses_effective_work_and_recipe_inputs(self):
        state = FactionState(time_of_day=8)
        forester = buildings.make_building("Forester", 1, 1, building_id="forester1")
        sawmill = buildings.make_building("Sawmill", 2, 1, building_id="saw1")
        forester.staffed_by.append("forester")
        sawmill.staffed_by.append("sawyer")
        state.buildings = {forester.id: forester, sawmill.id: sawmill}
        state.pawns = {
            "forester": worker("forester", "forestry"),
            "sawyer": worker("sawyer", "woodworking"),
        }

        for _ in range(4):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.PLANKS), 2)
        self.assertNotIn(Good.LOGS, state.stockpile.counts)

    def test_off_shift_pawns_do_not_produce(self):
        state = FactionState(time_of_day=2)
        forester = buildings.make_building("Forester", 1, 1, building_id="forester1")
        forester.staffed_by.append("forester")
        state.buildings[forester.id] = forester
        state.pawns["forester"] = worker("forester", "forestry")

        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts, {})


class TrackA3Tests(unittest.TestCase):
    def test_construction_delivery_work_and_completion(self):
        state = FactionState(coin=construction.building_coin_cost("Sawmill"))
        state.stockpile = Stockpile({Good.PLANKS: 4, Good.STONE: 2})

        site = construction.place_construction_site(state, "Sawmill", 4, 5, site_id="site1")

        self.assertEqual(state.coin, 0)
        self.assertEqual(state.construction_sites, {"site1": site})
        self.assertEqual(construction.haul_to_site(state, site, Good.PLANKS, 10), 4)
        self.assertEqual(construction.haul_to_site(state, site, Good.STONE, 1), 1)
        self.assertFalse(construction.goods_satisfied(site))
        construction.advance_construction(site, 10)
        self.assertGreater(site.work_remaining, 0)

        self.assertEqual(construction.haul_to_site(state, site, Good.STONE, 10), 1)
        self.assertTrue(construction.goods_satisfied(site))
        construction.advance_construction(site, site.work_remaining)
        building = construction.complete_if_ready(state, site)

        self.assertIsNotNone(building)
        self.assertEqual(state.construction_sites, {})
        self.assertIn(building.id, state.buildings)
        self.assertEqual(building.kind, "Sawmill")

    def test_place_construction_site_blocks_low_coin_without_mutating(self):
        state = FactionState(coin=construction.building_coin_cost("Bakery") - 1)

        with self.assertRaisesRegex(ValueError, "Insufficient coin"):
            construction.place_construction_site(state, "Bakery", 6, 7, site_id="site1")

        self.assertEqual(state.construction_sites, {})


class TrackA4Tests(unittest.TestCase):
    def test_food_stone_chains_tax_and_affordability(self):
        state = FactionState(time_of_day=8, tax_rate=0.2)
        for kind, skill in (
            ("Farm", "farming"),
            ("Mill", "milling"),
            ("Bakery", "baking"),
            ("Quarry", "mining"),
        ):
            building = buildings.make_building(kind, 0, 0, building_id=kind.lower())
            pawn = worker(f"{kind.lower()}-worker", skill)
            building.staffed_by.append(pawn.id)
            state.buildings[building.id] = building
            state.pawns[pawn.id] = pawn

        for _ in range(8):
            economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.BREAD), 2)
        self.assertEqual(state.stockpile.counts.get(Good.STONE), 8)
        self.assertTrue(economy.can_afford(state, {Good.BREAD: 1}, coin_cost=0))
        self.assertFalse(economy.can_afford(state, {Good.PLANKS: 1}, coin_cost=0))

        income = economy.apply_daily_tax(state)
        self.assertGreater(income, 0)
        self.assertEqual(state.coin, income)


if __name__ == "__main__":
    unittest.main()
