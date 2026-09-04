import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.joker_sale import (
    apply_verdant_leaf_debuff,
    sell_static_joker_during_verdant,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.state import BalatroState


def _verdant_run(joker) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SELECTING_HAND"
    state.boss_name = "Verdant Leaf"
    state.blind = Blind(BlindType.BOSS, 1000)
    state.money = 7
    joker.sell_cost = 3
    state.jokers = [joker]
    return HeadlessRunState(public=state, seed="VERDANT-SELL")


def test_env_r2_verdant_debuff_and_static_joker_sale_disable_boss_exactly():
    run = apply_verdant_leaf_debuff(_verdant_run(FlatMultJoker()))
    assert all(card.debuffed for card in run.require_playing_card_order())

    result = sell_static_joker_during_verdant(run, 0)

    assert result.public.money == 10
    assert result.public.jokers == []
    assert result.public.boss_name == "Verdant Leaf"
    assert result.public.blind.disabled is True
    assert all(not card.debuffed for card in result.require_playing_card_order())


def test_env_r2_verdant_sale_isolates_input_state_and_cards():
    run = apply_verdant_leaf_debuff(_verdant_run(FlatMultJoker()))
    result = sell_static_joker_during_verdant(run, 0)

    assert run.public.money == 7
    assert len(run.public.jokers) == 1
    assert run.public.blind.disabled is False
    assert all(card.debuffed for card in run.require_playing_card_order())
    assert all(not card.debuffed for card in result.require_playing_card_order())


def test_env_r2_verdant_sale_rejects_resource_sensitive_inverse_lifecycle():
    run = apply_verdant_leaf_debuff(_verdant_run(JugglerJoker()))

    with pytest.raises(HeadlessTransitionError, match="inverse lifecycle"):
        sell_static_joker_during_verdant(run, 0)


def test_env_r2_verdant_sale_rejects_eternal_edition_and_inexact_sell_cost():
    for field, value, message in (
        ("eternal", True, "Eternal"),
        ("edition", "NEGATIVE", "editions"),
        ("sell_cost", True, "sell_cost"),
        ("sell_cost", 2.5, "sell_cost"),
        ("sell_cost", -1, "sell_cost"),
    ):
        joker = FlatMultJoker()
        run = _verdant_run(joker)
        setattr(joker, field, value)
        # _verdant_run installs the object before the mutation above, so rebuild
        # the headless boundary to validate the exact supplied metadata.
        run = HeadlessRunState(public=run.public, seed="VERDANT-SELL")
        run = apply_verdant_leaf_debuff(run)
        with pytest.raises(HeadlessTransitionError, match=message):
            sell_static_joker_during_verdant(run, 0)


def test_env_r2_verdant_sale_requires_active_owned_debuff_and_exact_index():
    run = _verdant_run(FlatMultJoker())
    with pytest.raises(HeadlessTransitionError, match="all-card debuff"):
        sell_static_joker_during_verdant(run, 0)

    run = apply_verdant_leaf_debuff(run)
    with pytest.raises(HeadlessTransitionError, match="out of range"):
        sell_static_joker_during_verdant(run, 1)

    run.public.blind.disabled = True
    with pytest.raises(HeadlessTransitionError, match="already disabled"):
        sell_static_joker_during_verdant(run, 0)


def test_blind_copy_retains_disabled_state_for_verdant_replay():
    blind = Blind(BlindType.BOSS, 1234, disabled=True)
    copied = blind.copy()

    assert copied is not blind
    assert copied.disabled is True
    assert copied.requirement == 1234
