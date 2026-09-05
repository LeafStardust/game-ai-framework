from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    materialize_shop_joker_descriptor,
)
from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.transition import HeadlessRunState, ShopTransitionEngine
from games.balatro.state import BalatroState


def _descriptor(*, edition: str | None = None) -> OrdinaryShopJokerDescriptor:
    state = BalatroState()
    state.deck_name = "RED"
    state.stake_name = "WHITE"
    state.phase = "SHOP"
    state.shop_active = True
    state.money = 20
    state.shop_inflation_observed = True
    state.shop_inflation = 1
    state.shop_discount_percent_observed = True
    state.shop_discount_percent = 25
    run = HeadlessRunState(public=state, seed="SHOP-ITEM")
    return OrdinaryShopJokerDescriptor(
        run=run,
        center_key="j_joker",
        rarity=1,
        base_cost=5,
        edition=edition,
        resamples=0,
    )


def test_env_r2_generated_shop_joker_item_carries_exact_public_metadata():
    run, item = materialize_shop_joker_descriptor(_descriptor(edition="Foil"))

    assert isinstance(item, GeneratedShopJokerItem)
    assert item.kind == "JOKER"
    assert item.center == "j_joker"
    assert item.center_key == "j_joker"
    assert item.rarity == 1
    assert item.base_cost == 5
    assert item.edition == "Foil"
    assert item.price == 6
    assert run.public.phase == "SHOP"


def test_env_r2_materialization_isolates_descriptor_run_and_does_not_insert_inventory():
    descriptor = _descriptor()

    run, item = materialize_shop_joker_descriptor(descriptor)

    assert run is not descriptor.run
    assert run.public is not descriptor.run.public
    assert descriptor.run.public.shop_jokers == []
    assert run.public.shop_jokers == []
    assert item not in descriptor.run.public.shop_jokers


def test_env_r2_generated_metadata_does_not_make_purchase_semantics_exact():
    run, item = materialize_shop_joker_descriptor(_descriptor())
    run.public.shop_jokers.append(item)

    actions = ShopTransitionEngine().legal_actions(run)

    assert all(action.alias != "BUY_JOKER" for action in actions)
    assert any(action.alias == "END_SHOP" for action in actions)
