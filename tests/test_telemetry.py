import io
import json
import unittest

from agent_town import civilization, engine, pawns, telemetry
from agent_town.core import FactionState, Good, GovernorAction, Pawn


def _state_with_one_pawn() -> FactionState:
    state = FactionState(day=0, time_of_day=8, coin=12)
    state.stockpile.add(Good.BREAD, 3)
    state.pawns["p1"] = Pawn(
        id="p1",
        name="Pat",
        needs={need: 1.0 for need in pawns.BUILD1_NEEDS},
        mood=75.0,
    )
    return state


class SnapshotTests(unittest.TestCase):
    def test_snapshot_contains_operator_fields(self):
        state = _state_with_one_pawn()
        result = engine.StepResult(tax_collected=2, days_rolled=1)

        snapshot = telemetry.build_snapshot(state, result)

        self.assertEqual(snapshot["type"], "snapshot")
        self.assertEqual(snapshot["day"], 0)
        self.assertEqual(snapshot["hour"], 8)
        self.assertEqual(snapshot["population"], 1)
        self.assertEqual(snapshot["coin"], 12)
        self.assertEqual(snapshot["stockpile"]["bread"], 3)
        self.assertEqual(snapshot["tax_collected"], 2)
        self.assertEqual(snapshot["days_rolled"], 1)
        self.assertIn("food", snapshot["avg_needs"])


class RunLoggerTests(unittest.TestCase):
    def test_logger_writes_parseable_jsonl_to_stream_sink(self):
        stream = io.StringIO()
        logger = telemetry.RunLogger(telemetry.JsonlStreamSink(stream), run_id="test-run")
        state = _state_with_one_pawn()

        logger.log_run_start(state, governor_kind="fallback", model="", config={"hours": 1})
        logger.log_hour(state, engine.StepResult(), governor=None)
        logger.log_run_end(state)

        records = [json.loads(line) for line in stream.getvalue().splitlines()]
        self.assertEqual([record["type"] for record in records[:3]], ["run_start", "snapshot", "decision"])
        self.assertEqual(records[-1]["type"], "run_end")

    def test_diff_events_include_depleted_bread_and_new_breaks(self):
        logger = telemetry.RunLogger(telemetry.RingBufferSink(maxlen=20), run_id="test-run")
        state = _state_with_one_pawn()
        previous = telemetry.build_snapshot(state, engine.StepResult())

        state.stockpile.remove(Good.BREAD, 3)
        state.pawns["p1"].state = pawns.STATE_WANDERING
        logger.log_hour(state, engine.StepResult(), governor=None, previous_snapshot=previous)

        events = [record for record in logger.records if record["type"] == "event"]
        self.assertTrue(any(event["kind"] == "good_depleted" for event in events))
        self.assertTrue(any(event["kind"] == "pawn_break" for event in events))

    def test_logging_on_or_off_leaves_sim_state_identical(self):
        with_logs = civilization.create_default_civilization()
        without_logs = civilization.create_default_civilization()
        logger = telemetry.RunLogger(telemetry.NullSink())

        for _ in range(6):
            result = engine.step_hour(with_logs)
            logger.log_hour(with_logs, result, governor=None)
            engine.step_hour(without_logs)

        self.assertEqual(with_logs.day, without_logs.day)
        self.assertEqual(with_logs.time_of_day, without_logs.time_of_day)
        self.assertEqual(with_logs.coin, without_logs.coin)
        self.assertEqual(with_logs.stockpile.counts, without_logs.stockpile.counts)
        self.assertEqual(
            {pid: (pawn.assignment, round(pawn.mood, 6), pawn.state) for pid, pawn in with_logs.pawns.items()},
            {pid: (pawn.assignment, round(pawn.mood, 6), pawn.state) for pid, pawn in without_logs.pawns.items()},
        )


class TelemetryGovernorTests(unittest.TestCase):
    def test_telemetry_governor_is_pass_through_and_records_actions(self):
        actions = [GovernorAction.set_schedule("all", "rest")]

        class Inner:
            status = object()

            def decide(self, context):
                return list(actions)

        wrapped = telemetry.TelemetryGovernor(Inner())

        self.assertEqual(wrapped.decide({"x": 1}), actions)
        self.assertEqual(wrapped.last_actions, tuple(actions))
        self.assertIs(wrapped.status, Inner.status)
        self.assertGreaterEqual(wrapped.last_latency, 0.0)


if __name__ == "__main__":
    unittest.main()
