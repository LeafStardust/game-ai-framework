import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.deal import deal_pristine_round_start
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.hand_size = 8
    return HeadlessRunState(public=state, seed=seed)


def _identity(card: BalatroCard) -> tuple[str, str]:
    return card.rank, card.suit


def test_env_r2_pristine_round_start_pins_shuffle_tail_draw_and_hand_sort():
    run = _run()

    result = deal_pristine_round_start(run)

    assert [_identity(card) for card in result.public.hand] == [
        ("A", "Hearts"),
        ("K", "Hearts"),
        ("Q", "Diamonds"),
        ("9", "Spades"),
        ("9", "Clubs"),
        ("5", "Clubs"),
        ("5", "Diamonds"),
        ("4", "Clubs"),
    ]
    # Vanilla CardArea:remove_card draws from the tail of a deck area.  After
    # eight cards, the next physical draw is therefore the current tail.
    assert _identity(result.draw_pile[-1]) == ("10", "Clubs")
    assert result.rng.nodes["nr1"] == 0.8232194488594


def test_env_r2_pristine_round_start_keeps_future_draw_order_private():
    result = deal_pristine_round_start(_run())

    assert len(result.draw_pile) == 44
    assert len(result.public.deck) == 44
    assert {_identity(card) for card in result.draw_pile} == {
        _identity(card) for card in result.public.deck
    }
    assert [_identity(card) for card in result.public.deck] != [
        _identity(card) for card in result.draw_pile
    ]
    assert [_identity(card) for card in result.public.deck] == sorted(
        [_identity(card) for card in result.public.deck],
        key=lambda value: (value[1], value[0]),
    )


def test_env_r2_pristine_round_start_installs_authoritative_owned_deck():
    result = deal_pristine_round_start(_run())

    assert result.public.owned_deck is not None
    assert len(result.public.owned_deck) == 52
    assert {id(card) for card in result.public.owned_deck} == {
        id(card) for card in result.require_playing_card_order()
    }
    assert {id(card) for card in result.public.hand}.isdisjoint(
        {id(card) for card in result.public.deck}
    )
    assert {id(card) for card in result.public.hand} | {
        id(card) for card in result.public.deck
    } == {id(card) for card in result.public.owned_deck}


def test_env_r2_pristine_round_start_isolates_input_state_and_rng():
    run = _run()
    before_rng = run.rng_snapshot()
    before_deck = list(run.public.deck)

    result = deal_pristine_round_start(run)

    assert result is not run
    assert run.public.phase == "DRAW_TO_HAND"
    assert run.public.hand == []
    assert run.public.owned_deck is None
    assert run.public.deck == before_deck
    assert run.draw_pile == []
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng


def test_env_r2_pristine_round_start_transitions_to_selecting_hand():
    result = deal_pristine_round_start(_run())

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8


def test_env_r2_pristine_round_start_respects_smaller_hand_size():
    run = _run()
    run.public.hand_size = 3

    result = deal_pristine_round_start(run)

    assert len(result.public.hand) == 3
    assert len(result.draw_pile) == 49
    assert len(result.public.deck) == 49


def test_env_r2_pristine_round_start_rejects_wrong_phase_and_nonempty_zones():
    run = _run()
    run.public.phase = "BLIND_SELECT"
    with pytest.raises(HeadlessTransitionError, match="DRAW_TO_HAND"):
        deal_pristine_round_start(run)

    run = _run()
    run.public.hand.append(run.public.deck[0])
    with pytest.raises(HeadlessTransitionError, match="empty public hand/discard"):
        deal_pristine_round_start(run)

    run = _run()
    run.draw_pile.append(run.public.deck[0])
    with pytest.raises(HeadlessTransitionError, match="empty private card zones"):
        deal_pristine_round_start(run)


def test_env_r2_pristine_round_start_fails_closed_on_modified_or_live_decks():
    run = _run()
    run.public.deck[0].enhancement = "Bonus"
    with pytest.raises(HeadlessTransitionError, match="hand sort is unavailable"):
        deal_pristine_round_start(run)

    run = _run()
    for index, card in enumerate(run.public.deck, start=1):
        card.live_id = index
    # Reconstruct the state so its retained creation order reflects those ids.
    live_run = HeadlessRunState(public=run.public, seed="TESTSEED")
    with pytest.raises(HeadlessTransitionError, match="hand sort is unavailable"):
        deal_pristine_round_start(live_run)
