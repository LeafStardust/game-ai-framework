import pytest

from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_policy import (
    BUY,
    HOLD,
    REPLACE,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.superposition import SuperpositionJoker
from games.balatro.card import BalatroCard
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


def _state(*, money: int = 20, slots: int = 2) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = slots
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("9", "Hearts"),
    ]
    return state


def _no_economy_thresholds(**overrides) -> JokerAcquisitionThresholds:
    values = {
        "minimum_purchase_advantage": 0.0,
        "minimum_replacement_advantage": 0.0,
        "price_weight": 0.0,
        "interest_weight": 0.0,
        "reserve_weight": 0.0,
        "last_joker_slot_penalty": 0.0,
        "penultimate_joker_slot_penalty": 0.0,
    }
    values.update(overrides)
    return JokerAcquisitionThresholds(**values)


def test_d2_threshold_mapping_rejects_unknown_fields():
    with pytest.raises(ValueError, match="unknown D2 Joker threshold"):
        JokerAcquisitionThresholds.from_mapping({"shared_shop_threshold": 1})


def test_d2_buys_positive_whole_build_candidate_when_economics_allow():
    state = _state(money=20, slots=2)
    candidate = PlusMultJoker()
    candidate.cost = 2

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.mode == BUY
    assert decision.selected.build_gain > 0.0
    assert decision.selected.economics.price == 2
    assert decision.selected.economics.sell_credit == 0


def test_d2_buys_behavior_backed_economy_joker_without_scoring_gain():
    state = _state(money=20, slots=2)
    candidate = GoldenJoker()
    candidate.cost = 0

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.transition.candidate_value.direct_scoring_gain == 0.0
    assert decision.selected.transition.candidate_value.contextual.intrinsic_gain > 0.0
    assert decision.selected.build_gain > 0.0


def test_d2_buys_behavior_backed_non_scoring_generation_joker():
    state = _state(money=20, slots=2)
    candidate = SuperpositionJoker()
    candidate.cost = 0

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.transition.candidate_value.direct_scoring_gain == 0.0
    assert decision.selected.transition.candidate_value.contextual.intrinsic_gain > 0.0
    assert decision.selected.build_gain > 0.0


def test_d2_holds_when_purchase_would_create_large_reserve_shortfall():
    state = _state(money=10, slots=2)
    candidate = PlusMultJoker()
    candidate.cost = 10

    thresholds = JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_target=5,
        reserve_weight=100.0,
        last_joker_slot_penalty=0.0,
        penultimate_joker_slot_penalty=0.0,
    )
    decision = JokerAcquisitionPolicy(thresholds).decide(state, candidate)

    assert decision.action == HOLD
    assert decision.options[0].economics.money_after == 0
    assert decision.options[0].economics.reserve_penalty == 500.0


def test_d2_full_build_replacement_preserves_synergy_component_and_uses_sell_credit():
    state = _state(money=1, slots=2)
    mime = MimeJoker()
    mime.sell_cost = 1
    inert = InertJoker()
    inert.sell_cost = 5
    state.jokers = [mime, inert]

    candidate = BaronJoker()
    candidate.cost = 6

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert decision.action == REPLACE
    assert decision.selected is not None
    assert decision.selected.replace_index == 1
    assert decision.selected.replace_joker == "InertJoker"
    assert decision.selected.economics.sell_credit == 5
    assert decision.selected.economics.net_spend == 1
    assert decision.selected.economics.money_after == 0


def test_d2_scores_every_replacement_slot_before_applying_economics():
    state = _state(money=5, slots=2)
    low_sell = InertJoker()
    low_sell.sell_cost = 1
    high_sell = InertJoker()
    high_sell.sell_cost = 8
    state.jokers = [low_sell, high_sell]

    candidate = PlusMultJoker()
    candidate.cost = 10

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(price_weight=0.35),
    ).decide(state, candidate)

    assert len(decision.options) == 2
    assert decision.action == REPLACE
    assert decision.selected is not None
    assert decision.selected.replace_index == 1
    assert decision.selected.economics.sell_credit == 8
    assert any(not option.eligible for option in decision.options)


def test_d2_never_uses_sell_credit_to_justify_a_build_downgrade():
    state = _state(money=0, slots=1)
    incumbent = PlusMultJoker()
    incumbent.sell_cost = 20
    state.jokers = [incumbent]

    candidate = InertJoker()
    candidate.cost = 1

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(price_weight=1.0),
    ).decide(state, candidate)

    assert decision.action == HOLD
    assert decision.options
    assert decision.options[0].build_gain <= 0.0
    assert decision.options[0].eligible is False
