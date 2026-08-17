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
        "ten_four",
        "sixes",
        "jacks_hit_road",
        "queens_shoot_moon",
        "face_cards",
        "faceless",
        "idol_exact",
    }
)

SECTION_THREE_ROOT_IDS = frozenset(
    {
        "hearts",
        "diamonds",
        "clubs",
        "spades",
        "blackboard",
        "raised_fist",
        "ancient_suit_rotation",
        "flower_pot",
    }
)
SECTION_THREE_NODE_IDS = frozenset(
    {
        *SECTION_THREE_ROOT_IDS,
        "hearts_bloodstone_oops",
        "hearts_bloodstone_retrigger",
        "clubs_onyx",
        "clubs_seeing_double",
        "flower_pot_splash",
        "flower_pot_smeared",
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
        "ten_four": _strategy(
            "ten_four",
            "Ten-Four / Walkie Talkie",
            gold_jokers=("Walkie Talkie",),
            silver_consumables=("Death", "Strength", "The Hanged Man", "Cryptid"),
            directed_tarots=("Death", "Strength", "The Hanged Man"),
            directed_spectrals=("Cryptid",),
            preferred_ranks=("10", "4"),
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


def _section_three_definitions():
    """Return the audited suit and held-card strategy catalogue.

    One-child upgrade ladders are collapsed. Clubs remains indexed because Onyx
    rewards scoring many Clubs while Seeing Double requires a Club plus another
    suit. Flower Pot's Splash and Smeared routes remain peers; owning both activates
    both leaves instead of manufacturing a redundant combination node.
    """

    return {
        "hearts": _strategy(
            "hearts",
            "Hearts",
            gold_jokers=("Bloodstone",),
            silver_jokers=("Lusty Joker",),
            gold_consumables=("The Sun",),
            silver_consumables=("Death", "The Hanged Man", "Sigil"),
            directed_tarots=("The Sun", "Death", "The Hanged Man"),
            directed_spectrals=("Sigil",),
            preferred_suits=("Hearts",),
            preferred_enhancements=("Wild",),
        ),
        "hearts_bloodstone_oops": _strategy(
            "hearts_bloodstone_oops",
            "Bloodstone + Oops! All 6s Hearts",
        ),
        "hearts_bloodstone_retrigger": _strategy(
            "hearts_bloodstone_retrigger",
            "Bloodstone Retrigger Hearts",
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "diamonds": _strategy(
            "diamonds",
            "Diamonds / Rough Gem Economy",
            gold_jokers=("Rough Gem",),
            silver_jokers=("Greedy Joker",),
            gold_consumables=("The Star",),
            silver_consumables=("Death", "The Hanged Man", "Sigil"),
            directed_tarots=("The Star", "Death", "The Hanged Man"),
            directed_spectrals=("Sigil",),
            preferred_suits=("Diamonds",),
            preferred_enhancements=("Wild",),
        ),
        "clubs": _strategy(
            "clubs",
            "Clubs",
            silver_jokers=("Gluttonous Joker",),
            gold_consumables=("The Moon",),
            silver_consumables=("Death", "The Hanged Man", "Sigil"),
            directed_tarots=("The Moon", "Death", "The Hanged Man"),
            directed_spectrals=("Sigil",),
            preferred_suits=("Clubs",),
            preferred_enhancements=("Wild",),
        ),
        "clubs_onyx": _strategy(
            "clubs_onyx",
            "Onyx Agate Club Scoring",
            gold_jokers=("Onyx Agate",),
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "clubs_seeing_double": _strategy(
            "clubs_seeing_double",
            "Seeing Double Mixed-Suit Clubs",
            gold_jokers=("Seeing Double",),
            silver_consumables=("The Lovers",),
            directed_tarots=("The Lovers",),
        ),
        "spades": _strategy(
            "spades",
            "Spades / Arrowhead Chips",
            gold_jokers=("Arrowhead",),
            silver_jokers=("Wrathful Joker",),
            gold_consumables=("The World",),
            silver_consumables=("Death", "The Hanged Man", "Sigil"),
            directed_tarots=("The World", "Death", "The Hanged Man"),
            directed_spectrals=("Sigil",),
            preferred_suits=("Spades",),
            preferred_enhancements=("Wild",),
        ),
        "blackboard": _strategy(
            "blackboard",
            "Blackboard Held-Black Cards",
            gold_jokers=("Blackboard",),
            gold_consumables=("The Moon", "The World"),
            directed_tarots=("The Moon", "The World"),
            preferred_suits=("Clubs", "Spades"),
            preferred_enhancements=("Wild",),
        ),
        "raised_fist": _strategy(
            "raised_fist",
            "Raised Fist Held-Minimum",
            gold_jokers=("Raised Fist",),
            silver_consumables=(
                "Strength", "Death", "The Hanged Man", "Familiar", "Grim",
                "Cryptid", "Deja Vu",
            ),
            directed_tarots=("Strength", "Death", "The Hanged Man"),
            directed_spectrals=("Familiar", "Grim", "Cryptid", "Deja Vu"),
        ),
        "ancient_suit_rotation": _strategy(
            "ancient_suit_rotation",
            "Ancient Joker Suit-Rotation",
            gold_jokers=("Ancient Joker",),
            silver_consumables=(
                "The Star", "The Moon", "The Sun", "The World", "Sigil",
                "Deja Vu",
            ),
            directed_tarots=("The Star", "The Moon", "The Sun", "The World"),
            directed_spectrals=("Sigil", "Deja Vu"),
            preferred_enhancements=("Wild",),
        ),
        "flower_pot": _strategy(
            "flower_pot",
            "Flower Pot Multi-Suit",
            gold_jokers=("Flower Pot",),
            silver_consumables=(
                "The Star", "The Moon", "The Sun", "The World", "Sigil",
            ),
            directed_tarots=("The Star", "The Moon", "The Sun", "The World"),
            directed_spectrals=("Sigil",),
            preferred_enhancements=("Wild",),
        ),
        "flower_pot_splash": _strategy(
            "flower_pot_splash",
            "Splash + Flower Pot",
        ),
        "flower_pot_smeared": _strategy(
            "flower_pot_smeared",
            "Smeared Joker + Flower Pot",
        ),
    }


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
for _strategy_id in SECTION_ONE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_TWO_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_THREE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
_tree_definitions.update(_section_one_definitions())
_tree_definitions.update(_section_two_definitions())
_tree_definitions.update(_section_three_definitions())

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
    StrategyNodeSpec("hearts", "Hearts"),
    StrategyNodeSpec(
        "hearts_bloodstone_oops",
        "Bloodstone + Oops! All 6s Hearts",
        parent_strategy_id="hearts",
    ),
    StrategyNodeSpec(
        "hearts_bloodstone_retrigger",
        "Bloodstone Retrigger Hearts",
        parent_strategy_id="hearts",
    ),
    StrategyNodeSpec("clubs", "Clubs"),
    StrategyNodeSpec(
        "clubs_onyx",
        "Onyx Agate Club Scoring",
        parent_strategy_id="clubs",
    ),
    StrategyNodeSpec(
        "clubs_seeing_double",
        "Seeing Double Mixed-Suit Clubs",
        parent_strategy_id="clubs",
    ),
    StrategyNodeSpec("flower_pot", "Flower Pot Multi-Suit"),
    StrategyNodeSpec(
        "flower_pot_splash",
        "Splash + Flower Pot",
        parent_strategy_id="flower_pot",
    ),
    StrategyNodeSpec(
        "flower_pot_smeared",
        "Smeared Joker + Flower Pot",
        parent_strategy_id="flower_pot",
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
        "hearts",
        "hearts_bloodstone_oops",
        "hearts_bloodstone_retrigger",
        "clubs",
        "clubs_onyx",
        "clubs_seeing_double",
        "flower_pot",
        "flower_pot_splash",
        "flower_pot_smeared",
    }
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
