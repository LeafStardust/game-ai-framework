import pytest

from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    insert_generated_shop_joker_item,
    materialize_generated_shop_joker_for_acquisition,
    materialize_shop_joker_descriptor,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.hand import PokerHand
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _descriptor(
    *,
    edition: str | None = None,
    base_cost: int = 5,
    discovered: bool | None = None,
) -> OrdinaryShopJokerDescriptor:
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
    run = HeadlessRunState(
        public=state,
        seed="SHOP-ITEM",
        generation_discovery=(
            None if discovered is None else {"j_joker": discovered}
        ),
    )
    return OrdinaryShopJokerDescriptor(
        run=run,
        center_key="j_joker",
        rarity=1,
        base_cost=base_cost,
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


def test_env_r2_generated_item_insertion_isolated_and_preserves_exact_metadata():
    descriptor = _descriptor(edition="Holographic")
    run, item = materialize_shop_joker_descriptor(descriptor)

    inserted = insert_generated_shop_joker_item(run, item)

    assert inserted is not run
    assert run.public.shop_jokers == []
    assert inserted.public.shop_jokers == [item]
    assert inserted.public.shop_jokers[0].center_key == "j_joker"
    assert inserted.public.shop_jokers[0].edition == "Holographic"
    assert inserted.public.shop_jokers[0].price == 7


def test_env_r2_generated_item_insertion_enforces_shared_two_card_main_shop_capacity():
    run, item = materialize_shop_joker_descriptor(_descriptor())
    first = insert_generated_shop_joker_item(run, item)
    first.public.shop_consumables.append(object())

    with pytest.raises(HeadlessTransitionError, match="already full"):
        insert_generated_shop_joker_item(first, item)


def test_env_r2_only_exact_base_joker_materializes_for_acquisition():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(base_cost=2, discovered=True)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    actions = ShopTransitionEngine().legal_actions(inserted)

    assert action in actions
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.public.money == 20
    assert inserted.public.jokers == []
    assert inserted.public.shop_jokers == [item]
    assert next_run.public.money == 18
    assert next_run.public.shop_jokers == []
    assert len(next_run.public.jokers) == 1
    joker = next_run.public.jokers[0]
    assert type(joker) is FlatMultJoker
    assert joker.mult == 4
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.edition,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
        joker.eternal,
    ) == ("j_joker", "Joker", 1, None, 2, 2, 1, True, False)

    score = BalatroScorer().score(PokerHand.HIGH_CARD, state=next_run.public)
    assert (score.chips, score.mult, score.total) == (5, 5, 25)

    sell = EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    assert sell in ShopTransitionEngine().legal_actions(next_run)
    sold_run = ShopTransitionEngine().step(next_run, sell)
    assert sold_run.public.jokers == []
    assert sold_run.public.money == 19


@pytest.mark.parametrize(
    "item",
    (
        GeneratedShopJokerItem("j_greedy_joker", 1, 5, None, 5, True),
        GeneratedShopJokerItem("j_joker", 2, 2, None, 2, True),
        GeneratedShopJokerItem("j_joker", 1, 3, None, 3, True),
        GeneratedShopJokerItem("j_joker", 1, 2, "Foil", 4, True),
        GeneratedShopJokerItem("j_joker", 1, 2, None, 2, False),
        GeneratedShopJokerItem("j_joker", 1, 2, None, 2, None),
    ),
)
def test_env_r2_unsupported_generated_joker_materialization_fails_closed(item):
    run, _ = materialize_shop_joker_descriptor(
        _descriptor(base_cost=2, discovered=True)
    )
    inserted = insert_generated_shop_joker_item(run, item)

    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in (
        ShopTransitionEngine().legal_actions(inserted)
    )
