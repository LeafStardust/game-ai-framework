from types import SimpleNamespace

import pytest

from games.balatro.jokers.ancient_joker import AncientJoker
from games.balatro.jokers.blackboard import BlackboardJoker
from games.balatro.jokers.bloodstone import BloodstoneJoker
from games.balatro.jokers.flower_pot import FlowerPotJoker
from games.balatro.jokers.gluttonous_joker import GluttonousJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.mime import MimeJoker
from games.balatro.jokers.onyx_agate import OnyxAgateJoker
from games.balatro.jokers.oops_all_6s import OopsAll6sJoker
from games.balatro.jokers.raised_fist import RaisedFistJoker
from games.balatro.jokers.rough_gem import RoughGemJoker
from games.balatro.jokers.seeing_double import SeeingDoubleJoker
from games.balatro.jokers.smeared_joker import SmearedJoker
from games.balatro.jokers.splash import SplashJoker
from games.balatro.strategy import GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    SECTION_THREE_NODE_IDS,
    SECTION_THREE_ROOT_IDS,
    TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
)
from games.balatro.strategy_tree_tracker import (
    TreeAwareStateAwareBalatroStrategyTracker,
)


def _card(rank: str, suit: str, *, enhancement: str = ""):
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
        for rank in (
            "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"
        )
    ]


def _state(*, jokers=(), deck=None, ante=1):
    cards = _natural_deck() if deck is None else list(deck)
    return SimpleNamespace(
        jokers=list(jokers),
        vouchers=[],
        owned_deck=cards,
        deck=cards,
        hand_levels={},
        hand_play_counts={},
        ante=ante,
    )


def _tracker():
    return TreeAwareStateAwareBalatroStrategyTracker(
        RUNTIME_UNIVERSAL_BALATRO_STRATEGIES,
        topology=TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY,
    )


def _by_id(resolution):
    return {
        assessment.strategy_id: assessment
        for assessment in resolution.assessments
    }


def test_section_three_has_eight_roots_eleven_leaves_and_no_one_child_branches():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
    terminal = {
        strategy_id
        for strategy_id in SECTION_THREE_NODE_IDS
        if topology.is_leaf(strategy_id)
    }

    assert len(SECTION_THREE_ROOT_IDS) == 8
    assert len(SECTION_THREE_NODE_IDS) == 14
    assert len(terminal) == 11
    assert topology.children_by_id["hearts"] == (
        "hearts_bloodstone_oops",
        "hearts_bloodstone_retrigger",
    )
    assert topology.children_by_id["clubs"] == (
        "clubs_onyx",
        "clubs_seeing_double",
    )
    assert topology.children_by_id["flower_pot"] == (
        "flower_pot_smeared",
        "flower_pot_splash",
    )
    assert all(
        len(topology.children_by_id[strategy_id]) != 1
        for strategy_id in SECTION_THREE_NODE_IDS
    )


def test_bloodstone_stays_on_hearts_parent_until_a_real_specialization_exists():
    tracker = _tracker()

    generic = tracker.observe(_state(jokers=(BloodstoneJoker(),)))
    assert generic.assessment("hearts").score == pytest.approx(8.0)
    assert "hearts_bloodstone_oops" not in _by_id(generic)

    oops = tracker.observe(_state(jokers=(BloodstoneJoker(), OopsAll6sJoker())))
    assert "hearts" not in _by_id(oops)
    assert oops.assessment("hearts_bloodstone_oops").score == pytest.approx(16.0)

    retrigger = tracker.observe(
        _state(jokers=(BloodstoneJoker(), HangingChadJoker()))
    )
    assert "hearts" not in _by_id(retrigger)
    assert retrigger.assessment("hearts_bloodstone_retrigger").score == pytest.approx(11.0)


def test_bloodstone_children_fail_closed_without_bloodstone():
    state = _state(jokers=(OopsAll6sJoker(), HangingChadJoker()))

    assert (
        conditional_joker_relationship(
            state,
            "hearts_bloodstone_oops",
            state.jokers[0],
        )
        == NEUTRAL
    )
    assert (
        conditional_joker_relationship(
            state,
            "hearts_bloodstone_retrigger",
            state.jokers[1],
        )
        == NEUTRAL
    )


