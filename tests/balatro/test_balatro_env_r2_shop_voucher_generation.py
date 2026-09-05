import pytest

from games.balatro.env.rng import BalatroRNG
from games.balatro.env.shop_voucher_generation import poll_normal_voucher_key
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed="VOUCHER-SEED", ante=1):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.ante = ante
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_normal_voucher_single_fallback_is_exact_and_input_isolated():
    run = _run()
    before = run.rng_snapshot()

    result = poll_normal_voucher_key(run, ["v_blank"])

    assert result.center_key == "v_blank"
    assert result.resamples == 0
    assert run.rng_snapshot() == before
    assert result.run.rng_snapshot() != before
    assert "Voucher1" in result.run.rng.nodes


def test_env_r2_normal_voucher_uses_voucher_ante_key():
    first = poll_normal_voucher_key(_run("VOUCHER-ANTE", ante=1), ["v_blank"])
    second = poll_normal_voucher_key(_run("VOUCHER-ANTE", ante=2), ["v_blank"])

    assert "Voucher1" in first.run.rng.nodes
    assert "Voucher2" not in first.run.rng.nodes
    assert "Voucher2" in second.run.rng.nodes
    assert "Voucher1" not in second.run.rng.nodes


def test_env_r2_normal_voucher_retries_unavailable_with_source_resample_suffix():
    # Find a deterministic seed whose first two-position poll selects position 0.
    seed = None
    for candidate in range(1, 10000):
        rng = BalatroRNG(candidate)
        if rng.pseudorandom_element_index(2, "Voucher1") == 0:
            seed = candidate
            break
    assert seed is not None

    result = poll_normal_voucher_key(
        _run(seed),
        ["UNAVAILABLE", "v_blank"],
    )

    assert result.center_key == "v_blank"
    assert result.resamples >= 1
    assert "Voucher1" in result.run.rng.nodes
    assert "Voucher1_resample2" in result.run.rng.nodes


def test_env_r2_normal_voucher_replay_is_deterministic():
    pool = ["v_overstock_norm", "UNAVAILABLE", "v_clearance_sale", "v_blank"]

    first = poll_normal_voucher_key(_run("VOUCHER-REPLAY"), pool)
    second = poll_normal_voucher_key(_run("VOUCHER-REPLAY"), pool)

    assert first.center_key == second.center_key
    assert first.resamples == second.resamples
    assert first.run.rng_snapshot() == second.run.rng_snapshot()


@pytest.mark.parametrize(
    "pool,match",
    [
        ([], "cannot be empty"),
        (["UNAVAILABLE"], "available/fallback"),
        (["j_joker"], "non-Voucher"),
        (["v_blank", "v_blank"], "duplicate"),
        (["v_blank", 3], "nonempty strings"),
    ],
)
def test_env_r2_normal_voucher_rejects_malformed_pool_before_rng(pool, match):
    run = _run()
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match=match):
        poll_normal_voucher_key(run, pool)

    assert run.rng_snapshot() == before


def test_env_r2_normal_voucher_rejects_invalid_ante_before_rng():
    run = _run(ante=0)
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="positive exact Ante"):
        poll_normal_voucher_key(run, ["v_blank"])

    assert run.rng_snapshot() == before
