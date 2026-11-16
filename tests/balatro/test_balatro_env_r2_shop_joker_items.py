import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.shop_items import (
    GeneratedShopJokerItem,
    insert_generated_shop_joker_item,
    materialize_generated_shop_joker_for_acquisition,
    materialize_shop_joker_descriptor,
)
from games.balatro.env.actions import EnvAction
from games.balatro.env.shop_joker_generation import OrdinaryShopJokerDescriptor
from games.balatro.env.tag_selection import TagProfileState
from games.balatro.env.transition import (
    HeadlessRunState,
    HeadlessTransitionError,
    ShopTransitionEngine,
)
from games.balatro.hand import PokerHand
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _descriptor(
    *,
    edition: str | None = None,
    base_cost: int = 5,
    discovered: bool | None = None,
    center_key: str = "j_joker",
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
            None if discovered is None else {center_key: discovered}
        ),
        tag_profile_state=(
            None
            if discovered is None
            else TagProfileState(
                frozenset({center_key} if discovered else set())
            )
        ),
    )
    return OrdinaryShopJokerDescriptor(
        run=run,
        center_key=center_key,
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


def test_env_r2_exact_droll_materialization_updates_discovery_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_droll",
            base_cost=4,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_droll": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_droll": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_droll"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is DrollJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_droll", "Droll Joker", 1, 4, 4, 2, True)

    flush = [
        BalatroCard(rank, "Hearts")
        for rank in ("2", "4", "6", "8", "10")
    ]
    score = BalatroScorer().score(
        PokerHand.FLUSH,
        state=next_run.public,
        cards=flush,
    )
    assert (score.chips, score.mult, score.total) == (35, 14, 490)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_odd_todd_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_odd_todd",
            base_cost=4,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_odd_todd": False}
    assert next_run.generation_discovery == {"j_odd_todd": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_odd_todd"}
    )
    joker = next_run.public.jokers[0]
    assert type(joker) is OddToddJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_odd_todd", "Odd Todd", 1, 4, 4, 2, True)

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("3", "Hearts")],
        include_card_chips=True,
    )
    assert (score.chips, score.mult, score.total) == (39, 1, 39)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_even_steven_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_even_steven",
            base_cost=4,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_even_steven": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_even_steven": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_even_steven"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is EvenStevenJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_even_steven", "Even Steven", 1, 4, 4, 2, True)

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts")],
        include_card_chips=True,
    )
    assert (score.chips, score.mult, score.total) == (7, 5, 35)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


@pytest.mark.parametrize(
    "item",
    (
        GeneratedShopJokerItem("j_greedy_joker", 1, 5, None, 5, True),
        GeneratedShopJokerItem("j_joker", 2, 2, None, 2, True),
        GeneratedShopJokerItem("j_joker", 1, 3, None, 3, True),
        GeneratedShopJokerItem("j_joker", 1, 2, "Foil", 4, True),
        GeneratedShopJokerItem("j_joker", 1, 2, None, 2, None),
        GeneratedShopJokerItem("j_droll", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_droll", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_odd_todd", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_odd_todd", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_even_steven", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_even_steven", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_even_steven", 1, 4, "Foil", 6, False),
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
