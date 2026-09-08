import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_pillar_start,
    start_supported_pillar,
)
from games.balatro.env.boss_debuffs import clear_pillar_history_debuff
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "PILLAR") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 3
    state.round = 6
    state.blind = Blind(BlindType.BOSS, requirement=8000)
    state.boss_name = "The Pillar"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    run = HeadlessRunState(public=state, seed=seed)
    for card in run.require_playing_card_order():
        card.played_this_ante_observed = True
        card.played_this_ante = False
    return run


def _identity(card):
    return card.rank, card.suit


def test_env_r2_pillar_predeal_debuffs_exact_played_this_ante_cards():
    run = _run()
    marked = run.require_playing_card_order()[::9]
    marked_ids = {_identity(card) for card in marked}
    for card in marked:
        card.played_this_ante = True

    result = prepare_supported_pillar_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 7
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert {
        _identity(card)
        for card in result.require_playing_card_order()
        if card.debuffed
    } == marked_ids
    assert all(card.played_this_ante_observed for card in result.require_playing_card_order())
    assert {
        _identity(card)
        for card in result.require_playing_card_order()
        if card.played_this_ante
    } == marked_ids


def test_env_r2_pillar_start_preserves_history_debuffs_through_shuffle_and_deal():
    run = _run()
    marked = run.require_playing_card_order()[0]
    marked_id = _identity(marked)
    marked.played_this_ante = True

    result = start_supported_pillar(run)

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size
    visible_cards = list(result.public.hand) + list(result.public.deck)
    matches = [card for card in visible_cards if _identity(card) == marked_id]
    assert len(matches) == 1
    assert matches[0].debuffed is True
    assert matches[0].played_this_ante is True
    assert matches[0].played_this_ante_observed is True


def test_env_r2_pillar_start_isolates_source_state_and_rng():
    run = _run()
    run.require_playing_card_order()[0].played_this_ante = True
    before_rng = run.rng_snapshot()

    result = start_supported_pillar(run)

    assert result is not run
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 6
    assert not any(card.debuffed for card in run.require_playing_card_order())
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng


def test_env_r2_pillar_missing_history_on_any_permanent_card_fails_closed():
    run = _run()
    run.require_playing_card_order()[-1].played_this_ante_observed = False

    with pytest.raises(
        HeadlessTransitionError,
        match="authoritative played-this-ante state",
    ):
        prepare_supported_pillar_start(run)


def test_env_r2_pillar_false_history_produces_no_debuffs():
    result = prepare_supported_pillar_start(_run())

    assert not any(card.debuffed for card in result.require_playing_card_order())


def test_env_r2_pillar_wrong_boss_fails_closed():
    run = _run()
    run.public.boss_name = "The Plant"

    with pytest.raises(HeadlessTransitionError, match="requires The Pillar"):
        prepare_supported_pillar_start(run)


def test_env_r2_pillar_cleanup_clears_transient_debuff_but_retains_history():
    run = _run()
    marked = run.require_playing_card_order()[::11]
    marked_ids = {_identity(card) for card in marked}
    for card in marked:
        card.played_this_ante = True

    prepared = prepare_supported_pillar_start(run)
    cleaned = clear_pillar_history_debuff(prepared)

    assert not any(card.debuffed for card in cleaned.require_playing_card_order())
    assert {
        _identity(card)
        for card in cleaned.require_playing_card_order()
        if card.played_this_ante
    } == marked_ids
    assert all(
        card.played_this_ante_observed
        for card in cleaned.require_playing_card_order()
    )


def test_env_r2_pillar_cleanup_rejects_unowned_debuff_pattern():
    run = _run()
    cards = run.require_playing_card_order()
    cards[0].played_this_ante = True
    prepared = prepare_supported_pillar_start(run)
    prepared.require_playing_card_order()[1].debuffed = True

    with pytest.raises(HeadlessTransitionError, match="unowned card debuff"):
        clear_pillar_history_debuff(prepared)
