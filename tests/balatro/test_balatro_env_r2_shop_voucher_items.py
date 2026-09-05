import pytest

from games.balatro.env.shop_voucher_items import (
    GeneratedShopVoucherItem,
    describe_observed_normal_shop_voucher,
    generate_observed_normal_shop_voucher,
    insert_generated_shop_voucher_item,
    materialize_normal_shop_voucher_descriptor,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _voucher_record(
    key: str = "v_blank",
    *,
    cost: int = 10,
    eligible: bool = True,
) -> dict[str, object]:
    return {
        "key": key,
        "cost": cost,
        "unlocked": True,
        "requires": [],
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "eligible": eligible,
    }


def _run(*, records=None) -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.shop_inflation_observed = True
    state.shop_inflation = 2
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 25
    state.voucher_generation_pool_observed = True
    state.voucher_generation_pool = list(records or [_voucher_record()])
    return HeadlessRunState(public=state, seed="VOUCHER-SLOT")


def test_env_r2_normal_voucher_descriptor_uses_selected_observed_center_cost():
    run = _run()
    before_rng = run.rng_snapshot()

    descriptor = describe_observed_normal_shop_voucher(run)

    assert descriptor.center_key == "v_blank"
    assert descriptor.base_cost == 10
    assert descriptor.resamples == 0
    assert descriptor.run is not run
    assert run.rng_snapshot() == before_rng
    assert descriptor.run.rng_snapshot() != before_rng


def test_env_r2_normal_voucher_materialization_uses_exact_card_set_cost_pricing():
    descriptor = describe_observed_normal_shop_voucher(_run())

    priced_run, item = materialize_normal_shop_voucher_descriptor(descriptor)

    # floor((10 base + 2 inflation + 0.5) * 0.75) = 9
    assert item == GeneratedShopVoucherItem(
        center_key="v_blank",
        base_cost=10,
        price=9,
    )
    assert item.kind == "VOUCHER"
    assert item.center == "v_blank"
    assert priced_run is not descriptor.run


def test_env_r2_normal_voucher_publication_uses_separate_voucher_slot():
    run = _run()
    # The two-card main shop may already be occupied; Voucher publication is a
    # separate vanilla card area and must not consume or alter either main slot.
    run.public.shop_jokers = ["main-joker"]
    run.public.shop_consumables = ["main-consumable"]
    before_jokers = list(run.public.shop_jokers)
    before_consumables = list(run.public.shop_consumables)

    result, item = generate_observed_normal_shop_voucher(run)

    assert result.public.shop_vouchers == [item]
    assert result.public.shop_jokers == before_jokers
    assert result.public.shop_consumables == before_consumables
    assert run.public.shop_vouchers == []


def test_env_r2_normal_voucher_generation_isolates_input_state_and_rng():
    run = _run()
    before_rng = run.rng_snapshot()
    before_pool = [dict(record) for record in run.public.voucher_generation_pool]

    result, item = generate_observed_normal_shop_voucher(run)

    assert item.center_key == "v_blank"
    assert result is not run
    assert run.public.shop_vouchers == []
    assert run.public.voucher_generation_pool == before_pool
    assert run.rng_snapshot() == before_rng
    assert result.rng_snapshot() != before_rng


def test_env_r2_normal_voucher_generation_rejects_unobserved_catalogue_before_rng():
    run = _run()
    run.public.voucher_generation_pool_observed = False
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="unobserved"):
        generate_observed_normal_shop_voucher(run)

    assert run.rng_snapshot() == before_rng
    assert run.public.shop_vouchers == []


def test_env_r2_normal_voucher_generation_rejects_malformed_cost_before_rng():
    run = _run(records=[_voucher_record(cost=10)])
    run.public.voucher_generation_pool[0]["cost"] = True
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="cost"):
        generate_observed_normal_shop_voucher(run)

    assert run.rng_snapshot() == before_rng
    assert run.public.shop_vouchers == []


def test_env_r2_normal_voucher_materialization_requires_authoritative_pricing_state():
    run = _run()
    descriptor = describe_observed_normal_shop_voucher(run)
    descriptor.run.public.shop_inflation_observed = False

    with pytest.raises(HeadlessTransitionError, match="inflation"):
        materialize_normal_shop_voucher_descriptor(descriptor)

    run = _run()
    descriptor = describe_observed_normal_shop_voucher(run)
    descriptor.run.public.shop_discount_percent_observed = False
    with pytest.raises(HeadlessTransitionError, match="discount"):
        materialize_normal_shop_voucher_descriptor(descriptor)


def test_env_r2_normal_voucher_generation_rejects_active_tag_effects_without_mutating_input():
    run = _run()
    run.tags = ["Voucher Tag"]
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="Tag"):
        generate_observed_normal_shop_voucher(run)

    assert run.rng_snapshot() == before_rng
    assert run.public.shop_vouchers == []


def test_env_r2_normal_voucher_slot_rejects_duplicate_publication_before_rng():
    run = _run()
    existing = GeneratedShopVoucherItem(center_key="v_blank", base_cost=10, price=10)
    run.public.shop_vouchers = [existing]
    before_rng = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match="already occupied"):
        generate_observed_normal_shop_voucher(run)

    assert run.rng_snapshot() == before_rng
    assert run.public.shop_vouchers == [existing]


def test_env_r2_direct_voucher_insertion_rejects_duplicate_slot():
    run = _run()
    item = GeneratedShopVoucherItem(center_key="v_blank", base_cost=10, price=9)
    first = insert_generated_shop_voucher_item(run, item)

    with pytest.raises(HeadlessTransitionError, match="already occupied"):
        insert_generated_shop_voucher_item(first, item)
