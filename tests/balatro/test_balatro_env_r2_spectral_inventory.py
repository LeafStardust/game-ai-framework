import pytest

from games.balatro.blinds.blind import Blind, BlindType
from games.balatro.env.consumable_use import can_use_planet_exact
from games.balatro.env.deal import deal_supported_round_start
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import encode_public_observation
from games.balatro.env.play_transition import apply_supported_ordinary_play
from games.balatro.env.shop_repricing import reprice_exact_generated_shop
from games.balatro.env.spectral_inventory import GeneratedHeldSpectral, generate_seance_held_spectral
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError
from games.balatro.jokers.seance import SeanceJoker


def _run():
    run = pristine_red_white_reset(15)
    run.public.phase = "SELECTING_HAND"
    run.public.shop_inflation_observed = True
    run.consumable_usage_observed = True
    return run


def test_env_r2_seance_inventory_discovers_cards_and_suppresses_held_duplicates():
    run = _run()
    assert run.generated_center_discovered("c_incantation") is False

    generate_seance_held_spectral(run)
    generate_seance_held_spectral(run)

    first, second = run.public.consumables
    assert type(first) is type(second) is GeneratedHeldSpectral
    assert (first.center_key, second.center_key) == ("c_cryptid", "c_medium")
    assert "Spectralsea1_resample2" in run.rng.nodes
    for item in (first, second):
        assert item.price == 4
        assert run.generated_center_discovered(item.center_key) is True
        assert item.center_key in run.tag_profile_state.discovered_center_keys
    snapshot = run.rng_snapshot()
    generate_seance_held_spectral(run)
    assert run.public.consumables == [first, second]
    assert run.rng_snapshot() == snapshot

    assert not can_use_planet_exact(run, 0)
    assert not can_use_planet_exact(run, 1)
    frame = EnvStateFrame(run.public, RunStatus.RUNNING, TurnOwner.TACTICAL_POLICY)
    assert encode_public_observation(frame).shape == (2480,)


def test_env_r2_seance_missing_profile_authority_fails_before_draw():
    run = _run()
    del run.generation_discovery["c_incantation"]
    snapshot = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="Spectral authority"):
        generate_seance_held_spectral(run)

    assert run.rng_snapshot() == snapshot
    assert run.public.consumables == []


def test_env_r2_held_spectral_reprices_with_canonical_discount():
    run = _run()
    generate_seance_held_spectral(run)
    run.public.phase = "SHOP"
    run.public.shop_active = True
    original = run.public.consumables[0]

    for discount, expected in ((25, 3), (50, 2)):
        result = reprice_exact_generated_shop(run, discount_percent=discount)
        assert result.public.consumables == [GeneratedHeldSpectral(original.center_key, expected)]
        assert run.public.consumables == [original]
        assert result.rng_snapshot() == run.rng_snapshot()


_STRAIGHT_FLUSH_INDICES = (0, 1, 2, 4, 5)


def _seance_play_run(*, mouth_locked=False):
    run = pristine_red_white_reset(9)
    state = run.public
    state.phase = "DRAW_TO_HAND"
    state.shop_inflation_observed = True
    state.blind = Blind(BlindType.SMALL, requirement=99_999)
    state.blind_score = 99_999
    state.hands_remaining = 4
    state.discards_remaining = 3
    if mouth_locked:
        state.blind = Blind(BlindType.BOSS, requirement=99_999)
        state.blind_is_boss = True
        state.boss_name = "The Mouth"
        state.boss_blind_state_observed = True
        state.boss_blind_only_hand = "PAIR"
    joker = SeanceJoker()
    joker.center = "j_seance"
    state.jokers = [joker]
    return deal_supported_round_start(run)


def test_env_r4_seance_play_generates_from_scoring_callback_in_order():
    run = _seance_play_run()
    run.public.jokers.append(SeanceJoker())
    run.public.jokers[1].center = "j_seance"
    before = run.rng_snapshot()
    expected = run.copy()
    generate_seance_held_spectral(expected)
    generate_seance_held_spectral(expected)

    result = apply_supported_ordinary_play(run, _STRAIGHT_FLUSH_INDICES)

    assert result.public.last_played_hand == "STRAIGHT_FLUSH"
    assert result.public.score > 0
    assert len(result.public.consumables) == 2
    assert result.public.consumables == expected.public.consumables
    assert result.rng_snapshot() == expected.rng_snapshot()
    assert run.public.consumables == []
    assert run.rng_snapshot() == before


@pytest.mark.parametrize("boundary", ["high_card", "full", "mouth"])
def test_env_r4_seance_play_consumes_no_spectral_rng_at_inert_boundaries(boundary):
    run = _seance_play_run(mouth_locked=boundary == "mouth")
    if boundary == "full":
        generate_seance_held_spectral(run)
        generate_seance_held_spectral(run)
    indices = (0,) if boundary == "high_card" else _STRAIGHT_FLUSH_INDICES

    result = apply_supported_ordinary_play(run, indices)

    assert result.public.last_played_hand == (
        "HIGH_CARD" if boundary == "high_card" else "STRAIGHT_FLUSH"
    )
    if boundary == "mouth":
        assert result.public.score == 0
    assert result.public.consumables == run.public.consumables
    assert result.rng_snapshot() == run.rng_snapshot()
