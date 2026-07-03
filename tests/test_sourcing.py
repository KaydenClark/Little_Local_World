"""Physical resource sourcing: faucets draw from located, gated map nodes.

The conservation ledger (Slice C) proved goods balance in *count*; these tests
pin that Tier 0 goods now exist in *place and time* (review E-9, BLUEPRINT
"Physical sourcing"): grain comes from a planted field that needed a growing
season, logs from depleting-then-regrowing tree stands, stone from finite
outcrops that mine out. The Water Well stays a named replenished source.
"""

import unittest

from agent_town import buildings, civilization, economy, engine, governor, work, world
from agent_town.core import (
    FactionState,
    Good,
    NODE_EMPTY,
    NODE_GROWING,
    NODE_READY,
    Pawn,
    ResourceNode,
)
from agent_town.pawns import BUILD1_NEEDS


def _worker(pawn_id: str, skill: str, level: int = 10) -> Pawn:
    return Pawn(
        id=pawn_id,
        name=pawn_id.title(),
        skills={skill: level},
        needs={need: 1.0 for need in BUILD1_NEEDS},
        mood=80.0,
        schedule="default",
    )


def _staffed_farm(state: FactionState) -> tuple:
    farm = buildings.make_building("Farm", 2, 2, building_id="farm1")
    pawn = _worker("farmer", "farming")
    farm.staffed_by.append(pawn.id)
    state.buildings[farm.id] = farm
    state.pawns[pawn.id] = pawn
    return farm, pawn


class FieldLifecycleTests(unittest.TestCase):
    def test_planting_consumes_seed_and_starts_growth(self):
        state = FactionState(time_of_day=8, seed_grain=economy.PLANT_SEED_COST)
        farm, _ = _staffed_farm(state)

        economy.production_tick(state)

        field = world.farm_field(state, farm)
        self.assertIsNotNone(field)
        self.assertEqual(field.state, NODE_GROWING)
        self.assertEqual(state.seed_grain, 0)
        self.assertNotIn(Good.GRAIN, state.stockpile.counts)

    def test_no_seed_means_no_planting_and_no_grain(self):
        state = FactionState(time_of_day=8, seed_grain=0)
        farm, _ = _staffed_farm(state)
        world.claim_farm_field(state, farm)

        for _ in range(6):
            economy.production_tick(state)

        field = world.farm_field(state, farm)
        self.assertEqual(field.state, NODE_EMPTY)
        self.assertNotIn(Good.GRAIN, state.stockpile.counts)
        kinds = [exc.kind for exc in governor.build_exception_queue(state)]
        self.assertIn("no_seed_grain", kinds)

    def test_growth_needs_time_not_labor(self):
        # A staffed farm working flat out cannot conjure grain from a growing
        # field: the growing season is the rate limiter, not headcount.
        state = FactionState(time_of_day=8, seed_grain=economy.PLANT_SEED_COST)
        farm, _ = _staffed_farm(state)
        economy.production_tick(state)  # plants
        field = world.farm_field(state, farm)
        self.assertEqual(field.state, NODE_GROWING)

        for _ in range(world.FIELD_GROWTH_HOURS - 1):
            economy.production_tick(state)  # labor, but no world time
        self.assertEqual(field.state, NODE_GROWING)
        self.assertNotIn(Good.GRAIN, state.stockpile.counts)

        for _ in range(world.FIELD_GROWTH_HOURS):
            world.advance_nodes(state)
        self.assertEqual(field.state, NODE_READY)
        self.assertEqual(field.amount, world.FIELD_YIELD)

    def test_growth_continues_while_farmer_is_elsewhere(self):
        state = FactionState(seed_grain=0)
        farm, _ = _staffed_farm(state)
        field = world.claim_farm_field(state, farm)
        field.state = NODE_GROWING
        field.growth_progress = 0.0
        farm.staffed_by.clear()  # nobody home

        for _ in range(world.FIELD_GROWTH_HOURS):
            world.advance_nodes(state)

        self.assertEqual(field.state, NODE_READY)

    def test_harvest_moves_grain_from_field_to_stockpile_and_reseeds(self):
        state = FactionState(time_of_day=8, seed_grain=0)
        farm, _ = _staffed_farm(state)
        field = world.create_field_node(state, 3, 3, field_id="field-farm1", ripe=True)
        farm.source_node_id = field.id
        start_on_field = field.amount

        hours = 0
        while field.amount > 0 and hours < 40:
            economy.production_tick(state)
            hours += 1

        harvested = state.stockpile.counts.get(Good.GRAIN, 0)
        # Every harvested unit is accounted for: reserve topped up first, the
        # rest in the stockpile, and the emptied field cycles back to EMPTY.
        self.assertEqual(state.seed_grain, economy.SEED_RESERVE_TARGET)
        self.assertEqual(harvested + state.seed_grain, start_on_field)
        self.assertEqual(field.state, NODE_EMPTY)

    def test_new_farm_cannot_produce_grain_within_a_season(self):
        # The dig-out oracle's timing premise: a farm built mid-crisis takes at
        # least a full growing season (plant + grow) before its first grain.
        state = FactionState(time_of_day=8, seed_grain=economy.PLANT_SEED_COST)
        _staffed_farm(state)

        for _ in range(world.FIELD_GROWTH_HOURS):
            economy.production_tick(state)  # hour of labor...
            world.advance_nodes(state)  # ...and hour of world time

        self.assertNotIn(Good.GRAIN, state.stockpile.counts)

    def test_field_growing_is_informational_and_suppresses_unstaffed_noise(self):
        state = FactionState(seed_grain=0)
        farm, pawn = _staffed_farm(state)
        farm.staffed_by.clear()  # farmer freed by design while the crop grows
        field = world.claim_farm_field(state, farm)
        field.state = NODE_GROWING

        kinds = [exc.kind for exc in governor.build_exception_queue(state)]
        self.assertIn("field_growing", kinds)
        self.assertNotIn("unstaffed_building", kinds)


