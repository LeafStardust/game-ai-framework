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


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
_tree_definitions.pop("high_card", None)
_tree_definitions.update(_high_card_tree_definitions())

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
]
_runtime_nodes.extend(
    StrategyNodeSpec(strategy_id, definition.name)
    for strategy_id, definition in TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES.items()
    if strategy_id not in _HIGH_CARD_TREE_IDS
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
