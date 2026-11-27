import pytest

from games.balatro.card import BalatroCard
from games.balatro.env.card_order import derive_playing_card_order
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
from games.balatro.jokers.bull import BullJoker
from games.balatro.jokers.clever_joker import CleverJoker
from games.balatro.jokers.crazy_joker import CrazyJoker
from games.balatro.jokers.crafty_joker import CraftyJoker
from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.droll_joker import DrollJoker
from games.balatro.jokers.drunkard import DrunkardJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.flat_mult import FlatMultJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.golden_joker import GoldenJoker
from games.balatro.jokers.greedy_joker import GreedyJoker
from games.balatro.jokers.half_joker import HalfJoker
from games.balatro.jokers.jolly_joker import JollyJoker
from games.balatro.jokers.juggler import JugglerJoker
from games.balatro.jokers.lusty_joker import LustyJoker
from games.balatro.jokers.mad_joker import MadJoker
from games.balatro.jokers.mystic_summit import MysticSummitJoker
from games.balatro.jokers.odd_todd import OddToddJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.rocket import RocketJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.sly_joker import SlyJoker
from games.balatro.jokers.smiley_face import SmileyFaceJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wily_joker import WilyJoker
from games.balatro.jokers.wrathful_joker import WrathfulJoker
from games.balatro.jokers.zany_joker import ZanyJoker
from games.balatro.scoring import BalatroScorer
from games.balatro.state import BalatroState


