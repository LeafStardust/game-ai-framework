import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.consumable_use import (
    ConsumableTransitionEngine,
    can_use_planet_exact,
    use_planet_exact,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.jokers.constellation import ConstellationJoker
from games.balatro.planets import create_planet
from games.balatro.state import BalatroState
from games.balatro.tarots import create_tarot


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.consumables = [create_planet("PLUTO")]
    constellation = ConstellationJoker()
    constellation.x_mult = 1.4
    state.jokers = [constellation]
    return HeadlessRunState(
        public=state,
        seed="USE-PLANET",
        consumable_usage_observed=True,
        consumable_usage_counts={"c_pluto": 2},
        consumable_usage_totals={"planet": 2, "tarot_planet": 2, "all": 2},
    )


def test_env_r3_planet_use_updates_all_exact_run_state_and_isolates_input():
    run = _run()
    before_rng = run.rng_snapshot()
    assert can_use_planet_exact(run, 0)
    result = use_planet_exact(run, 0)

    assert result.public.consumables == []
    assert result.public.hand_levels["HIGH_CARD"] == 2
    assert result.public.last_tarot_planet == "c_pluto"
    assert result.public.jokers[0].x_mult == pytest.approx(1.5)
    assert result.consumable_usage_counts["c_pluto"] == 3
    assert result.consumable_usage_totals == {
        "planet": 3,
        "tarot_planet": 3,
        "all": 3,
    }
    assert result.rng_snapshot() == before_rng
    assert len(run.public.consumables) == 1
    assert run.public.hand_levels["HIGH_CARD"] == 1
    assert run.public.jokers[0].x_mult == pytest.approx(1.4)


def test_env_r3_consumable_engine_masks_and_executes_exact_planet_use():
    run = _run()
    action = EnvAction.from_alias("USE_CONSUMABLE", {"consumable_index": 0})
    engine = ConsumableTransitionEngine()
    assert engine.legal_actions(run) == (action,)
    assert engine.step(run, action).public.hand_levels["HIGH_CARD"] == 2


def test_env_r3_planet_use_fails_closed_without_usage_history_or_active_shop():
    run = _run()
    run.consumable_usage_observed = False
    assert not can_use_planet_exact(run, 0)

    run = _run()
    run.public.shop_active = False
    assert not can_use_planet_exact(run, 0)


def test_env_r3_planet_use_masks_tarot_and_invalid_index():
    run = _run()
    run.public.consumables = [create_tarot("THE_HERMIT")]
    assert not can_use_planet_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="Planet cards only"):
        use_planet_exact(run, 0)
    assert not can_use_planet_exact(run, True)
    assert not can_use_planet_exact(run, 1)


def test_env_r3_planet_use_rejects_non_run_input():
    assert not can_use_planet_exact(object(), 0)
    with pytest.raises(TypeError, match="HeadlessRunState"):
        use_planet_exact(object(), 0)
