from types import SimpleNamespace

import pytest

from games.balatro.build.joker_strategy import JokerBuildValueEvaluator
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
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.zany_joker import ZanyJoker
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


class FixedReplacementPlanner:
    def plan(self, state, candidate):
        return SimpleNamespace(
            candidate_value=SimpleNamespace(total_gain=0.5),
            alternatives=(
                SimpleNamespace(
                    replace_index=0,
                    build_delta=0.5,
                    rationale=("fixed low-margin replacement",),
                ),
            ),
        )


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


def _standard_deck_state(*, money: int = 20, slots: int = 5) -> BalatroState:
    state = _state(money=money, slots=slots)
    state.deck = BalatroState().deck
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
    build_value = JokerBuildValueEvaluator().evaluate(state, candidate)

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert build_value.direct_scoring_gain == 0.0
    assert build_value.contextual.intrinsic_gain > 0.0
    assert decision.action == BUY
    assert decision.selected is not None
    # D2 now adds bounded canonical Bond-transition value on top of the raw
    # whole-build evaluator. The selected gain must preserve, not erase, the
    # underlying behavioral/economic value.
    assert decision.selected.build_gain >= build_value.total_gain
    assert decision.selected.build_gain > 0.0


def test_d2_holds_conditional_generation_joker_when_build_requirements_are_absent():
    state = _state(money=20, slots=2)
    candidate = SuperpositionJoker()
    candidate.cost = 0
    build_value = JokerBuildValueEvaluator().evaluate(state, candidate)

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert build_value.direct_scoring_gain == 0.0
    assert build_value.contextual.intrinsic_gain > 0.0
    assert set(build_value.contextual.unmet_requirements) == {"hand:STRAIGHT", "rank:A"}
    assert build_value.total_gain <= 0.0
    assert decision.action == HOLD


def test_d2_buys_conditional_generation_joker_when_build_requirements_are_present():
    state = _state(money=20, slots=2)
    state.deck.append(BalatroCard("A", "Clubs"))
    state.hand_levels["STRAIGHT"] = 2
    candidate = SuperpositionJoker()
    candidate.cost = 0
    build_value = JokerBuildValueEvaluator().evaluate(state, candidate)

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
    ).decide(state, candidate)

    assert build_value.direct_scoring_gain == 0.0
    assert build_value.contextual.intrinsic_gain > 0.0
    assert build_value.contextual.unmet_requirements == ()
    assert set(build_value.contextual.matched_requirements) == {"hand:STRAIGHT", "rank:A"}
    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.build_gain >= build_value.total_gain
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


def test_d2_bond_bonus_cannot_rescue_negative_raw_replacement(monkeypatch):
    state = _state(money=20, slots=1)
    state.jokers = [PlusMultJoker()]
    candidate = InertJoker()
    candidate.cost = 0
    planner = FixedReplacementPlanner()
    planner.plan = lambda _state, _candidate: SimpleNamespace(
        candidate_value=SimpleNamespace(total_gain=0.5),
        alternatives=(
            SimpleNamespace(
                replace_index=0,
                build_delta=-1.0,
                rationale=("negative common-baseline replacement",),
            ),
        ),
    )
    monkeypatch.setattr(
        "games.balatro.joker_policy._bond_transition_bonus",
        lambda *_args, **_kwargs: (4.0, ("canonical Bond transition bonus=4.000",)),
    )

    decision = JokerAcquisitionPolicy(
        _no_economy_thresholds(),
        transition_planner=planner,
    ).decide(state, candidate)

    assert decision.action == HOLD
    assert decision.options[0].build_gain == pytest.approx(3.0)
    assert decision.options[0].eligible is False
    assert any(
        "raw whole-build replacement delta=-1.000" in note
        for note in decision.options[0].rationale
    )


def test_d2_does_not_use_retired_strategy_tier_shortcut_for_replacement():
    state = _state(money=20, slots=1)
    state.jokers = [InertJoker()]
    candidate = PlusMultJoker()
    candidate.cost = 0
    thresholds = _no_economy_thresholds(
        minimum_replacement_advantage=0.75,
        aligned_minimum_replacement_advantage=0.25,
    )

    decision = JokerAcquisitionPolicy(
        thresholds,
        transition_planner=FixedReplacementPlanner(),
    ).decide(state, candidate)

    # A raw +0.5 replacement no longer receives the deleted Gold/Silver/Bronze
    # alignment threshold. It must clear the ordinary threshold or earn enough
    # projected canonical Bond value from the real public state.
    assert decision.action == HOLD
    assert decision.selected is None
    assert decision.options
    assert decision.options[0].total_advantage == pytest.approx(0.5)
    assert all("strategy tier" not in note.lower() for note in decision.rationale)


def test_d2_bond_transition_treats_first_axis_as_scouting_not_an_engine():
    from games.balatro.joker_policy import _bond_transition_bonus

    adjustment, rationale = _bond_transition_bonus(
        _standard_deck_state(),
        ZanyJoker(),
    )

    assert 0.0 < adjustment <= 0.50
    assert any("new-axis rank gain=1.0" in note for note in rationale)


def test_d2_bond_transition_penalizes_unrelated_second_hand_axis():
    from games.balatro.joker_policy import _bond_transition_bonus

    state = _standard_deck_state()
    state.jokers = [ZanyJoker()]

    adjustment, rationale = _bond_transition_bonus(state, CrazyJoker())

    assert adjustment < 0.0
    assert any("new-axis rank gain=1.0" in note for note in rationale)


def test_d2_bond_transition_rewards_deepening_the_existing_hand_axis():
    from games.balatro.joker_policy import _bond_transition_bonus

    state = _standard_deck_state()
    state.jokers = [ZanyJoker()]

    adjustment, rationale = _bond_transition_bonus(state, WilyJoker())

    assert adjustment > 1.0
    assert any("established rank gain=1.0" in note for note in rationale)
