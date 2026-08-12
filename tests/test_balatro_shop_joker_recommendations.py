import pytest

from games.balatro.actions import BUY_JOKER, END_SHOP, BalatroAction
from games.balatro.joker import Joker, JokerContext
from games.balatro.jokers.baron import BaronJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.shop_policy import BalatroShopPolicy
from games.balatro.state import BalatroState


class InertJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        return context


class PlusMultJoker(Joker):
    def apply(self, context: JokerContext) -> JokerContext:
        if context.score is not None and context.trigger == "HAND_SCORED":
            context.score.mult += 8
        return context


def _shop_state(*, slots: int = 5, money: int = 20) -> BalatroState:
    state = BalatroState()
    state.phase = "SHOP"
    state.money = money
    state.joker_slots = slots
    return state


def test_open_slot_improving_joker_is_executable_buy():
    state = _shop_state(slots=2)
    state.jokers = [InertJoker()]
    candidate = PlusMultJoker()
    candidate.cost = 0
    policy = BalatroShopPolicy()

    recommendation = policy.recommend_joker(state, candidate)

    assert recommendation.decision == "BUY"
    assert recommendation.build_transition.action == "ADD"
    assert recommendation.executable_action is not None
    assert recommendation.executable_action.name == BUY_JOKER
    assert recommendation.executable_action.target is candidate
    assert recommendation.replacement is None

    chosen = policy.choose_action(
        state,
        [
            BalatroAction(BUY_JOKER, target=candidate),
            BalatroAction(END_SHOP),
        ],
    )
    assert chosen.name == BUY_JOKER


def test_non_improving_open_slot_joker_is_held_and_rejected_from_ranking():
    state = _shop_state(slots=2)
    state.jokers = [PlusMultJoker()]
    candidate = InertJoker()
    candidate.cost = 0
    policy = BalatroShopPolicy()

    recommendation = policy.recommend_joker(state, candidate)

    assert recommendation.decision == "HOLD"
    assert recommendation.build_transition.action == "HOLD"
    assert recommendation.executable_action is None

    ranked = policy.rank_actions(
        state,
        [
            BalatroAction(BUY_JOKER, target=candidate),
            BalatroAction(END_SHOP),
        ],
    )
    assert [score.action.name for score in ranked] == [END_SHOP]


def test_full_row_recommendation_identifies_best_whole_build_replacement():
    state = _shop_state(slots=2)
    state.jokers = [MimeJoker(), InertJoker()]
    candidate = BaronJoker()
    state.shop_jokers = [candidate]
    policy = BalatroShopPolicy()

    recommendation = policy.recommend_jokers(state)[0]

    assert recommendation.decision == "REPLACE"
    assert recommendation.build_transition.action == "REPLACE"
    assert recommendation.replacement is not None
    assert recommendation.replacement.replace_index == 1
    assert recommendation.replacement.replace_joker == "InertJoker"
    assert recommendation.replacement.build_delta > 0.0
    assert any("replacement delta=" in note for note in recommendation.rationale)


def test_full_row_inferior_candidate_is_held():
    state = _shop_state(slots=2)
    state.jokers = [PlusMultJoker(), BaronJoker()]
    candidate = InertJoker()
    state.shop_jokers = [candidate]
    policy = BalatroShopPolicy()

    recommendation = policy.recommend_jokers(state)[0]

    assert recommendation.decision == "HOLD"
    assert recommendation.build_transition.action == "HOLD"
    assert recommendation.replacement is None
    assert recommendation.executable_action is None


def test_replacement_advice_never_masquerades_as_direct_buy():
    state = _shop_state(slots=2)
    state.jokers = [MimeJoker(), InertJoker()]
    candidate = BaronJoker()
    policy = BalatroShopPolicy()

    recommendation = policy.recommend_joker(state, candidate)

    assert recommendation.decision == "REPLACE"
    assert recommendation.executable_action is None
    assert recommendation.replacement is not None
    assert any("advisory only" in note for note in recommendation.rationale)

    with pytest.raises(ValueError, match="requires a free Joker slot"):
        policy.score_action(
            state,
            BalatroAction(BUY_JOKER, target=candidate),
        )
