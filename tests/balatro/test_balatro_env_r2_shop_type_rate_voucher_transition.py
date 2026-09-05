import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.env.voucher_capabilities import shop_generation_vouchers_are_exact
from games.balatro.state import BalatroState


def _run(*, vouchers=(), tarot_rate=4.0, planet_rate=4.0, money=30):
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = money
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.tarot_rate = tarot_rate
    state.planet_rate = planet_rate
    state.joker_generation_edition_rate = 1.0
    return HeadlessRunState(public=state, seed="TYPE-RATE-ENGINE")


def _voucher(key, price=10):
    return GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)


def _buy():
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": 0})


@pytest.mark.parametrize(
    ("key", "vouchers", "tarot_before", "planet_before", "tarot_after", "planet_after"),
    [
        ("v_tarot_merchant", (), 4.0, 4.0, 9.6, 4.0),
        ("v_tarot_tycoon", ("v_tarot_merchant",), 9.6, 4.0, 32.0, 4.0),
        ("v_planet_merchant", (), 4.0, 4.0, 4.0, 9.6),
        ("v_planet_tycoon", ("v_planet_merchant",), 4.0, 9.6, 4.0, 32.0),
    ],
)
def test_env_r2_shop_engine_exposes_and_executes_type_rate_vouchers(
    key,
    vouchers,
    tarot_before,
    planet_before,
    tarot_after,
    planet_after,
):
    run = _run(
        vouchers=vouchers,
        tarot_rate=tarot_before,
        planet_rate=planet_before,
    )
    run.public.shop_vouchers = [_voucher(key)]
    before_rng = run.rng_snapshot()
    engine = ShopTransitionEngine()

    assert _buy() in engine.legal_actions(run)
    result = engine.step(run, _buy())

    assert result.public.money == 20
    assert result.public.vouchers == [*vouchers, key]
    assert result.public.tarot_rate == tarot_after
    assert result.public.planet_rate == planet_after
    assert result.public.shop_vouchers == []
    assert result.rng_snapshot() == before_rng
    assert shop_generation_vouchers_are_exact(result.public)


def test_env_r2_shop_engine_hides_tycoon_without_merchant_and_rate_mismatches():
    engine = ShopTransitionEngine()

    no_base = _run()
    no_base.public.shop_vouchers = [_voucher("v_tarot_tycoon")]
    assert _buy() not in engine.legal_actions(no_base)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(no_base, _buy())

    stale = _run(vouchers=("v_tarot_merchant",), tarot_rate=4.0)
    stale.public.shop_vouchers = [_voucher("v_planet_merchant")]
    assert _buy() not in engine.legal_actions(stale)


def test_env_r2_shop_engine_hides_type_rate_voucher_without_exact_generated_metadata():
    run = _run()
    run.public.shop_vouchers = [object()]

    assert _buy() not in ShopTransitionEngine().legal_actions(run)
