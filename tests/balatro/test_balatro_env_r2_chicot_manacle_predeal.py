import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_disable import disable_supported_boss
from games.balatro.env.round_zones import require_full_retained_preblind_deck
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _retained_manacle_disable_run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 8
    state.blind = Blind(BlindType.BOSS, 20000)
    state.boss_name = "The Manacle"
    run = HeadlessRunState(public=state, seed="CHICOT-MANACLE")

    order = run.require_playing_card_order()
    run.public.owned_deck = list(order)
    # Deliberately retain a physical order different from creation order. The
    # pre-shuffle Manacle replacement must use this tail, not canonical deck or
    # sort_id order.
    run.draw_pile = [*order[7:], *order[:7]]
    run.public.deck = list(order)
    require_full_retained_preblind_deck(run)

    # State immediately after Blind:set_blind(The Manacle), before Chicot's
    # queued Blind:disable event runs.
    run.boss_hand_size_sub = 1
    run.public.hand_size -= 1
    return run


def _identity(card) -> tuple[str, str]:
    return card.rank, card.suit


def test_env_r2_chicot_predeal_manacle_disable_restores_slot_and_draws_retained_tail():
    run = _retained_manacle_disable_run()
    expected = _identity(run.draw_pile[-1])
    original_hand_size = run.public.hand_size
    before_rng = run.rng_snapshot()

    result = disable_supported_boss(run, pre_deal=True)

    assert result.public.hand_size == original_hand_size + 1
    assert result.boss_hand_size_sub is None
    assert result.public.blind.disabled is True
    assert [_identity(card) for card in result.public.hand] == [expected]
    assert len(result.draw_pile) == 51
    assert {_identity(card) for card in result.public.deck} == {
        _identity(card) for card in result.draw_pile
    }
    assert result.rng_snapshot() == before_rng


def test_env_r2_chicot_predeal_manacle_disable_isolates_input():
    run = _retained_manacle_disable_run()
    original_hand_size = run.public.hand_size
    original_draw = [_identity(card) for card in run.draw_pile]

    result = disable_supported_boss(run, pre_deal=True)

    assert result is not run
    assert run.public.hand_size == original_hand_size
    assert run.boss_hand_size_sub == 1
    assert run.public.hand == []
    assert [_identity(card) for card in run.draw_pile] == original_draw
    assert not getattr(run.public.blind, "disabled", False)


def test_env_r2_chicot_predeal_manacle_disable_fails_closed_without_retained_deck():
    run = _retained_manacle_disable_run()
    run.draw_pile.pop()
    run.public.deck = list(run.draw_pile)

    with pytest.raises(HeadlessTransitionError, match="complete permanent deck"):
        disable_supported_boss(run, pre_deal=True)

    assert run.boss_hand_size_sub == 1
    assert not getattr(run.public.blind, "disabled", False)


def test_env_r2_postdeal_manacle_disable_still_requires_selecting_hand_draw_boundary():
    run = _retained_manacle_disable_run()

    with pytest.raises(HeadlessTransitionError, match="SELECTING_HAND"):
        disable_supported_boss(run, pre_deal=False)
