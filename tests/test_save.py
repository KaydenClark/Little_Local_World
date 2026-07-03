"""Save/load: the pocket universe survives a window close.

The strongest oracle here is determinism: because the engine is deterministic,
a civilization that is saved, reloaded, and stepped N hours must land in
exactly the same place as one that never stopped. If any field fails to
round-trip (a thought, a banked cycle fraction, a growing field, dict order),
the trajectories diverge and this suite catches it.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from agent_town import civilization, economy, engine, governor, health, save
from agent_town.core import Good


def _advance(state, hours):
    gov = governor.FallbackGovernor()
    for _ in range(hours):
        engine.step_hour(state, gov)


class RoundTripTests(unittest.TestCase):
    def test_fresh_civ_round_trips_exactly(self):
        state = civilization.create_default_civilization()
        clone = save.from_dict(save.to_dict(state))

        self.assertEqual(save.to_dict(clone), save.to_dict(state))
        self.assertEqual(health.check_invariants(clone), [])

    def test_mid_run_civ_round_trips_exactly(self):
        state = civilization.create_default_civilization()
        _advance(state, 30)  # thoughts, banked cycles, growing fields, wallets
        clone = save.from_dict(save.to_dict(state))

        self.assertEqual(save.to_dict(clone), save.to_dict(state))
        self.assertEqual(health.check_invariants(clone), [])

    def test_loaded_civ_steps_identically_to_one_that_never_stopped(self):
        original = civilization.create_default_civilization()
        _advance(original, 17)  # mid-day, mid-growth, mid-everything
        reloaded = save.from_dict(save.to_dict(original))

        _advance(original, 48)
        _advance(reloaded, 48)

        self.assertEqual(save.to_dict(reloaded), save.to_dict(original))

    def test_unsupported_format_is_rejected(self):
        data = save.to_dict(civilization.create_default_civilization())
        data["format"] = 999
        with self.assertRaisesRegex(ValueError, "Unsupported save format"):
            save.from_dict(data)


class SaveFileTests(unittest.TestCase):
    def test_save_and_load_state_files(self):
        state = civilization.create_default_civilization()
        _advance(state, 5)
        with tempfile.TemporaryDirectory() as tmp:
            path = save.save_state(state, Path(tmp) / "world.json")
            loaded = save.load_state(path)
        self.assertEqual(save.to_dict(loaded), save.to_dict(state))

    def test_load_autosave_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(save.load_autosave(tmp))

    def test_load_autosave_corrupt_returns_none_not_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            save.autosave_path(tmp).parent.mkdir(parents=True, exist_ok=True)
            save.autosave_path(tmp).write_text("{not json", encoding="utf-8")
            self.assertIsNone(save.load_autosave(tmp))

    def test_autosave_round_trip_keeps_the_clock_and_stock(self):
        state = civilization.create_default_civilization()
        _advance(state, 26)  # into day 1
        with tempfile.TemporaryDirectory() as tmp:
            save.save_state(state, save.autosave_path(tmp))
            loaded = save.load_autosave(tmp)
        self.assertIsNotNone(loaded)
        self.assertEqual((loaded.day, loaded.time_of_day), (state.day, state.time_of_day))
        self.assertEqual(
            loaded.stockpile.counts.get(Good.BREAD, 0), state.stockpile.counts.get(Good.BREAD, 0)
        )
        self.assertEqual(loaded.seed_grain, state.seed_grain)
        self.assertAlmostEqual(
            economy.food_days_of_cover(loaded), economy.food_days_of_cover(state)
        )


class ViewerResumeTests(unittest.TestCase):
    def test_viewer_resumes_the_autosave_on_boot(self):
        from agent_town.civilization_view import CivilizationViewer

        state = civilization.create_default_civilization()
        _advance(state, 30)
        with tempfile.TemporaryDirectory() as tmp:
            save.save_state(state, save.autosave_path(tmp))
            viewer = CivilizationViewer(
                smoke_test=False, governor=governor.FallbackGovernor(), save_dir=tmp
            )
            try:
                self.assertTrue(viewer.resumed_from_save)
                self.assertEqual((viewer.state.day, viewer.state.time_of_day), (state.day, state.time_of_day))
            finally:
                viewer._shutdown_governor()

    def test_viewer_starts_fresh_when_resume_disabled(self):
        from agent_town.civilization_view import CivilizationViewer

        state = civilization.create_default_civilization()
        _advance(state, 30)
        with tempfile.TemporaryDirectory() as tmp:
            save.save_state(state, save.autosave_path(tmp))
            viewer = CivilizationViewer(
                smoke_test=False, governor=governor.FallbackGovernor(), save_dir=tmp, resume=False
            )
            try:
                self.assertFalse(viewer.resumed_from_save)
                self.assertEqual(viewer.state.day, 0)
            finally:
                viewer._shutdown_governor()


if __name__ == "__main__":
    unittest.main()