def _descriptor(
    *,
    edition: str | None = None,
    rarity: int = 1,
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
        rarity=rarity,
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


def test_env_r2_exact_walkie_talkie_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_walkie_talkie", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_walkie_talkie": False}
    assert next_run.generation_discovery == {"j_walkie_talkie": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_walkie_talkie"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is WalkieTalkieJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_walkie_talkie", "Walkie Talkie", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("4", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (15, 5, 75)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_smiley_face_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_smiley", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_smiley": False}
    assert next_run.generation_discovery == {"j_smiley": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_smiley"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is SmileyFaceJoker
    assert (
        joker.center,
        joker.label,
        joker.rarity,
        joker.base_cost,
        joker.cost,
        joker.sell_cost,
        joker.discovered,
    ) == ("j_smiley", "Smiley Face", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("K", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (5, 6, 30)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_raised_fist_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_raised_fist", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_raised_fist": False}
    assert next_run.generation_discovery == {"j_raised_fist": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_raised_fist"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is RaisedFistJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_raised_fist", "Raised Fist", 1, 5, 4, 2, True)
    next_run.public.hand = [BalatroCard("3", "Clubs")]
    score = BalatroScorer().score(
        PokerHand.HIGH_CARD,
        state=next_run.public,
        cards=[BalatroCard("K", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (5, 7, 35)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_clever_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_clever", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_clever": False}
    assert next_run.generation_discovery == {"j_clever": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_clever"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is CleverJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_clever", "Clever Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.TWO_PAIR,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"), BalatroCard("2", "Clubs"),
            BalatroCard("3", "Hearts"), BalatroCard("3", "Clubs"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (100, 2, 200)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_mad_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_mad", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_mad": False}
    assert next_run.generation_discovery == {"j_mad": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_mad"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is MadJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_mad", "Mad Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.TWO_PAIR,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"), BalatroCard("2", "Clubs"),
            BalatroCard("3", "Hearts"), BalatroCard("3", "Clubs"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (20, 12, 240)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_zany_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_zany", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_zany": False}
    assert next_run.generation_discovery == {"j_zany": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_zany"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is ZanyJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_zany", "Zany Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.THREE_OF_A_KIND,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"), BalatroCard("2", "Clubs"),
            BalatroCard("2", "Spades"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (30, 15, 450)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_crafty_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_crafty", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_crafty": False}
    assert next_run.generation_discovery == {"j_crafty": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_crafty"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is CraftyJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_crafty", "Crafty Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.FLUSH,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"), BalatroCard("4", "Hearts"),
            BalatroCard("6", "Hearts"), BalatroCard("8", "Hearts"),
            BalatroCard("10", "Hearts"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (115, 4, 460)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_crazy_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_crazy", base_cost=4, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_crazy": False}
    assert next_run.generation_discovery == {"j_crazy": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_crazy"})
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is CrazyJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_crazy", "Crazy Joker", 1, 4, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.STRAIGHT,
        state=next_run.public,
        cards=[
            BalatroCard("2", "Hearts"), BalatroCard("3", "Clubs"),
            BalatroCard("4", "Spades"), BalatroCard("5", "Diamonds"),
            BalatroCard("6", "Hearts"),
        ],
    )
    assert (score.chips, score.mult, score.total) == (30, 16, 480)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_greedy_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_greedy_joker", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_greedy_joker": False}
    assert next_run.generation_discovery == {"j_greedy_joker": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_greedy_joker"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is GreedyJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_greedy_joker", "Greedy Joker", 1, 5, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("10", "Diamonds"), BalatroCard("10", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (10, 5, 50)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_lusty_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_lusty_joker", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_lusty_joker": False}
    assert next_run.generation_discovery == {"j_lusty_joker": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_lusty_joker"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is LustyJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_lusty_joker", "Lusty Joker", 1, 5, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("10", "Hearts"), BalatroCard("10", "Diamonds")],
    )
    assert (score.chips, score.mult, score.total) == (10, 5, 50)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_wrathful_joker_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_wrathful_joker", base_cost=5, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_wrathful_joker": False}
    assert next_run.generation_discovery == {"j_wrathful_joker": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_wrathful_joker"}
    )
    assert next_run.public.money == 16
    joker = next_run.public.jokers[0]
    assert type(joker) is WrathfulJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_wrathful_joker", "Wrathful Joker", 1, 5, 4, 2, True)
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("10", "Spades"), BalatroCard("10", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (10, 5, 50)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.jokers == []


def test_env_r2_exact_fibonacci_materialization_scores_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(
            center_key="j_fibonacci",
            rarity=2,
            base_cost=8,
            discovered=False,
        )
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)
    assert inserted.generation_discovery == {"j_fibonacci": False}
    assert next_run.generation_discovery == {"j_fibonacci": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_fibonacci"}
    )
    assert next_run.public.money == 13
    joker = next_run.public.jokers[0]
    assert type(joker) is FibonacciJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_fibonacci", "Fibonacci", 2, 8, 7, 3, True)
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("A", "Spades"), BalatroCard("A", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (10, 18, 180)
    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 16
    assert sold_run.public.jokers == []


def test_env_r2_exact_juggler_materialization_updates_hand_size_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_juggler", base_cost=4, discovered=False)
    )
    run.public.hand_size = 8
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_juggler": False}
    assert next_run.generation_discovery == {"j_juggler": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_juggler"}
    )
    assert inserted.public.hand_size == 8
    assert next_run.public.money == 16
    assert next_run.public.hand_size == 9
    joker = next_run.public.jokers[0]
    assert type(joker) is JugglerJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_juggler", "Juggler", 1, 4, 4, 2, True)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.hand_size == 8
    assert sold_run.public.jokers == []


def test_env_r2_exact_drunkard_materialization_updates_reset_discards_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_drunkard", base_cost=4, discovered=False)
    )
    run.public.round_reset_discards_observed = True
    run.public.round_reset_discards = 3
    run.public.discards_remaining = 1
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_drunkard": False}
    assert next_run.generation_discovery == {"j_drunkard": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_drunkard"}
    )
    assert inserted.public.round_reset_discards == 3
    assert inserted.public.discards_remaining == 1
    assert next_run.public.money == 16
    assert next_run.public.round_reset_discards == 4
    assert next_run.public.discards_remaining == 1
    joker = next_run.public.jokers[0]
    assert type(joker) is DrunkardJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_drunkard", "Drunkard", 1, 4, 4, 2, True)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 18
    assert sold_run.public.round_reset_discards == 3
    assert sold_run.public.discards_remaining == 1
    assert sold_run.public.jokers == []


def test_env_r2_exact_golden_joker_materialization_acquires_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_golden", base_cost=6, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_golden": False}
    assert next_run.generation_discovery == {"j_golden": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_golden"}
    )
    assert next_run.public.money == 15
    joker = next_run.public.jokers[0]
    assert type(joker) is GoldenJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_golden", "Golden Joker", 1, 6, 5, 2, True)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 17
    assert sold_run.public.jokers == []


def test_env_r2_exact_bull_materialization_scores_from_money_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_bull", rarity=2, base_cost=6, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_bull": False}
    assert next_run.generation_discovery == {"j_bull": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset({"j_bull"})
    assert next_run.public.money == 15
    joker = next_run.public.jokers[0]
    assert type(joker) is BullJoker
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_bull", "Bull", 2, 6, 5, 2, True)
    score = BalatroScorer().score(
        PokerHand.PAIR,
        state=next_run.public,
        cards=[BalatroCard("A", "Spades"), BalatroCard("A", "Hearts")],
    )
    assert (score.chips, score.mult, score.total) == (40, 2, 80)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 17
    assert sold_run.public.jokers == []


def test_env_r2_exact_rocket_materialization_acquires_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_rocket", rarity=2, base_cost=6, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_rocket": False}
    assert next_run.generation_discovery == {"j_rocket": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_rocket"}
    )
    assert next_run.public.money == 15
    joker = next_run.public.jokers[0]
    assert type(joker) is RocketJoker
    assert (joker.dollars, joker.increase) == (1, 2)
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_rocket", "Rocket", 2, 6, 5, 2, True)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 17
    assert sold_run.public.jokers == []


