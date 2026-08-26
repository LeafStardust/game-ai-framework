from __future__ import annotations

import games.balatro  # install package-level live authorities

from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import create_small_blind
from games.balatro.card import BalatroCard
from games.balatro.hand_order_policy import HandOrderPolicy
from games.balatro.joker_order_policy import JokerOrderPolicy
from games.balatro.jokers.blueprint import BlueprintJoker
from games.balatro.jokers.brainstorm import BrainstormJoker
from games.balatro.jokers.dagger import DaggerJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.blind = create_small_blind(10_000)
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 3
    state.deck = []
    return state


def test_blueprint_order_uses_exact_selected_play_to_copy_stronger_right_joker() -> None:
    state = _state()
    card = BalatroCard("A", "Spades", live_id="ace")
    state.hand = [card]

    weak = FlatMultJoker(4)
    strong = FlatMultJoker(20)
    blueprint = BlueprintJoker()
    state.jokers = [blueprint, weak, strong]

    decision = JokerOrderPolicy().recommend_for_play(state, [card])

    assert decision is not None
    ordered = [state.jokers[index] for index in decision.permutation]
    blueprint_index = ordered.index(blueprint)
    assert blueprint_index + 1 < len(ordered)
    assert ordered[blueprint_index + 1] is strong
    assert decision.ordered_score > decision.current_score


def test_brainstorm_order_uses_exact_selected_play_to_copy_stronger_leftmost_joker() -> None:
    state = _state()
    card = BalatroCard("A", "Spades", live_id="ace")
    state.hand = [card]

    weak = FlatMultJoker(4)
    strong = FlatMultJoker(20)
    brainstorm = BrainstormJoker()
    state.jokers = [weak, brainstorm, strong]

    decision = JokerOrderPolicy().recommend_for_play(state, [card])

    assert decision is not None
    ordered = [state.jokers[index] for index in decision.permutation]
    assert ordered[0] is strong
    assert ordered.index(brainstorm) > 0
    assert decision.ordered_score > decision.current_score


def test_photograph_reorders_selected_straight_to_put_face_card_first() -> None:
    state = _state()
    cards = [
        BalatroCard("9", "Clubs", live_id="9"),
        BalatroCard("10", "Diamonds", live_id="10"),
        BalatroCard("J", "Hearts", live_id="J"),
        BalatroCard("Q", "Spades", live_id="Q"),
        BalatroCard("K", "Clubs", live_id="K"),
    ]
    state.hand = list(cards)
    state.jokers = [PhotographJoker()]
    action = BalatroAction(PLAY_CARDS, cards=list(cards))

    decision = HandOrderPolicy().recommend(state, action)

    assert decision is not None
    reordered_hand = [state.hand[index] for index in decision.permutation]
    first_selected = reordered_hand[0]
    assert first_selected.rank in {"J", "Q", "K"}
    assert decision.ordered_guaranteed_score > decision.current_guaranteed_score


def test_dagger_preblind_order_avoids_eternal_target_and_uses_legal_fodder() -> None:
    state = _state()
    state.phase = "BLIND_SELECT"

    dagger = DaggerJoker()
    eternal = FlatMultJoker(20)
    eternal.eternal = True
    eternal.sell_value = 10
    fodder = FlatMultJoker(0)
    fodder.sell_value = 1
    state.jokers = [dagger, eternal, fodder]

    decision = JokerOrderPolicy().recommend(state, phase="BLIND_SELECT")

    assert decision is not None
    ordered = [state.jokers[index] for index in decision.permutation]
    dagger_index = ordered.index(dagger)
    assert dagger_index + 1 < len(ordered)
    assert ordered[dagger_index + 1] is fodder
    assert eternal in ordered
    assert decision.ordered_score > decision.current_score
