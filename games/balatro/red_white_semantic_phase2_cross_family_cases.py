from __future__ import annotations

"""Final Phase-2 semantics for simple cross-family SHOP arbitration."""

from types import SimpleNamespace

from games.balatro.actions import BUY_VOUCHER, END_SHOP, BalatroAction
from games.balatro.joker_policy import (
    BUY,
    JokerAcquisitionDecision,
    JokerAcquisitionOption,
    JokerAcquisitionThresholds,
    JokerTransactionEconomics,
)
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_policy import ShopActionScore
from games.balatro.shop_reroll_policy import ShopRerollRecommendation
from games.balatro.state import BalatroState


class _ShopPolicy:
    hold_bias = 0.0

    def __init__(self, deterministic_total: float) -> None:
        self.deterministic_total = float(deterministic_total)

    def rank_actions(self, state, actions):
        del state
        return [
            ShopActionScore(
                action=action,
                total=self.deterministic_total,
                notes=("synthetic deterministic support/economy value",),
            )
            for action in actions
        ]


class _JokerPolicy:
    def __init__(self, build_gain: float) -> None:
        economics = JokerTransactionEconomics(
            price=0,
            sell_credit=0,
            net_spend=0,
            money_after=20,
            edition_delta=0.0,
            price_penalty=0.0,
            interest_penalty=0.0,
            reserve_penalty=0.0,
            slot_penalty=0.0,
        )
        option = JokerAcquisitionOption(
            mode=BUY,
            build_gain=float(build_gain),
            total_advantage=float(build_gain),
            economics=economics,
            eligible=True,
        )
        self.decision = JokerAcquisitionDecision(
            action=BUY,
            candidate="FlatMultJoker",
            selected=option,
            options=(option,),
            thresholds=JokerAcquisitionThresholds(),
            rationale=("synthetic admitted scoring Joker",),
        )

    def decide(self, state, candidate):
        del state, candidate
        return self.decision


class _HoldRerollPolicy:
    def recommend(self, state, visible_actions, *, reroll_cost, visible_score_floor=None):
        del state, visible_actions, reroll_cost, visible_score_floor
        return ShopRerollRecommendation(
            decision="HOLD",
            reroll_cost=5,
            executable_action=None,
            current_best_score=0.0,
            future_shop_ev=0.0,
            reroll_resource_cost=0.0,
            reroll_score=-1.0,
            rationale=("synthetic reroll HOLD",),
        )


class _UnusedPolicy:
    def recommend(self, *args, **kwargs):
        raise AssertionError("unexpected booster recommendation request")

    def decide(self, *args, **kwargs):
        raise AssertionError("unexpected consumable decision request")


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.ante = 1
    state.joker_slots = 5
    state.jokers = []
    state.shop_jokers = [FlatMultJoker(4)]
    state.shop_consumables = []
    return state


def _decide(*, joker_gain: float, deterministic_gain: float):
    arbiter = BuildAwareShopArbiter(
        shop_policy=_ShopPolicy(deterministic_gain),
        reroll_policy=_HoldRerollPolicy(),
        joker_policy=_JokerPolicy(joker_gain),
        consumable_policy=_UnusedPolicy(),
        booster_policy=_UnusedPolicy(),
    )
    voucher = SimpleNamespace(name="Synthetic Support Voucher")
    return arbiter.decide(
        _state(),
        [BalatroAction(BUY_VOUCHER, target=voucher), BalatroAction(END_SHOP)],
        reroll_cost=5,
    )


def _first_scoring_engine_beats_weaker_support() -> SemanticCheck:
    decision = _decide(joker_gain=4.0, deterministic_gain=1.0)
    return SemanticCheck(
        decision.source == "JOKER_BUY" and decision.normalized_gain > 1.0,
        observed=(
            f"source={decision.source}, action={decision.action.name}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="the higher shared-value first scoring engine beats a weaker support/economy purchase",
        detail=(
            "D14 must compare admitted families on one parent scale; an early scoring foothold cannot be "
            "lost merely because a lower-value deterministic support option was also admitted"
        ),
    )


def _support_can_beat_weaker_first_engine() -> SemanticCheck:
    decision = _decide(joker_gain=1.0, deterministic_gain=4.0)
    return SemanticCheck(
        decision.source == "DETERMINISTIC" and decision.normalized_gain >= 4.0,
        observed=(
            f"source={decision.source}, action={decision.action.name}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="first-engine status is not a hardcoded family priority over materially stronger support value",
        detail=(
            "the first scoring engine preference is survival evidence, not a second arbiter; D14 must still "
            "select whichever admitted option has the higher normalized run value"
        ),
    )


RED_WHITE_PHASE2_CROSS_FAMILY_CASES = (
    SemanticBenchmarkCase(
        case_id="shop.simple.cross_family_first_engine_wins",
        category="SHOP_SURVIVAL",
        description="higher-value first scoring engine wins cross-family D14 arbitration",
        evaluate=_first_scoring_engine_beats_weaker_support,
        source="Phase 2 simple-shop audit: shared-scale scoring foothold precedence",
    ),
    SemanticBenchmarkCase(
        case_id="shop.simple.cross_family_support_can_win",
        category="SHOP_SURVIVAL",
        description="cross-family D14 arbitration remains value-based rather than Joker-hardcoded",
        evaluate=_support_can_beat_weaker_first_engine,
        source="Phase 2 simple-shop audit: shared-scale reverse precedence",
    ),
)
