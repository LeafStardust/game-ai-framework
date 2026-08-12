from games.balatro.actions import DISCARD_CARDS, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _live_like_state():
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = [
        BalatroCard("K", "Clubs", live_id=0),
        BalatroCard("10", "Diamonds", live_id=1),
        BalatroCard("9", "Clubs", live_id=2),
        BalatroCard("6", "Diamonds", live_id=3),
        BalatroCard("4", "Spades", live_id=4),
        BalatroCard("4", "Hearts", live_id=5),
        BalatroCard("3", "Clubs", live_id=6),
        BalatroCard("2", "Clubs", live_id=7),
    ]
    state.deck = [
        BalatroCard("A", "Clubs"),
        BalatroCard("Q", "Clubs"),
        BalatroCard("J", "Hearts"),
        BalatroCard("8", "Spades"),
        BalatroCard("7", "Diamonds"),
    ]
    state.score = 0
    state.hands_remaining = 4
    state.discards_remaining = 4
    state.blind = Blind(BlindType.SMALL, 300)
    state.jokers = []
    return state


def test_d1_play_beam_preserves_pair_plus_trash_cycle_sizes():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=False)
    plays = [action for action in actions if action.name == PLAY_CARDS]

    pair_core_ids = {id(state.hand[4]), id(state.hand[5])}
    represented_sizes = set()
    for action in plays:
        hand = planner.evaluator.hand_evaluator.evaluate(action.cards)
        scoring = planner.evaluator.scorer.scoring_cards(hand, action.cards)
        if {id(card) for card in scoring} == pair_core_ids:
            represented_sizes.add(len(action.cards))

    assert {2, 3, 4, 5}.issubset(represented_sizes)


def test_d1_discard_beam_preserves_distinct_redraw_sizes():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)
    discards = [action for action in actions if action.name == DISCARD_CARDS]

    assert {len(action.cards) for action in discards} == {1, 2, 3, 4}


def test_four_card_discard_can_preserve_four_club_flush_structure():
    state = _live_like_state()
    planner = D1LiveBlindClearPlanner(play_width=6, discard_width=4, horizon=2)

    actions = planner._candidate_actions(state, allow_discards=True)
    four_card = next(
        action
        for action in actions
        if action.name == DISCARD_CARDS and len(action.cards) == 4
    )
    discarded_ids = {id(card) for card in four_card.cards}
    kept = [card for card in state.hand if id(card) not in discarded_ids]

    assert sum(1 for card in kept if card.suit == "Clubs") == 4
