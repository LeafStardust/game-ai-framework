from __future__ import annotations

from types import SimpleNamespace

from games.balatro.actions import BUY_AND_USE_CONSUMABLE, BUY_BOOSTER, END_SHOP, BalatroAction
from games.balatro.consumable import Consumable, ConsumableContext
from games.balatro.semantic_benchmark import SemanticBenchmarkCase, SemanticCheck
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import BUY as BOOSTER_BUY, ShopBoosterRecommendation
from games.balatro.shop_consumable_policy import (
    BUY_AND_USE,
    ConsumableAcquisitionDecision,
    ConsumableAcquisitionOption,
    ConsumableAcquisitionThresholds,
    ConsumableTransactionEconomics,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_reroll_policy import ShopRerollRecommendation
from games.balatro.state import BalatroState


class _SyntheticConsumable(Consumable):
    category = "TAROT"

    def __init__(self, name: str = "The Hermit", *, price: int = 0) -> None:
        self.name = name
        self.price = int(price)

    def can_use(self, context: ConsumableContext) -> bool:
        return True

    def use(self, context: ConsumableContext) -> ConsumableContext:
        return context


class _FixedConsumablePolicy:
    def __init__(self, *, child_build_gain: float, immediate_gain: float) -> None:
        self.child_build_gain = float(child_build_gain)
        self.immediate_gain = float(immediate_gain)

    def decide(self, state, candidate):
        economics = ConsumableTransactionEconomics(
            price=int(getattr(candidate, "price", 0)),
            money_after=int(state.money) - int(getattr(candidate, "price", 0)),
            price_penalty=0.0,
            interest_penalty=0.0,
            reserve_penalty=0.0,
            slot_penalty=0.0,
        )
        option = ConsumableAcquisitionOption(
            mode=BUY_AND_USE,
            build_gain=self.child_build_gain,
            immediate_gain=self.immediate_gain,
            total_advantage=self.child_build_gain + self.immediate_gain,
            economics=economics,
            eligible=True,
            executable_action=BalatroAction(BUY_AND_USE_CONSUMABLE, target=candidate),
            rationale=("synthetic admitted D4 option",),
        )
        return ConsumableAcquisitionDecision(
            action=BUY_AND_USE,
            candidate=str(getattr(candidate, "name", "synthetic")),
            selected=option,
            options=(option,),
            thresholds=ConsumableAcquisitionThresholds(),
            rationale=("synthetic D4 admission",),
        )


class _FixedBoosterPolicy:
    def __init__(self, *, option_utility: float) -> None:
        self.option_utility = float(option_utility)

    def recommend(self, state, action):
        del state
        return ShopBoosterRecommendation(
            decision=BOOSTER_BUY,
            action=action,
            family="ARCANA",
            variant="NORMAL",
            total=self.option_utility,
            advantage_over_save=self.option_utility,
            option_utility=self.option_utility,
            rationale=("synthetic admitted D8 option",),
        )


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


class _UnusedJokerPolicy:
    def decide(self, *args, **kwargs):
        raise AssertionError("unexpected Joker decision")


def _state(*, with_consumable: bool) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.ante = 3
    state.joker_slots = 5
    state.jokers = []
    state.shop_jokers = []
    state.shop_consumables = [_SyntheticConsumable()] if with_consumable else []
    return state


def _booster_action() -> BalatroAction:
    return BalatroAction(
        BUY_BOOSTER,
        target=SimpleNamespace(label="Arcana Pack", price=0),
    )


def _arbiter(*, child_build_gain: float = 0.0, immediate_gain: float = 0.0, booster_value: float = 0.0):
    return BuildAwareShopArbiter(
        shop_policy=BalatroShopPolicy(hold_bias=0.0),
        booster_policy=_FixedBoosterPolicy(option_utility=booster_value),
        reroll_policy=_HoldRerollPolicy(),
        joker_policy=_UnusedJokerPolicy(),
        consumable_policy=_FixedConsumablePolicy(
            child_build_gain=child_build_gain,
            immediate_gain=immediate_gain,
        ),
    )


def _negative_admitted_child_cannot_beat_parent_hold() -> SemanticCheck:
    arbiter = _arbiter(booster_value=-1.0)
    decision = arbiter.decide(
        _state(with_consumable=False),
        [_booster_action(), BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    return SemanticCheck(
        decision.source == "END_SHOP" and abs(float(decision.normalized_gain)) <= 1e-12,
        observed=(
            f"source={decision.source}, action={decision.action.name}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="an admitted child with negative shared parent utility cannot beat END_SHOP=0",
        detail=(
            "child BUY/HOLD admission is necessary but not sufficient for cross-family execution; D14 must retain "
            "the explicit zero parent baseline after recomputing shared resource/value units"
        ),
    )


def _structural_d4_units_do_not_overpower_stronger_booster() -> SemanticCheck:
    arbiter = _arbiter(child_build_gain=100.0, immediate_gain=1.0, booster_value=2.0)
    decision = arbiter.decide(
        _state(with_consumable=True),
        [_booster_action(), BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    return SemanticCheck(
        decision.source == "BOOSTER" and float(decision.normalized_gain) > 1.0,
        observed=(
            f"source={decision.source}, action={decision.action.name}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="a stronger D8 parent option beats a D4 BUY_AND_USE whose huge child structural gain has only weak literal immediate value",
        detail=(
            "D4 may use B4 structural units for admission, but consumable_d14_literal_policy must strip those units "
            "before D14 compares the consumable with boosters, Jokers, vouchers, rerolls, or END_SHOP"
        ),
    )


def _literal_consumable_can_beat_weaker_booster() -> SemanticCheck:
    arbiter = _arbiter(child_build_gain=0.0, immediate_gain=20.0, booster_value=2.0)
    decision = arbiter.decide(
        _state(with_consumable=True),
        [_booster_action(), BalatroAction(END_SHOP)],
        reroll_cost=5,
    )
    return SemanticCheck(
        decision.source == "CONSUMABLE_BUY_AND_USE" and float(decision.normalized_gain) > 2.0,
        observed=(
            f"source={decision.source}, action={decision.action.name}, "
            f"normalized_gain={decision.normalized_gain:.3f}"
        ),
        expected="a materially stronger literal immediate consumable beats a weaker admitted booster on the shared D14 scale",
        detail=(
            "D14 must remain value-based after child normalization; the Phase-4 resource audit must not turn booster, "
            "consumable, voucher, Joker, or reroll family identity into a second hardcoded arbiter"
        ),
    )


RED_WHITE_PHASE4_CROSS_FAMILY_CASES = (
    SemanticBenchmarkCase(
        case_id="resource.shop.cross_family_negative_child_holds",
        category="RESOURCE_COHERENCE",
        description="negative normalized child cannot beat END_SHOP",
        evaluate=_negative_admitted_child_cannot_beat_parent_hold,
        source="Phase 4 cross-family audit: D14 zero parent baseline",
    ),
    SemanticBenchmarkCase(
        case_id="resource.shop.cross_family_structural_units_do_not_leak",
        category="RESOURCE_COHERENCE",
        description="D4 structural admission units do not leak into D14",
        evaluate=_structural_d4_units_do_not_overpower_stronger_booster,
        source="Phase 4 cross-family audit: child-to-parent utility normalization",
    ),
    SemanticBenchmarkCase(
        case_id="resource.shop.cross_family_literal_consumable_can_win",
        category="RESOURCE_COHERENCE",
        description="normalized cross-family arbitration remains value based",
        evaluate=_literal_consumable_can_beat_weaker_booster,
        source="Phase 4 cross-family audit: reverse family precedence",
    ),
)
