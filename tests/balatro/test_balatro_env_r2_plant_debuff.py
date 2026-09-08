import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.blind_start import prepare_supported_plant_start, start_supported_plant
from games.balatro.env.boss_debuffs import clear_plant_face_debuff
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.state import BalatroState


def _run(*, pareidolia: bool = False, seed: str = "PLANT") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "BLIND_SELECT"
    state.ante = 4
    state.round = 8
    state.blind = Blind(BlindType.BOSS, 20000)
    state.boss_name = "The Plant"
    state.round_reset_hands_observed = True
    state.round_reset_hands = 4
    state.round_reset_discards_observed = True
    state.round_reset_discards = 3
    if pareidolia:
        state.jokers = [PareidoliaJoker()]
    return HeadlessRunState(public=state, seed=seed)


def _identity(card):
    return card.rank, card.suit


def test_env_r2_plant_predeal_debuffs_natural_twelve_face_cards_without_pareidolia():
    result = prepare_supported_plant_start(_run())

    cards = result.require_playing_card_order()
    assert result.public.phase == "DRAW_TO_HAND"
    assert result.public.round == 9
    assert sum(card.debuffed for card in cards) == 12
    assert all(card.debuffed is (card.rank in {"J", "Q", "K"}) for card in cards)


def test_env_r2_plant_pareidolia_makes_all_fifty_two_cards_face_for_boss_check():
    result = prepare_supported_plant_start(_run(pareidolia=True))

    cards = result.require_playing_card_order()
    assert len(cards) == 52
    assert all(card.debuffed for card in cards)


def test_env_r2_plant_full_start_preserves_face_debuffs_through_shuffle_and_deal():
    result = start_supported_plant(_run(seed="PLANT-DEAL"))

    assert result.public.phase == "SELECTING_HAND"
    assert len(result.public.hand) == 8
    assert len(result.draw_pile) == 44
    assert result.public.owned_deck is not None
    assert sum(card.debuffed for card in result.public.owned_deck) == 12
    for card in result.public.hand + result.draw_pile:
        assert card.debuffed is (card.rank in {"J", "Q", "K"})


def test_env_r2_plant_pareidolia_does_not_change_shuffle_or_draw_identity():
    natural = start_supported_plant(_run(seed="SAME-PLANT"))
    all_face = start_supported_plant(_run(pareidolia=True, seed="SAME-PLANT"))

    assert [_identity(card) for card in all_face.public.hand] == [
        _identity(card) for card in natural.public.hand
    ]
    assert [_identity(card) for card in all_face.draw_pile] == [
        _identity(card) for card in natural.draw_pile
    ]
    assert all_face.rng_snapshot() == natural.rng_snapshot()
    assert sum(card.debuffed for card in natural.require_playing_card_order()) == 12
    assert sum(card.debuffed for card in all_face.require_playing_card_order()) == 52


@pytest.mark.parametrize("pareidolia", [False, True])
def test_env_r2_plant_cleanup_clears_exact_owned_debuff_pattern_without_zone_or_rng_change(
    pareidolia,
):
    active = start_supported_plant(_run(pareidolia=pareidolia))
    before_hand = [_identity(card) for card in active.public.hand]
    before_draw = [_identity(card) for card in active.draw_pile]
    before_rng = active.rng_snapshot()

    result = clear_plant_face_debuff(active)

    assert all(not card.debuffed for card in result.require_playing_card_order())
    assert [_identity(card) for card in result.public.hand] == before_hand
    assert [_identity(card) for card in result.draw_pile] == before_draw
    assert result.rng_snapshot() == before_rng


def test_env_r2_plant_start_isolates_input_cards_and_rng():
    run = _run(pareidolia=True)
    before_rng = run.rng_snapshot()

    result = start_supported_plant(run)

    assert all(not card.debuffed for card in run.require_playing_card_order())
    assert run.public.phase == "BLIND_SELECT"
    assert run.public.round == 8
    assert run.rng_snapshot() == before_rng
    assert all(card.debuffed for card in result.require_playing_card_order())
    assert result.rng_snapshot() != before_rng


def test_env_r2_plant_rejects_preexisting_unknown_debuff_and_permanent_mutation():
    run = _run()
    run.public.deck[0].debuffed = True
    before_rng = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="clean pre-blind"):
        start_supported_plant(run)
    assert run.rng_snapshot() == before_rng

    run = _run()
    run.public.deck[0].enhancement = "Bonus"
    before_rng = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="modified playing cards"):
        start_supported_plant(run)
    assert run.rng_snapshot() == before_rng


def test_env_r2_plant_cleanup_rejects_unowned_debuff_pattern():
    active = start_supported_plant(_run())
    nonface = next(card for card in active.require_playing_card_order() if card.rank == "A")
    nonface.debuffed = True

    with pytest.raises(HeadlessTransitionError, match="unowned card debuff"):
        clear_plant_face_debuff(active)


def test_env_r2_plant_gate_rejects_other_boss():
    run = _run()
    run.public.boss_name = "The Pillar"

    with pytest.raises(HeadlessTransitionError, match="requires The Plant"):
        prepare_supported_plant_start(run)
