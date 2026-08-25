from types import SimpleNamespace

import pytest

from games.balatro.actions import (
    BUY_BOOSTER,
    SELECT_PACK_CARD,
    SKIP_BOOSTER,
    BalatroAction,
)
from games.balatro.live.pack import LivePackChoice
from games.balatro.live.shop import LiveShopItem
from games.balatro.playbook import default_balatro_playbooks
from games.balatro.playbook_pack_policy import (
    PlaybookBalatroPackPolicy,
    PlaybookPackTargetEvaluator,
)
from games.balatro.playbook_shop_policy import (
    PlaybookVoucherAwareBalatroShopPolicy,
    ResourceValuationThresholds,
)
from games.balatro.resource_value import RunResourceValuator
from games.balatro.shop_arbiter import BuildAwareShopArbiter
from games.balatro.shop_booster_policy import (
    HOLD as BOOSTER_HOLD,
    BoosterAcquisitionThresholds,
    BuildAwareShopBoosterPolicy,
)
from games.balatro.shop_voucher_policy import BUY as VOUCHER_BUY
from games.balatro.state import BalatroState


class _FlatEstimator:
    def __init__(self, value: float):
        self.value = float(value)

    def estimate(self, state, action):
        del state, action
        return self.value, ("calibration fixture value",)


class _ZeroPlayingCardBuild:
    def evaluate(self, state, **kwargs):
        del state, kwargs
        return SimpleNamespace(total_gain=0.0, rationale=())


class _TargetEvaluator:
    def __init__(self, *, total_gain: float, contextual_delta: float):
        self.evaluation = SimpleNamespace(
            total_gain=float(total_gain),
            contextual_delta=float(contextual_delta),
            cards=(),
            target_indices=(),
            rationale=(),
        )

    def recommend(self, state, consumable):
        del state, consumable
        return self.evaluation


def _state(*, money: int = 20, ante: int = 1, phase: str = "SHOP") -> BalatroState:
    state = BalatroState()
    state.phase = phase
    state.money = money
    state.ante = ante
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_red_white_d3_uses_weighted_reserve_cost_not_hard_five_dollar_veto():
    state = _state(money=10, ante=1)
    voucher = LiveShopItem(
        kind="VOUCHER",
        label="Antimatter",
        price=10,
        area_index=0,
    )
    policy = PlaybookVoucherAwareBalatroShopPolicy(
        item_value_estimator=_FlatEstimator(10.0),
    )

    decision = policy.recommend_voucher(state, voucher)

    assert decision.thresholds.minimum_money_after == 0
    assert decision.money_after == 0
    assert decision.reserve_penalty > 0.0
    assert decision.total_advantage > decision.thresholds.minimum_purchase_advantage
    assert decision.action == VOUCHER_BUY


def test_red_white_d8_holds_zero_demand_standard_pack_even_with_runway():
    playbook = default_balatro_playbooks().get("RED", "WHITE")
    thresholds = BoosterAcquisitionThresholds.from_mapping(
        playbook.thresholds_for("D8")
    )
    policy = BuildAwareShopBoosterPolicy(thresholds=thresholds)
    booster = LiveShopItem(
        kind="BOOSTER",
        label="Standard Pack",
        price=4,
        area_index=0,
    )
    action = BalatroAction(BUY_BOOSTER, target=booster)

    healthy = policy.recommend(_state(money=10, ante=1), action)
    strained = policy.recommend(_state(money=5, ante=1), action)

    assert healthy.at_least_one_hit_probability >= thresholds.minimum_pack_hit_probability
    assert healthy.advantage_over_save > thresholds.minimum_buy_advantage
    assert healthy.build_need_score == pytest.approx(0.0)
    assert healthy.decision == BOOSTER_HOLD
    assert any("random deck bloat" in note for note in healthy.rationale)

    assert strained.reserve_penalty > healthy.reserve_penalty
    assert strained.advantage_over_save <= thresholds.minimum_buy_advantage
    assert strained.decision == BOOSTER_HOLD


def test_red_white_d9_skip_bias_rejects_rank_only_standard_card_dilution():
    state = _state(phase="STANDARD_PACK")
    policy = PlaybookBalatroPackPolicy(
        playing_card_build=_ZeroPlayingCardBuild(),
    )
    choice = LivePackChoice(
        area_index=0,
        address=0x1234,
        data={
            "ability_set": "PLAYING_CARD",
            "value": {"rank": "10", "suit": "Hearts"},
            "modifier": {},
        },
    )
    take = BalatroAction(SELECT_PACK_CARD, target=choice)
    skip = BalatroAction(SKIP_BOOSTER)

    ranked = policy.rank_actions(state, [take, skip])

    assert policy.skip_bias_for_state(state) == pytest.approx(0.35)
    assert ranked[0].action is skip
    assert ranked[0].total == pytest.approx(0.35)
    assert policy.score_action(state, take).total == pytest.approx(0.10)


def test_red_white_d10_requires_nonnegative_build_context_for_pack_target():
    state = _state(phase="ARCANA_PACK")

    harmful = PlaybookPackTargetEvaluator(
        evaluator=_TargetEvaluator(total_gain=0.50, contextual_delta=-0.01),
    )
    neutral = PlaybookPackTargetEvaluator(
        evaluator=_TargetEvaluator(total_gain=0.50, contextual_delta=0.0),
    )

    assert harmful.recommend(state, object()) is None
    assert neutral.recommend(state, object()) is not None


def test_red_white_d11_keeps_quarter_point_margin_for_paid_rerolls():
    state = _state()
    policy = BuildAwareShopArbiter()._reroll_policy_for_state(state)

    assert policy.thresholds.minimum_margin == pytest.approx(0.25)


def test_red_white_d14_makes_crossing_interest_and_reserve_breakpoint_material():
    state = _state(money=10)
    playbook = default_balatro_playbooks().for_state(state)
    thresholds = ResourceValuationThresholds.from_mapping(
        playbook.thresholds_for("D14")
    )
    valuator = RunResourceValuator()

    at_reserve = valuator.money_spend_cost(
        money=10,
        spend=5,
        price_weight=thresholds.price_weight,
        interest_weight=thresholds.interest_weight,
        reserve_target=thresholds.reserve_target,
        reserve_weight=thresholds.reserve_weight,
    )
    below_reserve = valuator.money_spend_cost(
        money=10,
        spend=6,
        price_weight=thresholds.price_weight,
        interest_weight=thresholds.interest_weight,
        reserve_target=thresholds.reserve_target,
        reserve_weight=thresholds.reserve_weight,
    )

    assert at_reserve.reserve == pytest.approx(0.0)
    assert below_reserve.reserve == pytest.approx(0.45)
    assert below_reserve.interest > at_reserve.interest
    assert below_reserve.total > at_reserve.total
