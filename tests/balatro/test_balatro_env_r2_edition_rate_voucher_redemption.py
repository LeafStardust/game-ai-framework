import pytest

from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.state import BalatroState


def _run(center_key: str, *, owned=(), rate=1.0, observed=True) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.vouchers = list(owned)
    state.vouchers_observed = observed
    state.joker_generation_edition_rate = rate
    state.shop_vouchers = [
        GeneratedShopVoucherItem(
            center_key=center_key,
            base_cost=10,
            price=10,
        )
    ]
    return HeadlessRunState(public=state, seed="EDITION-VOUCHER-REDEEM")


def _buy() -> EnvAction:
    return EnvAction.from_alias("BUY_VOUCHER", {"slot": 0})


def test_env_r2_hone_redeems_to_exact_edition_rate_two():
    engine = ShopTransitionEngine()
    run = _run("v_hone")
    before_rng = run.rng_snapshot()

    assert _buy() in engine.legal_actions(run)
    result = engine.step(run, _buy())

    assert result.public.money == 10
    assert result.public.shop_vouchers == []
    assert result.public.vouchers == ["v_hone"]
    assert result.public.joker_generation_edition_rate == 2.0
    assert result.rng_snapshot() == before_rng

    assert run.public.money == 20
    assert run.public.vouchers == []
    assert run.public.joker_generation_edition_rate == 1.0
    assert len(run.public.shop_vouchers) == 1


def test_env_r2_glow_up_requires_hone_and_upgrades_rate_to_four():
    engine = ShopTransitionEngine()

    missing_hone = _run("v_glow_up")
    before_rng = missing_hone.rng_snapshot()
    assert _buy() not in engine.legal_actions(missing_hone)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(missing_hone, _buy())
    assert missing_hone.rng_snapshot() == before_rng
    assert missing_hone.public.money == 20
    assert missing_hone.public.vouchers == []

    run = _run("v_glow_up", owned=("v_hone",), rate=2.0)
    before_rng = run.rng_snapshot()
    assert _buy() in engine.legal_actions(run)

    result = engine.step(run, _buy())

    assert result.public.money == 10
    assert result.public.vouchers == ["v_hone", "v_glow_up"]
    assert result.public.joker_generation_edition_rate == 4.0
    assert result.rng_snapshot() == before_rng


def test_env_r2_edition_rate_voucher_duplicates_remain_illegal():
    engine = ShopTransitionEngine()
    run = _run("v_hone", owned=("v_hone",), rate=2.0)

    assert _buy() not in engine.legal_actions(run)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(run, _buy())


def test_env_r2_hone_redemption_does_not_require_round_allowance_observation():
    engine = ShopTransitionEngine()
    run = _run("v_hone")
    run.public.round_reset_hands_observed = False
    run.public.round_reset_discards_observed = False

    assert _buy() in engine.legal_actions(run)
    result = engine.step(run, _buy())

    assert result.public.joker_generation_edition_rate == 2.0
