"""Crisis-line Slice 3: the trader - a deterministic coin -> bread trade core.

Covers the deterministic trade mechanics (buy_good clamps to price, treasury,
the per-transaction cap, and storage headroom; conservation holds), the
governor levers (buy_good validates/applies like every other GovernorAction;
the fallback's trader_relief_action tops bread up to one day of cover during a
food shortage, alongside the existing dig-out expansion), the model-safety
guard (bread only, a bounded positive amount), and the optional local-LLM
trader personality (hard fallback to a default quip on any client error,
mirroring LLMGovernor's hard fallback).
"""

import unittest

from agent_town import economy, engine, governor, health
from agent_town import pawns as pawns_mod
from agent_town.core import FactionState, Good, GovernorAction, NEED_FOOD, Pawn, Stockpile
from agent_town.llm import LLMClientError, LocalLLMClient


def _hungry_pawn(pid: str) -> Pawn:
    """A pawn with every need full except food, near-empty (see test_dig_out.py)."""
    return Pawn(id=pid, name=pid, needs={n: 1.0 for n in pawns_mod.BUILD1_NEEDS} | {NEED_FOOD: 0.05})


class BuyGoodCoreTests(unittest.TestCase):
    def test_buys_the_requested_amount_when_affordable(self):
        state = FactionState(coin=10)

        result = economy.buy_good(state, Good.BREAD, 3)

        price = economy.TRADER_PRICES[Good.BREAD]
        self.assertEqual(result.units, 3)
        self.assertEqual(result.coin_spent, 3 * price)
        self.assertEqual(state.coin, 10 - 3 * price)
        self.assertEqual(state.stockpile.counts[Good.BREAD], 3)

    def test_clamps_to_what_the_treasury_can_afford(self):
        price = economy.TRADER_PRICES[Good.BREAD]
        state = FactionState(coin=price)  # exactly one unit's worth

        result = economy.buy_good(state, Good.BREAD, 5)

        self.assertEqual(result.units, 1)
        self.assertEqual(state.coin, 0)

    def test_zero_coin_buys_nothing(self):
        state = FactionState(coin=0)

        result = economy.buy_good(state, Good.BREAD, 5)

        self.assertEqual(result, economy.TradeResult())
        self.assertNotIn(Good.BREAD, state.stockpile.counts)

    def test_clamps_to_the_per_transaction_cap(self):
        state = FactionState(coin=10_000)

        result = economy.buy_good(state, Good.BREAD, 10_000)

        self.assertEqual(result.units, economy.TRADER_MAX_PURCHASE)

    def test_clamps_to_storage_headroom(self):
        state = FactionState(coin=10_000, stockpile=Stockpile(capacity=5))

        result = economy.buy_good(state, Good.BREAD, 10_000)

        self.assertEqual(result.units, 5)
        self.assertEqual(state.stockpile.used_capacity(), 5)

    def test_full_storage_is_a_no_op_not_a_capacity_error(self):
        state = FactionState(coin=10_000, stockpile=Stockpile(counts={Good.BREAD: 5}, capacity=5))

        result = economy.buy_good(state, Good.BREAD, 3)

        self.assertEqual(result, economy.TradeResult())
        self.assertEqual(state.coin, 10_000)

    def test_untradeable_good_is_a_no_op(self):
        state = FactionState(coin=100)

        result = economy.buy_good(state, Good.STONE, 3)

        self.assertEqual(result, economy.TradeResult())
        self.assertEqual(state.coin, 100)

    def test_non_positive_amount_is_a_no_op(self):
        state = FactionState(coin=100)

        self.assertEqual(economy.buy_good(state, Good.BREAD, 0), economy.TradeResult())
        self.assertEqual(economy.buy_good(state, Good.BREAD, -1), economy.TradeResult())
        self.assertEqual(state.coin, 100)

    def test_conservation_ledger_holds_after_a_trade(self):
        state = FactionState(coin=100)

        economy.buy_good(state, Good.BREAD, 4)

        self.assertEqual(health.check_invariants(state), [])


