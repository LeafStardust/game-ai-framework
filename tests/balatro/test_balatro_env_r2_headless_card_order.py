import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _state() -> BalatroState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    return state


def test_env_r2_headless_state_derives_fresh_deck_creation_order():
    run = HeadlessRunState(public=_state(), seed="TESTSEED")

    order = run.require_playing_card_order()

    assert len(order) == 52
    assert [(card.rank, card.suit) for card in order[:5]] == [
        ("2", "Clubs"),
        ("3", "Clubs"),
        ("4", "Clubs"),
        ("5", "Clubs"),
        ("6", "Clubs"),
    ]


def test_env_r2_headless_state_retains_live_playing_card_creation_order():
    state = _state()
    later = BalatroCard("A", "Spades", live_id=91)
    earlier = BalatroCard("2", "Clubs", live_id=4)
    state.owned_deck = [later, earlier]

    run = HeadlessRunState(public=state, seed="TESTSEED")

    assert run.require_playing_card_order() == [earlier, later]


def test_env_r2_headless_state_leaves_unprovable_order_unavailable():
    state = _state()
    state.owned_deck = [
        BalatroCard("A", "Spades"),
        BalatroCard("K", "Spades"),
    ]
    run = HeadlessRunState(public=state, seed="TESTSEED")

    assert run.playing_card_order is None
    with pytest.raises(HeadlessTransitionError, match="creation order is unavailable"):
        run.require_playing_card_order()


def test_env_r2_headless_state_rejects_detached_explicit_order():
    state = _state()
    detached = list(BalatroState().deck)

    with pytest.raises(HeadlessTransitionError, match="authoritative owned cards exactly"):
        HeadlessRunState(
            public=state,
            seed="TESTSEED",
            playing_card_order=detached,
        )


def test_env_r2_headless_copy_preserves_private_order_links_to_copied_public_cards():
    run = HeadlessRunState(public=_state(), seed="TESTSEED")
    original_order = run.require_playing_card_order()

    copied = run.copy()
    copied_order = copied.require_playing_card_order()

    assert copied is not run
    assert copied.public is not run.public
    assert all(card is not original for card, original in zip(copied_order, original_order))
    assert {id(card) for card in copied_order} == {id(card) for card in copied.public.deck}


def test_env_r2_headless_state_detects_stale_order_after_owned_deck_change():
    state = _state()
    state.owned_deck = [
        BalatroCard("2", "Clubs", live_id=1),
        BalatroCard("3", "Clubs", live_id=2),
    ]
    run = HeadlessRunState(public=state, seed="TESTSEED")
    state.owned_deck.append(BalatroCard("4", "Clubs", live_id=3))

    with pytest.raises(HeadlessTransitionError, match="stale relative to the public deck"):
        run.require_playing_card_order()
