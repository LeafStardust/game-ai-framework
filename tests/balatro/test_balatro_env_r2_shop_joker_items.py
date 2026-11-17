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
from games.balatro.jokers.abstract_joker import AbstractJoker
from games.balatro.jokers.banner import BannerJoker
from games.balatro.jokers.devious_joker import DeviousJoker
from games.balatro.jokers.blue_joker import BlueJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.wily_joker import WilyJoker
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


def test_env_r2_exact_devious_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_devious",
            base_cost=4,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_devious": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_devious": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_devious"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is DeviousJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_devious", "Devious Joker", 1, 4, 4, 2, True)

    straight = [
        BalatroCard(rank, "Hearts")
        for rank in ("2", "3", "4", "5", "6")
    ]
    score = BalatroScorer().score(
        PokerHand.STRAIGHT,
        state=next_run.public,
        cards=straight,
    )
    assert (score.chips, score.mult, score.total) == (130, 4, 520)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_gluttonous_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_gluttenous_joker",
            base_cost=5,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_gluttenous_joker": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_gluttenous_joker": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_gluttenous_joker"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is GluttonousJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_gluttenous_joker", "Gluttonous Joker", 1, 5, 4, 2, True)

    clubs = [
        BalatroCard(rank, "Clubs")
        for rank in ("2", "4", "6", "8", "10")
    ]
    score = BalatroScorer().score(
        PokerHand.FLUSH,
        state=next_run.public,
        cards=clubs,
    )
    assert (score.chips, score.mult, score.total) == (35, 19, 665)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_scholar_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_scholar",
            base_cost=4,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_scholar": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_scholar": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_scholar"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is ScholarJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_scholar", "Scholar", 1, 4, 4, 2, True)

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("A", "Hearts")],
        include_card_chips=True,
    )
    assert (score.chips, score.mult, score.total) == (36, 5, 180)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_blue_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_blue_joker",
            base_cost=5,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_blue_joker": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_blue_joker": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_blue_joker"}
    )
    assert next_run.public.money == 16
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is BlueJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_blue_joker", "Blue Joker", 1, 5, 4, 2, True)

    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("A", "Hearts")],
        include_card_chips=True,
    )
    assert (score.chips, score.mult, score.total) == (120, 1, 120)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_jolly_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_jolly", base_cost=3, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_jolly": False}
    assert inserted.tag_profile_state.discovered_center_keys == frozenset()
    assert next_run.generation_discovery == {"j_jolly": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_jolly"})
    assert next_run.public.money == 17
    assert next_run.public.shop_jokers == []
    joker = next_run.public.jokers[0]
    assert type(joker) is JollyJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_jolly", "Jolly Joker", 1, 3, 3, 1, True)

    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts"), BalatroCard("2", "Clubs")],
    )
    assert (score.chips, score.mult, score.total) == (10, 10, 100)

    sold_run = ShopTransitionEngine().step(
        next_run,
        EnvAction.from_alias("SELL_JOKER", {"joker_index": 0}),
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_sly_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_sly", base_cost=3, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_sly": False}
    assert next_run.generation_discovery == {"j_sly": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_sly"})
    assert next_run.public.money == 17
    joker = next_run.public.jokers[0]
    assert type(joker) is SlyJoker
    assert (joker.center, joker.label, joker.rarity, joker.base_cost, joker.cost,
            joker.sell_cost, joker.discovered) == (
        "j_sly", "Sly Joker", 1, 3, 3, 1, True
    )
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts"), BalatroCard("2", "Clubs")],
    )
    assert (score.chips, score.mult, score.total) == (60, 2, 120)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_wily_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_wily", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_wily": False}
    assert next_run.generation_discovery == {"j_wily": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_wily"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is WilyJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_wily", "Wily Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.THREE_OF_A_KIND,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"),
            BalatroCard("2", "Clubs"),
            BalatroCard("2", "Spades"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (130, 3, 390)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_abstract_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_abstract", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_abstract": False}
    assert next_run.generation_discovery == {"j_abstract": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_abstract"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is AbstractJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_abstract", "Abstract Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (5, 4, 20)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_photograph_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_photograph", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_photograph": False}
    assert next_run.generation_discovery == {"j_photograph": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_photograph"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is PhotographJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_photograph", "Photograph", 1, 5, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("K", "Hearts")],
    )
    assert (score.chips, score.mult, score.x_mult, score.total) == (
        5,
        2.0,
        1.0,
        10,
    )
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_half_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_half", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_half": False}
    assert next_run.generation_discovery == {"j_half": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_half"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is HalfJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_half", "Half Joker", 1, 5, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (5, 21, 105)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_mystic_summit_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_mystic_summit", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_mystic_summit": False}
    assert next_run.generation_discovery == {"j_mystic_summit": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_mystic_summit"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is MysticSummitJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_mystic_summit", "Mystic Summit", 1, 5, 4, 2, True)
    next_run.public.discards_remaining = 0
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (5, 16, 80)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_mystic_summit_purchase_is_masked_when_unaffordable():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_mystic_summit", base_cost=5, discovered=False)
    )
    run.public.money = 3
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action not in ShopTransitionEngine().legal_actions(inserted)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        ShopTransitionEngine().step(inserted, action)


def test_env_r2_exact_banner_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_banner", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_banner": False}
    assert next_run.generation_discovery == {"j_banner": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_banner"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is BannerJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_banner", "Banner", 1, 5, 4, 2, True)
    next_run.public.discards_remaining = 3
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("2", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (95, 1, 95)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_scary_face_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_scary_face", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_scary_face": False}
    assert next_run.generation_discovery == {"j_scary_face": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_scary_face"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is ScaryFaceJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_scary_face", "Scary Face", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("K", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (35, 1, 35)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
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
        GeneratedShopJokerItem("j_devious", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_devious", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_devious", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_gluttenous_joker", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_gluttenous_joker", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_gluttenous_joker", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_scholar", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_scholar", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_scholar", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_blue_joker", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_blue_joker", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_blue_joker", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_jolly", 2, 3, None, 3, False),
        GeneratedShopJokerItem("j_jolly", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_jolly", 1, 3, "Foil", 5, False),
        GeneratedShopJokerItem("j_sly", 2, 3, None, 3, False),
        GeneratedShopJokerItem("j_sly", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_sly", 1, 3, "Foil", 5, False),
        GeneratedShopJokerItem("j_wily", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_wily", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_wily", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_abstract", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_abstract", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_abstract", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_photograph", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_photograph", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_photograph", 1, 5, "Holographic", 8, False),
        GeneratedShopJokerItem("j_half", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_half", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_half", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_mystic_summit", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_mystic_summit", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_mystic_summit", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_banner", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_banner", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_banner", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_scary_face", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_scary_face", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_scary_face", 1, 4, "Foil", 6, False),
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