class ExtractionTests(unittest.TestCase):
    def _staffed_extractor(self, kind: str, skill: str) -> tuple:
        state = FactionState(time_of_day=8)
        building = buildings.make_building(kind, 0, 0, building_id=f"{kind.lower()}1")
        pawn = _worker("digger", skill)
        building.staffed_by.append(pawn.id)
        state.buildings[building.id] = building
        state.pawns[pawn.id] = pawn
        return state, building

    def test_quarry_depletes_its_node_and_stops(self):
        state, quarry = self._staffed_extractor("Quarry", "mining")
        node = ResourceNode(Good.STONE, 3, 1, 1)
        state.resource_nodes.append(node)

        for _ in range(6):
            economy.production_tick(state)

        # Exactly what the outcrop held - not one stone more.
        self.assertEqual(state.stockpile.counts.get(Good.STONE, 0), 3)
        self.assertEqual(node.amount, 0)
        kinds = [exc.kind for exc in governor.build_exception_queue(state)]
        self.assertIn("node_depleted", kinds)

    def test_stone_never_regrows_but_trees_do(self):
        state = FactionState()
        stone = ResourceNode(Good.STONE, 0, 1, 1, max_amount=10, state=NODE_EMPTY)
        trees = ResourceNode(Good.LOGS, 0, 2, 2, max_amount=10, state=NODE_EMPTY)
        state.resource_nodes.extend([stone, trees])

        for _ in range(8):
            world.advance_nodes(state)

        self.assertEqual(stone.amount, 0)
        self.assertEqual(trees.amount, int(8 * world.TREE_REGROW_PER_HOUR))
        self.assertEqual(trees.state, NODE_READY)

    def test_forester_harvests_nearest_stand_first(self):
        state, forester = self._staffed_extractor("Forester", "forestry")
        near = ResourceNode(Good.LOGS, 2, 1, 0)
        far = ResourceNode(Good.LOGS, 50, 9, 9)
        state.resource_nodes.extend([near, far])

        for _ in range(3):
            economy.production_tick(state)

        self.assertEqual(near.amount, 0)
        self.assertEqual(far.amount, 49)
        self.assertEqual(state.stockpile.counts.get(Good.LOGS, 0), 3)


