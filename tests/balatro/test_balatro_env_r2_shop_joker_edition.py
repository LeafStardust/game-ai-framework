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


def test_env_r2_base_shop_joker_edition_rejects_rate_modifiers():
    run = _run()
    run.public.joker_generation_edition_rate = 2.0

    with pytest.raises(HeadlessTransitionError, match="does not own edition-rate modifiers"):
        poll_base_shop_joker_edition(run)


def test_env_r2_base_shop_joker_edition_reuses_base_shop_fail_closed_boundary():
    run = _run()
    run.public.vouchers.append("Hone")
    with pytest.raises(HeadlessTransitionError, match="voucher modifiers"):
        poll_base_shop_joker_edition(run)

    run = _run()
    run.tags.append("Negative Tag")
    with pytest.raises(HeadlessTransitionError, match="Tag shop effects"):
        poll_base_shop_joker_edition(run)