class GovernorActionValidationTests(unittest.TestCase):
    def test_validate_allows_an_affordable_buy(self):
        state = FactionState(coin=10)
        action = governor.buy_good_action(Good.BREAD, 2)

        self.assertTrue(governor.validate_action(state, action))

    def test_validate_rejects_when_treasury_cannot_afford_one_unit(self):
        state = FactionState(coin=0)
        action = governor.buy_good_action(Good.BREAD, 2)

        self.assertFalse(governor.validate_action(state, action))

    def test_validate_rejects_untradeable_good(self):
        state = FactionState(coin=100)
        action = governor.buy_good_action(Good.STONE, 2)

        self.assertFalse(governor.validate_action(state, action))

    def test_validate_rejects_missing_or_non_positive_amount(self):
        state = FactionState(coin=100)

        self.assertFalse(
            governor.validate_action(
                state, GovernorAction(kind=governor.ACTION_BUY_GOOD, good=Good.BREAD, amount=None)
            )
        )
        self.assertFalse(governor.validate_action(state, governor.buy_good_action(Good.BREAD, 0)))

    def test_apply_actions_buys_and_reports_the_action_applied(self):
        state = FactionState(coin=10)
        action = governor.buy_good_action(Good.BREAD, 2)

        applied = governor.apply_actions(state, [action])

        self.assertEqual(applied, [action])
        self.assertEqual(state.stockpile.counts[Good.BREAD], 2)

    def test_apply_actions_drops_a_trade_storage_cannot_hold(self):
        state = FactionState(coin=10, stockpile=Stockpile(counts={Good.BREAD: 5}, capacity=5))
        action = governor.buy_good_action(Good.BREAD, 2)

        # Structurally legal (affordable) but nothing can physically arrive.
        self.assertTrue(governor.validate_action(state, action))
        applied = governor.apply_actions(state, [action])

        self.assertEqual(applied, [])
        self.assertEqual(state.coin, 10)


class TraderReliefTests(unittest.TestCase):
    """The fallback's second escape valve: buy today's bread while wheat grows."""

    def test_no_relief_when_food_is_healthy(self):
        context = {"faction": {"population": 4, "coin": 50, "food_days_of_cover": 5.0}}

        self.assertIsNone(governor.trader_relief_action(context))

    def test_no_relief_without_coin(self):
        context = {"faction": {"population": 4, "coin": 0, "food_days_of_cover": 0.1}}

        self.assertIsNone(governor.trader_relief_action(context))

    def test_relief_buys_bread_when_short_and_affordable(self):
        context = {"faction": {"population": 4, "coin": 50, "food_days_of_cover": 0.0}}

        action = governor.trader_relief_action(context)

        self.assertIsNotNone(action)
        self.assertEqual(action.kind, governor.ACTION_BUY_GOOD)
        self.assertEqual(action.good, Good.BREAD)
        self.assertGreater(action.amount, 0)
        self.assertLessEqual(action.amount, economy.TRADER_MAX_PURCHASE)

    def test_fallback_governor_proposes_relief_alongside_the_dig_out(self):
        state = FactionState()
        state.coin = 50
        state.pawns["a"] = _hungry_pawn("a")
        state.pawns["b"] = _hungry_pawn("b")
        # No bread and hungry pawns -> low_food fires (see test_dig_out.py).

        context = governor.build_context(state)
        actions = governor.FallbackGovernor().decide(context)

        self.assertIn(governor.ACTION_BUY_GOOD, [a.kind for a in actions])

    def test_fallback_governor_skips_relief_when_treasury_is_empty(self):
        state = FactionState()
        state.coin = 0
        state.pawns["a"] = _hungry_pawn("a")

        context = governor.build_context(state)
        actions = governor.FallbackGovernor().decide(context)

        self.assertNotIn(governor.ACTION_BUY_GOOD, [a.kind for a in actions])


