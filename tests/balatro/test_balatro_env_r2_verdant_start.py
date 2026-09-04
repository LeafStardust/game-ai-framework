import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_verdant_leaf_start,
    start_supported_verdant_leaf,
)
from games.balatro.env.joker_sale import sell_static_joker_during_verdant
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.round = 5
    state.ante = 3
    state.boss_name = "Verdant Leaf"
    state.blind = Blind(BlindType.BOSS, 8000)
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    joker = FlatMultJoker()
    joker.sell_cost = 4
    state.jokers = [joker]
    return HeadlessRunState(public=state, seed="VERDANT-START")


def test_env_r2_verdant_prepare_applies_source_ordered_all_card_debuff():
    run = _run()

    result = prepare_supported_verdant_leaf_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 6
    assert result.public.blind_score == 8000
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert result.public.blind.disabled is False
    assert all(card.debuffed for card in result.require_playing_card_order())

    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 5
    assert all(not card.debuffed for card in run.require_playing_card_order())


def test_env_r2_verdant_start_composes_exact_shuffle_deal_without_losing_debuffs():
    result = start_supported_verdant_leaf(_run())

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == result.public.hand_size
    assert len(result.draw_pile) + len(result.public.hand) == 52
    assert all(card.debuffed for card in result.require_playing_card_order())
    assert all(card.debuffed for card in result.public.hand)


def test_env_r2_verdant_start_then_static_sale_disables_and_clears_every_card():
    run = start_supported_verdant_leaf(_run())

    result = sell_static_joker_during_verdant(run, 0)

    assert result.public.blind.disabled is True
    assert result.public.jokers == []
    assert result.public.money == run.public.money + 4
    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert all(not card.debuffed for card in result.public.hand)
    assert all(not card.debuffed for card in result.draw_pile)


def test_env_r2_verdant_start_rejects_wrong_boss_and_disabled_blind():
    run = _run()
    run.public.boss_name = "The Plant"
    with pytest.raises(HeadlessTransitionError, match="requires Verdant Leaf"):
        prepare_supported_verdant_leaf_start(run)

    run = _run()
    run.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="active blind state"):
        prepare_supported_verdant_leaf_start(run)
