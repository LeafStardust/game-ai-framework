from types import SimpleNamespace

import pytest

from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.glass_joker import GlassJoker
from games.balatro.jokers.golden_ticket import GoldenTicketJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.lucky_cat import LuckyCatJoker
from games.balatro.jokers.marble_joker import MarbleJoker
from games.balatro.jokers.midas_mask import MidasMaskJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.steel_joker import SteelJoker
from games.balatro.jokers.stone_joker import StoneJoker
from games.balatro.jokers.vampire import VampireJoker
from games.balatro.strategy import GOLD, NEUTRAL
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    SECTION_FOUR_NODE_IDS,
    SECTION_FOUR_ROOT_IDS,
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)


def _card(rank, suit, *, enhancement=""):
    return SimpleNamespace(
        rank=rank,
        suit=suit,
        enhancement=enhancement,
        seal="",
        edition="",
    )


def _natural_deck():
    return [
        _card(rank, suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A")
    ]


def _state(*, jokers=(), enhancement=""):
    deck = _natural_deck()
    if enhancement:
        deck[0].enhancement = enhancement
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=deck,
        deck=deck,
        hand_levels={},
        hand_play_counts={},
        ante=4,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def _by_id(resolution):
    return {item.strategy_id: item for item in resolution.assessments}


def test_section_four_has_five_roots_fifteen_leaves_and_no_one_child_branches():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
    terminal = {
        strategy_id
        for strategy_id in SECTION_FOUR_NODE_IDS
        if topology.is_leaf(strategy_id)
    }

    assert len(SECTION_FOUR_ROOT_IDS) == 5
    assert len(SECTION_FOUR_NODE_IDS) == 20
    assert len(terminal) == 15
    assert topology.children_by_id["stone"] == (
        "stone_dna_duplication",
        "stone_high_card",
        "stone_marble_scaling",
        "stone_marble_vampire",
    )
    assert topology.children_by_id["gold_cards"] == (
        "gold_cards_held_mime",
        "gold_cards_midas",
        "gold_cards_midas_ticket",
        "gold_cards_ticket",
    )
    assert all(
        len(topology.children_by_id[strategy_id]) != 1
        for strategy_id in SECTION_FOUR_NODE_IDS
    )


def test_stone_children_require_real_stone_or_marble_infrastructure():
    plain = _state(jokers=(DNAJoker(),))
    stone = _state(jokers=(DNAJoker(),), enhancement="Stone")
    paired = _state(jokers=(MarbleJoker(), StoneJoker(), VampireJoker()))

    assert conditional_joker_relationship(plain, "stone_dna_duplication", plain.jokers[0]) == NEUTRAL
    assert conditional_joker_relationship(stone, "stone_dna_duplication", stone.jokers[0]) == GOLD
    resolution = _tracker().observe(paired)
    assert resolution.assessment("stone_marble_scaling").score >= 16.0
    assert resolution.assessment("stone_marble_vampire").score >= 16.0


def test_glass_retrigger_does_not_seed_from_generic_hanging_chad():
    plain = _state(jokers=(HangingChadJoker(),))
    glass = _state(jokers=(HangingChadJoker(),), enhancement="Glass")

    assert conditional_joker_relationship(plain, "glass_retrigger", plain.jokers[0]) == NEUTRAL
    assert conditional_joker_relationship(glass, "glass_retrigger", glass.jokers[0]) == GOLD
    assert _tracker().observe(_state(jokers=(GlassJoker(),))).dominant_strategy_id == "glass_breakage"


def test_steel_mime_requires_steel_while_steel_joker_owns_density_leaf():
    plain = _state(jokers=(MimeJoker(),))
    steel = _state(jokers=(MimeJoker(),), enhancement="Steel")

    assert conditional_joker_relationship(plain, "steel_mime", plain.jokers[0]) == NEUTRAL
    assert conditional_joker_relationship(steel, "steel_mime", steel.jokers[0]) == GOLD
    assert _tracker().observe(_state(jokers=(SteelJoker(),))).dominant_strategy_id == "steel_density"


def test_lucky_cat_oops_and_gold_midas_ticket_pairs_select_combo_leaves():
    lucky = _tracker().observe(
        _state(jokers=(LuckyCatJoker(), OopsAll6sJoker()), enhancement="Lucky")
    )
    gold = _tracker().observe(
        _state(jokers=(MidasMaskJoker(), GoldenTicketJoker()), enhancement="Gold")
    )

    assert lucky.assessment("lucky_cat_oops").score >= 16.0
    assert lucky.dominant_strategy_id == "lucky_cat_oops"
    assert gold.assessment("gold_cards_midas_ticket").score >= 16.0
    assert gold.dominant_strategy_id == "gold_cards_midas_ticket"


def test_indexed_section_four_children_do_not_duplicate_parent_components():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    for parent_id in SECTION_FOUR_ROOT_IDS:
        parent = definitions[parent_id]
        for child_id in topology.children_by_id[parent_id]:
            child = definitions[child_id]
            for kind in ("JOKER", "CONSUMABLE", "PLANET", "VOUCHER"):
                parent_components = set().union(
                    *(components for _, components in parent._buckets(kind))
                )
                child_components = set().union(
                    *(components for _, components in child._buckets(kind))
                )
                assert parent_components.isdisjoint(child_components)
