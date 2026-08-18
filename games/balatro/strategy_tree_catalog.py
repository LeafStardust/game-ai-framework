from __future__ import annotations

from types import MappingProxyType

from games.balatro.strategy_catalog import UNIVERSAL_BALATRO_STRATEGIES, _strategy
from games.balatro.strategy_topology import StrategyNodeSpec, StrategyTopology


ALL_TAROT_NAMES = (
    "The Fool", "The Magician", "The High Priestess", "The Empress",
    "The Emperor", "The Hierophant", "The Lovers", "The Chariot", "Justice",
    "The Hermit", "The Wheel of Fortune", "Strength", "The Hanged Man", "Death",
    "Temperance", "The Devil", "The Tower", "The Star", "The Moon", "The Sun",
    "Judgement", "The World",
)
ALL_PLANET_NAMES = (
    "Mercury", "Venus", "Earth", "Mars", "Jupiter", "Saturn", "Uranus",
    "Neptune", "Pluto", "Planet X", "Ceres", "Eris",
)


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
SECTION_FOUR_ROOT_IDS = frozenset(
    {
        "stone",
        "glass",
        "steel",
        "lucky",
        "gold_cards",
    }
)
SECTION_FOUR_NODE_IDS = frozenset(
    {
        *SECTION_FOUR_ROOT_IDS,
        "stone_marble_scaling",
        "stone_marble_vampire",
        "stone_dna_duplication",
        "stone_high_card",
        "glass_breakage",
        "glass_retrigger",
        "steel_density",
        "steel_mime",
        "lucky_cat",
        "lucky_cat_oops",
        "lucky_retrigger",
        "gold_cards_held_mime",
        "gold_cards_ticket",
        "gold_cards_midas",
        "gold_cards_midas_ticket",
    }
)
SECTION_FIVE_ROOT_IDS = frozenset(
    {
        "red_seal",
        "blue_seal",
        "purple_seal",
        "gold_seal",
    }
)
SECTION_FIVE_NODE_IDS = frozenset(
    {
        *SECTION_FIVE_ROOT_IDS,
        "red_seal_played",
        "red_seal_held",
    }
)
SECTION_SIX_ROOT_IDS = frozenset(
    {
        "canio_destruction",
        "vampire",
        "dagger_sacrifice",
        "madness",
        "deck_thinning",
    }
)
SECTION_SIX_NODE_IDS = frozenset(
    {
        *SECTION_SIX_ROOT_IDS,
        "canio_trading",
        "canio_pareidolia",
        "canio_glass",
        "canio_consumable",
        "vampire_midas",
        "vampire_pareidolia_midas",
        "madness_solo",
        "madness_eternal",
        "thinning_trading",
        "thinning_erosion",
        "thinning_trading_erosion",
    }
)
SECTION_SEVEN_ROOT_IDS = frozenset(
    {
        "hologram_growth",
        "hiker_training",
        "drivers_license",
        "blue_joker_deck",
    }
)
SECTION_SEVEN_NODE_IDS = frozenset(
    {
        *SECTION_SEVEN_ROOT_IDS,
        "hologram_dna",
        "hologram_certificate",
        "hologram_marble",
    }
)
SECTION_EIGHT_ROOT_IDS = frozenset(
    {
        "planet_engine",
        "perkeo",
        "tarot_engine",
        "vagabond",
    }
)
SECTION_EIGHT_NODE_IDS = frozenset(
    {
        *SECTION_EIGHT_ROOT_IDS,
        "planet_constellation",
        "planet_satellite",
        "planet_constellation_satellite",
        "perkeo_observatory",
        "perkeo_cryptid",
        "perkeo_tarot_spectral",
        "tarot_cartomancer",
        "tarot_hallucination",
        "tarot_eight_ball",
    }
)
SECTION_NINE_ROOT_IDS = frozenset(
    {
        "cash_hoard",
        "campfire",
        "flash_card",
        "red_card",
        "throwback",
    }
)
SECTION_NINE_NODE_IDS = frozenset(
    {
        *SECTION_NINE_ROOT_IDS,
        "cash_growth",
        "cash_bull",
        "cash_bootstraps",
        "cash_bull_bootstraps",
        "cash_cloud_nine",
    }
)
SECTION_TEN_ROOT_IDS = frozenset(
    {
        "joker_stencil",
        "baseball_card",
        "abstract_joker",
        "swashbuckler",
    }
)
SECTION_TEN_NODE_IDS = SECTION_TEN_ROOT_IDS
SECTION_ELEVEN_ROOT_IDS = frozenset(
    {
        "discard_utilization",
        "no_discard",
        "obelisk_rotation",
        "burnt_joker_engine",
    }
)
SECTION_ELEVEN_NODE_IDS = frozenset(
    {
        *SECTION_ELEVEN_ROOT_IDS,
        "discard_castle",
        "discard_mail_rebate",
        "discard_yorick",
        "no_discard_green",
        "no_discard_reserve",
        "no_discard_ramen",
        "no_discard_burglar",
    }
)
SECTION_TWELVE_ROOT_IDS = frozenset({"last_hand_burst", "loyalty_cycle"})
SECTION_TWELVE_NODE_IDS = frozenset(
    {
        *SECTION_TWELVE_ROOT_IDS,
        "last_hand_acrobat",
        "last_hand_dusk",
    }
)
REMAINING_SECTION_ROOT_IDS = frozenset(
    {
        *SECTION_FIVE_ROOT_IDS,
        *SECTION_SIX_ROOT_IDS,
        *SECTION_SEVEN_ROOT_IDS,
        *SECTION_EIGHT_ROOT_IDS,
        *SECTION_NINE_ROOT_IDS,
        *SECTION_TEN_ROOT_IDS,
        *SECTION_ELEVEN_ROOT_IDS,
        *SECTION_TWELVE_ROOT_IDS,
    }
)
REMAINING_SECTION_NODE_IDS = frozenset(
    {
        *SECTION_FIVE_NODE_IDS,
        *SECTION_SIX_NODE_IDS,
        *SECTION_SEVEN_NODE_IDS,
        *SECTION_EIGHT_NODE_IDS,
        *SECTION_NINE_NODE_IDS,
        *SECTION_TEN_NODE_IDS,
        *SECTION_ELEVEN_NODE_IDS,
        *SECTION_TWELVE_NODE_IDS,
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


def _section_four_definitions():
    """Return enhancement strategy parents and mechanically distinct leaves.

    Parents own enhancement creation and broad preservation semantics. Leaves own
    only their defining payoff or route-specific support; conditional runtime
    relationships prevent a generic retrigger/Mime/economy Joker from seeding an
    enhancement route before matching cards or the defining payoff exist.
    """

    return {
        "stone": _strategy(
            "stone",
            "Stone",
            gold_consumables=("The Tower",),
            silver_consumables=("Death", "Cryptid"),
            directed_tarots=("The Tower", "Death"),
            directed_spectrals=("Cryptid",),
            preferred_enhancements=("Stone",),
        ),
        "stone_marble_scaling": _strategy(
            "stone_marble_scaling",
            "Marble Joker + Stone Joker Scaling",
            gold_jokers=("Marble Joker",),
        ),
        "stone_marble_vampire": _strategy(
            "stone_marble_vampire",
            "Marble Joker + Vampire Stone Feed",
            gold_jokers=("Marble Joker",),
        ),
        "stone_dna_duplication": _strategy(
            "stone_dna_duplication",
            "DNA + Stone Joker Duplication",
        ),
        "stone_high_card": _strategy(
            "stone_high_card",
            "Stone High Card",
            "HIGH_CARD",
            gold_planets=("Pluto",),
        ),
        "glass": _strategy(
            "glass",
            "Glass",
            banned_jokers=("Vampire", "Midas Mask"),
            gold_consumables=("Justice",),
            silver_consumables=("Death", "Cryptid", "Ankh"),
            directed_tarots=("Justice", "Death"),
            directed_spectrals=("Cryptid", "Ankh"),
            preferred_enhancements=("Glass",),
        ),
        "glass_breakage": _strategy(
            "glass_breakage",
            "Glass Joker Breakage Scaling",
            gold_jokers=("Glass Joker",),
        ),
        "glass_retrigger": _strategy(
            "glass_retrigger",
            "Glass Retrigger Scoring",
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "steel": _strategy(
            "steel",
            "Steel",
            banned_jokers=("Vampire", "Midas Mask"),
            gold_consumables=("The Chariot",),
            silver_consumables=("Death", "Cryptid", "Trance"),
            directed_tarots=("The Chariot", "Death"),
            directed_spectrals=("Cryptid", "Trance"),
            preferred_enhancements=("Steel",),
        ),
        "steel_density": _strategy(
            "steel_density",
            "Steel Joker Density Scaling",
            gold_jokers=("Steel Joker",),
        ),
        "steel_mime": _strategy(
            "steel_mime",
            "Mime Steel Retrigger",
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "lucky": _strategy(
            "lucky",
            "Lucky",
            banned_jokers=("Vampire", "Midas Mask"),
            gold_consumables=("The Magician",),
            silver_consumables=("Death", "Cryptid"),
            directed_tarots=("The Magician", "Death"),
            directed_spectrals=("Cryptid",),
            preferred_enhancements=("Lucky",),
        ),
        "lucky_cat": _strategy(
            "lucky_cat",
            "Lucky Cat Scaling",
            gold_jokers=("Lucky Cat",),
        ),
        "lucky_cat_oops": _strategy(
            "lucky_cat_oops",
            "Lucky Cat + Oops! All 6s",
        ),
        "lucky_retrigger": _strategy(
            "lucky_retrigger",
            "Lucky Retrigger",
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "gold_cards": _strategy(
            "gold_cards",
            "Gold Cards",
            banned_jokers=("Vampire",),
            gold_consumables=("The Devil",),
            silver_consumables=("Death", "Cryptid", "Talisman"),
            directed_tarots=("The Devil", "Death"),
            directed_spectrals=("Cryptid", "Talisman"),
            preferred_enhancements=("Gold",),
        ),
        "gold_cards_held_mime": _strategy(
            "gold_cards_held_mime",
            "Held Gold + Mime Economy",
            silver_consumables=("Deja Vu",),
            directed_spectrals=("Deja Vu",),
        ),
        "gold_cards_ticket": _strategy(
            "gold_cards_ticket",
            "Golden Ticket Gold Scoring",
            gold_jokers=("Golden Ticket",),
        ),
        "gold_cards_midas": _strategy(
            "gold_cards_midas",
            "Midas Mask Gold Generation",
            gold_jokers=("Midas Mask",),
        ),
        "gold_cards_midas_ticket": _strategy(
            "gold_cards_midas_ticket",
            "Midas Mask + Golden Ticket Economy",
        ),
    }


def _remaining_section_definitions():
    """Return topology-owned catalogue definitions for frozen Sections 5–12.

    Parents own shared mechanics and transformation tools.  Children own only
    unconditional defining cores; context-dependent combo/support tiers are kept
    in ``strategy_conditional_relationships`` so an off-route Joker cannot seed a
    strategy merely by being generally useful.
    """

    return {
        # Section 5: seals.
        "red_seal": _strategy(
            "red_seal",
            "Red Seal",
            gold_consumables=("Deja Vu",),
            silver_consumables=("Death", "Cryptid"),
            directed_spectrals=("Deja Vu", "Cryptid"),
            preferred_seals=("Red",),
        ),
        "red_seal_played": _strategy(
            "red_seal_played",
            "Played Red-Seal Retrigger",
        ),
        "red_seal_held": _strategy(
            "red_seal_held",
            "Held Red-Seal Retrigger",
        ),
        "blue_seal": _strategy(
            "blue_seal",
            "Blue Seal Hand-Level Scaling",
            gold_consumables=("Trance",),
            silver_consumables=("Death", "Cryptid"),
            directed_spectrals=("Trance", "Cryptid"),
            preferred_seals=("Blue",),
        ),
        "purple_seal": _strategy(
            "purple_seal",
            "Purple Seal Tarot Engine",
            banned_jokers=(
                "Burglar",
                "Delayed Gratification",
                "Green Joker",
                "Ramen",
                "Banner",
            ),
            gold_consumables=("Medium",),
            silver_consumables=("Death", "Cryptid"),
            directed_spectrals=("Medium", "Cryptid"),
            preferred_seals=("Purple",),
        ),
        "gold_seal": _strategy(
            "gold_seal",
            "Gold-Seal Retrigger Economy",
            gold_consumables=("Talisman",),
            silver_consumables=("Death", "Cryptid"),
            directed_spectrals=("Talisman", "Cryptid"),
            preferred_seals=("Gold",),
        ),

        # Section 6: destruction, sacrifice, consumption and thinning.
        "canio_destruction": _strategy(
            "canio_destruction",
            "Canio Destruction",
            gold_jokers=("Canio",),
            silver_consumables=("The Hanged Man", "Justice", "Familiar", "Immolate"),
            directed_tarots=("The Hanged Man", "Justice"),
            directed_spectrals=("Familiar", "Immolate"),
        ),
        "canio_trading": _strategy("canio_trading", "Trading Card Canio"),
        "canio_pareidolia": _strategy("canio_pareidolia", "Pareidolia Canio"),
        "canio_glass": _strategy(
            "canio_glass",
            "Glass Canio",
            preferred_enhancements=("Glass",),
        ),
        "canio_consumable": _strategy("canio_consumable", "Consumable Canio"),
        "vampire": _strategy(
            "vampire",
            "Vampire",
            gold_jokers=("Vampire",),
            silver_consumables=(
                "The Magician", "The Empress", "The Hierophant", "The Lovers",
                "The Chariot", "Justice", "The Devil", "The Tower",
                "Familiar", "Grim", "Incantation",
            ),
            directed_tarots=(
                "The Magician", "The Empress", "The Hierophant", "The Lovers",
                "The Chariot", "Justice", "The Devil", "The Tower",
            ),
            directed_spectrals=("Familiar", "Grim", "Incantation"),
        ),
        "vampire_midas": _strategy(
            "vampire_midas",
            "Midas Mask + Vampire",
            preferred_enhancements=("Gold",),
        ),
        "vampire_pareidolia_midas": _strategy(
            "vampire_pareidolia_midas",
            "Pareidolia + Midas Mask + Vampire",
            preferred_enhancements=("Gold",),
        ),
        "dagger_sacrifice": _strategy(
            "dagger_sacrifice",
            "Ceremonial Dagger / Disposable-Joker Feed",
            gold_jokers=("Ceremonial Dagger", "Dagger"),
            silver_jokers=("Riff-Raff", "Egg", "Gift Card"),
            bronze_jokers=("Invisible Joker",),
        ),
        "madness": _strategy("madness", "Madness Destruction", gold_jokers=("Madness",)),
        "madness_solo": _strategy("madness_solo", "Solo Madness"),
        "madness_eternal": _strategy("madness_eternal", "Eternal-Joker Madness"),
        "deck_thinning": _strategy(
            "deck_thinning",
            "Deck Thinning",
            silver_consumables=("The Hanged Man", "Immolate"),
            directed_tarots=("The Hanged Man",),
            directed_spectrals=("Immolate",),
        ),
        "thinning_trading": _strategy(
            "thinning_trading",
            "Trading Card Thinning / Economy",
            gold_jokers=("Trading Card",),
        ),
        "thinning_erosion": _strategy(
            "thinning_erosion",
            "Erosion Thinning",
            gold_jokers=("Erosion",),
        ),
        "thinning_trading_erosion": _strategy(
            "thinning_trading_erosion",
            "Trading Card + Erosion",
        ),

        # Section 7: deck growth and card training.
        "hologram_growth": _strategy(
            "hologram_growth",
            "Hologram Deck-Growth",
            gold_jokers=("Hologram",),
            silver_consumables=("Cryptid", "Familiar", "Grim", "Incantation"),
            directed_spectrals=("Cryptid", "Familiar", "Grim", "Incantation"),
        ),
        "hologram_dna": _strategy(
            "hologram_dna",
            "DNA + Hologram",
        ),
        "hologram_certificate": _strategy("hologram_certificate", "Certificate + Hologram"),
        "hologram_marble": _strategy(
            "hologram_marble",
            "Marble Joker + Hologram",
            gold_consumables=("The Tower",),
            directed_tarots=("The Tower",),
            preferred_enhancements=("Stone",),
        ),
        "hiker_training": _strategy(
            "hiker_training",
            "Hiker Retrigger / Copy Training",
            gold_jokers=("Hiker",),
            silver_consumables=("Cryptid", "Deja Vu"),
            directed_spectrals=("Cryptid", "Deja Vu"),
        ),
        "drivers_license": _strategy(
            "drivers_license",
            "Driver's License Enhancement-Density",
            gold_jokers=("Driver's License",),
            banned_jokers=("Vampire",),
            gold_consumables=(
                "The Magician", "The Empress", "The Hierophant", "The Lovers",
                "The Chariot", "Justice", "The Devil", "The Tower",
            ),
            silver_consumables=("Familiar", "Grim", "Incantation"),
            directed_tarots=(
                "The Magician", "The Empress", "The Hierophant", "The Lovers",
                "The Chariot", "Justice", "The Devil", "The Tower",
            ),
            directed_spectrals=("Familiar", "Grim", "Incantation"),
            preferred_enhancements=(
                "Lucky", "Mult", "Bonus", "Wild", "Steel", "Glass", "Gold", "Stone",
            ),
        ),
        "blue_joker_deck": _strategy(
            "blue_joker_deck",
            "Blue Joker Large-Deck Chips",
            gold_jokers=("Blue Joker",),
            banned_jokers=("Erosion", "Trading Card"),
            silver_consumables=("Familiar", "Grim", "Incantation", "Cryptid"),
            directed_spectrals=("Familiar", "Grim", "Incantation", "Cryptid"),
        ),

        # Section 8: Planet, Tarot and consumable engines.
        "planet_engine": _strategy(
            "planet_engine",
            "Planet Engine",
            silver_jokers=("Astronomer",),
            gold_consumables=("The High Priestess", "Black Hole"),
            gold_planets=ALL_PLANET_NAMES,
            directed_tarots=("The High Priestess",),
            directed_spectrals=("Black Hole",),
        ),
        "planet_constellation": _strategy(
            "planet_constellation",
            "Constellation Planet-Scaling",
            gold_jokers=("Constellation",),
        ),
        "planet_satellite": _strategy(
            "planet_satellite",
            "Satellite Planet-Economy",
            gold_jokers=("Satellite",),
        ),
        "planet_constellation_satellite": _strategy(
            "planet_constellation_satellite",
            "Constellation + Satellite Planet Engine",
        ),
        "perkeo": _strategy("perkeo", "Perkeo Consumable Duplication", gold_jokers=("Perkeo",)),
        "perkeo_observatory": _strategy(
            "perkeo_observatory",
            "Perkeo + Observatory Planet Stack",
        ),
        "perkeo_cryptid": _strategy(
            "perkeo_cryptid",
            "Perkeo + Cryptid Copy Engine",
            gold_consumables=("Cryptid",),
            directed_spectrals=("Cryptid",),
        ),
        "perkeo_tarot_spectral": _strategy(
            "perkeo_tarot_spectral",
            "Perkeo Tarot / Spectral Engine",
        ),
        "tarot_engine": _strategy(
            "tarot_engine",
            "Tarot Engine",
            gold_jokers=("Fortune Teller",),
            silver_consumables=ALL_TAROT_NAMES,
            directed_tarots=ALL_TAROT_NAMES,
        ),
        "tarot_cartomancer": _strategy(
            "tarot_cartomancer",
            "Cartomancer Blind-Select Generation",
            gold_jokers=("Cartomancer",),
        ),
        "tarot_hallucination": _strategy(
            "tarot_hallucination",
            "Hallucination Pack-Open Generation",
            gold_jokers=("Hallucination",),
        ),
        "tarot_eight_ball": _strategy(
            "tarot_eight_ball",
            "8 Ball / Eights Tarot Generation",
            gold_jokers=("8 Ball", "Eight Ball"),
            preferred_ranks=("8",),
        ),
        "vagabond": _strategy(
            "vagabond",
            "Vagabond Low-Money Tarot Engine",
            gold_jokers=("Vagabond",),
            silver_jokers=("Fortune Teller",),
            silver_consumables=ALL_TAROT_NAMES,
            directed_tarots=ALL_TAROT_NAMES,
        ),

        # Section 9: economy, shop, reroll and blind-skip engines.
        "cash_hoard": _strategy(
            "cash_hoard",
            "Cash Hoard / Interest",
            gold_consumables=("The Hermit", "Temperance", "Immolate"),
            directed_tarots=("The Hermit", "Temperance"),
            directed_spectrals=("Immolate",),
        ),
        "cash_growth": _strategy(
            "cash_growth",
            "Rocket / To the Moon Cash Growth",
            gold_jokers=("Rocket", "To the Moon"),
        ),
        "cash_bull": _strategy("cash_bull", "Bull Cash-to-Chips", gold_jokers=("Bull",)),
        "cash_bootstraps": _strategy(
            "cash_bootstraps",
            "Bootstraps Cash-to-Mult",
            gold_jokers=("Bootstraps",),
        ),
        "cash_bull_bootstraps": _strategy(
            "cash_bull_bootstraps",
            "Bull + Bootstraps Cash Scoring",
        ),
        "cash_cloud_nine": _strategy(
            "cash_cloud_nine",
            "Cloud 9 Nines Economy",
            gold_jokers=("Cloud 9",),
            silver_consumables=("Ouija",),
            directed_spectrals=("Ouija",),
            preferred_ranks=("9",),
        ),
        "campfire": _strategy(
            "campfire",
            "Campfire Sell-Scaling",
            gold_jokers=("Campfire",),
            silver_consumables=("Temperance",),
            directed_tarots=("Temperance",),
        ),
        "flash_card": _strategy(
            "flash_card",
            "Flash Card Reroll-Scaling",
            gold_jokers=("Flash Card",),
        ),
        "red_card": _strategy("red_card", "Red Card Pack-Skip Scaling", gold_jokers=("Red Card",)),
        "throwback": _strategy("throwback", "Throwback Blind-Skip Scaling", gold_jokers=("Throwback",)),

        # Section 10: Joker-board composition.
        "joker_stencil": _strategy(
            "joker_stencil",
            "Joker Stencil / Duplication",
            gold_jokers=("Joker Stencil",),
            silver_consumables=("Ankh",),
            directed_spectrals=("Ankh",),
            preferred_editions=("Negative",),
        ),
        "baseball_card": _strategy(
            "baseball_card",
            "Baseball Card Uncommon Stack",
            gold_jokers=("Baseball Card",),
            silver_consumables=("Judgement", "Wraith", "The Soul"),
            directed_tarots=("Judgement",),
            directed_spectrals=("Wraith", "The Soul"),
        ),
        "abstract_joker": _strategy(
            "abstract_joker",
            "Abstract Joker Wide-Board",
            gold_jokers=("Abstract Joker",),
            silver_consumables=("Judgement", "Wraith", "The Soul"),
            directed_tarots=("Judgement",),
            directed_spectrals=("Wraith", "The Soul"),
            preferred_editions=("Negative",),
        ),
        "swashbuckler": _strategy(
            "swashbuckler",
            "Egg / Gift-Card Swashbuckler",
            gold_jokers=("Swashbuckler",),
            silver_consumables=("Judgement", "Wraith", "The Soul"),
            directed_tarots=("Judgement",),
            directed_spectrals=("Wraith", "The Soul"),
        ),

        # Section 11: discard and hand rotation.
        "discard_utilization": _strategy("discard_utilization", "Discard Utilization"),
        "discard_castle": _strategy(
            "discard_castle",
            "Castle Suit-Discard Scaling",
            gold_jokers=("Castle",),
            silver_consumables=("The Star", "The Moon", "The Sun", "The World", "Sigil"),
            directed_tarots=("The Star", "The Moon", "The Sun", "The World"),
            directed_spectrals=("Sigil",),
            preferred_enhancements=("Wild",),
        ),
        "discard_mail_rebate": _strategy(
            "discard_mail_rebate",
            "Mail-In Rebate Rank-Discard Economy",
            gold_jokers=("Mail-In Rebate",),
            silver_consumables=("Strength", "Death", "Ouija"),
            directed_tarots=("Strength", "Death"),
            directed_spectrals=("Ouija",),
        ),
        "discard_yorick": _strategy(
            "discard_yorick",
            "Yorick Discard-Scaling",
            gold_jokers=("Yorick",),
            silver_consumables=("Medium",),
            directed_spectrals=("Medium",),
        ),
        "no_discard": _strategy("no_discard", "No-Discard / Discard-Preservation"),
        "no_discard_green": _strategy(
            "no_discard_green",
            "Green Joker No-Discard Scaling",
            gold_jokers=("Green Joker",),
        ),
        "no_discard_reserve": _strategy(
            "no_discard_reserve",
            "Banner + Delayed Gratification Discard Reserve",
            gold_jokers=("Banner", "Delayed Gratification"),
        ),
        "no_discard_ramen": _strategy(
            "no_discard_ramen",
            "Ramen Preservation",
            gold_jokers=("Ramen",),
        ),
        "no_discard_burglar": _strategy(
            "no_discard_burglar",
            "Burglar Zero-Discard / Extra-Hand",
            gold_jokers=("Burglar",),
        ),
        "obelisk_rotation": _strategy(
            "obelisk_rotation",
            "Obelisk Hand-Rotation",
            gold_jokers=("Obelisk",),
        ),
        "burnt_joker_engine": _strategy(
            "burnt_joker_engine",
            "Burnt Joker Hand-Level Engine",
            gold_jokers=("Burnt Joker",),
            silver_jokers=("Astronomer",),
            gold_consumables=("Black Hole",),
            silver_planets=ALL_PLANET_NAMES,
            directed_spectrals=("Black Hole",),
        ),

        # Section 12: hand scheduling.
        "last_hand_burst": _strategy("last_hand_burst", "Last-Hand Burst"),
        "last_hand_acrobat": _strategy(
            "last_hand_acrobat",
            "Acrobat Last-Hand XMult",
            gold_jokers=("Acrobat",),
        ),
        "last_hand_dusk": _strategy(
            "last_hand_dusk",
            "Dusk Last-Hand Retrigger",
            gold_jokers=("Dusk",),
        ),
        "loyalty_cycle": _strategy(
            "loyalty_cycle",
            "Loyalty Card Six-Hand Cycle",
            gold_jokers=("Loyalty Card",),
        ),
    }


_tree_definitions = dict(UNIVERSAL_BALATRO_STRATEGIES)
for _strategy_id in SECTION_ONE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_TWO_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_THREE_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in SECTION_FOUR_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
for _strategy_id in REMAINING_SECTION_ROOT_IDS:
    _tree_definitions.pop(_strategy_id, None)
# Editions are portable item value, not a strategy branch.  The former flat
# ``edition`` definition is intentionally retired during the final migration.
_tree_definitions.pop("edition", None)
_tree_definitions.update(_section_one_definitions())
_tree_definitions.update(_section_two_definitions())
_tree_definitions.update(_section_three_definitions())
_tree_definitions.update(_section_four_definitions())
_tree_definitions.update(_remaining_section_definitions())

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
    StrategyNodeSpec("stone", "Stone"),
    StrategyNodeSpec("stone_marble_scaling", "Marble Joker + Stone Joker Scaling", parent_strategy_id="stone"),
    StrategyNodeSpec("stone_marble_vampire", "Marble Joker + Vampire Stone Feed", parent_strategy_id="stone"),
    StrategyNodeSpec("stone_dna_duplication", "DNA + Stone Joker Duplication", parent_strategy_id="stone"),
    StrategyNodeSpec("stone_high_card", "Stone High Card", parent_strategy_id="stone"),
    StrategyNodeSpec("glass", "Glass"),
    StrategyNodeSpec("glass_breakage", "Glass Joker Breakage Scaling", parent_strategy_id="glass"),
    StrategyNodeSpec("glass_retrigger", "Glass Retrigger Scoring", parent_strategy_id="glass"),
    StrategyNodeSpec("steel", "Steel"),
    StrategyNodeSpec("steel_density", "Steel Joker Density Scaling", parent_strategy_id="steel"),
    StrategyNodeSpec("steel_mime", "Mime Steel Retrigger", parent_strategy_id="steel"),
    StrategyNodeSpec("lucky", "Lucky"),
    StrategyNodeSpec("lucky_cat", "Lucky Cat Scaling", parent_strategy_id="lucky"),
    StrategyNodeSpec("lucky_cat_oops", "Lucky Cat + Oops! All 6s", parent_strategy_id="lucky"),
    StrategyNodeSpec("lucky_retrigger", "Lucky Retrigger", parent_strategy_id="lucky"),
    StrategyNodeSpec("gold_cards", "Gold Cards"),
    StrategyNodeSpec("gold_cards_held_mime", "Held Gold + Mime Economy", parent_strategy_id="gold_cards"),
    StrategyNodeSpec("gold_cards_ticket", "Golden Ticket Gold Scoring", parent_strategy_id="gold_cards"),
    StrategyNodeSpec("gold_cards_midas", "Midas Mask Gold Generation", parent_strategy_id="gold_cards"),
    StrategyNodeSpec("gold_cards_midas_ticket", "Midas Mask + Golden Ticket Economy", parent_strategy_id="gold_cards"),
]
_runtime_nodes.extend(
    StrategyNodeSpec(strategy_id, name, parent_strategy_id=parent_id)
    for strategy_id, name, parent_id in (
        # Section 5.
        ("red_seal", "Red Seal", None),
        ("red_seal_played", "Played Red-Seal Retrigger", "red_seal"),
        ("red_seal_held", "Held Red-Seal Retrigger", "red_seal"),
        ("blue_seal", "Blue Seal Hand-Level Scaling", None),
        ("purple_seal", "Purple Seal Tarot Engine", None),
        ("gold_seal", "Gold-Seal Retrigger Economy", None),
        # Section 6.
        ("canio_destruction", "Canio Destruction", None),
        ("canio_trading", "Trading Card Canio", "canio_destruction"),
        ("canio_pareidolia", "Pareidolia Canio", "canio_destruction"),
        ("canio_glass", "Glass Canio", "canio_destruction"),
        ("canio_consumable", "Consumable Canio", "canio_destruction"),
        ("vampire", "Vampire", None),
        ("vampire_midas", "Midas Mask + Vampire", "vampire"),
        (
            "vampire_pareidolia_midas",
            "Pareidolia + Midas Mask + Vampire",
            "vampire",
        ),
        ("dagger_sacrifice", "Ceremonial Dagger / Disposable-Joker Feed", None),
        ("madness", "Madness Destruction", None),
        ("madness_solo", "Solo Madness", "madness"),
        ("madness_eternal", "Eternal-Joker Madness", "madness"),
        ("deck_thinning", "Deck Thinning", None),
        ("thinning_trading", "Trading Card Thinning / Economy", "deck_thinning"),
        ("thinning_erosion", "Erosion Thinning", "deck_thinning"),
        ("thinning_trading_erosion", "Trading Card + Erosion", "deck_thinning"),
        # Section 7.
        ("hologram_growth", "Hologram Deck-Growth", None),
        ("hologram_dna", "DNA + Hologram", "hologram_growth"),
        ("hologram_certificate", "Certificate + Hologram", "hologram_growth"),
        ("hologram_marble", "Marble Joker + Hologram", "hologram_growth"),
        ("hiker_training", "Hiker Retrigger / Copy Training", None),
        ("drivers_license", "Driver's License Enhancement-Density", None),
        ("blue_joker_deck", "Blue Joker Large-Deck Chips", None),
        # Section 8.
        ("planet_engine", "Planet Engine", None),
        ("planet_constellation", "Constellation Planet-Scaling", "planet_engine"),
        ("planet_satellite", "Satellite Planet-Economy", "planet_engine"),
        (
            "planet_constellation_satellite",
            "Constellation + Satellite Planet Engine",
            "planet_engine",
        ),
        ("perkeo", "Perkeo Consumable Duplication", None),
        ("perkeo_observatory", "Perkeo + Observatory Planet Stack", "perkeo"),
        ("perkeo_cryptid", "Perkeo + Cryptid Copy Engine", "perkeo"),
        ("perkeo_tarot_spectral", "Perkeo Tarot / Spectral Engine", "perkeo"),
        ("tarot_engine", "Tarot Engine", None),
        ("tarot_cartomancer", "Cartomancer Blind-Select Generation", "tarot_engine"),
        ("tarot_hallucination", "Hallucination Pack-Open Generation", "tarot_engine"),
        ("tarot_eight_ball", "8 Ball / Eights Tarot Generation", "tarot_engine"),
        ("vagabond", "Vagabond Low-Money Tarot Engine", None),
        # Section 9.
        ("cash_hoard", "Cash Hoard / Interest", None),
        ("cash_growth", "Rocket / To the Moon Cash Growth", "cash_hoard"),
        ("cash_bull", "Bull Cash-to-Chips", "cash_hoard"),
        ("cash_bootstraps", "Bootstraps Cash-to-Mult", "cash_hoard"),
        ("cash_bull_bootstraps", "Bull + Bootstraps Cash Scoring", "cash_hoard"),
        ("cash_cloud_nine", "Cloud 9 Nines Economy", "cash_hoard"),
        ("campfire", "Campfire Sell-Scaling", None),
        ("flash_card", "Flash Card Reroll-Scaling", None),
        ("red_card", "Red Card Pack-Skip Scaling", None),
        ("throwback", "Throwback Blind-Skip Scaling", None),
        # Section 10.
        ("joker_stencil", "Joker Stencil / Duplication", None),
        ("baseball_card", "Baseball Card Uncommon Stack", None),
        ("abstract_joker", "Abstract Joker Wide-Board", None),
        ("swashbuckler", "Egg / Gift-Card Swashbuckler", None),
        # Section 11.
        ("discard_utilization", "Discard Utilization", None),
        ("discard_castle", "Castle Suit-Discard Scaling", "discard_utilization"),
        (
            "discard_mail_rebate",
            "Mail-In Rebate Rank-Discard Economy",
            "discard_utilization",
        ),
        ("discard_yorick", "Yorick Discard-Scaling", "discard_utilization"),
        ("no_discard", "No-Discard / Discard-Preservation", None),
        ("no_discard_green", "Green Joker No-Discard Scaling", "no_discard"),
        (
            "no_discard_reserve",
            "Banner + Delayed Gratification Discard Reserve",
            "no_discard",
        ),
        ("no_discard_ramen", "Ramen Preservation", "no_discard"),
        ("no_discard_burglar", "Burglar Zero-Discard / Extra-Hand", "no_discard"),
        ("obelisk_rotation", "Obelisk Hand-Rotation", None),
        ("burnt_joker_engine", "Burnt Joker Hand-Level Engine", None),
        # Section 12.
        ("last_hand_burst", "Last-Hand Burst", None),
        ("last_hand_acrobat", "Acrobat Last-Hand XMult", "last_hand_burst"),
        ("last_hand_dusk", "Dusk Last-Hand Retrigger", "last_hand_burst"),
        ("loyalty_cycle", "Loyalty Card Six-Hand Cycle", None),
    )
)
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
        *SECTION_FOUR_NODE_IDS,
        *REMAINING_SECTION_NODE_IDS,
    }
)

TREE_MIGRATED_BALATRO_STRATEGY_TOPOLOGY = StrategyTopology(_runtime_nodes)