class WorkArbiterSourcingTests(unittest.TestCase):
    def _two_job_civ(self) -> FactionState:
        """One skilled farmer, a Farm, and a Mill with grain waiting."""
        state = FactionState(time_of_day=8, seed_grain=economy.SEED_RESERVE_TARGET)
        farm = buildings.make_building("Farm", 2, 2, building_id="farm1")
        mill = buildings.make_building("Mill", 4, 2, building_id="mill1")
        state.buildings = {farm.id: farm, mill.id: mill}
        pawn = _worker("farmer", "farming", level=19)
        state.pawns[pawn.id] = pawn
        state.stockpile.add(Good.GRAIN, 20)
        return state

    def test_growing_field_frees_the_farmer_for_other_work(self):
        state = self._two_job_civ()
        farm = state.buildings["farm1"]
        field = world.claim_farm_field(state, farm)
        field.state = NODE_GROWING

        work.assign_jobs(state)

        pawn = state.pawns["farmer"]
        self.assertIsNotNone(pawn.assignment)
        self.assertEqual(pawn.assignment.building_id, "mill1")

    def test_farmer_returns_for_the_harvest(self):
        state = self._two_job_civ()
        farm = state.buildings["farm1"]
        field = world.claim_farm_field(state, farm)
        field.state = NODE_GROWING
        work.assign_jobs(state)
        self.assertEqual(state.pawns["farmer"].assignment.building_id, "mill1")

        # The crop ripens; the strict-priority upgrade walks the farmer back.
        field.state = NODE_READY
        field.amount = world.FIELD_YIELD
        work.assign_jobs(state)

        pawn = state.pawns["farmer"]
        self.assertEqual(pawn.assignment.building_id, "farm1")
        self.assertNotIn(pawn.id, state.buildings["mill1"].staffed_by)
        self.assertIn(pawn.id, farm.staffed_by)

    def test_no_thrash_between_equal_priority_jobs(self):
        # The upgrade release fires only on a STRICT priority improvement, so a
        # pawn holding one of two equal jobs never ping-pongs between them.
        state = FactionState(time_of_day=8)
        mill_a = buildings.make_building("Mill", 2, 2, building_id="mill-a")
        mill_b = buildings.make_building("Mill", 4, 2, building_id="mill-b")
        state.buildings = {mill_a.id: mill_a, mill_b.id: mill_b}
        pawn = _worker("miller", "milling", level=19)
        state.pawns[pawn.id] = pawn
        state.stockpile.add(Good.GRAIN, 20)

        work.assign_jobs(state)
        first = state.pawns["miller"].assignment.building_id
        for _ in range(4):
            work.assign_jobs(state)
            self.assertEqual(state.pawns["miller"].assignment.building_id, first)


class DefaultCivilizationSourcingTests(unittest.TestCase):
    def test_default_civ_fields_are_staggered_and_owned(self):
        state = civilization.create_default_civilization()
        farms = [b for b in state.buildings.values() if b.kind == "Farm"]
        fields = [world.farm_field(state, farm) for farm in farms]
        self.assertTrue(all(field is not None for field in fields))
        ripe = [field for field in fields if field.state == NODE_READY]
        growing = [field for field in fields if field.state == NODE_GROWING]
        self.assertEqual(len(ripe), 1)
        self.assertEqual(len(growing), 3)
        self.assertGreater(state.seed_grain, 0)

    def test_default_civ_still_sustains_under_fallback_with_real_growth(self):
        # The Slice 0/1 survival claim re-verified against growth time: the
        # default civ keeps its people fed for three days when grain must be
        # planted, grown, and harvested rather than minted.
        state = civilization.create_default_civilization()
        engine.run_days(state, governor.FallbackGovernor(), days=3)

        self.assertGreaterEqual(economy.average_mood(state), 45)
        self.assertGreater(economy.food_days_of_cover(state), 0.0)
        self.assertGreaterEqual(economy.average_need(state, "food"), 0.5)


if __name__ == "__main__":
    unittest.main()
