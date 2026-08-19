from types import SimpleNamespace

import pytest

from games.balatro.jokers.dna import DNAJoker
from games.balatro.jokers.even_steven import EvenStevenJoker
from games.balatro.jokers.fibonacci import FibonacciJoker
from games.balatro.jokers.hack import HackJoker
from games.balatro.jokers.hanging_chad import HangingChadJoker
from games.balatro.jokers.pareidolia import PareidoliaJoker
from games.balatro.jokers.photograph import PhotographJoker
from games.balatro.jokers.ride_the_bus import RideTheBusJoker
from games.balatro.jokers.scary_face import ScaryFaceJoker
from games.balatro.jokers.scholar import ScholarJoker
from games.balatro.jokers.the_idol import TheIdolJoker
from games.balatro.jokers.walkie_talkie import WalkieTalkieJoker
from games.balatro.jokers.wee_joker import WeeJoker
from games.balatro.strategy import BRONZE, GOLD, NEUTRAL, SILVER
from games.balatro.strategy_catalog_guard import RUNTIME_UNIVERSAL_BALATRO_STRATEGIES
from games.balatro.strategy_conditional_relationships import (
    conditional_joker_relationship,
)
from games.balatro.strategy_tree_catalog import (
    SECTION_TWO_NODE_IDS,
    SECTION_TWO_ROOT_IDS,
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


def test_section_two_collapses_upgrade_stacks_and_keeps_real_branches():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY

    assert len(SECTION_TWO_ROOT_IDS) == 10
    assert len(SECTION_TWO_NODE_IDS) == 17
    assert topology.is_leaf("aces") is True
    assert topology.is_leaf("low_rank") is True
    assert topology.is_leaf("twos") is True
    assert topology.children_by_id["face_cards"] == (
        "face_business_card",
        "face_held_economy",
        "face_pareidolia",
        "face_photochad",
        "face_triboulet_sock",
    )
    assert topology.children_by_id["faceless"] == (
        "faceless_discard_economy",
        "faceless_ride_bus",
    )
    assert all(
        len(topology.children_by_id[strategy_id]) != 1
        for strategy_id in SECTION_TWO_NODE_IDS
    )


def test_section_two_contains_fifteen_terminal_strategies():
    topology = TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY
    terminal = {
        strategy_id
        for strategy_id in SECTION_TWO_NODE_IDS
        if topology.is_leaf(strategy_id)
    }

    assert len(terminal) == 15
    assert terminal == SECTION_TWO_NODE_IDS - {"face_cards", "faceless"}


def test_collapsed_rank_relationships_match_the_frozen_contract():
    definitions = RUNTIME_UNIVERSAL_BALATRO_STRATEGIES

    assert definitions["aces"].relationship_for(ScholarJoker(), kind="JOKER") == GOLD
    assert definitions["aces"].relationship_for(DNAJoker(), kind="JOKER") == NEUTRAL
    assert definitions["low_rank"].relationship_for(FibonacciJoker(), kind="JOKER") == GOLD
    assert definitions["low_rank"].relationship_for(HackJoker(), kind="JOKER") == GOLD
    assert definitions["twos"].relationship_for(WeeJoker(), kind="JOKER") == GOLD
    assert definitions["twos"].relationship_for(HackJoker(), kind="JOKER") == NEUTRAL
    assert definitions["ten_four"].relationship_for(
        WalkieTalkieJoker(), kind="JOKER"
    ) == GOLD
    assert definitions["low_rank"].relationship_for(
        WalkieTalkieJoker(), kind="JOKER"
    ) == NEUTRAL


def test_scholar_establishes_aces_and_dna_only_supports_a_real_ace_route():
    tracker = _tracker()
    dna_only = tracker.observe(_state(jokers=(DNAJoker(),)))
    scholar_dna = tracker.observe(_state(jokers=(ScholarJoker(), DNAJoker())))

    assert dna_only.assessment("aces").score == pytest.approx(0.0)
    assert scholar_dna.assessment("aces").score == pytest.approx(11.0)
    assert scholar_dna.dominant_strategy_id == "aces"


def test_wee_hack_is_one_twos_strategy_while_hack_fibonacci_is_one_low_rank_strategy():
    tracker = _tracker()

    twos = tracker.observe(_state(jokers=(WeeJoker(), HackJoker())))
    assert twos.assessment("twos").score == pytest.approx(11.0)
    assert twos.assessment("low_rank").score == pytest.approx(8.0)
    assert twos.dominant_strategy_id == "twos"

    low_rank = tracker.observe(_state(jokers=(HackJoker(), FibonacciJoker())))
    assert low_rank.assessment("low_rank").score == pytest.approx(16.0)
    assert low_rank.dominant_strategy_id == "low_rank"


def test_low_rank_retrigger_support_requires_real_low_rank_commitment():
    unsupported = _state()
    committed = _state(jokers=(FibonacciJoker(),))

    assert (
        conditional_joker_relationship(
            unsupported,
            "low_rank",
            HangingChadJoker(),
        )
        == NEUTRAL
    )
    assert (
        conditional_joker_relationship(
            committed,
            "low_rank",
            HangingChadJoker(),
        )
        == SILVER
    )


def test_ten_four_owns_walkie_talkie_and_even_steven_support_is_conditional():
    tracker = _tracker()

    unsupported = tracker.observe(_state(jokers=(EvenStevenJoker(),)))
    supported = tracker.observe(
        _state(jokers=(WalkieTalkieJoker(), EvenStevenJoker()))
    )

    assert unsupported.assessment("ten_four").score == pytest.approx(0.0)
    assert supported.assessment("ten_four").score == pytest.approx(11.0)
    assert supported.dominant_strategy_id == "ten_four"


def test_generic_face_evidence_stays_on_parent_until_a_real_child_exists():
    tracker = _tracker()
    resolution = tracker.observe(_state(jokers=(ScaryFaceJoker(),)))
    by_id = _by_id(resolution)

    assert by_id["face_cards"].score == pytest.approx(3.0)
    assert "face_photochad" not in by_id
    assert "face_pareidolia" not in by_id
    assert tracker.tree_node_scores()["face_cards"].on_frontier is True


def test_photochad_replaces_face_parent_and_inherits_parent_evidence_once():
    tracker = _tracker()
    resolution = tracker.observe(
        _state(
            jokers=(ScaryFaceJoker(), PhotographJoker(), HangingChadJoker()),
        )
    )
    by_id = _by_id(resolution)

    assert "face_cards" not in by_id
    assert by_id["face_photochad"].score == pytest.approx(14.0)
    assert resolution.dominant_strategy_id == "face_photochad"


def test_pareidolia_requires_an_inherited_face_payoff_before_selecting_its_leaf():
    tracker = _tracker()
    unsupported = tracker.observe(_state(jokers=(PareidoliaJoker(),)))
    supported = tracker.observe(
        _state(jokers=(PareidoliaJoker(), ScaryFaceJoker()))
    )

    assert "face_pareidolia" not in _by_id(unsupported)
    assert supported.assessment("face_pareidolia").score == pytest.approx(11.0)
    assert supported.dominant_strategy_id == "face_pareidolia"


def test_ride_the_bus_replaces_generic_faceless_parent_without_inheriting_a_conflict():
    abandoned = [
        _card(rank, suit)
        for suit in ("Hearts", "Diamonds", "Clubs", "Spades")
        for rank in ("2", "3", "4", "5", "6", "7", "8", "9", "10", "A")
    ]
    tracker = _tracker()
    resolution = tracker.observe(
        _state(jokers=(RideTheBusJoker(),), deck=abandoned)
    )
    by_id = _by_id(resolution)

    assert "faceless" not in by_id
    assert by_id["faceless_ride_bus"].score > 5.0
    assert resolution.dominant_strategy_id == "faceless_ride_bus"


def test_idol_exact_card_evidence_uses_the_current_public_target_count():
    deck = _natural_deck()
    deck.extend(
        [
            _card("A", "Hearts"),
            _card("A", "Hearts"),
            _card("A", "Hearts"),
        ]
    )
    state = _state(jokers=(), deck=deck)
    idol = TheIdolJoker("A", "Hearts")

    assert conditional_joker_relationship(state, "idol_exact", idol) == GOLD
    assert conditional_joker_relationship(state, "aces", idol) == BRONZE
