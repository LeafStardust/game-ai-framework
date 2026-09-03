import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.boss_draw import apply_cerulean_bell_drawn_to_hand
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _dealt_cerulean(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.boss_name = "Cerulean Bell"
    state.phase = "DRAW_TO_HAND"
    state.hand_size = 8
    return deal_supported_round_start(HeadlessRunState(public=state, seed=seed))


def _identity(card: BalatroCard) -> tuple[str, str]:
    return card.rank, card.suit


def test_env_r2_cerulean_bell_pins_sort_id_ordered_testseed_choice():
    run = _dealt_cerulean()
    assert [_identity(card) for card in run.public.hand] == [
        ("A", "Hearts"),
        ("K", "Hearts"),
        ("Q", "Diamonds"),
        ("9", "Spades"),
        ("9", "Clubs"),
        ("5", "Clubs"),
        ("5", "Diamonds"),
        ("4", "Clubs"),
    ]

    result = apply_cerulean_bell_drawn_to_hand(run)

    forced = [card for card in result.public.hand if card.forced_selection]
    assert len(forced) == 1
    # TESTSEED chooses position 1 in the sort_id-ordered candidate set. Of the
    # dealt cards, 4 of Clubs is earliest in retained creation/sort_id order even
    # though it is last in visible hand sort order.
    assert _identity(forced[0]) == ("4", "Clubs")
    assert result.rng.nodes["cerulean_bell"] == pytest.approx(0.2175606045966)


def test_env_r2_cerulean_bell_isolates_input_cards_and_rng():
    run = _dealt_cerulean()
    before_rng = run.rng_snapshot()

    result = apply_cerulean_bell_drawn_to_hand(run)

    assert all(not card.forced_selection for card in run.public.hand)
    assert run.rng_snapshot() == before_rng
    assert sum(card.forced_selection for card in result.public.hand) == 1
    assert result.rng_snapshot() != before_rng


def test_env_r2_cerulean_bell_existing_forced_card_consumes_no_rng():
    run = _dealt_cerulean()
    run.public.hand[2].forced_selection = True
    before_rng = run.rng_snapshot()

    result = apply_cerulean_bell_drawn_to_hand(run)

    assert [_identity(card) for card in result.public.hand if card.forced_selection] == [
        _identity(run.public.hand[2])
    ]
    assert result.rng_snapshot() == before_rng


def test_env_r2_cerulean_bell_fails_closed_on_multiple_forced_cards():
    run = _dealt_cerulean()
    run.public.hand[0].forced_selection = True
    run.public.hand[1].forced_selection = True

    with pytest.raises(HeadlessTransitionError, match="multiple forced"):
        apply_cerulean_bell_drawn_to_hand(run)


def test_env_r2_cerulean_bell_requires_owned_playing_card_identity():
    run = _dealt_cerulean()
    run.public.hand[0] = BalatroCard("A", "Spades")

    with pytest.raises(HeadlessTransitionError, match="outside authoritative"):
        apply_cerulean_bell_drawn_to_hand(run)


def test_env_r2_cerulean_bell_rejects_wrong_boss_phase_or_empty_hand():
    run = _dealt_cerulean()
    run.public.boss_name = "The Wall"
    with pytest.raises(HeadlessTransitionError, match="requires Cerulean Bell"):
        apply_cerulean_bell_drawn_to_hand(run)

    run = _dealt_cerulean()
    run.public.phase = "DRAW_TO_HAND"
    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        apply_cerulean_bell_drawn_to_hand(run)

    run = _dealt_cerulean()
    run.public.hand.clear()
    with pytest.raises(HeadlessTransitionError, match="non-empty hand"):
        apply_cerulean_bell_drawn_to_hand(run)
