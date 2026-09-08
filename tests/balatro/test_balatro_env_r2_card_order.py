from games.balatro.card import BalatroCard
from games.balatro.env.card_order import (
    derive_playing_card_order,
    playing_card_order_matches,
)
from games.balatro.state import BalatroState


def _red_state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_env_r2_fresh_standard_deck_uses_vanilla_control_code_creation_order():
    state = _red_state()

    order = derive_playing_card_order(state)

    assert order is not None
    assert [(card.rank, card.suit) for card in order] == [
        (rank, suit)
        for suit in ("Clubs", "Diamonds", "Hearts", "Spades")
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "A", "J", "K", "Q", "10")
    ]
    assert playing_card_order_matches(order, state)


def test_env_r2_live_owned_deck_orders_by_unique_integer_playing_card_id():
    state = _red_state()
    low = BalatroCard("A", "Spades", live_id=7)
    middle = BalatroCard("2", "Clubs", live_id=41)
    high = BalatroCard("10", "Hearts", live_id=99)
    state.owned_deck = [high, low, middle]

    order = derive_playing_card_order(state)

    assert order == [low, middle, high]
    assert playing_card_order_matches(order, state)


def test_env_r2_duplicate_live_playing_card_ids_fail_closed():
    state = _red_state()
    state.owned_deck = [
        BalatroCard("A", "Spades", live_id=3),
        BalatroCard("K", "Spades", live_id=3),
    ]

    assert derive_playing_card_order(state) is None


def test_env_r2_partial_or_noninteger_live_playing_card_ids_fail_closed():
    state = _red_state()

    state.owned_deck = [
        BalatroCard("A", "Spades", live_id=3),
        BalatroCard("K", "Spades"),
    ]
    assert derive_playing_card_order(state) is None

    state.owned_deck = [
        BalatroCard("A", "Spades", live_id=3),
        BalatroCard("K", "Spades", live_id="4"),
    ]
    assert derive_playing_card_order(state) is None

    state.owned_deck = [
        BalatroCard("A", "Spades", live_id=3),
        BalatroCard("K", "Spades", live_id=True),
    ]
    assert derive_playing_card_order(state) is None


def test_env_r2_modified_identity_set_without_live_ids_fails_closed():
    state = _red_state()
    state.deck = list(state.deck)
    state.deck[-1] = BalatroCard("2", "Hearts")

    assert derive_playing_card_order(state) is None


def test_env_r2_order_match_requires_same_card_objects_not_equal_copies():
    state = _red_state()
    order = derive_playing_card_order(state)
    assert order is not None

    copied_cards = [
        BalatroCard(
            card.rank,
            card.suit,
            enhancement=card.enhancement,
            edition=card.edition,
            seal=card.seal,
            live_id=card.live_id,
            debuffed=card.debuffed,
            permanent_bonus=card.permanent_bonus,
            forced_selection=card.forced_selection,
        )
        for card in order
    ]

    assert not playing_card_order_matches(copied_cards, state)