def test_diamonds_is_a_leaf_and_smeared_requires_a_real_diamond_payoff():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
    tracker = _tracker()

    assert topology.is_leaf("diamonds") is True
    smeared_only = tracker.observe(_state(jokers=(SmearedJoker(),)))
    rough_smeared = tracker.observe(
        _state(jokers=(RoughGemJoker(), SmearedJoker()))
    )

    assert smeared_only.assessment("diamonds").score == pytest.approx(0.0)
    assert rough_smeared.assessment("diamonds").score == pytest.approx(11.0)


def test_clubs_separates_many_clubs_from_mixed_suit_seeing_double():
    tracker = _tracker()

    generic = tracker.observe(_state(jokers=(GluttonousJoker(),)))
    assert generic.assessment("clubs").score == pytest.approx(3.0)

    onyx = tracker.observe(_state(jokers=(GluttonousJoker(), OnyxAgateJoker())))
    assert "clubs" not in _by_id(onyx)
    assert onyx.assessment("clubs_onyx").score == pytest.approx(11.0)

    mixed = tracker.observe(
        _state(jokers=(GluttonousJoker(), SeeingDoubleJoker()))
    )
    assert "clubs" not in _by_id(mixed)
    assert mixed.assessment("clubs_seeing_double").score == pytest.approx(11.0)


def test_raised_fist_mime_support_is_exact_and_blackboard_is_independent():
    tracker = _tracker()
    mime_only = _state(jokers=(MimeJoker(),))

    assert (
        conditional_joker_relationship(mime_only, "raised_fist", mime_only.jokers[0])
        == NEUTRAL
    )

    raised = tracker.observe(_state(jokers=(RaisedFistJoker(), MimeJoker())))
    blackboard = tracker.observe(_state(jokers=(BlackboardJoker(),)))

    assert raised.assessment("raised_fist").score == pytest.approx(11.0)
    assert blackboard.assessment("blackboard").score == pytest.approx(8.0)


def test_ancient_and_flower_pot_upgrade_relationships_require_their_owner():
    tracker = _tracker()

    ancient = tracker.observe(_state(jokers=(AncientJoker(), SmearedJoker())))
    assert ancient.assessment("ancient_suit_rotation").score == pytest.approx(11.0)

    flower = tracker.observe(_state(jokers=(FlowerPotJoker(), SplashJoker())))
    assert "flower_pot" not in _by_id(flower)
    assert flower.assessment("flower_pot_splash").score == pytest.approx(16.0)

    unsupported = _state(jokers=(SplashJoker(), SmearedJoker()))
    assert (
        conditional_joker_relationship(
            unsupported,
            "flower_pot_splash",
            unsupported.jokers[0],
        )
        == NEUTRAL
    )
    assert (
        conditional_joker_relationship(
            unsupported,
            "flower_pot_smeared",
            unsupported.jokers[1],
        )
        == NEUTRAL
    )


def test_section_three_exact_relationship_tiers_and_directed_consumables():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES

    assert definitions["hearts"].relationship_for(
        BloodstoneJoker(), kind="JOKER"
    ) == GOLD
    assert definitions["clubs"].relationship_for(
        OnyxAgateJoker(), kind="JOKER"
    ) == NEUTRAL
    assert definitions["clubs_onyx"].relationship_for(
        OnyxAgateJoker(), kind="JOKER"
    ) == GOLD
    assert definitions["raised_fist"].directed_spectrals == frozenset(
        {"familiar", "grim", "cryptid", "dejavu"}
    )
    assert definitions["ancient_suit_rotation"].directed_tarots == frozenset(
        {"thestar", "themoon", "thesun", "theworld"}
    )


def test_indexed_section_three_children_do_not_duplicate_parent_components():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    for parent_id in ("hearts", "clubs", "flower_pot"):
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

            assert parent.directed_tarots.isdisjoint(child.directed_tarots)
            assert parent.directed_spectrals.isdisjoint(child.directed_spectrals)
            assert set(parent.preferred_enhancements).isdisjoint(
                child.preferred_enhancements
            )


def test_suit_support_relationships_are_conditional_not_static():
    smeared = SmearedJoker()
    state = _state(jokers=(RoughGemJoker(), smeared))

    assert RUNTIME_UNIVERSAL_BALATRO_STRATEGIES["diamonds"].relationship_for(
        smeared, kind="JOKER"
    ) == NEUTRAL
    assert conditional_joker_relationship(state, "diamonds", smeared) == SILVER
