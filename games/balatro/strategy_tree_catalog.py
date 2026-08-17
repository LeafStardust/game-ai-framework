from __future__ import annotations

from types import MappingProxyType

from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES, _strategy
from games.balatro.strategy_topology import StrategyNodeSpec, StrategyTopology


SECTION_ONE_ROOT_IDS = frozenset(
    {
        "high_card",
        "pair",
        "two_pair",
        "three_kind",
        "straight",
        "flush",
        "full_house",
        "four_kind",
        "straight_flush",
        "five_kind",
        "flush_house",
        "flush_five",
    }
)
SECTION_ONE_NODE_IDS = frozenset(
    {
        *SECTION_ONE_ROOT_IDS,
        "high_card_stuntman",
        "high_card_baron_mime",
    }
)


def _section_one_definitions():
    """Return the frozen poker-hand strategy catalogue.

    These definitions mirror section 1 of ``BALATRO_STRATEGY_RELATIONSHIPS.md``.
    High Card is the only indexed branch: its parent owns generic evidence and its
    children own only differentiating evidence. Every other poker hand is a
    standalone strategy leaf.
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
            silver_consumables=("The Chariot",),
            directed_tarots=("The Chariot",),
            gold_planets=("Pluto",),
            preferred_enhancements=("Steel",),
        ),
        "high_card_stuntman": _strategy(
            "high_card_stuntman",
            "Stuntman / Small-Hand High Card",
            gold_jokers=("Stuntman",),
        ),
        "high_card_baron_mime": _strategy(
            "high_card_baron_mime",
            "Baron-Mime Steel-King High Card",
            gold_jokers=("Baron", "Mime"),
            silver_jokers=(
                "Blackboard",
                "Shoot the Moon",
                "Troubadour",
                "Juggler",
            ),
            bronze_jokers=("Raised Fist", "Reserved Parking"),
            banned_jokers=("Stuntman",),
        ),
        "pair": _strategy(
            "pair",
            "Pair",
            "PAIR",
            gold_jokers=("The Duo",),
            silver_jokers=("Jolly Joker", "Sly Joker", "Half Joker"),
            gold_planets=("Mercury",),
        ),
        "two_pair": _strategy(
            "two_pair",
            "Two Pair",
            "TWO_PAIR",
            gold_jokers=("Spare Trousers",),
            silver_jokers=("Mad Joker", "Clever Joker", "Square Joker", "The Duo"),
            bronze_jokers=("Jolly Joker", "Sly Joker"),
            silver_consumables=("Death", "Strength"),
            directed_tarots=("Death", "Strength"),
            gold_planets=("Uranus",),
        ),
        "three_kind": _strategy(
            "three_kind",
            "Three of a Kind",
            "THREE_OF_A_KIND",
            gold_jokers=("The Trio",),
            silver_jokers=("Zany Joker", "Wily Joker", "DNA", "Half Joker", "The Duo"),
            bronze_jokers=("Jolly Joker", "Sly Joker", "Trading Card"),
            silver_consumables=("Death", "Strength", "Cryptid", "Ouija"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid", "Ouija"),
            gold_planets=("Venus",),
        ),
        "straight": _strategy(
            "straight",
            "Straight",
            "STRAIGHT",
            gold_jokers=("The Order", "Shortcut", "Four Fingers", "Runner", "Superposition"),
            silver_jokers=("Crazy Joker", "Devious Joker"),
            silver_consumables=("Strength", "Death"),
            directed_tarots=("Strength", "Death"),
            gold_planets=("Saturn",),
        ),
        "flush": _strategy(
            "flush",
            "Flush",
            "FLUSH",
            gold_jokers=("The Tribe",),
            silver_jokers=("Droll Joker", "Crafty Joker", "Smeared Joker", "Four Fingers"),
            silver_consumables=("The Lovers", "Sigil"),
            directed_tarots=("The Lovers",),
            directed_spectrals=("Sigil",),
            gold_planets=("Jupiter",),
            preferred_enhancements=("Wild",),
            any_suit_concentration=True,
        ),
        "full_house": _strategy(
            "full_house",
            "Full House",
            "FULL_HOUSE",
            silver_jokers=(
                "The Trio", "The Duo", "Spare Trousers", "Zany Joker",
                "Wily Joker", "Mad Joker", "Clever Joker",
            ),
            bronze_jokers=("Jolly Joker", "Sly Joker", "DNA", "Trading Card"),
            silver_consumables=("Death", "Strength", "Cryptid", "Ouija"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid", "Ouija"),
            gold_planets=("Earth",),
            minimum_positive_jokers=2,
        ),
        "four_kind": _strategy(
            "four_kind",
            "Four of a Kind",
            "FOUR_OF_A_KIND",
            gold_jokers=("The Family",),
            silver_jokers=("The Trio", "DNA", "Zany Joker", "Wily Joker", "Square Joker"),
            bronze_jokers=("The Duo", "Jolly Joker", "Sly Joker", "Trading Card"),
            silver_consumables=("Death", "Strength", "Cryptid", "Ouija"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid", "Ouija"),
            gold_planets=("Mars",),
        ),
        "straight_flush": _strategy(
            "straight_flush",
            "Straight Flush",
            "STRAIGHT_FLUSH",
            gold_jokers=(
                "The Order", "The Tribe", "Shortcut", "Four Fingers", "Runner",
                "Smeared Joker", "Seance",
            ),
            silver_jokers=("Crazy Joker", "Devious Joker", "Droll Joker", "Crafty Joker"),
            silver_consumables=("Strength", "Death", "The Lovers", "Sigil"),
            directed_tarots=("Strength", "Death", "The Lovers"),
            directed_spectrals=("Sigil",),
            gold_planets=("Neptune",),
            preferred_enhancements=("Wild",),
            any_suit_concentration=True,
            minimum_positive_jokers=2,
        ),
        "five_kind": _strategy(
            "five_kind",
            "Five of a Kind",
            "FIVE_OF_A_KIND",
            gold_jokers=("The Family",),
            silver_jokers=("The Trio", "DNA", "The Idol", "Zany Joker", "Wily Joker"),
            bronze_jokers=("The Duo", "Jolly Joker", "Sly Joker", "Trading Card"),
            silver_consumables=("Death", "Strength", "Cryptid", "Ouija"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid", "Ouija"),
            gold_planets=("Planet X",),
            minimum_positive_jokers=2,
        ),
        "flush_house": _strategy(
            "flush_house",
            "Flush House",
            "FLUSH_HOUSE",
            gold_jokers=("The Tribe",),
            silver_jokers=(
                "The Trio", "The Duo", "Spare Trousers", "Zany Joker", "Wily Joker",
                "Mad Joker", "Clever Joker", "Smeared Joker", "Droll Joker", "Crafty Joker",
            ),
            bronze_jokers=("Jolly Joker", "Sly Joker", "DNA", "Trading Card"),
            silver_consumables=("Death", "Strength", "The Lovers", "Cryptid", "Ouija", "Sigil"),
            directed_tarots=("Death", "Strength", "The Lovers"),
            directed_spectrals=("Cryptid", "Ouija", "Sigil"),
            gold_planets=("Ceres",),
            preferred_enhancements=("Wild",),
            any_suit_concentration=True,
            minimum_positive_jokers=2,
        ),
        "flush_five": _strategy(
            "flush_five",
            "Flush Five",
            "FLUSH_FIVE",
            gold_jokers=("The Family", "DNA", "The Idol", "The Tribe"),
            silver_jokers=("The Trio", "Zany Joker", "Wily Joker", "Smeared Joker", "Droll Joker", "Crafty Joker"),
            bronze_jokers=("The Duo", "Jolly Joker", "Sly Joker", "Trading Card"),
            silver_consumables=("Death", "Strength", "The Lovers", "Cryptid", "Ouija", "Sigil"),
            directed_tarots=("Death", "Strength", "The Lovers"),
            directed_spectrals=("Cryptid", "Ouija", "Sigil"),
            gold_planets=("Eris",),
            preferred_enhancements=("Wild",),
            any_suit_concentration=True,
            minimum_positive_jokers=2,
        ),
    }


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
for _strategy_id in SECTION_ONE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
_tree_definitions.update(_section_one_definitions())

TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES = MappingProxyType(_tree_definitions)


_runtime_nodes = [
    StrategyNodeSpec("high_card", "High Card"),
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
    if strategy_id not in {"high_card", "high_card_stuntman", "high_card_baron_mime"}
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
