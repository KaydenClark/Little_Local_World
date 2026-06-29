"""Civilization contract proof: frozen core shapes import, instantiate, and the
cross-track seam is callable.

Headless - no Pygame.
"""

import importlib
import inspect
import unittest

from agent_town import core


CIVILIZATION_MODULES = [
    "world",
    "buildings",
    "economy",
    "construction",
    "schedule",
    "mood",
    "pawns",
    "governor",
]


class ContractDataclassTests(unittest.TestCase):
    def test_goods_enum_has_build1_chain(self):
        names = {g.value for g in core.Good}
        self.assertEqual(
            names, {"logs", "planks", "grain", "flour", "bread", "stone"}
        )

    def test_faction_state_is_the_root_container(self):
        state = core.FactionState()
        self.assertIsInstance(state.stockpile, core.Stockpile)
        self.assertEqual(state.coin, 0)
        self.assertEqual(state.pawns, {})
        self.assertEqual(state.buildings, {})
        self.assertEqual(state.construction_sites, {})
        self.assertEqual(state.time_of_day, 0)
        self.assertEqual(state.day, 0)

    def test_core_entities_instantiate_with_expected_fields(self):
        recipe = core.Recipe(
            inputs={core.Good.LOGS: 1},
            outputs={core.Good.PLANKS: 1},
            work_units=4.0,
            skill="woodcutting",
        )
        building = core.Building(
            id="saw1", kind="Sawmill", x=2, y=3, recipe=recipe, job_slots=2
        )
        self.assertTrue(building.built)
        self.assertEqual(building.staffed_by, [])

        pawn = core.Pawn(id="p1", name="Ada", skills={"woodcutting": 5})
        pawn.assignment = core.JobRef(building_id="saw1", role="woodcutting")
        self.assertEqual(pawn.assignment.building_id, "saw1")

        site = core.ConstructionSite(
            id="c1", building_kind="Sawmill", x=2, y=3, required={core.Good.PLANKS: 5}
        )
        self.assertEqual(site.delivered, {})

        exc = core.CivilizationException(kind="unstaffed", building_id="saw1", detail="empty")
        self.assertEqual(exc.pawn_id, None)

    def test_schedule_template_requires_24_blocks(self):
        blocks = tuple(["sleep"] * 6 + ["work"] * 10 + ["rec"] * 4 + ["sleep"] * 4)
        template = core.ScheduleTemplate("day", blocks)
        self.assertEqual(template.block_at(8), "work")
        self.assertEqual(template.block_at(0), "sleep")
        with self.assertRaises(ValueError):
            core.ScheduleTemplate("bad", ("work",))

    def test_grid_map_bounds_and_lookup(self):
        grid = core.GridMap(2, 2, (("grass", "grass"), ("grass", "tree")))
        self.assertTrue(grid.in_bounds(1, 1))
        self.assertFalse(grid.in_bounds(2, 0))
        self.assertEqual(grid.tile_at(1, 1), "tree")
        with self.assertRaises(IndexError):
            grid.tile_at(5, 5)


class GovernorActionTests(unittest.TestCase):
    def test_factory_methods_set_the_right_kind(self):
        self.assertEqual(
            core.GovernorAction.assign_pawn("p1", "saw1", "woodcutting").kind,
            core.ACTION_ASSIGN_PAWN,
        )
        self.assertEqual(
            core.GovernorAction.set_schedule("p1", "night").kind,
            core.ACTION_SET_SCHEDULE,
        )
        self.assertEqual(
            core.GovernorAction.place_building("Farm", 4, 5).kind,
            core.ACTION_PLACE_BUILDING,
        )
        target = core.GovernorAction.set_production_target("mill1", core.Good.FLOUR, 20)
        self.assertEqual(target.kind, core.ACTION_SET_PRODUCTION_TARGET)
        self.assertEqual(target.good, core.Good.FLOUR)
        self.assertEqual(
            core.GovernorAction.set_research("better_tools").kind,
            core.ACTION_SET_RESEARCH,
        )


class SeamTests(unittest.TestCase):
    def test_effective_work_signature_is_frozen(self):
        from agent_town import mood

        params = list(inspect.signature(mood.effective_work).parameters)
        self.assertEqual(params, ["pawn", "recipe", "time_of_day"])

    def test_effective_work_placeholder_returns_float(self):
        from agent_town import mood

        pawn = core.Pawn(id="p", name="P")
        recipe = core.Recipe({}, {}, 1.0, "woodcutting")
        result = mood.effective_work(pawn, recipe, 8)
        self.assertIsInstance(result, float)


class SkeletonTests(unittest.TestCase):
    def test_all_civilization_modules_import(self):
        for name in CIVILIZATION_MODULES:
            with self.subTest(module=name):
                importlib.import_module(f"agent_town.{name}")

    def test_track_a_modules_are_implemented(self):
        from agent_town import buildings, construction, economy, world

        state = core.FactionState()
        self.assertFalse(core.Stockpile().has(core.Good.LOGS, 1))
        self.assertEqual(economy.daily_tax_income(state), 0)
        self.assertTrue(world.generate_map(8, 8).in_bounds(7, 7))
        self.assertEqual(buildings.building_def("Sawmill").kind, "Sawmill")
        self.assertFalse(
            construction.goods_satisfied(
                core.ConstructionSite(id="c", building_kind="Sawmill", x=0, y=0, required={core.Good.PLANKS: 1})
            )
        )


if __name__ == "__main__":
    unittest.main()
