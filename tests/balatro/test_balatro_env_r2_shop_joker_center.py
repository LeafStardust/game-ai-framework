import pytest

from games.balatro.env.joker_centers import vanilla_joker_pool
from games.balatro.env.shop_generation import poll_base_shop_joker_center
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _shop_run(seed: str = "TESTSEED") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_shop_joker_center_empty_pool_uses_joker_fallback_without_resample():
    run = _shop_run()
    before_rng = run.rng_snapshot()

    result = poll_base_shop_joker_center(run, 3, set())

    assert result.center_key == "j_joker"
    assert result.rarity == 3
    assert result.resamples == 0
    assert run.rng_snapshot() == before_rng
    assert "Joker3sho" in result.run.rng.nodes
    assert all("resample" not in key for key in result.run.rng.nodes)


def test_env_r2_shop_joker_center_preserves_source_resample_numbering():
    common = vanilla_joker_pool(1)

    # Probe the source-exact first index on an isolated run, then deliberately
    # make that position unavailable so the production helper must take the
    # vanilla `_resample2` path rather than a compacted-pool shortcut.
    probe = _shop_run()
    first_index = probe.rng.pseudorandom_element_index(len(common), "Joker1sho")
    eligible_key = common[(first_index + 1) % len(common)]

    result = poll_base_shop_joker_center(_shop_run(), 1, {eligible_key})

    assert result.center_key == eligible_key
    assert result.resamples >= 1
    assert "Joker1sho" in result.run.rng.nodes
    assert "Joker1sho_resample2" in result.run.rng.nodes
    assert "Joker1sho_resample1" not in result.run.rng.nodes


def test_env_r2_shop_joker_center_is_deterministic_and_isolates_input_rng():
    run = _shop_run("IDENTITY-SEED")
    common = set(vanilla_joker_pool(1))
    before = run.rng_snapshot()

    left = poll_base_shop_joker_center(run, 1, common)
    right = poll_base_shop_joker_center(run, 1, common)

    assert left.center_key == right.center_key
    assert left.resamples == right.resamples == 0
    assert left.run.rng_snapshot() == right.run.rng_snapshot()
    assert run.rng_snapshot() == before


def test_env_r2_shop_joker_center_rejects_nonordinary_rarity_and_wrong_shop_boundary():
    run = _shop_run()

    for rarity in (0, 4, True, "1"):
        with pytest.raises(HeadlessTransitionError, match="rarity"):
            poll_base_shop_joker_center(run, rarity, {"j_joker"})

    run.public.shop_active = False
    with pytest.raises(HeadlessTransitionError, match="active SHOP"):
        poll_base_shop_joker_center(run, 1, {"j_joker"})


def test_env_r2_shop_joker_center_keeps_dynamic_eligibility_external_and_strict():
    run = _shop_run()

    with pytest.raises(ValueError, match="unknown vanilla Joker"):
        poll_base_shop_joker_center(run, 1, {"j_not_real"})
    with pytest.raises(TypeError, match="collection"):
        poll_base_shop_joker_center(run, 1, "j_joker")
