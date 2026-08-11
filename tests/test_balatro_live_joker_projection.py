from games.balatro.actions import BalatroAction, PLAY_CARDS
from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.card import BalatroCard
from games.balatro.hand import PokerHand
from games.balatro.jokers.ice_cream import IceCreamJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.live.blind_clear_planner import LiveBlindClearPlanner
from games.balatro.live.external.save_observer import _normalize_item
from games.balatro.live.joker_factory import LiveJokerFactory
from games.balatro.live.score_outcomes import VisibleCardScoreOutcomeModel
from games.balatro.state import BalatroState


def _state(hand, deck=None, *, target=1000, hands=2, discards=0):
    state = BalatroState()
    state.phase = "SELECTING_HAND"
    state.hand = list(hand)
    state.deck = list(deck or [])
    state.score = 0
    state.hands_remaining = hands
    state.discards_remaining = discards
    state.blind = Blind(BlindType.BIG, target)
    return state


def test_ice_cream_projection_scores_and_decays_only_copied_joker():
    cards = [
        BalatroCard("K", "Spades", live_id=0),
        BalatroCard("K", "Diamonds", live_id=1),
    ]
    state = _state(cards)
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    # Pair: (10 base + 20 rank chips + 100 Ice Cream) * 2 Mult.
    assert transition.distribution.minimum == 260
    assert transition.joker_projection_complete is True
    assert ice_cream.chips == 100
    assert transition.state_after_scoring.jokers[0] is not ice_cream
    assert transition.state_after_scoring.jokers[0].chips == 95


def test_two_action_planner_carries_ice_cream_decay_into_second_play():
    ace = BalatroCard("A", "Spades", live_id=0)
    state = _state(
        [ace],
        [BalatroCard("K", "Hearts")],
        target=1000,
        hands=2,
        discards=0,
    )
    ice_cream = IceCreamJoker()
    state.jokers = [ice_cream]

    planner = LiveBlindClearPlanner(
        play_width=1,
        discard_width=0,
        horizon=2,
    )
    plan = planner.plan(state)

    # First High Card A: (5 + 11 + 100) * 1 = 116.
    # Second High Card K after Ice Cream decay: (5 + 10 + 95) * 1 = 110.
    assert plan.action.name == PLAY_CARDS
    assert plan.value.expected_score == 226.0
    assert plan.exact is True
    assert ice_cream.chips == 100


def test_unsupported_joker_is_reported_and_not_silently_applied():
    cards = [
        BalatroCard("10", "Spades"),
        BalatroCard("10", "Diamonds"),
    ]
    state = _state(cards)
    state.jokers = [JollyJoker()]

    transition = VisibleCardScoreOutcomeModel().project_transition(
        PokerHand.PAIR,
        state,
        cards,
    )

    assert transition.distribution.minimum == 60
    assert transition.joker_projection_complete is False
    assert transition.unsupported_jokers == ("Jolly",)


def test_ice_cream_public_save_state_is_narrowly_whitelisted_and_restored():
    normalized = _normalize_item(
        {
            "sort_id": 77,
            "label": "Ice Cream",
            "save_fields": {"center": "j_ice_cream"},
            "ability": {
                "name": "Ice Cream",
                "set": "Joker",
                "extra": {
                    "chips": 65,
                    "chip_mod": 5,
                    "private_test_field": 12345,
                },
            },
        }
    )

    assert normalized["public_state"] == {
        "chips": 65,
        "chip_mod": 5,
    }
    assert "ability" not in normalized
    assert "private_test_field" not in normalized["public_state"]

    joker = LiveJokerFactory().create(normalized)
    assert isinstance(joker, IceCreamJoker)
    assert joker.chips == 65
    assert joker.chip_mod == 5
    assert joker.live_id == 77
