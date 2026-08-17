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

SECTION_TWO_ROOT_IDS = frozenset(
    {
        "aces",
        "low_rank",
        "twos",
        "sixes",
        "jacks_hit_road",
        "queens_shoot_moon",
        "face_cards",
        "faceless",
        "idol_exact",
    }
)
SECTION_TWO_NODE_IDS = frozenset(
    {
        *SECTION_TWO_ROOT_IDS,
        "face_photochad",
        "face_triboulet_sock",
        "face_pareidolia",
        "face_held_economy",
        "face_business_card",
        "faceless_ride_bus",
        "faceless_discard_economy",
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


def _section_two_definitions():
    """Return the frozen rank and face-card strategy catalogue.

    Upgrade stacks are collapsed into their owning strategy: DNA amplifies Aces,
    Hack amplifies Low-Rank/Twos, and neither creates a distinct decision policy.
    Face Cards and Faceless retain indexed children because those routes prescribe
    materially different scoring or economy behaviour.
    """

    return {
        "aces": _strategy(
            "aces",
            "Aces",
            gold_jokers=("Scholar",),
            silver_consumables=("Death", "Strength", "The Hanged Man", "Grim", "Cryptid"),
            directed_tarots=("Death", "Strength", "The Hanged Man"),
            directed_spectrals=("Grim", "Cryptid"),
            preferred_ranks=("A",),
        ),
        "low_rank": _strategy(
            "low_rank",
            "Low-Rank Scoring",
            gold_jokers=("Fibonacci", "Hack"),
            silver_jokers=("Odd Todd", "Even Steven"),
            bronze_jokers=("Walkie Talkie",),
            silver_consumables=("Death", "Strength", "The Hanged Man", "Incantation", "Cryptid"),
            directed_tarots=("Death", "Strength", "The Hanged Man"),
            directed_spectrals=("Incantation", "Cryptid"),
            preferred_ranks=("2", "3", "4", "5"),
        ),
        "twos": _strategy(
            "twos",
            "Twos / Wee-Hack",
            gold_jokers=("Wee Joker",),
            silver_consumables=("Death", "Strength", "The Hanged Man", "Cryptid"),
            directed_tarots=("Death", "Strength", "The Hanged Man"),
            directed_spectrals=("Cryptid",),
            preferred_ranks=("2",),
        ),
        "sixes": _strategy(
            "sixes",
            "Sixes / Sixth Sense",
            gold_jokers=("Sixth Sense",),
            silver_consumables=("Death", "Strength"),
            directed_tarots=("Death", "Strength"),
            preferred_ranks=("6",),
        ),
        "jacks_hit_road": _strategy(
            "jacks_hit_road",
            "Jacks / Hit the Road",
            gold_jokers=("Hit the Road",),
            silver_consumables=("Death", "Strength", "Cryptid"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid",),
            preferred_ranks=("J",),
        ),
        "queens_shoot_moon": _strategy(
            "queens_shoot_moon",
            "Queens / Shoot the Moon",
            gold_jokers=("Shoot the Moon",),
            silver_consumables=("Death", "Strength", "Cryptid"),
            directed_tarots=("Death", "Strength"),
            directed_spectrals=("Cryptid",),
            preferred_ranks=("Q",),
        ),
        "face_cards": _strategy(
            "face_cards",
            "Face Cards",
            silver_jokers=("Scary Face", "Smiley Face", "Midas Mask"),
            banned_jokers=("Ride the Bus",),
            silver_consumables=("Death", "Strength", "The Hanged Man", "Familiar"),
            directed_tarots=("Death", "Strength", "The Hanged Man"),
            directed_spectrals=("Familiar",),
            face_mode="FACE",
        ),
        "face_photochad": _strategy(
            "face_photochad",
            "Photograph + Hanging Chad (PhotoChad)",
            gold_jokers=("Photograph",),
            silver_consumables=("Justice", "Deja Vu", "Cryptid"),
            directed_tarots=("Justice",),
            directed_spectrals=("Deja Vu", "Cryptid"),
        ),
        "face_triboulet_sock": _strategy(
            "face_triboulet_sock",
            "Triboulet + Sock and Buskin",
            gold_jokers=("Triboulet",),
            silver_consumables=("Justice", "Deja Vu", "Cryptid"),
            directed_tarots=("Justice",),
            directed_spectrals=("Deja Vu", "Cryptid"),
            preferred_ranks=("Q", "K"),
        ),
        "face_pareidolia": _strategy(
            "face_pareidolia",
            "Pareidolia Universal Face Scoring",
        ),
        "face_held_economy": _strategy(
            "face_held_economy",
            "Held Face-Card Economy",
            gold_jokers=("Reserved Parking",),
            silver_consumables=("The Devil",),
            directed_tarots=("The Devil",),
        ),
        "face_business_card": _strategy(
            "face_business_card",
            "Business Card Face Economy",
            gold_jokers=("Business Card",),
        ),
        "faceless": _strategy(
            "faceless",
            "Faceless / No-Face",
            silver_consumables=("The Hanged Man", "Death", "Incantation", "Grim"),
            directed_tarots=("The Hanged Man", "Death"),
            directed_spectrals=("Incantation", "Grim"),
            face_mode="NO_FACE",
        ),
        "faceless_ride_bus": _strategy(
            "faceless_ride_bus",
            "Ride the Bus No-Face Scaling",
            gold_jokers=("Ride the Bus",),
            banned_jokers=(
                "Pareidolia", "Splash", "Photograph", "Sock and Buskin",
                "Triboulet", "Scary Face", "Smiley Face", "Business Card",
                "Midas Mask",
            ),
            banned_consumables=("Familiar",),
        ),
        "faceless_discard_economy": _strategy(
            "faceless_discard_economy",
            "Faceless Joker Discard Economy",
            gold_jokers=("Faceless Joker",),
            silver_consumables=("Familiar",),
            directed_spectrals=("Familiar",),
        ),
        "idol_exact": _strategy(
            "idol_exact",
            "The Idol Exact-Card Concentration",
            silver_consumables=("Death", "The Hanged Man", "Cryptid"),
            directed_tarots=("Death", "The Hanged Man"),
            directed_spectrals=("Cryptid",),
        ),
    }


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
for _strategy_id in SECTION_ONE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_TWO_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
_tree_definitions.update(_section_one_definitions())
_tree_definitions.update(_section_two_definitions())

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
    StrategyNodeSpec("face_cards", "Face Cards"),
    StrategyNodeSpec(
        "face_photochad",
        "Photograph + Hanging Chad (PhotoChad)",
        parent_strategy_id="face_cards",
    ),
    StrategyNodeSpec(
        "face_triboulet_sock",
        "Triboulet + Sock and Buskin",
        parent_strategy_id="face_cards",
    ),
    StrategyNodeSpec(
        "face_pareidolia",
        "Pareidolia Universal Face Scoring",
        parent_strategy_id="face_cards",
    ),
    StrategyNodeSpec(
        "face_held_economy",
        "Held Face-Card Economy",
        parent_strategy_id="face_cards",
    ),
    StrategyNodeSpec(
        "face_business_card",
        "Business Card Face Economy",
        parent_strategy_id="face_cards",
    ),
    StrategyNodeSpec("faceless", "Faceless / No-Face"),
    StrategyNodeSpec(
        "faceless_ride_bus",
        "Ride the Bus No-Face Scaling",
        parent_strategy_id="faceless",
    ),
    StrategyNodeSpec(
        "faceless_discard_economy",
        "Faceless Joker Discard Economy",
        parent_strategy_id="faceless",
    ),
]
_runtime_nodes.extend(
    StrategyNodeSpec(strategy_id, definition.name)
    for strategy_id, definition in TREE_MIGRATED_UNIVERSAL_BALATRO_STRATEGIES.items()
    if strategy_id
    not in {
        "high_card",
        "high_card_stuntman",
        "high_card_baron_mime",
        "face_cards",
        "face_photochad",
        "face_triboulet_sock",
        "face_pareidolia",
        "face_held_economy",
        "face_business_card",
        "faceless",
        "faceless_ride_bus",
        "faceless_discard_economy",
    }
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
