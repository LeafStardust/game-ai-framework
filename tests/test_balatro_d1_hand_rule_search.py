from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand_rules import hand_rules_for_state
from games.balatro.jokers.four_fingers import FourFingersJoker
from games.balatro.jokers.shortcut import ShortcutJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.live.hand_action_planner import D1LiveBlindClearPlanner
from games.balatro.state import BalatroState


def _state(cards, jokers):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(cards)
    state.deck = []
    state.score = 0
    state.hands_remaining = 3
    state.discards_remaining = 0
    state.blind = Blind(BlindType.BIG, 10000)
    state.jokers = list(jokers)
    return state


def _child_candidates(state):
    planner = D1LiveBlindClearPlanner(
        horizon=1,
        play_width=6,
        discard_width=0,
        max_nodes=500,
    )
    # D1 uses bounded direct candidate construction after at least one search node.
    planner.nodes_evaluated = 1
    return planner._candidate_actions(
        state,
        allow_discards=False,
        play_width=6,
        discard_width=0,
    )


def _identity(cards):
    return tuple(sorted(id(card) for card in cards))


def test_recursive_d1_generates_four_fingers_four_card_straight():
    straight = [
        BalatroCard("2", "Hearts"),
        BalatroCard("3", "Spades"),
        BalatroCard("4", "Clubs"),
        BalatroCard("5", "Diamonds"),
    ]
    cards = [
        *straight,
        BalatroCard("A", "Hearts"),
        BalatroCard("K", "Clubs"),
        BalatroCard("Q", "Diamonds"),
    ]
    state = _state(cards, [FourFingersJoker()])

    candidates = _child_candidates(state)

    assert _identity(straight) in {
        _identity(action.cards)
        for action in candidates
    }


def test_recursive_d1_generates_shortcut_gapped_straight():
    straight = [
        BalatroCard("2", "Hearts"),
        BalatroCard("4", "Spades"),
        BalatroCard("6", "Clubs"),
        BalatroCard("8", "Diamonds"),
        BalatroCard("10", "Hearts"),
    ]
    cards = [
        *straight,
        BalatroCard("A", "Spades"),
        BalatroCard("A", "Clubs"),
        BalatroCard("A", "Diamonds"),
    ]
    state = _state(cards, [ShortcutJoker()])

    candidates = _child_candidates(state)

    assert _identity(straight) in {
        _identity(action.cards)
        for action in candidates
    }


def test_d1_splash_scoring_core_includes_pair_kicker():
    pair = [
        BalatroCard("10", "Diamonds"),
        BalatroCard("10", "Spades"),
    ]
    ace = BalatroCard("A", "Clubs")
    cards = [*pair, ace]
    state = _state(cards, [SplashJoker()])
    planner = D1LiveBlindClearPlanner(horizon=1, discard_width=0)
    planner._active_hand_rules = hand_rules_for_state(state)

    hand = planner._search_hand(cards)
    pair_core = planner._scoring_core(hand, pair)
    extended_core = planner._scoring_core(hand, cards)

    assert id(ace) not in pair_core
    assert id(ace) in extended_core
    assert pair_core != extended_core
