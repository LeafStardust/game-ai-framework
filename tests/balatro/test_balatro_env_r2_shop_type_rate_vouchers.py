import pytest

from games.balatro.env.shop_generation import (
    _shop_rates_for_state,
    _shop_type_from_polled_rate,
    poll_base_shop_card_type,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.env.voucher_capabilities import (
    expected_planet_rate_for_vouchers,
    expected_tarot_rate_for_vouchers,
    shop_generation_vouchers_are_exact,
)
from games.balatro.state import BalatroState


def _run(*, vouchers=(), tarot_rate=4.0, planet_rate=4.0, edition_rate=1.0):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.vouchers_observed = bool(vouchers)
    state.vouchers = list(vouchers)
    state.tarot_rate = tarot_rate
    state.planet_rate = planet_rate
    state.joker_generation_edition_rate = edition_rate
    return HeadlessRunState(public=state, seed="TYPE-RATE")


@pytest.mark.parametrize(
    ("vouchers", "tarot", "planet"),
    [
        ((), 4.0, 4.0),
        (("v_tarot_merchant",), 9.6, 4.0),
        (("v_tarot_merchant", "v_tarot_tycoon"), 32.0, 4.0),
        (("v_planet_merchant",), 4.0, 9.6),
        (("v_planet_merchant", "v_planet_tycoon"), 4.0, 32.0),
        (
            (
                "v_tarot_merchant",
                "v_tarot_tycoon",
                "v_planet_merchant",
                "v_planet_tycoon",
            ),
            32.0,
            32.0,
        ),
    ],
)
def test_env_r2_shop_type_rate_voucher_ownership_implies_exact_rates(
    vouchers,
    tarot,
    planet,
):
    run = _run(vouchers=vouchers, tarot_rate=tarot, planet_rate=planet)

    assert expected_tarot_rate_for_vouchers(run.public) == tarot
    assert expected_planet_rate_for_vouchers(run.public) == planet
    assert shop_generation_vouchers_are_exact(run.public)


def test_env_r2_shop_type_rate_upgrades_require_their_base_vouchers():
    tarot = _run(vouchers=("v_tarot_tycoon",), tarot_rate=32.0)
    assert expected_tarot_rate_for_vouchers(tarot.public) is None
    assert not shop_generation_vouchers_are_exact(tarot.public)

    planet = _run(vouchers=("v_planet_tycoon",), planet_rate=32.0)
    assert expected_planet_rate_for_vouchers(planet.public) is None
    assert not shop_generation_vouchers_are_exact(planet.public)


def test_env_r2_shop_type_rate_mismatch_blocks_before_cdt_rng():
    run = _run(vouchers=("v_tarot_merchant",), tarot_rate=4.0)
    before = run.rng_snapshot()

    assert not shop_generation_vouchers_are_exact(run.public)
    with pytest.raises(HeadlessTransitionError, match="voucher modifiers"):
        poll_base_shop_card_type(run)
    assert run.rng_snapshot() == before


def test_env_r2_tarot_merchant_and_tycoon_expand_only_tarot_weight_interval():
    base = _run()
    merchant = _run(vouchers=("v_tarot_merchant",), tarot_rate=9.6)
    tycoon = _run(
        vouchers=("v_tarot_merchant", "v_tarot_tycoon"),
        tarot_rate=32.0,
    )

    assert _shop_type_from_polled_rate(26.0, _shop_rates_for_state(base.public)) == "Planet"
    assert _shop_type_from_polled_rate(26.0, _shop_rates_for_state(merchant.public)) == "Tarot"
    assert _shop_type_from_polled_rate(40.0, _shop_rates_for_state(tycoon.public)) == "Tarot"


def test_env_r2_planet_merchant_and_tycoon_expand_only_planet_weight_interval():
    merchant = _run(vouchers=("v_planet_merchant",), planet_rate=9.6)
    tycoon = _run(
        vouchers=("v_planet_merchant", "v_planet_tycoon"),
        planet_rate=32.0,
    )

    assert _shop_type_from_polled_rate(26.0, _shop_rates_for_state(merchant.public)) == "Planet"
    assert _shop_type_from_polled_rate(40.0, _shop_rates_for_state(tycoon.public)) == "Planet"


def test_env_r2_type_rate_vouchers_compose_with_hone_and_clearance_generation_state():
    run = _run(
        vouchers=("v_hone", "v_clearance_sale", "v_tarot_merchant", "v_planet_merchant"),
        tarot_rate=9.6,
        planet_rate=9.6,
        edition_rate=2.0,
    )

    assert shop_generation_vouchers_are_exact(run.public)
    before = run.rng_snapshot()
    result = poll_base_shop_card_type(run)

    assert result.run.rng_snapshot() != before
    assert "cdt1" in result.run.rng.nodes
    assert "edisho1" not in result.run.rng.nodes
