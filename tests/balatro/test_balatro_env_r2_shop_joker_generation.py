import pytest

from games.balatro.env.shop_joker_generation import (
    generate_ordinary_shop_joker_descriptor,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "SHOP-JOKER") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [{"rarity": 1, "key": "j_joker"}],
        "2": [{"rarity": 2, "key": "j_stencil"}],
        "3": [{"rarity": 3, "key": "j_dna"}],
        "4": [],
    }
    state.joker_generation_edition_rate = 1.0
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_ordinary_shop_joker_descriptor_is_deterministic_and_source_ordered():
    first = _run("SHOP-JOKER-SEED")
    second = _run("SHOP-JOKER-SEED")
    before = first.rng_snapshot()

    result = generate_ordinary_shop_joker_descriptor(first)
    repeated = generate_ordinary_shop_joker_descriptor(second)

    assert (result.center_key, result.rarity, result.edition, result.resamples) == (
        repeated.center_key,
        repeated.rarity,
        repeated.edition,
        repeated.resamples,
    )
    assert result.run.rng_snapshot() == repeated.run.rng_snapshot()
    assert first.rng_snapshot() == before
    assert result.run.rng_snapshot() != before

    expected_center = {
        1: "j_joker",
        2: "j_stencil",
        3: "j_dna",
    }[result.rarity]
    assert result.center_key == expected_center
    assert result.resamples >= 0
    assert result.edition in {None, "Foil", "Holographic", "Polychrome", "Negative"}

    nodes = result.run.rng.nodes
    assert "rarity1sho" in nodes
    assert f"Joker{result.rarity}sho" in nodes
    assert "edisho1" in nodes


def test_env_r2_ordinary_shop_joker_descriptor_requires_authoritative_pool():
    run = _run()
    run.public.joker_generation_pool_observed = False

    with pytest.raises(HeadlessTransitionError, match="not authoritatively observed"):
        generate_ordinary_shop_joker_descriptor(run)


def test_env_r2_ordinary_shop_joker_descriptor_rejects_edition_rate_modifiers():
    run = _run()
    run.public.joker_generation_edition_rate = 2.0

    with pytest.raises(HeadlessTransitionError, match="edition-rate modifiers"):
        generate_ordinary_shop_joker_descriptor(run)
