import pytest

from games.balatro.env.deal import (
    deal_pristine_round_start,
    deal_supported_round_start,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "DEBUFF") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "DRAW_TO_HAND"
    state.ante = 1
    state.hand_size = 8
    return HeadlessRunState(public=state, seed=seed)


def _identity(card):
    return card.rank, card.suit


def _debuff_spades(run: HeadlessRunState) -> None:
    for card in run.public.deck:
        if card.suit == "Spades":
            card.debuffed = True


def test_env_r2_base_deck_with_only_transient_debuffs_still_deals_exactly():
    run = _run()
    _debuff_spades(run)

    result = deal_supported_round_start(run)

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert result.public.owned_deck is not None
    assert sum(card.debuffed for card in result.public.owned_deck) == 13


def test_env_r2_transient_debuff_does_not_change_shuffle_or_physical_draw_identity():
    clean = deal_supported_round_start(_run(seed="SAME"))
    debuffed_run = _run(seed="SAME")
    _debuff_spades(debuffed_run)
    debuffed = deal_supported_round_start(debuffed_run)

    assert [_identity(card) for card in debuffed.public.hand] == [
        _identity(card) for card in clean.public.hand
    ]
    assert [_identity(card) for card in debuffed.draw_pile] == [
        _identity(card) for card in clean.draw_pile
    ]
    assert debuffed.rng_snapshot() == clean.rng_snapshot()


def test_env_r2_transient_debuff_flags_follow_same_card_objects_through_zones():
    run = _run()
    _debuff_spades(run)

    result = deal_supported_round_start(run)

    assert result.public.owned_deck is not None
    for card in result.public.hand + result.draw_pile:
        assert card.debuffed is (card.suit == "Spades")
    assert {id(card) for card in result.public.hand} | {
        id(card) for card in result.draw_pile
    } == {id(card) for card in result.public.owned_deck}


def test_env_r2_pristine_wrapper_still_rejects_transiently_debuffed_deck():
    run = _run()
    _debuff_spades(run)

    with pytest.raises(HeadlessTransitionError, match="pristine base-card"):
        deal_pristine_round_start(run)


def test_env_r2_permanent_card_mutation_without_history_still_fails_closed():
    run = _run()
    run.public.deck[0].enhancement = "Bonus"

    before_rng = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="authoritative owned deck"):
        deal_supported_round_start(run)
    assert run.rng_snapshot() == before_rng
    assert run.public.hand == []
