from types import SimpleNamespace

import pytest

from games.balatro.actions import BUY_JOKER
from games.balatro.build import JokerBuildTransitionPlanner
from games.balatro.joker import Joker, JokerContext
from games.balatro.joker_edition import joker_has_negative_edition
from games.balatro.joker_policy import (
    BUY,
    REPLACE,
    JokerAcquisitionPolicy,
    JokerAcquisitionThresholds,
)
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.shop_utility_scale import ShopUtilityScale
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = 20
    state.joker_slots = 1
    state.jokers = [InertJoker()]
    return state


def _thresholds() -> JokerAcquisitionThresholds:
    return JokerAcquisitionThresholds(
        minimum_purchase_advantage=0.0,
        minimum_replacement_advantage=0.0,
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=100.0,
        penultimate_joker_slot_penalty=100.0,
    )


def _candidate(*, negative: bool) -> PlusMultJoker:
    candidate = PlusMultJoker()
    candidate.cost = 0
    candidate.edition = "Negative" if negative else None
    return candidate


def test_negative_edition_predicate_supports_string_and_live_mapping_forms():
    assert joker_has_negative_edition(SimpleNamespace(edition="Negative"))
    assert joker_has_negative_edition(
        SimpleNamespace(edition={"negative": True, "foil": False})
    )
    assert not joker_has_negative_edition(SimpleNamespace(edition="Foil"))


def test_build_transition_treats_full_roster_negative_as_add():
    state = _state()
    candidate = _candidate(negative=True)

    transition = JokerBuildTransitionPlanner().plan(state, candidate)

    assert transition.action == "ADD"
    assert transition.replacement is None
    assert transition.candidate_value.total_gain > 0.0
    assert any("slot-neutral" in note for note in transition.rationale)


def test_full_joker_roster_can_buy_useful_negative_without_replacement():
    state = _state()
    candidate = _candidate(negative=True)

    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)

    assert decision.action == BUY
    assert decision.selected is not None
    assert decision.selected.mode == BUY
    assert decision.selected.replace_index is None
    assert decision.selected.economics.slot_penalty == 0.0
    assert any("slot-neutral" in note for note in decision.rationale)


def test_same_useful_nonnegative_candidate_still_uses_full_roster_replacement():
    state = _state()
    candidate = _candidate(negative=False)

    transition = JokerBuildTransitionPlanner().plan(state, candidate)
    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)

    assert transition.action == "REPLACE"
    assert decision.action == REPLACE
    assert decision.selected is not None
    assert decision.selected.replace_index == 0


def test_generic_shop_recommendation_can_buy_negative_on_full_roster():
    state = _state()
    candidate = _candidate(negative=True)

    recommendation = BalatroShopPolicy(
        price_weight=0.0,
        interest_weight=0.0,
        reserve_weight=0.0,
        last_joker_slot_penalty=100.0,
        penultimate_joker_slot_penalty=100.0,
        hold_bias=0.0,
    ).recommend_joker(state, candidate)

    assert recommendation.decision == "BUY"
    assert recommendation.executable_action is not None
    assert recommendation.executable_action.name == BUY_JOKER
    assert recommendation.shop_score is not None
    assert recommendation.shop_score.slot_penalty == 0.0


def test_d14_does_not_reapply_joker_slot_cost_to_negative_purchase():
    state = _state()
    candidate = _candidate(negative=True)
    decision = JokerAcquisitionPolicy(_thresholds()).decide(state, candidate)
    assert decision.action == BUY
    assert decision.selected is not None

    executable = SimpleNamespace(
        source="JOKER_BUY",
        candidate=candidate,
        decision=decision,
    )
    utility = ShopUtilityScale(BalatroShopPolicy()).joker_gain(state, executable)

    assert utility.resource_cost == pytest.approx(0.0)
    assert utility.gain == pytest.approx(
        decision.selected.build_gain + decision.selected.economics.edition_delta
    )