@pytest.mark.parametrize(("rarity", "base_cost", "edition"), [(1, 5, None), (2, 4, None), (2, 5, "Foil")])
def test_env_r2_mime_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_mime", rarity, base_cost, edition, 5, False)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(("rarity", "base_cost", "edition"), [(1, 7, None), (2, 6, None), (2, 7, "Foil")])
@pytest.mark.parametrize("center", ["j_madness", "j_midas_mask"])
def test_env_r2_madness_and_midas_reject_unsupported_metadata(rarity, base_cost, edition, center):
    item = GeneratedShopJokerItem(center, rarity, base_cost, edition, 7, False)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 8, None), (3, 7, None), (3, 8, "Foil")]
)
def test_env_r2_dna_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_dna", rarity, base_cost, edition, 8, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize("unsupported", ["missing_card_order", "duplicate_dna"])
def test_env_r2_dna_purchase_masks_unsupported_inventory(unsupported):
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_dna", rarity=3, base_cost=8, discovered=True)
    )
    run.public.owned_deck = run.public.deck.copy()
    run.playing_card_order = derive_playing_card_order(run.public)
    inserted = insert_generated_shop_joker_item(run, item)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})
    assert action in engine.legal_actions(inserted)

    if unsupported == "missing_card_order":
        inserted.playing_card_order = None
    else:
        inserted.public.jokers.append(DNAJoker())

    assert action not in engine.legal_actions(inserted)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(inserted, action)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 4, None), (1, 5, None), (1, 4, "Foil")]
)
def test_env_r2_faceless_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_faceless", rarity, base_cost, edition, 4, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 3, None), (1, 4, None), (1, 3, "Foil")]
)
def test_env_r2_splash_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_splash", rarity, base_cost, edition, 3, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 5, None), (1, 4, None), (1, 5, "Foil")]
)
def test_env_r2_runner_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_runner", rarity, base_cost, edition, 5, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 5, None), (1, 4, None), (1, 5, "Foil")]
)
def test_env_r2_supernova_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_supernova", rarity, base_cost, edition, 5, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(2, 4, None), (1, 5, None), (1, 4, "Foil")]
)
def test_env_r2_green_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_green_joker", rarity, base_cost, edition, 4, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(
    ("rarity", "base_cost", "edition"), [(1, 6, None), (2, 5, None), (2, 6, "Foil")]
)
def test_env_r2_sixth_sense_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_sixth_sense", rarity, base_cost, edition, 6, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(("rarity", "cost", "edition", "rank"), [
    (2, 4, None, "K"), (1, 5, None, "K"), (1, 4, "Foil", "K"),
    (1, 4, None, None), (1, 4, None, "Unknown"),
])
def test_env_r2_mail_materialization_requires_exact_offer_and_target(rarity, cost, edition, rank):
    item = GeneratedShopJokerItem("j_mail", rarity, cost, edition, 4, True)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item, mail_rebate_rank=rank)


def test_env_r2_madness_purchase_requires_retained_joker_order():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_madness", rarity=2, base_cost=7, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    inserted.joker_order_state = None
    assert EnvAction.from_alias("BUY_JOKER", {"slot": 0}) not in (
        ShopTransitionEngine().legal_actions(inserted)
    )


def test_env_r2_seance_purchase_is_masked_without_exact_spectral_authority():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_seance", rarity=2, base_cost=6, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action not in engine.legal_actions(inserted)
    with pytest.raises(HeadlessTransitionError, match="illegal shop transition"):
        engine.step(inserted, action)
    assert inserted.public.jokers == []


@pytest.mark.parametrize(("rarity", "base_cost", "edition"), [(1, 6, None), (2, 5, None), (2, 6, "Foil")])
def test_env_r2_seance_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_seance", rarity, base_cost, edition, 6, False)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize(("rarity", "base_cost", "edition"), [(1, 7, None), (2, 6, None), (2, 7, "Foil")])
def test_env_r2_cloud9_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_cloud_9", rarity, base_cost, edition, 7, False)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item)


@pytest.mark.parametrize("suit", [None, "Unknown", "Hearts"])
def test_env_r2_castle_purchase_requires_the_retained_round_suit(suit):
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_castle", rarity=2, base_cost=6, discovered=False)
    )
    run.castle_suit = suit
    inserted = insert_generated_shop_joker_item(run, item)
    engine = ShopTransitionEngine()
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert (action in engine.legal_actions(inserted)) == (suit == "Hearts")
    if suit == "Hearts":
        purchased = engine.step(inserted, action)
        joker = purchased.public.jokers[0]
        assert (joker.center, joker.suit, joker.chips, joker.chip_mod) == (
            "j_castle", "Hearts", 0, 3,
        )
        assert purchased.generated_center_discovered("j_castle") is True
    else:
        with pytest.raises(HeadlessTransitionError):
            engine.step(inserted, action)
        assert inserted.public.jokers == []


