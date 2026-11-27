import pytest

from games.balatro.env.episode_backend import pristine_red_white_reset
from games.balatro.env.shop_consumable_generation_state import generate_held_eight_ball_tarot
from games.balatro.env.transition import HeadlessTransitionError


def _run():
    run = pristine_red_white_reset(48)
    run.public.phase = "SELECTING_HAND"
    run.public.ante = 2
    run.public.shop_inflation_observed = True
    return run


def test_env_r2_eight_ball_publishes_tarot_and_suppresses_held_center():
    run = _run()
    first = generate_held_eight_ball_tarot(run)
    second = generate_held_eight_ball_tarot(first)

    assert run.public.consumables == []
    assert run.rng.nodes == {}
    strength, other = second.public.consumables
    assert (strength.center_key, strength.price, strength.discovered) == (
        "c_strength", 3, True,
    )
    assert other.center_key != strength.center_key
    eligible = {record["key"] for record in second.public.consumable_generation_pools["Tarot"]}
    for item in (strength, other):
        assert item.center_key not in eligible
        assert second.generated_center_discovered(item.center_key) is True
        assert item.center_key in second.tag_profile_state.discovered_center_keys
    assert "Tarot8ba2" in second.rng.nodes

    snapshot = second.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="exact open inventory"):
        generate_held_eight_ball_tarot(second)
    assert second.rng_snapshot() == snapshot


def test_env_r2_eight_ball_rejects_inconsistent_pool_before_rng():
    run = _run()
    result = generate_held_eight_ball_tarot(run)
    result.public.consumable_generation_pools = run.public.consumable_generation_pools
    snapshot = result.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="visible duplicate"):
        generate_held_eight_ball_tarot(result)
    assert result.rng_snapshot() == snapshot
