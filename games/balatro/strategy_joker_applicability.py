from __future__ import annotations


UNIVERSAL = "UNIVERSAL"
ALIGNED = "ALIGNED"
PIVOT = "PIVOT"
OFF_PATH = "OFF_PATH"
CONFLICT = "CONFLICT"
NEUTRAL_APPLICABILITY = "NEUTRAL"


def _normalize(value: object) -> str:
    return "".join(character for character in str(value).lower() if character.isalnum())


def joker_tokens(item: object) -> frozenset[str]:
    """Return every stable public token by which a Joker may be identified."""

    values = (
        type(item).__name__,
        getattr(item, "name", ""),
        getattr(item, "label", ""),
        getattr(item, "key", ""),
        getattr(item, "center", ""),
    )
    return frozenset(token for value in values if (token := _normalize(value)))


def _joker_names(*values: str) -> frozenset[str]:
    normalized = {_normalize(value) for value in values}
    return frozenset(
        {
            *normalized,
            *(f"{value}joker" for value in normalized if not value.endswith("joker")),
        }
    )


# A positive strategy mapping is evidence about *where* a Joker is strongest. It
# must not automatically imply exclusivity: Bull, Cloud 9, Misprint, and many other
# ordinary value engines remain useful across unrelated hand plans. Only Jokers
# whose trigger or enabling rule actually requires a particular hand shape, rank,
# suit, face/held shell, or card-property shell pay the off-path opportunity cost.
#
# Explicit BANNED relationships remain conflicts regardless of this set. This list
# therefore answers only whether an otherwise-positive mapping is route-bound.
STRATEGY_BOUND_JOKERS = _joker_names(
    # Poker-hand requirements and hand-specific enablers.
    "Jolly Joker",
    "Sly Joker",
    "Mad Joker",
    "Clever Joker",
    "Zany Joker",
    "Wily Joker",
    "Crazy Joker",
    "Devious Joker",
    "Droll Joker",
    "Crafty Joker",
    "The Duo",
    "The Trio",
    "The Family",
    "The Order",
    "The Tribe",
    "Half Joker",
    "Square Joker",
    "Runner",
    "Four Fingers",
    "Shortcut",
    "Superposition",
    "Seance",
    "Spare Trousers",
    # Rank-specific triggers and rank shells.
    "Scholar",
    "Fibonacci",
    "Hack",
    "Odd Todd",
    "Even Steven",
    "Wee Joker",
    "Walkie Talkie",
    "Sixth Sense",
    "8 Ball",
    "Hit the Road",
    "Shoot the Moon",
    "The Idol",
    # Suit-specific triggers and suit/flush enablers.
    "Greedy Joker",
    "Lusty Joker",
    "Wrathful Joker",
    "Gluttonous Joker",
    "Rough Gem",
    "Bloodstone",
    "Onyx Agate",
    "Arrowhead",
    "Seeing Double",
    "Ancient Joker",
    "Castle",
    "Blackboard",
    "Flower Pot",
    "Smeared Joker",
    # Face-card and held-card shells.
    "Baron",
    "Mime",
    "Photograph",
    "Triboulet",
    "Sock and Buskin",
    "Pareidolia",
    "Scary Face",
    "Smiley Face",
    "Business Card",
    "Midas Mask",
    "Reserved Parking",
    "Raised Fist",
    "Faceless Joker",
    "Ride the Bus",
    # Enhancement/property-dependent engines.
    "Glass Joker",
    "Steel Joker",
    "Stone Joker",
    "Marble Joker",
    "Lucky Cat",
    "Golden Ticket",
    "Vampire",
    "Driver's License",
    "Oops! All 6s",
)


def joker_is_strategy_bound(item: object) -> bool:
    """Return whether a positive strategy mapping is exclusive enough to punish."""

    return bool(joker_tokens(item) & STRATEGY_BOUND_JOKERS)
