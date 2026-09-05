import pytest

from games.balatro.env.consumable_centers import (
    VANILLA_PLANET_CENTER_ORDER,
    VANILLA_TAROT_CENTER_ORDER,
)
from games.balatro.env.shop_consumable_generation import poll_base_shop_consumable_center
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "CONSUMABLE") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 3
    return HeadlessRunState(public=state, seed=seed)


@pytest.mark.parametrize(
    ("card_type", "eligible"),
    [
        ("Tarot", VANILLA_TAROT_CENTER_ORDER),
        ("Planet", VANILLA_PLANET_CENTER_ORDER),
    ],
)
def test_env_r2_consumable_identity_is_seed_replay_deterministic(card_type, eligible):
    first = poll_base_shop_consumable_center(_run(), card_type, eligible)
    second = poll_base_shop_consumable_center(_run(), card_type, eligible)

    assert first.center_key == second.center_key
    assert first.resamples == 0
    assert first.run.rng_snapshot() == second.run.rng_snapshot()
    assert first.center_key in eligible


@pytest.mark.parametrize(
    ("card_type", "fallback"),
    [("Tarot", "c_strength"), ("Planet", "c_pluto")],
)
def test_env_r2_consumable_identity_uses_vanilla_empty_pool_fallback(card_type, fallback):
    result = poll_base_shop_consumable_center(_run(), card_type, ())

    assert result.center_key == fallback
    assert result.resamples == 0


def test_env_r2_consumable_identity_preserves_input_rng_state():
    run = _run()
    before = run.rng_snapshot()

    result = poll_base_shop_consumable_center(run, "Tarot", VANILLA_TAROT_CENTER_ORDER)

    assert result.run is not run
    assert run.rng_snapshot() == before
    assert result.run.rng_snapshot() != before


def test_env_r2_consumable_identity_rejects_guessed_or_modified_boundaries():
    run = _run()
    with pytest.raises(HeadlessTransitionError, match="Tarot or Planet"):
        poll_base_shop_consumable_center(run, "Spectral", ())

    run = _run()
    run.public.vouchers.append("Tarot Merchant")
    with pytest.raises(HeadlessTransitionError, match="voucher modifiers"):
        poll_base_shop_consumable_center(run, "Tarot", VANILLA_TAROT_CENTER_ORDER)

    run = _run()
    run.tags.append("Charm Tag")
    with pytest.raises(HeadlessTransitionError, match="Tag effects"):
        poll_base_shop_consumable_center(run, "Tarot", VANILLA_TAROT_CENTER_ORDER)

    run = _run()
    with pytest.raises(HeadlessTransitionError, match="invalid authoritative"):
        poll_base_shop_consumable_center(run, "Planet", {"c_fake"})
