import pytest

from games.balatro.env.reroll_voucher_redemption import (
    redeem_exact_reroll_voucher,
    reroll_voucher_redemption_is_exact,
)
from games.balatro.env.shop_main_generation import generate_base_main_shop
from games.balatro.env.shop_reroll import reroll_base_main_shop
from games.balatro.env.shop_voucher_items import GeneratedShopVoucherItem
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.env.voucher_capabilities import (
    expected_base_reroll_cost_for_vouchers,
    shop_generation_vouchers_are_exact,
)
from games.balatro.state import BalatroState


def _voucher(key: str, price: int = 10) -> GeneratedShopVoucherItem:
    return GeneratedShopVoucherItem(center_key=key, base_cost=10, price=price)


def _run(
    *,
    vouchers=(),
    base_reroll_cost=5,
    reroll_cost=5,
    money=30,
) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = money
    state.vouchers_observed = True
    state.vouchers = list(vouchers)
    state.joker_generation_edition_rate = 1.0
    state.tarot_rate = 4.0
    state.planet_rate = 4.0
    return HeadlessRunState(
        public=state,
        seed="REROLL-VOUCHER",
        base_reroll_cost=base_reroll_cost,
        reroll_cost=reroll_cost,
    )


def _joker_record(rarity, key, cost):
    return {
        "rarity": rarity,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
    }


def _consumable_record(card_type, key, cost=3):
    return {
        "type": card_type,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }


def _generated_run_with_surplus(seed="REROLL-SURPLUS-SHOP") -> HeadlessRunState:
    run = _run(vouchers=("v_reroll_surplus",), base_reroll_cost=3, reroll_cost=3)
    state = run.public
    state.ante = 1
    state.money = 20
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    state.joker_generation_pool_observed = True
    state.joker_generation_pools = {
        "1": [_joker_record(1, "j_joker", 2)],
        "2": [_joker_record(2, "j_stencil", 8)],
        "3": [_joker_record(3, "j_dna", 8)],
        "4": [_joker_record(4, "j_caino", 20)],
    }
    state.consumable_generation_pool_observed = True
    state.consumable_generation_pools = {
        "Tarot": [_consumable_record("Tarot", "c_strength")],
        "Planet": [_consumable_record("Planet", "c_pluto")],
    }
    run.seed = seed
    # Reconstruct so RNG ownership uses the requested replay seed.
    return generate_base_main_shop(
        HeadlessRunState(
            public=state,
            seed=seed,
            base_reroll_cost=3,
            reroll_cost=3,
        )
    ).run


def test_env_r2_reroll_surplus_reduces_persistent_and_current_cost_without_rng():
    run = _run(base_reroll_cost=5, reroll_cost=7)
    run.public.shop_vouchers = [_voucher("v_reroll_surplus")]
    run.public.shop_jokers = ["JOKER-SENTINEL"]
    run.public.shop_consumables = ["CONSUMABLE-SENTINEL"]
    before_rng = run.rng_snapshot()

    assert reroll_voucher_redemption_is_exact(run, 0)
    result = redeem_exact_reroll_voucher(run, 0)

    assert result.public.money == 20
    assert result.public.vouchers == ["v_reroll_surplus"]
    assert result.public.shop_vouchers == []
    assert result.public.shop_jokers == ["JOKER-SENTINEL"]
    assert result.public.shop_consumables == ["CONSUMABLE-SENTINEL"]
    assert result.base_reroll_cost == 3
    assert result.reroll_cost == 5
    assert result.rng_snapshot() == before_rng
    assert expected_base_reroll_cost_for_vouchers(result.public) == 3
    assert shop_generation_vouchers_are_exact(result.public)

    assert run.public.money == 30
    assert run.public.vouchers == []
    assert run.base_reroll_cost == 5
    assert run.reroll_cost == 7
    assert run.rng_snapshot() == before_rng


def test_env_r2_reroll_glut_requires_surplus_then_reduces_both_cost_owners():
    missing = _run()
    missing.public.shop_vouchers = [_voucher("v_reroll_glut")]
    assert not reroll_voucher_redemption_is_exact(missing, 0)
    with pytest.raises(HeadlessTransitionError, match="requires v_reroll_surplus"):
        redeem_exact_reroll_voucher(missing, 0)

    run = _run(
        vouchers=("v_reroll_surplus",),
        base_reroll_cost=3,
        reroll_cost=4,
    )
    run.public.shop_vouchers = [_voucher("v_reroll_glut")]

    result = redeem_exact_reroll_voucher(run, 0)

    assert result.public.vouchers == ["v_reroll_surplus", "v_reroll_glut"]
    assert result.base_reroll_cost == 1
    assert result.reroll_cost == 2
    assert expected_base_reroll_cost_for_vouchers(result.public) == 1
    assert shop_generation_vouchers_are_exact(result.public)


