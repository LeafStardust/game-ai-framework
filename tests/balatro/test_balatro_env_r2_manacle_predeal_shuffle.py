import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.boss_disable import disable_supported_boss
from games.balatro.env.predeal_continuation import deal_after_retained_preblind_draw
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _prepared_run() -> tuple[HeadlessRunState, tuple[str, str]]:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 8
    state.blind = Blind(BlindType.BOSS, 20000)
    state.boss_name = "The Manacle"
    run = HeadlessRunState(public=state, seed="CHICOT-MANACLE-SHUFFLE")

    order = run.require_playing_card_order()
    run.public.owned_deck = list(order)
    run.draw_pile = [*order[7:], *order[:7]]
    run.public.deck = list(order)
    run.boss_hand_size_sub = 1
    run.public.hand_size -= 1

    disabled = disable_supported_boss(run, pre_deal=True)
    pre_draw = (disabled.public.hand[0].rank, disabled.public.hand[0].suit)
    disabled.public.phase = "DRAW_TO_HAND"
    return disabled, pre_draw


def _identity(card) -> tuple[str, str]:
    return card.rank, card.suit


def test_env_r2_post_manacle_shuffle_keeps_predraw_and_fills_restored_hand():
    run, pre_draw = _prepared_run()

    result = deal_after_retained_preblind_draw(run)

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size == 8
    assert pre_draw in [_identity(card) for card in result.public.hand]
    assert pre_draw not in [_identity(card) for card in result.draw_pile]
    assert len(result.draw_pile) == 44
    assert len(result.public.deck) == 44
    assert f"nr{result.public.ante}" in result.rng.nodes


def test_env_r2_post_manacle_shuffle_partitions_all_owned_cards_without_redraw():
    run, pre_draw = _prepared_run()

    result = deal_after_retained_preblind_draw(run)

    order = result.require_playing_card_order()
    zones = [*result.public.hand, *result.draw_pile]
    assert len(zones) == len(order) == 52
    assert len({id(card) for card in zones}) == 52
    assert {id(card) for card in zones} == {id(card) for card in order}
    assert [_identity(card) for card in result.public.hand].count(pre_draw) == 1


def test_env_r2_post_manacle_shuffle_is_deterministic_and_isolates_input():
    run, _ = _prepared_run()
    before_rng = run.rng_snapshot()
    before_hand = [_identity(card) for card in run.public.hand]
    before_draw = [_identity(card) for card in run.draw_pile]

    first = deal_after_retained_preblind_draw(run)
    second = deal_after_retained_preblind_draw(run)

    assert [_identity(card) for card in first.public.hand] == [
        _identity(card) for card in second.public.hand
    ]
    assert [_identity(card) for card in first.draw_pile] == [
        _identity(card) for card in second.draw_pile
    ]
    assert first.rng_snapshot() == second.rng_snapshot()
    assert run.rng_snapshot() == before_rng
    assert [_identity(card) for card in run.public.hand] == before_hand
    assert [_identity(card) for card in run.draw_pile] == before_draw


def test_env_r2_post_manacle_shuffle_rejects_partition_drift_before_rng():
    run, _ = _prepared_run()
    before_rng = run.rng_snapshot()
    run.draw_pile.pop()
    run.public.deck = list(run.draw_pile)

    with pytest.raises(HeadlessTransitionError, match="partition owned cards"):
        deal_after_retained_preblind_draw(run)

    assert run.rng_snapshot() == before_rng


def test_env_r2_post_manacle_shuffle_rejects_extra_predraw_card():
    run, _ = _prepared_run()
    extra = run.draw_pile.pop()
    run.public.deck = list(run.draw_pile)
    run.public.hand.append(extra)

    with pytest.raises(HeadlessTransitionError, match="exactly one hand card"):
        deal_after_retained_preblind_draw(run)
