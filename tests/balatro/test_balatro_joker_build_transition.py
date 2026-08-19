from games.balatro.build import (
    JokerBuildTransitionPlanner,
    JokerBuildValueEvaluator,
)
from games.balatro.card import BalatroCard
from games.balatro.joker import Joker, JokerContext
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None:
            context.score.mult += 8
        return context


def _state(*, slots: int = 5) -> BalatroState:
    state = BalatroState()
    state.joker_slots = slots
    state.deck = [
        BalatroCard("K", "Hearts", enhancement="Steel"),
        BalatroCard("K", "Spades", enhancement="Steel"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
        BalatroCard("9", "Hearts"),
    ]
    return state


def test_build_value_combines_direct_scoring_and_contextual_synergy():
    evaluator = JokerBuildValueEvaluator()
    state = _state()

    inert = evaluator.evaluate(state, InertJoker())
    scoring = evaluator.evaluate(state, PlusMultJoker())
    baron = evaluator.evaluate(state, BaronJoker())

    assert scoring.direct_scoring_gain > inert.direct_scoring_gain
    assert scoring.total_gain > inert.total_gain
    assert baron.contextual.interaction_gain > 0.0
    assert any("B3 interaction" in note for note in baron.rationale)


def test_free_slot_candidate_is_reported_as_add_without_shop_economics():
    state = _state(slots=2)
    state.jokers = [MimeJoker()]

    decision = JokerBuildTransitionPlanner().plan(state, BaronJoker())

    assert decision.action == "ADD"
    assert decision.replacement is None
    assert decision.candidate_value.total_gain > 0.0


def test_full_build_replaces_inert_joker_instead_of_synergy_component():
    state = _state(slots=2)
    state.jokers = [MimeJoker(), InertJoker()]

    decision = JokerBuildTransitionPlanner().plan(state, BaronJoker())

    assert decision.action == "REPLACE"
    assert decision.replacement is not None
    assert decision.replacement.replace_index == 1
    assert decision.replacement.replace_joker == "InertJoker"
    assert decision.replacement.build_delta > 0.0

    mime_option = next(
        option
        for option in decision.alternatives
        if option.replace_joker == "MimeJoker"
    )
    assert decision.replacement.build_delta > mime_option.build_delta


def test_full_build_holds_when_candidate_cannot_improve_any_slot():
    state = _state(slots=2)
    state.jokers = [PlusMultJoker(), BaronJoker()]

    decision = JokerBuildTransitionPlanner(
        minimum_replacement_delta=0.0,
    ).plan(state, InertJoker())

    assert decision.action == "HOLD"
    assert decision.replacement is None
    assert decision.alternatives
    assert max(option.build_delta for option in decision.alternatives) <= 0.0


def test_replacement_options_use_same_remaining_build_for_both_values():
    state = _state(slots=2)
    state.jokers = [MimeJoker(), InertJoker()]

    decision = JokerBuildTransitionPlanner().plan(state, BaronJoker())
    option = next(
        option
        for option in decision.alternatives
        if option.replace_joker == "InertJoker"
    )

    assert option.incumbent_value.joker == "InertJoker"
    assert option.candidate_value.joker == "BaronJoker"
    assert option.build_delta == (
        option.candidate_value.total_gain - option.incumbent_value.total_gain
    )
    assert any("common baseline" in note for note in option.rationale)
