import pytest

from games.balatro.env.shop_type_rate_voucher_redemption import (
    redeem_exact_shop_type_rate_voucher,
    shop_type_rate_voucher_redemption_is_exact,
)
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
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
    return HeadlessRunState(public=state, seed="TYPE-RATE-REDEEM")


def _voucher(key, price=10):
    return GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)


@pytest.mark.parametrize(
    ("key", "vouchers", "tarot_before", "planet_before", "tarot_after", "planet_after"),
    [
        ("v_tarot_merchant", (), 4.0, 4.0, 9.6, 4.0),
        ("v_tarot_tycoon", ("v_tarot_merchant",), 9.6, 4.0, 32.0, 4.0),
        ("v_planet_merchant", (), 4.0, 4.0, 4.0, 9.6),
        ("v_planet_tycoon", ("v_planet_merchant",), 4.0, 9.6, 4.0, 32.0),
    ],
)
def test_env_r2_shop_type_rate_redemption_changes_only_target_future_weight(
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
    run.public.shop_jokers = [object()]
    run.public.shop_consumables = [object()]
    before_rng = run.rng_snapshot()
    before_jokers = list(run.public.shop_jokers)
    before_consumables = list(run.public.shop_consumables)

    assert shop_type_rate_voucher_redemption_is_exact(run, 0)
    result = redeem_exact_shop_type_rate_voucher(run, 0)

    assert result.public.money == 20
    assert result.public.vouchers == [*vouchers, key]
    assert result.public.vouchers_observed is True
    assert result.public.tarot_rate == tarot_after
    assert result.public.planet_rate == planet_after
    assert result.public.shop_vouchers == []
    assert result.public.shop_jokers == before_jokers
    assert result.public.shop_consumables == before_consumables
    assert result.rng_snapshot() == before_rng
    assert shop_generation_vouchers_are_exact(result.public)

    assert run.public.money == 30
    assert run.public.vouchers == list(vouchers)
    assert run.public.tarot_rate == tarot_before
    assert run.public.planet_rate == planet_before
    assert run.public.shop_vouchers[0].center_key == key
    assert run.rng_snapshot() == before_rng


def test_env_r2_type_rate_tycoon_requires_matching_merchant():
    tarot = _run()
    tarot.public.shop_vouchers = [_voucher("v_tarot_tycoon")]
    assert not shop_type_rate_voucher_redemption_is_exact(tarot, 0)
    with pytest.raises(HeadlessTransitionError, match="requires v_tarot_merchant"):
        redeem_exact_shop_type_rate_voucher(tarot, 0)

    planet = _run()
    planet.public.shop_vouchers = [_voucher("v_planet_tycoon")]
    assert not shop_type_rate_voucher_redemption_is_exact(planet, 0)
    with pytest.raises(HeadlessTransitionError, match="requires v_planet_merchant"):
        redeem_exact_shop_type_rate_voucher(planet, 0)


def test_env_r2_type_rate_redemption_never_repairs_preexisting_rate_mismatch():
    run = _run(vouchers=("v_tarot_merchant",), tarot_rate=4.0)
    run.public.shop_vouchers = [_voucher("v_planet_merchant")]
    before_rng = run.rng_snapshot()

    assert not shop_type_rate_voucher_redemption_is_exact(run, 0)
    with pytest.raises(HeadlessTransitionError, match="type-rate state are not exact"):
        redeem_exact_shop_type_rate_voucher(run, 0)
    assert run.public.money == 30
    assert run.public.vouchers == ["v_tarot_merchant"]
    assert run.rng_snapshot() == before_rng


def test_env_r2_type_rate_redemption_rejects_unaffordable_legacy_and_other_voucher():
    unaffordable = _run(money=9)
    unaffordable.public.shop_vouchers = [_voucher("v_tarot_merchant")]
    assert not shop_type_rate_voucher_redemption_is_exact(unaffordable, 0)

    legacy = _run()
    legacy.public.shop_vouchers = [object()]
    assert not shop_type_rate_voucher_redemption_is_exact(legacy, 0)

    other = _run()
    other.public.shop_vouchers = [_voucher("v_hone")]
    assert not shop_type_rate_voucher_redemption_is_exact(other, 0)
    with pytest.raises(HeadlessTransitionError, match="exact shop type-rate family"):
        redeem_exact_shop_type_rate_voucher(other, 0)
