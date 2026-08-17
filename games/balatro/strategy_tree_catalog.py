from __future__ import annotations

from types import MappingProxyType

from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES, _strategy
from games.balatro.strategy_topology import StrategyNodeSpec, StrategyTopology


_HIGH_CARD_TREE_IDS = frozenset(
    {
        "high_card",
        "high_card_core",
        "high_card_stuntman",
        "high_card_baron_mime",
    }
)
_PAIR_STRATEGY_ID = "pair"
_TWO_PAIR_TREE_IDS = frozenset(
    {
        "two_pair",
        "two_pair_core",
        "two_pair_trousers_square",
    }
)


def _high_card_tree_definitions():
    """Return the first tree-owned strategy subtree.

    Relationship tiers describe strategy evidence, not generic Joker strength.
    Broad High Card evidence belongs to the parent. Specific leaves contain only
    evidence that distinguishes that realization from its siblings.
    """

    return {
        "high_card": _strategy(
            "high_card",
            "High Card",
            "HIGH_CARD",
            gold_jokers=("Burnt Joker",),
            silver_jokers=(
                "Card Sharp",
                "Supernova",
                "Space Joker",
                "Half Joker",
                "Green Joker",
                "Burglar",
            ),
            gold_planets=("Pluto",),
        ),
        "high_card_core": _strategy(
            "high_card_core",
            "Core Repetition / Level High Card",
        ),
        "high_card_stuntman": _strategy(
            "high_card_stuntman",
            "Stuntman / Small-Hand High Card",
            gold_jokers=("Stuntman",),
        ),
        "high_card_baron_mime": _strategy(
            "high_card_baron_mime",
            "Baron-Mime Steel-King High Card",
            silver_jokers=(
                "Baron",
                "Mime",
                "Blackboard",
                "Shoot the Moon",
                "Troubadour",
                "Juggler",
            ),
            bronze_jokers=("Raised Fist", "Reserved Parking"),
            banned_jokers=("Stuntman",),
            silver_consumables=("The Chariot",),
            preferred_enhancements=("Steel",),
            preferred_seals=("Red",),
            preferred_ranks=("K",),
            face_mode="FACE",
        ),
    }


def _pair_tree_definition():
    """Return the audited standalone Pair leaf.

    Static relationships are limited to components that directly indicate Pair.
    Generic repeated-hand and small-hand support is resolved conditionally once
    independent Pair evidence already exists, so those Jokers cannot create a Pair
    strategy from zero by themselves.
    """

    return _strategy(
        "pair",
        "Pair",
        "PAIR",
        gold_jokers=("The Duo",),
        silver_jokers=("Jolly Joker", "Sly Joker"),
        gold_planets=("Mercury",),
    )


def _two_pair_tree_definitions():
    """Return the frozen Two Pair branch with a true Core fallback.

    The parent owns broad evidence that specifically indicates Two Pair. The Core
    leaf intentionally owns no direct evidence and becomes actionable only by
    inheriting that parent foundation. Spare Trousers is placed on the specialized
    child immediately because its mechanic explicitly scales on Two Pair; Square
    Joker's conditional relationship is audited in the next leaf slice.
    """

    return {
        "two_pair": _strategy(
            "two_pair",
            "Two Pair",
            "TWO_PAIR",
            silver_jokers=("Mad Joker", "Clever Joker"),
            gold_planets=("Uranus",),
        ),
        "two_pair_core": _strategy(
            "two_pair_core",
            "Core Two Pair",
        ),
        "two_pair_trousers_square": _strategy(
            "two_pair_trousers_square",
            "Spare Trousers + Square Joker Two Pair",
            gold_jokers=("Spare Trousers",),
        ),
    }


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
_tree_definitions.pop("high_card", None)
_tree_definitions.pop("two_pair", None)
_tree_definitions[_PAIR_STRATEGY_ID] = _pair_tree_definition()
_tree_definitions.update(_high_card_tree_definitions())
_tree_definitions.update(_two_pair_tree_definitions())

TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(_tree_definitions)


_runtime_nodes = [
    StrategyNodeSpec("high_card", "High Card"),
    StrategyNodeSpec(
        "high_card_core",
        "Core Repetition / Level High Card",
        parent_strategy_id="high_card",
        is_fallback_leaf=True,
    ),
    StrategyNodeSpec(
        "high_card_stuntman",
        "Stuntman / Small-Hand High Card",
        parent_strategy_id="high_card",
    ),
    StrategyNodeSpec(
        "high_card_baron_mime",
        "Baron-Mime Steel-King High Card",
        parent_strategy_id="high_card",
    ),
    StrategyNodeSpec("two_pair", "Two Pair"),
    StrategyNodeSpec(
        "two_pair_core",
        "Core Two Pair",
        parent_strategy_id="two_pair",
        is_fallback_leaf=True,
    ),
    StrategyNodeSpec(
        "two_pair_trousers_square",
        "Spare Trousers + Square Joker Two Pair",
        parent_strategy_id="two_pair",
    ),
]
_runtime_nodes.extend(
    StrategyNodeSpec(strategy_id, definition.name)
    for strategy_id, definition in TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES.items()
    if strategy_id not in _HIGH_CARD_TREE_IDS
    and strategy_id not in _TWO_PAIR_TREE_IDS
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
