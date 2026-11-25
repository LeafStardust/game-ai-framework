import pytest

from games.balatro.env.consumable_use import can_use_planet_exact
from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.observation_encoding import encode_public_observation
from games.balatro.env.shop_repricing import reprice_exact_generated_shop
from games.balatro.env.spectral_inventory import GeneratedHeldSpectral, generate_seance_held_spectral
from games.balatro.env.state import EnvStateFrame, RunStatus, TurnOwner
from games.balatro.env.transition import HeadlessTransitionError


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
