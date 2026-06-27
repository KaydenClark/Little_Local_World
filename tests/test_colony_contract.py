import importlib
import unittest

from agent_town.core import (
    Building,
    ConstructionSite,
    Exception as GovernorException,
    FactionState,
    Good,
    GovernorAction,
    GridMap,
    JobRef,
    Pawn,
    Recipe,
    ResourceNode,
    ScheduleTemplate,
    Stockpile,
)


class ColonyContractTests(unittest.TestCase):
    def test_phase0_contract_shapes_can_be_instantiated(self):
        recipe = Recipe(
            inputs={Good.LOGS: 1},
            outputs={Good.PLANKS: 1},
            work_units=2.5,
            skill="woodcutting",
        )
        building = Building(
            kind="Sawmill",
            x=4,
            y=5,
            recipe=recipe,
            job_slots=2,
            staffed_by=["pawn-1"],
            built=True,
        )
        pawn = Pawn(
            id="pawn-1",
            name="Mira",
            skills={"woodcutting": 4},
            traits=("industrious",),
            wants=("wants_outdoor_work",),
            needs={"rest": 0.8, "food": 0.7, "recreation": 0.5},
            mood=0.75,
            schedule="day",
            assignment=JobRef(building_id="sawmill-1", role="worker"),
            x=4,
            y=5,
            state="working",
        )
        state = FactionState(
            stockpile=Stockpile(counts={Good.LOGS: 3}),
            coin=25,
            pawns=[pawn],
            buildings=[building],
            construction_sites=[
                ConstructionSite(
                    building_kind="Bakery",
                    required={Good.PLANKS: 4},
                    delivered={Good.PLANKS: 1},
                    work_remaining=10.0,
                )
            ],
            research="",
            season="spring",
            tax_rate=0.1,
            day=1,
            time_of_day=9,
        )

        self.assertEqual(ResourceNode(Good.STONE, 10, 2, 3).kind, Good.STONE)
        self.assertEqual(GridMap(width=8, height=6, tiles=("grass",) * 48).width, 8)
        self.assertEqual(ScheduleTemplate(name="day", blocks=["work"] * 24).blocks[9], "work")
        self.assertEqual(GovernorException(kind="idle", detail="no open jobs").kind, "idle")
        self.assertEqual(GovernorAction(action_type="assign_pawn", payload={"pawn_id": "pawn-1"}).action_type, "assign_pawn")
        self.assertEqual(state.buildings[0].recipe.outputs[Good.PLANKS], 1)

    def test_phase0_modules_import_without_pygame(self):
        for module_name in (
            "agent_town.world",
            "agent_town.economy",
            "agent_town.buildings",
            "agent_town.construction",
            "agent_town.pawns",
            "agent_town.mood",
            "agent_town.schedule",
            "agent_town.governor",
        ):
            with self.subTest(module=module_name):
                self.assertIsNotNone(importlib.import_module(module_name))

    def test_phase0_behavior_stubs_fail_explicitly(self):
        recipe = Recipe(inputs={}, outputs={Good.LOGS: 1}, work_units=1.0, skill="forestry")
        pawn = Pawn(
            id="pawn-1",
            name="Mira",
            skills={},
            traits=(),
            wants=(),
            needs={},
            mood=0.5,
            schedule="day",
            assignment=None,
            x=0,
            y=0,
            state="idle",
        )
        mood = importlib.import_module("agent_town.mood")
        with self.assertRaises(NotImplementedError):
            mood.effective_work(pawn, recipe, 9)


if __name__ == "__main__":
    unittest.main()
