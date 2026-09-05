import pytest

from games.balatro.env.shop_generation import (
    _joker_edition_from_roll,
    poll_base_shop_joker_edition,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "EDITION") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 1
    state.joker_generation_edition_rate = 1.0
    return HeadlessRunState(public=state, seed=seed)


def test_env_r2_base_shop_joker_edition_threshold_order_matches_vanilla():
    assert _joker_edition_from_roll(0.9971, 1.0) == "Negative"
    assert _joker_edition_from_roll(0.997, 1.0) == "Polychrome"
    assert _joker_edition_from_roll(0.9941, 1.0) == "Polychrome"
    assert _joker_edition_from_roll(0.994, 1.0) == "Holographic"
    assert _joker_edition_from_roll(0.9801, 1.0) == "Holographic"
    assert _joker_edition_from_roll(0.98, 1.0) == "Foil"
    assert _joker_edition_from_roll(0.9601, 1.0) == "Foil"
    assert _joker_edition_from_roll(0.96, 1.0) is None


def test_env_r2_edition_rate_scales_nonnegative_thresholds_but_not_negative():
    # At base rate this value is below the Foil threshold; Hone makes it Foil.
    assert _joker_edition_from_roll(0.94, 1.0) is None
    assert _joker_edition_from_roll(0.94, 2.0) == "Foil"

    # Glow Up widens the Holographic threshold further.
    assert _joker_edition_from_roll(0.93, 2.0) == "Foil"
    assert _joker_edition_from_roll(0.93, 4.0) == "Holographic"

    # Negative is tested first and its threshold is deliberately unscaled.
    assert _joker_edition_from_roll(0.998, 1.0) == "Negative"
    assert _joker_edition_from_roll(0.998, 4.0) == "Negative"


def test_env_r2_negative_threshold_is_not_scaled_by_edition_rate():
    assert _joker_edition_from_roll(0.998, 0.0) == "Negative"
    assert _joker_edition_from_roll(0.996, 0.0) is None


def test_env_r2_base_shop_joker_edition_is_deterministic_and_isolates_input_rng():
    first = _run("EDITION-SEED")
    second = _run("EDITION-SEED")
    before = first.rng_snapshot()

    first_result = poll_base_shop_joker_edition(first)
    second_result = poll_base_shop_joker_edition(second)

    assert first_result.edition == second_result.edition
    assert first_result.run.rng_snapshot() == second_result.run.rng_snapshot()
    assert first.rng_snapshot() == before
    assert first_result.run.rng_snapshot() != before
    assert "edisho1" in first_result.run.rng.nodes
    assert first_result.edition in {None, "Foil", "Holographic", "Polychrome", "Negative"}


@pytest.mark.parametrize(
    "vouchers,rate",
    (
        (["v_hone"], 2.0),
        (["v_hone", "v_glow_up"], 4.0),
    ),
)
def test_env_r2_exact_edition_rate_vouchers_are_generation_safe(vouchers, rate):
    run = _run("EDITION-VOUCHER")
    run.public.vouchers = list(vouchers)
    run.public.vouchers_observed = True
    run.public.joker_generation_edition_rate = rate
    before = run.rng_snapshot()

    result = poll_base_shop_joker_edition(run)

    assert result.run.rng_snapshot() != before
    assert run.rng_snapshot() == before
    assert "edisho1" in result.run.rng.nodes


@pytest.mark.parametrize(
    "vouchers,rate",
    (
        (["v_hone"], 1.0),
        (["v_hone"], 4.0),
        (["v_hone", "v_glow_up"], 2.0),
        (["v_glow_up"], 4.0),
    ),
)
def test_env_r2_edition_rate_voucher_state_mismatch_fails_before_rng(vouchers, rate):
    run = _run("EDITION-MISMATCH")
    run.public.vouchers = list(vouchers)
    run.public.vouchers_observed = True
    run.public.joker_generation_edition_rate = rate
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="voucher modifiers"):
        poll_base_shop_joker_edition(run)

    assert run.rng_snapshot() == before
    assert "edisho1" not in run.rng.nodes


def test_env_r2_base_shop_joker_edition_reuses_base_shop_fail_closed_boundary():
    run = _run()
    run.public.vouchers.append("v_hone")
    # Non-empty Voucher ownership must be authoritative and rate-consistent.
    with pytest.raises(HeadlessTransitionError, match="voucher modifiers"):
        poll_base_shop_joker_edition(run)

    run = _run()
    run.tags.append("Negative Tag")
    with pytest.raises(HeadlessTransitionError, match="Tag shop effects"):
        poll_base_shop_joker_edition(run)
