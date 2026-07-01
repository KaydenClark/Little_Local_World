"""Minimal research spine: `set_research` must be a real lever.

The truth-loop audit found that `set_research` validated and applied but only
stored a string nothing read. These tests pin the smallest useful replacement:
the action selects an active tech, a staffed Laboratory turns work into research
progress, completing the first tech changes a measured production value, and the
fallback governor pursues research after the build order is stable.
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


def staffed(kind: str, skill: str, *, building_id: str):
    building = buildings.make_building(kind, 0, 0, building_id=building_id)
    pawn = worker(f"{building_id}-worker", skill)
    building.staffed_by.append(pawn.id)
    return building, pawn


class ResearchActionTests(unittest.TestCase):
    def test_set_research_selects_active_target_not_completed_tech(self):
        state = FactionState()

        applied = governor.apply_actions(
            state, [GovernorAction.set_research(economy.TECH_EFFICIENT_BAKING)]
        )

        self.assertEqual([action.kind for action in applied], ["set_research"])
        self.assertEqual(state.research_target, economy.TECH_EFFICIENT_BAKING)
        self.assertEqual(state.research, ())

    def test_unknown_research_target_is_rejected(self):
        state = FactionState()

        applied = governor.apply_actions(state, [GovernorAction.set_research("space-magic")])

        self.assertEqual(applied, [])
        self.assertIsNone(state.research_target)


class ResearchProductionTests(unittest.TestCase):
    def test_laboratory_progress_completes_first_tech(self):
        lab, researcher = staffed("Laboratory", "research", building_id="lab1")
        state = FactionState(
            buildings={lab.id: lab},
            pawns={researcher.id: researcher},
            research_target=economy.TECH_EFFICIENT_BAKING,
            research_points=economy.RESEARCH_COSTS[economy.TECH_EFFICIENT_BAKING] - 1,
            time_of_day=8,
        )

        completed = economy.research_tick(state)

        self.assertEqual(completed, (economy.TECH_EFFICIENT_BAKING,))
        self.assertIn(economy.TECH_EFFICIENT_BAKING, state.research)
        self.assertIsNone(state.research_target)
        self.assertEqual(state.research_points, 0)

    def test_efficient_baking_increases_bread_output(self):
        bakery, baker = staffed("Bakery", "baking", building_id="bakery1")
        state = FactionState(
            buildings={bakery.id: bakery},
            pawns={baker.id: baker},
            stockpile=Stockpile({Good.FLOUR: 2}),
            research=(economy.TECH_EFFICIENT_BAKING,),
            time_of_day=8,
        )

        economy.production_tick(state)

        self.assertEqual(state.stockpile.counts.get(Good.BREAD), 5)
        self.assertEqual(state.stockpile.counts.get(Good.FLOUR, 0), 0)


class ResearchFallbackTests(unittest.TestCase):
    def test_fallback_places_laboratory_after_build_order(self):
        state = FactionState()
        for index, (kind, _x, _y) in enumerate(governor.BUILD_ORDER):
            building = buildings.make_building(kind, index, 0, building_id=f"b{index}")
            state.buildings[building.id] = building

        actions = governor.FallbackGovernor().decide(governor.build_context(state))

        self.assertEqual([action.kind for action in actions], ["place_building"])
        self.assertEqual(actions[0].building_kind, "Laboratory")

    def test_fallback_queues_first_research_once_laboratory_exists(self):
        state = FactionState()
        for index, (kind, _x, _y) in enumerate(governor.BUILD_ORDER):
            building = buildings.make_building(kind, index, 0, building_id=f"b{index}")
            state.buildings[building.id] = building
        lab = buildings.make_building("Laboratory", 8, 1, building_id="lab1")
        state.buildings[lab.id] = lab

        actions = governor.FallbackGovernor().decide(governor.build_context(state))

        self.assertEqual([action.kind for action in actions], ["set_research"])
        self.assertEqual(actions[0].tech, economy.TECH_EFFICIENT_BAKING)


if __name__ == "__main__":
    unittest.main()
