import pytest

from games.balatro.env.round_zones import (
    repopulate_round_end_deck,
    require_full_retained_preblind_deck,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _partitioned_run() -> tuple[HeadlessRunState, list]:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    run = HeadlessRunState(public=state, seed="ROUND-END-ZONES")
    order = run.require_playing_card_order()
    # Real post-deal headless state has authoritative permanent ownership even
    # while public deck is only the still-drawable subset.
    run.public.owned_deck = list(order)

    draw = list(order[:40])
    hand = list(order[40:45])
    discard = list(order[45:])
    run.draw_pile = draw
    run.public.deck = list(draw)
    run.public.hand = hand
    run.discard_pile = list(discard)
    run.public.discard_pile = list(discard)
    return run, order


def test_env_r2_round_end_repopulation_pins_hand_then_reverse_discard_order():
    run, _ = _partitioned_run()
    original_draw = list(run.draw_pile)
    original_discard = list(run.discard_pile)
    original_hand = list(run.public.hand)

    result = repopulate_round_end_deck(run)

    assert result.draw_pile == [
        *original_draw,
        *reversed([*original_discard, *original_hand]),
    ]
    # HeadlessRunState.copy() deep-copies the transition snapshot, so output
    # card identities must be compared with the output's retained creation order,
    # not with objects from the input snapshot.
    result_order = result.require_playing_card_order()
    assert {id(card) for card in result.draw_pile} == {
        id(card) for card in result_order
    }
    assert result.public.hand == []
    assert result.public.discard_pile == []
    assert result.discard_pile == []
    assert result.played_pile == []
    assert {id(card) for card in result.public.deck} == {
        id(card) for card in result.draw_pile
    }
    require_full_retained_preblind_deck(result)


def test_env_r2_round_end_repopulation_isolates_input_and_does_not_consume_rng():
    run, _ = _partitioned_run()
    before_rng = run.rng_snapshot()
    before_draw = list(run.draw_pile)
    before_hand = list(run.public.hand)
    before_discard = list(run.discard_pile)

    result = repopulate_round_end_deck(run)

    assert result is not run
    assert run.draw_pile == before_draw
    assert run.public.hand == before_hand
    assert run.discard_pile == before_discard
    assert run.public.discard_pile == before_discard
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() == before_rng


def test_env_r2_round_end_repopulation_requires_authoritative_owned_deck():
    run, _ = _partitioned_run()
    run.public.owned_deck = None

    with pytest.raises(HeadlessTransitionError, match="authoritative owned_deck"):
        repopulate_round_end_deck(run)


def test_env_r2_round_end_repopulation_rejects_unreturned_play_cards():
    run, _ = _partitioned_run()
    card = run.public.hand.pop()
    run.played_pile.append(card)

    with pytest.raises(
        HeadlessTransitionError,
        match="played cards already returned to discard",
    ):
        repopulate_round_end_deck(run)


def test_env_r2_round_end_repopulation_rejects_public_private_discard_order_drift():
    run, _ = _partitioned_run()
    run.public.discard_pile = list(reversed(run.public.discard_pile))

    with pytest.raises(
        HeadlessTransitionError,
        match="discard order is not authoritative",
    ):
        repopulate_round_end_deck(run)


def test_env_r2_retained_preblind_deck_requires_complete_permanent_partition():
    run, _ = _partitioned_run()
    result = repopulate_round_end_deck(run)
    require_full_retained_preblind_deck(result)

    missing = result.copy()
    missing.draw_pile.pop()
    missing.public.deck = list(missing.draw_pile)
    with pytest.raises(HeadlessTransitionError, match="complete permanent deck"):
        require_full_retained_preblind_deck(missing)

    residual_hand = result.copy()
    residual_hand.public.hand.append(residual_hand.draw_pile[-1])
    with pytest.raises(HeadlessTransitionError, match="empty hand/discard/play zones"):
        require_full_retained_preblind_deck(residual_hand)