@pytest.mark.parametrize("rarity,base_cost,edition", [(1, 6, None), (2, 5, None), (2, 6, "Foil")])
def test_env_r2_castle_materialization_rejects_unsupported_metadata(rarity, base_cost, edition):
    item = GeneratedShopJokerItem("j_castle", rarity, base_cost, edition, 6, False)
    with pytest.raises(HeadlessTransitionError):
        materialize_generated_shop_joker_for_acquisition(item, castle_suit="Hearts")


def test_env_r2_exact_vampire_materialization_acquires_and_sells():
    run, item = materialize_shop_joker_descriptor(
        _descriptor(center_key="j_vampire", rarity=2, base_cost=7, discovered=False)
    )
    inserted = insert_generated_shop_joker_item(run, item)
    action = EnvAction.from_alias("BUY_JOKER", {"slot": 0})

    assert action in ShopTransitionEngine().legal_actions(inserted)
    next_run = ShopTransitionEngine().step(inserted, action)

    assert inserted.generation_discovery == {"j_vampire": False}
    assert next_run.generation_discovery == {"j_vampire": True}
    assert next_run.tag_profile_state.discovered_center_keys == frozenset(
        {"j_vampire"}
    )
    assert next_run.public.money == 14
    joker = next_run.public.jokers[0]
    assert type(joker) is VampireJoker
    assert joker.x_mult == 1.0
    assert (
        joker.center, joker.label, joker.rarity, joker.base_cost,
        joker.cost, joker.sell_cost, joker.discovered,
    ) == ("j_vampire", "Vampire", 2, 7, 6, 3, True)

    sold_run = ShopTransitionEngine().step(
        next_run, EnvAction.from_alias("SELL_JOKER", {"joker_index": 0})
    )
    assert sold_run.public.money == 17
    assert sold_run.public.jokers == []


@pytest.mark.parametrize(
    "item",
    (
        GeneratedShopJokerItem("j_greedy_joker", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_greedy_joker", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_greedy_joker", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_lusty_joker", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_lusty_joker", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_lusty_joker", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_wrathful_joker", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_wrathful_joker", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_wrathful_joker", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_fibonacci", 1, 8, None, 8, False),
        GeneratedShopJokerItem("j_fibonacci", 2, 7, None, 7, False),
        GeneratedShopJokerItem("j_fibonacci", 2, 8, "Foil", 10, False),
        GeneratedShopJokerItem("j_juggler", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_juggler", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_juggler", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_drunkard", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_drunkard", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_drunkard", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_golden", 2, 6, None, 6, False),
        GeneratedShopJokerItem("j_golden", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_golden", 1, 6, "Foil", 8, False),
        GeneratedShopJokerItem("j_bull", 1, 6, None, 6, False),
        GeneratedShopJokerItem("j_bull", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_bull", 2, 6, "Foil", 8, False),
        GeneratedShopJokerItem("j_rocket", 1, 6, None, 6, False),
        GeneratedShopJokerItem("j_rocket", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_rocket", 2, 6, "Foil", 8, False),
        GeneratedShopJokerItem("j_vampire", 1, 7, None, 7, False),
        GeneratedShopJokerItem("j_vampire", 2, 6, None, 6, False),
        GeneratedShopJokerItem("j_vampire", 2, 7, "Foil", 9, False),
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
        GeneratedShopJokerItem("j_walkie_talkie", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_walkie_talkie", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_walkie_talkie", 1, 4, "Polychrome", 9, False),
        GeneratedShopJokerItem("j_smiley", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_smiley", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_smiley", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_raised_fist", 2, 5, None, 5, False),
        GeneratedShopJokerItem("j_raised_fist", 1, 4, None, 4, False),
        GeneratedShopJokerItem("j_raised_fist", 1, 5, "Foil", 7, False),
        GeneratedShopJokerItem("j_clever", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_clever", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_clever", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_mad", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_mad", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_mad", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_zany", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_zany", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_zany", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_crafty", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_crafty", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_crafty", 1, 4, "Foil", 6, False),
        GeneratedShopJokerItem("j_crazy", 2, 4, None, 4, False),
        GeneratedShopJokerItem("j_crazy", 1, 5, None, 5, False),
        GeneratedShopJokerItem("j_crazy", 1, 4, "Foil", 6, False),
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