def test_env_r2_reroll_voucher_fails_closed_on_private_cost_mismatch_and_temp_state():
    stale_base = _run(
        vouchers=("v_reroll_surplus",),
        base_reroll_cost=5,
        reroll_cost=5,
    )
    stale_base.public.shop_vouchers = [_voucher("v_reroll_glut")]
    assert not reroll_voucher_redemption_is_exact(stale_base, 0)
    with pytest.raises(HeadlessTransitionError, match="persistent reroll cost"):
        redeem_exact_reroll_voucher(stale_base, 0)

    below_base = _run(base_reroll_cost=5, reroll_cost=4)
    below_base.public.shop_vouchers = [_voucher("v_reroll_surplus")]
    assert not reroll_voucher_redemption_is_exact(below_base, 0)
    with pytest.raises(HeadlessTransitionError, match="temporary/free modifier"):
        redeem_exact_reroll_voucher(below_base, 0)


def test_env_r2_reroll_voucher_rejects_unaffordable_wrong_phase_and_legacy_metadata():
    unaffordable = _run(money=9)
    unaffordable.public.shop_vouchers = [_voucher("v_reroll_surplus")]
    assert not reroll_voucher_redemption_is_exact(unaffordable, 0)

    wrong_phase = _run()
    wrong_phase.public.phase = "BLIND_SELECT"
    wrong_phase.public.shop_vouchers = [_voucher("v_reroll_surplus")]
    assert not reroll_voucher_redemption_is_exact(wrong_phase, 0)

    legacy = _run()
    legacy.public.shop_vouchers = [object()]
    assert not reroll_voucher_redemption_is_exact(legacy, 0)


def test_env_r2_shop_transition_exposes_and_executes_exact_reroll_voucher():
    run = _run()
    run.public.shop_vouchers = [_voucher("v_reroll_surplus")]
    engine = ShopTransitionEngine()

    actions = engine.legal_actions(run)
    buys = [action for action in actions if action.alias == "BUY_VOUCHER"]
    assert len(buys) == 1
    assert buys[0].payload() == {"slot": 0}

    result = engine.step(run, buys[0])
    direct = redeem_exact_reroll_voucher(run, 0)

    assert result.public.money == direct.public.money == 20
    assert result.public.vouchers == direct.public.vouchers == ["v_reroll_surplus"]
    assert result.base_reroll_cost == direct.base_reroll_cost == 3
    assert result.reroll_cost == direct.reroll_cost == 3
    assert result.rng_snapshot() == direct.rng_snapshot() == run.rng_snapshot()


def test_env_r2_paid_reroll_uses_voucher_reduced_current_cost_and_preserves_base():
    run = _generated_run_with_surplus()

    first = reroll_base_main_shop(run)
    second = reroll_base_main_shop(first.run)

    assert first.previous_cost == 3
    assert first.next_cost == 4
    assert first.run.base_reroll_cost == 3
    assert first.run.public.money == 17
    assert second.previous_cost == 4
    assert second.next_cost == 5
    assert second.run.base_reroll_cost == 3
    assert second.run.public.money == 13


def test_env_r2_headless_reroll_cost_fields_reject_bool_and_negative_values():
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"

    with pytest.raises(HeadlessTransitionError, match="base_reroll_cost"):
        HeadlessRunState(public=state, seed="BAD-BASE", base_reroll_cost=True)
    with pytest.raises(HeadlessTransitionError, match="base_reroll_cost"):
        HeadlessRunState(public=state, seed="BAD-BASE", base_reroll_cost=-1)
    with pytest.raises(HeadlessTransitionError, match="reroll_cost"):
        HeadlessRunState(public=state, seed="BAD-CURRENT", reroll_cost=True)
    with pytest.raises(HeadlessTransitionError, match="reroll_cost"):
        HeadlessRunState(public=state, seed="BAD-CURRENT", reroll_cost=-1)
