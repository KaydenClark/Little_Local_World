import unittest

from agent_town.construction import advance_construction, create_construction_site
from agent_town.core import ConstructionSite, FactionState, Good, Stockpile


def _state(site, stockpile=None):
    return FactionState(
        stockpile=stockpile or Stockpile(),
        coin=0,
        pawns=[],
        buildings=[],
        construction_sites=[site],
        research="",
        season="spring",
        tax_rate=0.1,
        day=1,
        time_of_day=9,
    )


class ConstructionTests(unittest.TestCase):
    def test_create_construction_site_sets_required_goods_and_position(self):
        site = create_construction_site("Sawmill", 4, 5)

        self.assertEqual(site.building_kind, "Sawmill")
        self.assertEqual(site.required, {Good.PLANKS: 4, Good.STONE: 2})
        self.assertEqual(site.delivered, {})
        self.assertGreater(site.work_remaining, 0)
        self.assertEqual((site.x, site.y), (4, 5))

    def test_create_construction_site_rejects_unknown_building_kind(self):
        with self.assertRaisesRegex(ValueError, "Unknown building kind"):
            create_construction_site("Moon Mill", 1, 1)

    def test_partial_delivery_moves_available_goods_without_work(self):
        site = create_construction_site("Sawmill", 4, 5)
        state = _state(site, Stockpile({Good.PLANKS: 2, Good.STONE: 1}))

        advance_construction(state, site, 1.0)

        self.assertEqual(site.delivered, {Good.PLANKS: 2, Good.STONE: 1})
        self.assertEqual(state.stockpile.counts, {})
        self.assertEqual(site.work_remaining, 4.0)
        self.assertEqual(state.buildings, [])
        self.assertEqual(state.construction_sites, [site])

    def test_missing_goods_leave_work_unchanged(self):
        site = ConstructionSite(
            building_kind="Sawmill",
            required={Good.PLANKS: 4, Good.STONE: 2},
            delivered={Good.PLANKS: 4},
            work_remaining=2.0,
            x=4,
            y=5,
        )
        state = _state(site, Stockpile())

        advance_construction(state, site, 1.0)

        self.assertEqual(site.delivered, {Good.PLANKS: 4})
        self.assertEqual(site.work_remaining, 2.0)
        self.assertEqual(state.buildings, [])

    def test_delivered_site_consumes_work_until_complete(self):
        site = create_construction_site("Sawmill", 4, 5)
        state = _state(site, Stockpile({Good.PLANKS: 4, Good.STONE: 2}))

        advance_construction(state, site, 1.5)

        self.assertEqual(site.delivered, {Good.PLANKS: 4, Good.STONE: 2})
        self.assertEqual(state.stockpile.counts, {})
        self.assertEqual(site.work_remaining, 2.5)
        self.assertEqual(state.buildings, [])
        self.assertEqual(state.construction_sites, [site])

    def test_completed_site_adds_built_building_and_removes_site(self):
        site = ConstructionSite(
            building_kind="Sawmill",
            required={Good.PLANKS: 4, Good.STONE: 2},
            delivered={},
            work_remaining=1.0,
            x=4,
            y=5,
        )
        state = _state(site, Stockpile({Good.PLANKS: 4, Good.STONE: 2}))

        advance_construction(state, site, 1.0)

        self.assertEqual(state.construction_sites, [])
        self.assertEqual(len(state.buildings), 1)
        building = state.buildings[0]
        self.assertEqual(building.kind, "Sawmill")
        self.assertTrue(building.built)
        self.assertEqual((building.x, building.y), (4, 5))


if __name__ == "__main__":
    unittest.main()
