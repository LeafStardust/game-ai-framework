import pytest

from games.balatro.env.shop_consumable_items import (
    OrdinaryShopConsumableDescriptor,
    describe_base_shop_consumable_from_records,
    materialize_base_shop_consumable_descriptor,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run(seed: str = "CONSUMABLE-ITEM") -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.ante = 2
    state.shop_inflation_observed = True
    state.shop_inflation = 1
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    return HeadlessRunState(public=state, seed=seed)


def _record(card_type: str, key: str, cost: int = 3, **extra):
    value = {
        "type": card_type,
        "key": key,
        "cost": cost,
        "unlocked": True,
        "no_pool_flag": None,
        "yes_pool_flag": None,
        "softlock": False,
        "hand_type": None,
    }
    value.update(extra)
    return value


@pytest.mark.parametrize(
    ("card_type", "records", "expected_price"),
    [
        ("Tarot", [_record("Tarot", "c_strength", 3)], 4),
        ("Planet", [_record("Planet", "c_pluto", 3)], 8),
    ],
)
def test_env_r2_consumable_descriptor_carries_observed_cost_and_prices_exactly(
    card_type, records, expected_price
):
    run = _run()
    before = run.rng_snapshot()

    descriptor = describe_base_shop_consumable_from_records(run, card_type, records)
    result, item = materialize_base_shop_consumable_descriptor(descriptor)

    assert descriptor.center_key == records[0]["key"]
    assert descriptor.base_cost == 3
    assert item.card_type == card_type
    assert item.center_key == records[0]["key"]
    assert item.base_cost == 3
    assert item.price == expected_price
    assert item.kind == "CONSUMABLE"
    assert run.rng_snapshot() == before
    assert descriptor.run.rng_snapshot() != before
    assert result is not descriptor.run
    assert result.public.shop_consumables == []


@pytest.mark.parametrize(
    ("card_type", "fallback", "expected_price"),
    [("Tarot", "c_strength", 4), ("Planet", "c_pluto", 8)],
)
def test_env_r2_consumable_empty_pool_fallback_has_pinned_cost_three(
    card_type, fallback, expected_price
):
    descriptor = describe_base_shop_consumable_from_records(_run(), card_type, [])
    _, item = materialize_base_shop_consumable_descriptor(descriptor)

    assert descriptor.center_key == fallback
    assert descriptor.base_cost == 3
    assert item.price == expected_price


def test_env_r2_consumable_materialization_applies_vanilla_discount_formula():
    run = _run()
    run.public.shop_inflation = 2
    run.public.shop_discount_percent = 25
    run.public.vouchers_observed = True
    run.public.vouchers = ["v_clearance_sale"]
    descriptor = describe_base_shop_consumable_from_records(
        run,
        "Tarot",
        [_record("Tarot", "c_strength", 3)],
    )

    _, item = materialize_base_shop_consumable_descriptor(descriptor)

    assert item.price == 4  # floor((3 + 2 + .5) * .75) == 4


@pytest.mark.parametrize(
    "records,match",
    [
        (["bad"], "mapping"),
        ([_record("Planet", "c_pluto")], "type mismatch"),
        ([_record("Tarot", "")], "center key"),
        ([_record("Tarot", "c_strength", True)], "center cost"),
        ([_record("Tarot", "c_strength"), _record("Tarot", "c_strength")], "duplicate"),
        ([_record("Tarot", "c_strength", unlocked="yes")], "unlocked"),
        ([_record("Tarot", "c_strength", softlock=True, hand_type="High Card")], "Tarot"),
    ],
)
def test_env_r2_consumable_record_validation_fails_before_rng(records, match):
    run = _run()
    before = run.rng_snapshot()

    with pytest.raises(HeadlessTransitionError, match=match):
        describe_base_shop_consumable_from_records(run, "Tarot", records)

    assert run.rng_snapshot() == before


def test_env_r2_softlocked_planet_requires_hand_type():
    with pytest.raises(HeadlessTransitionError, match="requires hand_type"):
        describe_base_shop_consumable_from_records(
            _run(),
            "Planet",
            [_record("Planet", "c_planet_x", softlock=True)],
        )


def test_env_r2_consumable_materialization_requires_authoritative_pricing_state():
    run = _run()
    descriptor = OrdinaryShopConsumableDescriptor(
        run=run,
        card_type="Tarot",
        center_key="c_strength",
        base_cost=3,
        resamples=0,
    )

    run.public.shop_inflation_observed = False
    with pytest.raises(HeadlessTransitionError, match="inflation"):
        materialize_base_shop_consumable_descriptor(descriptor)

    run = _run()
    descriptor = OrdinaryShopConsumableDescriptor(
        run=run,
        card_type="Tarot",
        center_key="c_strength",
        base_cost=3,
        resamples=0,
    )
    run.public.shop_discount_percent_observed = False
    with pytest.raises(HeadlessTransitionError, match="discount"):
        materialize_base_shop_consumable_descriptor(descriptor)


def test_env_r2_consumable_materialization_rejects_unowned_voucher_or_tag_effects():
    run = _run()
    run.public.vouchers_observed = True
    run.public.vouchers = ["v_tarot_merchant"]
    descriptor = OrdinaryShopConsumableDescriptor(
        run=run,
        card_type="Tarot",
        center_key="c_strength",
        base_cost=3,
        resamples=0,
    )
    with pytest.raises(HeadlessTransitionError, match="Voucher"):
        materialize_base_shop_consumable_descriptor(descriptor)

    run = _run()
    run.tags = ["tag_coupon"]
    descriptor = OrdinaryShopConsumableDescriptor(
        run=run,
        card_type="Tarot",
        center_key="c_strength",
        base_cost=3,
        resamples=0,
    )
    with pytest.raises(HeadlessTransitionError, match="Tag"):
        materialize_base_shop_consumable_descriptor(descriptor)


def test_env_r2_consumable_descriptor_rejects_invalid_type_before_rng():
    run = _run()
    before = run.rng_snapshot()
    with pytest.raises(HeadlessTransitionError, match="Tarot or Planet"):
        describe_base_shop_consumable_from_records(run, "Spectral", [])
    assert run.rng_snapshot() == before
