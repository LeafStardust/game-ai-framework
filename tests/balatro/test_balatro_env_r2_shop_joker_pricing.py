import pytest

from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.shop_pricing import (
    price_base_shop_joker_descriptor,
    vanilla_card_cost,
)
from games.balatro.env.transition import HeadlessRunState, HeadlessTransitionError
from games.balatro.state import BalatroState


def _run() -> HeadlessRunState:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.shop_inflation_observed = True
    state.shop_inflation = 0
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 0
    return HeadlessRunState(public=state, seed="PRICE")


def _descriptor(base_cost: int, edition: str | None) -> OrdinaryShopJokerDescriptor:
    return OrdinaryShopJokerDescriptor(
        run=_run(),
        center_key="j_joker",
        rarity=1,
        base_cost=base_cost,
        edition=edition,
        resamples=0,
    )


@pytest.mark.parametrize(
    ("edition", "expected"),
    [
        (None, 5),
        ("Foil", 7),
        ("Holographic", 8),
        ("Polychrome", 10),
        ("Negative", 10),
    ],
)
def test_env_r2_vanilla_card_cost_applies_exact_edition_surcharge(edition, expected):
    assert vanilla_card_cost(
        5,
        edition=edition,
        inflation=0,
        discount_percent=0,
    ) == expected


def test_env_r2_vanilla_card_cost_matches_discount_rounding_and_floor():
    assert vanilla_card_cost(5, edition=None, inflation=0, discount_percent=25) == 4
    assert vanilla_card_cost(5, edition="Foil", inflation=0, discount_percent=50) == 3
    assert vanilla_card_cost(0, edition=None, inflation=0, discount_percent=100) == 1


def test_env_r2_vanilla_card_cost_includes_inflation_before_discount():
    assert vanilla_card_cost(5, edition="Holographic", inflation=2, discount_percent=25) == 7


def test_env_r2_vanilla_card_cost_rejects_inexact_inputs_and_unknown_editions():
    with pytest.raises(HeadlessTransitionError, match="base_cost must be an exact integer"):
        vanilla_card_cost(5.0, edition=None, inflation=0, discount_percent=0)
    with pytest.raises(HeadlessTransitionError, match="inflation cannot be negative"):
        vanilla_card_cost(5, edition=None, inflation=-1, discount_percent=0)
    with pytest.raises(HeadlessTransitionError, match="discount_percent"):
        vanilla_card_cost(5, edition=None, inflation=0, discount_percent=101)
    with pytest.raises(HeadlessTransitionError, match="unsupported Joker edition"):
        vanilla_card_cost(5, edition="Glitched", inflation=0, discount_percent=0)


def test_env_r2_base_shop_descriptor_pricing_uses_authoritative_zero_boundary():
    descriptor = _descriptor(8, "Polychrome")

    assert price_base_shop_joker_descriptor(descriptor) == 13


def test_env_r2_descriptor_pricing_consumes_observed_inflation_and_discount():
    descriptor = _descriptor(5, "Holographic")
    descriptor.run.public.shop_inflation = 2
    descriptor.run.public.shop_discount_percent = 25

    assert price_base_shop_joker_descriptor(descriptor) == 7


def test_env_r2_descriptor_pricing_requires_authoritative_pricing_inputs():
    descriptor = _descriptor(5, None)
    descriptor.run.public.shop_inflation_observed = False
    with pytest.raises(HeadlessTransitionError, match="inflation is not authoritative"):
        price_base_shop_joker_descriptor(descriptor)

    descriptor = _descriptor(5, None)
    descriptor.run.public.shop_discount_percent_observed = False
    with pytest.raises(HeadlessTransitionError, match="discount percent is not authoritative"):
        price_base_shop_joker_descriptor(descriptor)


def test_env_r2_descriptor_pricing_rejects_invalid_observed_values():
    descriptor = _descriptor(5, None)
    descriptor.run.public.shop_inflation = -1
    with pytest.raises(HeadlessTransitionError, match="inflation cannot be negative"):
        price_base_shop_joker_descriptor(descriptor)

    descriptor = _descriptor(5, None)
    descriptor.run.public.shop_discount_percent = 101
    with pytest.raises(HeadlessTransitionError, match="discount_percent"):
        price_base_shop_joker_descriptor(descriptor)


def test_env_r2_descriptor_pricing_does_not_infer_discount_from_voucher_names():
    descriptor = _descriptor(5, None)
    descriptor.run.public.vouchers.append("Clearance Sale")
    descriptor.run.public.shop_discount_percent = 25

    assert price_base_shop_joker_descriptor(descriptor) == 4


def test_env_r2_descriptor_pricing_keeps_active_tag_effects_fail_closed():
    descriptor = _descriptor(5, None)
    descriptor.run.tags.append("Coupon Tag")
    with pytest.raises(HeadlessTransitionError, match="Tag price effects"):
        price_base_shop_joker_descriptor(descriptor)


def test_env_r2_shop_pricing_state_survives_canonical_state_copy():
    state = _run().public
    state.shop_inflation = 3
    state.shop_discount_percent = 50

    copied = state.copy()

    assert copied.shop_inflation_observed is True
    assert copied.shop_inflation == 3
    assert copied.shop_discount_percent_observed is True
    assert copied.shop_discount_percent == 50
