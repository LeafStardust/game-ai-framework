import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.manacle_start import (
    prepare_retained_manacle_chicot_start,
    start_retained_manacle_chicot,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.chicot import ChicotJoker
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 8
    state.blind = Blind(BlindType.BOSS, 20000)
    state.boss_name = "The Manacle"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    state.jokers = [ChicotJoker()]
    run = HeadlessRunState(public=state, seed="MANACLE-RETAINED-FULL")

    order = run.require_playing_card_order()
    run.public.owned_deck = list(order)
    # Retain a deliberately non-creation physical order so the one pre-shuffle
    # draw can be distinguished from the later sort-before-nr shuffle.
    run.draw_pile = [*order[7:], *order[:7]]
    run.public.deck = list(order)
    return run


def _identity(card) -> tuple[str, str]:
    return card.rank, card.suit


def test_env_r2_retained_manacle_chicot_prepare_pins_source_order_before_shuffle():
    run = _run()
    expected_pre_draw = _identity(run.draw_pile[-1])
    initial_hand_size = run.public.hand_size
    before_rng = run.rng_snapshot()

    prepared = prepare_retained_manacle_chicot_start(run)

    assert prepared.public.phase == "DRAW_TO_HAND"
    assert prepared.public.blind.disabled is True
    assert prepared.public.hand_size == initial_hand_size
    assert prepared.boss_hand_size_sub is None
    assert [_identity(card) for card in prepared.public.hand] == [expected_pre_draw]
    assert len(prepared.draw_pile) == 51
    assert prepared.rng_snapshot() == before_rng


def test_env_r2_retained_manacle_chicot_full_start_keeps_predraw_out_of_nr_shuffle():
    run = _run()
    pre_draw = _identity(run.draw_pile[-1])

    result = start_retained_manacle_chicot(run)

    assert result.public.phase == "SELECTING_HAND"
    assert result.public.blind.disabled is True
    assert result.boss_hand_size_sub is None
    assert len(result.public.hand) == result.public.hand_size == 8
    assert [_identity(card) for card in result.public.hand].count(pre_draw) == 1
    assert pre_draw not in [_identity(card) for card in result.draw_pile]
    assert len(result.draw_pile) == 44
    assert f"nr{result.public.ante}" in result.rng.nodes

    order = result.require_playing_card_order()
    zones = [*result.public.hand, *result.draw_pile]
    assert len({id(card) for card in zones}) == len(order) == 52
    assert {id(card) for card in zones} == {id(card) for card in order}


def test_env_r2_retained_manacle_chicot_full_start_is_deterministic_and_isolates_input():
    run = _run()
    before_draw = [_identity(card) for card in run.draw_pile]
    before_rng = run.rng_snapshot()

    first = start_retained_manacle_chicot(run)
    second = start_retained_manacle_chicot(run)

    assert [_identity(card) for card in first.public.hand] == [
        _identity(card) for card in second.public.hand
    ]
    assert [_identity(card) for card in first.draw_pile] == [
        _identity(card) for card in second.draw_pile
    ]
    assert first.rng_snapshot() == second.rng_snapshot()
    assert [_identity(card) for card in run.draw_pile] == before_draw
    assert run.public.hand == []
    assert run.boss_hand_size_sub is None
    assert not getattr(run.public.blind, "disabled", False)
    assert run.rng_snapshot() == before_rng


def test_env_r2_retained_manacle_chicot_requires_exactly_one_chicot():
    run = _run()
    run.public.jokers = []
    with pytest.raises(HeadlessTransitionError, match="exactly one Chicot"):
        start_retained_manacle_chicot(run)

    run = _run()
    run.public.jokers = [ChicotJoker(), ChicotJoker()]
    with pytest.raises(HeadlessTransitionError, match="exactly one Chicot"):
        start_retained_manacle_chicot(run)


def test_env_r2_retained_manacle_chicot_fails_closed_without_complete_retained_deck():
    run = _run()
    run.draw_pile.pop()
    run.public.deck = list(run.draw_pile)

    with pytest.raises(HeadlessTransitionError, match="complete permanent deck"):
        start_retained_manacle_chicot(run)