class ModelSafetyGuardTests(unittest.TestCase):
    def test_action_from_dict_parses_buy_good(self):
        action = governor.action_from_dict({"kind": "buy_good", "good": "bread", "amount": "4"})

        self.assertEqual(action.kind, governor.ACTION_BUY_GOOD)
        self.assertEqual(action.good, Good.BREAD)
        self.assertEqual(action.amount, 4)

    def test_model_may_buy_bread(self):
        action = governor.buy_good_action(Good.BREAD, 4)

        self.assertEqual(governor.filter_model_actions({}, [action]), [action])

    def test_model_may_not_buy_a_good_other_than_bread(self):
        action = governor.buy_good_action(Good.STONE, 4)

        self.assertEqual(governor.filter_model_actions({}, [action]), [])

    def test_model_buy_good_needs_a_positive_amount(self):
        action = GovernorAction(kind=governor.ACTION_BUY_GOOD, good=Good.BREAD, amount=0)

        self.assertEqual(governor.filter_model_actions({}, [action]), [])

    def test_llm_governor_buy_good_proposal_survives_the_guard(self):
        state = FactionState(coin=20)
        state.pawns["p1"] = _hungry_pawn("p1")
        context = governor.build_context(state)
        gov = governor.LLMGovernor(
            propose=lambda ctx: {"actions": [{"kind": "buy_good", "good": "bread", "amount": 3}]}
        )

        actions = gov.decide(context)

        self.assertEqual([a.kind for a in actions], [governor.ACTION_BUY_GOOD])
        self.assertEqual(gov.last_guard_rejected, [])


class TraderQuipTests(unittest.TestCase):
    """Optional local-LLM trader personality; cosmetic only, hard fallback safe."""

    def test_default_quip_when_no_client(self):
        quip = governor.trader_quip(None, good=Good.BREAD, units=3, coin_spent=6)

        self.assertEqual(quip, governor.DEFAULT_TRADER_QUIP)

    def test_default_quip_when_client_disabled(self):
        client = LocalLLMClient(model=None)

        quip = governor.trader_quip(client, good=Good.BREAD, units=3, coin_spent=6)

        self.assertEqual(quip, governor.DEFAULT_TRADER_QUIP)

    def test_uses_the_model_quip_when_enabled(self):
        client = LocalLLMClient(
            model="test-model",
            http_post=lambda payload, timeout: {
                "choices": [{"message": {"content": '{"quip": "Fresh loaves, fair price!"}'}}]
            },
        )

        quip = governor.trader_quip(client, good=Good.BREAD, units=3, coin_spent=6)

        self.assertEqual(quip, "Fresh loaves, fair price!")

    def test_hard_falls_back_to_default_on_any_client_error(self):
        def boom(payload, timeout):
            raise LLMClientError("offline")

        client = LocalLLMClient(model="test-model", http_post=boom)

        quip = governor.trader_quip(client, good=Good.BREAD, units=3, coin_spent=6)

        self.assertEqual(quip, governor.DEFAULT_TRADER_QUIP)

    def test_hard_falls_back_on_malformed_model_reply(self):
        client = LocalLLMClient(
            model="test-model",
            http_post=lambda payload, timeout: {"choices": [{"message": {"content": "not json"}}]},
        )

        quip = governor.trader_quip(client, good=Good.BREAD, units=3, coin_spent=6)

        self.assertEqual(quip, governor.DEFAULT_TRADER_QUIP)


class EngineIntegrationTests(unittest.TestCase):
    def test_step_hour_applies_a_proposed_buy_good(self):
        state = FactionState(coin=10)
        state.pawns["a"] = _hungry_pawn("a")

        class OneShotGovernor:
            def decide(self, context):
                return [governor.buy_good_action(Good.BREAD, 2)]

        result = engine.step_hour(state, OneShotGovernor())

        self.assertIn(governor.ACTION_BUY_GOOD, [a.kind for a in result.actions_applied])
        self.assertGreater(state.stockpile.counts.get(Good.BREAD, 0), 0)


if __name__ == "__main__":
    unittest.main()
