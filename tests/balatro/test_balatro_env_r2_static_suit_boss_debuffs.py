import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import (
    prepare_supported_static_suit_debuff_boss_start,
    start_supported_static_suit_debuff_boss,
)
from games.balatro.env.boss_debuffs import clear_static_suit_boss_debuff
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


_BOSSES = [
    ("The Goad", "Spades"),
    ("The Window", "Diamonds"),
    ("The Head", "Hearts"),
    ("The Club", "Clubs"),
]


def _run(*, boss_name: str, seed: str = "SUIT-BOSS") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 2
    state.round = 3
    state.blind = Blind(BlindType.BOSS, 1600)
    state.boss_name = boss_name
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    return HeadlessRunState(public=state, seed=seed)


def _identity(card):
    return card.rank, card.suit


@pytest.mark.parametrize(("boss_name", "suit"), _BOSSES)
def test_env_r2_static_suit_boss_predeal_debuffs_exactly_thirteen_cards(boss_name, suit):
    run = _run(boss_name=boss_name)

    result = prepare_supported_static_suit_debuff_boss_start(run)

    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 4
    assert result.public.hands_remaining == 4
    assert result.public.discards_remaining == 3
    assert sum(card.debuffed for card in result.require_playing_card_order()) == 13
    assert all(
        card.debuffed is (card.suit == suit)
        for card in result.require_playing_card_order()
    )


@pytest.mark.parametrize(("boss_name", "suit"), _BOSSES)
def test_env_r2_static_suit_boss_full_start_preserves_debuffs_through_shuffle_and_deal(
    boss_name,
    suit,
):
    run = _run(boss_name=boss_name, seed="SAME-SUIT")

    result = start_supported_static_suit_debuff_boss(run)

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert len(result.public.deck) == 44
    assert result.public.owned_deck is not None
    assert sum(card.debuffed for card in result.public.owned_deck) == 13
    for card in result.public.hand + result.draw_pile:
        assert card.debuffed is (card.suit == suit)


@pytest.mark.parametrize(("boss_name", "suit"), _BOSSES)
def test_env_r2_static_suit_boss_cleanup_clears_owned_debuff_after_deal(boss_name, suit):
    active = start_supported_static_suit_debuff_boss(_run(boss_name=boss_name))
    before_rng = active.rng_snapshot()
    before_hand = [_identity(card) for card in active.public.hand]
    before_draw = [_identity(card) for card in active.draw_pile]

    result = clear_static_suit_boss_debuff(active)

    assert sum(card.debuffed for card in active.require_playing_card_order()) == 13
    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert [_identity(card) for card in result.public.hand] == before_hand
    assert [_identity(card) for card in result.draw_pile] == before_draw
    assert result.rng_snapshot() == before_rng


@pytest.mark.parametrize(("boss_name", "suit"), _BOSSES)
def test_env_r2_static_suit_boss_start_isolates_input_cards_and_rng(boss_name, suit):
    run = _run(boss_name=boss_name)
    before_rng = run.rng_snapshot()

    result = start_supported_static_suit_debuff_boss(run)

    assert all(not card.debuffed for card in run.require_playing_card_order())
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 3
    assert run.rng_snapshot() == before_rng
    assert any(card.debuffed for card in result.require_playing_card_order())
    assert result.rng_snapshot() != before_rng


def test_env_r2_static_suit_boss_rejects_preexisting_unknown_debuff_without_rng_advance():
    run = _run(boss_name="The Goad")
    run.public.deck[0].debuffed = True
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="clean pre-blind"):
        start_supported_static_suit_debuff_boss(run)

    assert run.rng_snapshot() == before_rng


def test_env_r2_static_suit_boss_rejects_permanent_card_mutation_without_rng_advance():
    run = _run(boss_name="The Head")
    run.public.deck[0].enhancement = "Wild Card"
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="modified playing cards"):
        start_supported_static_suit_debuff_boss(run)

    assert run.rng_snapshot() == before_rng


def test_env_r2_static_suit_boss_cleanup_rejects_unowned_debuff_pattern():
    active = start_supported_static_suit_debuff_boss(_run(boss_name="The Club"))
    nonclub = next(card for card in active.require_playing_card_order() if card.suit != "Clubs")
    nonclub.debuffed = True

    with pytest.raises(HeadlessTransitionError, match="unowned card debuff"):
        clear_static_suit_boss_debuff(active)


def test_env_r2_static_suit_boss_gate_rejects_other_bosses():
    run = _run(boss_name="The Plant")

    with pytest.raises(HeadlessTransitionError, match="static suit-debuff start set"):
        prepare_supported_static_suit_debuff_boss_start(run)
